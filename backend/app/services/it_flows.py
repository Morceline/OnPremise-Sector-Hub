"""
services/it_flows.py
----------------------
Atendimento de TI guiado: o bot descobre o problema com perguntas curtas, com
botões de resposta, e só então sugere um teste simples. Cada passo tem uma
pergunta por vez; o colaborador nunca recebe uma lista longa para ler.

Estrutura de cada nó:
- question: pergunta com opções; cada opção leva a outro nó.
- advice:   um teste simples (no máximo 2 passos) com "Resolveu" / "Não resolveu".
- escalate:  não resolveu; orienta quem chamar e o que dizer.
- end:       problema resolvido.
- menu:      escolha do tema.
- ask_text:  pessoa descreve o problema com as próprias palavras.

Opção "next" pode ser um id de nó, ou "start:<tema>" para abrir um tema.
Este conteúdo pode ser trocado por setor sem mudar o código.
"""

import re
from typing import Optional

from app.services.it_topics import SAFETY_KEYWORDS, SAFETY_TEXT
from app.services.query_normalizer import normalize

FIM = "fim"
MENU = "menu"


def _q(text, options):
    return {"kind": "question", "text": text, "options": options}


def _adv(text, steps, se_nao_resolver):
    return {"kind": "advice", "text": text, "steps": steps,
            "options": [("Resolveu", FIM), ("Não resolveu", se_nao_resolver)]}


def _ref(steps):
    return {"kind": "reference", "text": "Aqui estão os atalhos.", "steps": steps,
            "options": [("Ver outro atalho", "atalhos_0"), ("Começar de novo", MENU)]}


def _esc(text):
    return {"kind": "escalate", "text": text, "options": [("Começar de novo", MENU)]}


NODES = {
    FIM: {"kind": "end", "text": "Que bom que resolveu! Se voltar a acontecer, é só começar de novo.",
          "options": [("Começar de novo", MENU)]},
    MENU: {"kind": "menu",
           "text": "Qual é o problema?",
           "options": [("Impressora", "start:impressora"), ("Internet ou Wi-Fi", "start:rede"),
                       ("Teclado, mouse ou monitor", "start:perifericos"),
                       ("Computador lento ou travado", "start:sistema"), ("Atalhos do teclado", "start:atalhos"),
                       ("Outro problema", "outro")]},
    "outro": {"kind": "ask_text", "text": "Descreva o problema com as suas palavras.",
              "options": []},

    # ---------------- Impressora
    "imp_0": _q("Aparece alguma mensagem na tela do computador, onde você mandou imprimir?",
                [("Sim, uma mensagem de erro", "imp_pc_msg"), ("Não", "imp_visor")]),
    "imp_pc_msg": _q("Qual é a mensagem?", [("Falta de papel ou de tinta", "imp_papel"),
                                             ("Tipo ou tamanho de papel", "imp_tipo"),
                                             ("Outra mensagem", "imp_texto")]),
    "imp_texto": {"kind": "ask_text", "text": "Digite a mensagem que aparece na tela.", "options": [],
                  "free_routes": [(["tipo", "tamanho", "formato", "bandeja"], "imp_tipo"),
                                  (["papel", "tinta", "toner", "cartucho", "acabou"], "imp_papel"),
                                  (["localizar", "encontrar", "nao foi possivel", "nao encontr", "offline", "conex", "rede"],
                                   "imp_rede")],
                  "fallback": "imp_rede"},
    "imp_tipo": _adv("Na tela de impressão do computador, confira se o tamanho e o tipo de papel são iguais aos da bandeja. "
                     "Depois mande imprimir de novo.", [], "imp_msg"),
    "imp_visor": _q("O que aparece no visor da impressora?", [("Uma mensagem de erro", "imp_visor_texto"),
                                                              ("A tela está apagada", "imp_liga"),
                                                              ("Está tudo normal", "imp_rede")]),
    "imp_visor_texto": {"kind": "ask_text", "text": "Digite a mensagem do visor da impressora.", "options": [],
                        "free_routes": [(["papel", "tinta", "toner", "cartucho"], "imp_papel"),
                                        (["preso", "atolado", "emperrad"], "imp_papel")],
                        "fallback": "imp_msg"},
    "imp_liga": _adv("Confira se o cabo de força está na tomada e aperte o botão de ligar. Espere a luz parar de piscar.",
                     [], "imp_rede"),
    "imp_rede": _q("Ela aparece na lista de impressoras do seu computador?",
                   [("Não aparece", "imp_conecta"), ("Aparece", "imp_fila")]),
    "imp_conecta": _adv("Confira o cabo USB ou o cabo de rede, dos dois lados, até encaixar bem.", [], "imp_reinicia"),
    "imp_reinicia": _esc("Ela continua sem aparecer no seu computador. Chame a TI e diga que você já conferiu a energia e o cabo."),
    "imp_papel": _adv("Confira se há papel na bandeja e se a tinta ou o toner não acabou. Se houver papel preso, puxe devagar, sem forçar.",
                      ["Depois, feche as tampas até ouvir o clique."], "imp_msg"),
    "imp_msg": _adv("Desligue a impressora da tomada, espere 10 segundos e ligue de novo.", [], "imp_msg_esc"),
    "imp_msg_esc": _esc("Anote a mensagem exata do visor e chame a TI com ela."),
    "imp_fila": _adv("Pode haver um documento parado na fila. Abra a lista de impressão, cancele os documentos parados e mande imprimir de novo.",
                     [], "imp_outro_pc"),
    "imp_outro_pc": _q("A impressora imprime quando outra pessoa do setor manda um documento?",
                       [("Sim", "imp_pc"), ("Não", "imp_esc_setor")]),
    "imp_pc": _esc("O problema parece estar só no seu computador. Chame a TI e diga que a impressora funciona para os outros."),
    "imp_esc_setor": _esc("A impressora parece parada para todos. Chame a TI e diga que ela não imprime para ninguém do setor."),

    # ---------------- Atalhos do teclado (referência)
    "atalhos_0": _q("Qual tipo de atalho você procura?", [
        ("Janelas e área de trabalho", "atj_janelas"), ("Arquivos e Explorador", "atj_arquivos"),
        ("Sistema e tela", "atj_sistema"), ("Edição e texto", "atj_texto"),
        ("Navegador (abas e páginas)", "atj_nav"), ("Captura de tela", "atj_print"),
        ("Desfazer e refazer", "atj_desfazer"), ("Copiar, colar e recortar", "atj_copiar"),
        ("Outros úteis", "atj_outros")]),
    "atj_janelas": _ref([
        "Mostrar a área de trabalho: Windows + D",
        "Minimizar todas as janelas: Windows + M (restaurar: Windows + Shift + M)",
        "Trocar de janela: Alt + Tab",
        "Ver todas as janelas abertas: Windows + Tab",
        "Maximizar a janela atual: Windows + seta para cima",
        "Minimizar ou restaurar a janela atual: Windows + seta para baixo",
        "Abrir um programa fixado na barra de tarefas: Windows + número (1 a 9)",
        "Bloquear o computador: Windows + L"]),
    "atj_arquivos": _ref([
        "Abrir o Explorador de Arquivos: Windows + E",
        "Pesquisar dentro do Explorador: Ctrl + E",
        "Renomear o item selecionado: F2",
        "Mandar o item para a lixeira: Delete",
        "Criar uma nova pasta dentro do Explorador: Ctrl + Shift + N",
        "Ver as propriedades do item selecionado: Alt + Enter"]),
    "atj_sistema": _ref([
        "Abrir o Gerenciador de Tarefas: Ctrl + Shift + Esc",
        "Abrir a tela de segurança (bloquear, trocar de usuário, sair): Ctrl + Alt + Delete",
        "Abrir as Configurações do Windows: Windows + I",
        "Abrir a caixa Executar: Windows + R",
        "Escolher como a tela é exibida ou projetada (monitor extra): Windows + P",
        "Abrir o menu de atalhos do sistema: Windows + X"]),
    "atj_texto": _ref([
        "Selecionar uma linha inteira: clique três vezes seguidas",
        "Selecionar tudo: Ctrl + A",
        "Negrito: Ctrl + B",
        "Ir para o início ou o fim do documento: Ctrl + Home e Ctrl + End",
        "Imprimir: Ctrl + P",
        "Salvar: Ctrl + S",
        "Pular para o próximo campo: Tab (voltar: Shift + Tab)"]),
    "atj_nav": _ref([
        "Nova aba: Ctrl + T",
        "Fechar a aba: Ctrl + W",
        "Voltar e avançar na página: Alt + seta para a esquerda e Alt + seta para a direita",
        "Janela anônima (privada): Ctrl + Shift + N no Chrome e no Edge; Ctrl + Shift + P no Firefox",
        "Ver o histórico: Ctrl + H",
        "Ver os downloads: Ctrl + J (Chrome e Edge)",
        "Atualizar a página: F5"]),
    "atj_print": _ref([
        "Copiar a tela inteira: tecla Print Screen (PrtSc)",
        "Escolher uma parte da tela para copiar: Windows + Shift + S"]),
    "atj_desfazer": _ref(["Desfazer a última ação: Ctrl + Z", "Refazer a ação desfeita: Ctrl + Y"]),
    "atj_copiar": _ref(["Copiar: Ctrl + C", "Colar: Ctrl + V", "Recortar: Ctrl + X"]),
    "atj_outros": _ref(["Fechar uma caixa ou cancelar: Esc",
                        "Procurar uma palavra na página ou no documento: Ctrl + F",
                        "Fechar o programa ativo: Alt + F4 (salve antes, se der tempo)",
                        "Mostrar ou esconder a barra de notificações: Windows + A"]),

    # ---------------- Apito de equipamento
    "alarme_0": _q("Quem está apitando?", [("A impressora", "alarme_imp"), ("O nobreak (a caixa da energia)", "alarme_nobreak"),
                                            ("Outro aparelho", "alarme_outro")]),
    "alarme_imp": _adv("Apito de impressora costuma indicar um aviso. Olhe o visor e confira papel, tinta e se as tampas estão fechadas.",
                       [], "alarme_imp_texto"),
    "alarme_imp_texto": {"kind": "ask_text", "text": "Qual mensagem aparece no visor?", "options": [],
                         "free_routes": [(["papel", "tinta", "toner", "cartucho"], "imp_papel"),
                                         (["preso", "atolado", "emperrad"], "imp_papel")],
                         "fallback": "alarme_imp_esc"},
    "alarme_imp_esc": _esc("Anote a mensagem do visor e chame a TI com ela."),
    "alarme_nobreak": _adv("Apito de nobreak geralmente indica bateria fraca ou energia instável. Não desligue o equipamento "
                           "sozinho e não troque a bateria.", ["Se o apito continuar, veja se há luz vermelha no painel."],
                           "alarme_nobreak_esc"),
    "alarme_nobreak_esc": _esc("Avise a TI agora para verificar o nobreak. Se sentir cheiro de queimado, desligue da tomada e "
                               "afaste as pessoas."),
    "alarme_outro": _esc("Chame a TI e diga qual aparelho está apitando e o que aparece nele."),

    # ---------------- Computador não liga
    "nl_0": _q("O computador não liga de jeito nenhum, ou liga e desliga sozinho?",
               [("Não liga de jeito nenhum", "nl_tomada"), ("Liga e desliga sozinho", "nl_esc")]),
    "nl_tomada": _adv("Confira se o cabo de força está bem encaixado no computador e na tomada, e se a tomada tem energia.",
                      ["Teste a tomada com outro aparelho, como um abajur."], "nl_tela"),
    "nl_tela": _q("Ao apertar o botão de ligar, aparece alguma luz ou imagem?",
                  [("Sim, alguma luz ou imagem", "nl_monitor"), ("Não, nada", "nl_esc")]),
    "nl_monitor": _adv("Se a luz do computador acende mas a tela não mostra nada, confira o cabo que liga o monitor.", [],
                       "nl_esc"),
    "nl_esc": _esc("Chame a TI e diga o que acontece quando você aperta o botão de ligar. Não abra o gabinete."),

    # ---------------- Periféricos
    "per_0": _q("O que parou de funcionar?", [("Teclado ou mouse", "per_tipo"), ("Monitor (a tela)", "per_mon")]),
    "per_tipo": _q("O aparelho tem fio ou é sem fio?", [("Tem fio", "per_fio_1"), ("É sem fio", "per_sem_1")]),
    "per_fio_1": _adv("Encaixe o cabo na entrada USB do computador até ouvir o clique.", [], "per_fio_2"),
    "per_fio_2": _adv("Troque para outra entrada USB do computador.", [], "per_fio_esc"),
    "per_fio_esc": _esc("Peça à TI para verificar ou trocar o aparelho. Diga qual aparelho e o que você já tentou."),
    "per_sem_1": _adv("Troque as pilhas por novas, ou carregue o aparelho.", [], "per_sem_2"),
    "per_sem_2": _adv("Se houver um receptor pequeno ligado ao computador, tire e encaixe de novo.", [], "per_sem_esc"),
    "per_sem_esc": _esc("Peça à TI para verificar ou trocar o aparelho. Diga qual aparelho e o que você já tentou."),
    "per_mon": _q("A luz do monitor está acesa?", [("Não está acesa", "per_mon_liga"), ("Está acesa, mas sem imagem", "per_mon_cabo")]),
    "per_mon_liga": _adv("Confira se o monitor está ligado na tomada e se o botão de ligar foi apertado.", [], "per_mon_cabo"),
    "per_mon_cabo": _adv("Confira o cabo que liga o monitor ao computador. Aperte as duas pontas até encaixar bem.", [],
                         "per_mon_esc"),
    "per_mon_esc": _esc("Peça à TI para verificar ou trocar o monitor. Diga o que você já tentou."),

    # ---------------- Internet e Wi-Fi
    "rede_0": _q("No canto da tela, perto do relógio, o ícone da internet aparece com um X vermelho ou com aviso de sem acesso?",
                 [("Sim", "rede_tipo"), ("Não, parece normal", "rede_site")]),
    "rede_tipo": _q("Você usa cabo ou Wi-Fi?", [("Cabo", "rede_cabo"), ("Wi-Fi", "rede_wifi")]),
    "rede_cabo": _adv("Confira o cabo de rede no computador e na tomada da parede. O encaixe deve fazer um clique.", [],
                      "rede_reinicia"),
    "rede_wifi": _adv("Confira se o Wi-Fi está ligado e se a rede correta do órgão está escolhida.", [], "rede_reinicia"),
    "rede_reinicia": _adv("Reinicie o computador e espere o ícone da internet voltar ao normal.", [], "rede_vizinhos"),
    "rede_vizinhos": _q("Os colegas perto de você também estão sem internet?",
                        [("Sim", "rede_setor"), ("Não, só eu", "rede_pc")]),
    "rede_setor": _esc("Pode ser a rede do setor. Chame a TI ou a equipe de rede e diga que vários computadores estão sem internet."),
    "rede_pc": _esc("Chame a TI e diga que a internet não funciona só no seu computador."),
    "rede_site": _q("Você consegue abrir outros sites?", [("Não", "rede_reinicia"), ("Sim", "rede_sistema")]),
    "rede_sistema": _adv("A internet funciona. O problema parece estar em um sistema específico. Volte ao início e escolha "
                         "'Computador lento ou travado'.", [], "rede_sistema_esc"),
    "rede_sistema_esc": _esc("Se o sistema continuar fora do ar, chame a TI e diga qual sistema é."),

    # ---------------- Computador lento ou travado (sistema e sites)
    "sis_0": _q("O que está acontecendo?", [("A página não carrega ou dá erro", "sis_pagina"),
                                             ("O computador está lento ou travado", "sis_lento")]),
    "sis_pagina": _q("Acontece com outros colegas também?", [("Sim", "sis_fora"), ("Não, só comigo", "sis_atualiza")]),
    "sis_fora": _esc("Pode ser o sistema fora do ar para todos. Chame a TI e diga qual sistema não abre."),
    "sis_atualiza": _adv("Atualize a página apertando a tecla F5. Se não resolver, feche e abra o navegador de novo.", [],
                         "sis_rede"),
    "sis_rede": _esc("Se nenhum site abre, o problema pode ser a internet. Veja a dúvida de internet ou chame a TI."),
    "sis_lento": _q("O mouse ainda se move?", [("Sim, só está lento", "sis_fecha"), ("Não, travou de vez", "sis_forca")]),
    "sis_fecha": _adv("Feche os programas e as abas que você não está usando.", [], "sis_reinicia"),
    "sis_forca": _adv("Se der tempo, salve o que estiver aberto. Depois, segure o botão de ligar até o computador desligar, "
                      "espere 5 segundos e ligue de novo.", [], "sis_reinicia"),
    "sis_reinicia": _esc("Se continuar lento, chame a TI e diga quando começou e quais programas estavam abertos."),

    # ---------------- Pasta da equipe
    "pas_0": _q("Você consegue abrir outros sites na internet?", [("Não", "rede_0"), ("Sim", "pas_colegas")]),
    "pas_colegas": _q("Outros colegas também não conseguem abrir a pasta da equipe?",
                      [("Sim", "pas_urgente"), ("Não, só eu", "pas_tenta")]),
    "pas_tenta": _adv("Feche a janela da pasta e abra de novo pelo atalho. Se não abrir, reinicie o computador.", [],
                      "pas_pc"),
    "pas_urgente": _esc("Chame a TI com urgência e diga que a pasta da equipe não abre para ninguém."),
    "pas_pc": _esc("Chame a TI e diga que a pasta não abre só no seu computador."),

    # ---------------- Planilha
    "pla_0": _q("O que acontece na planilha?", [("Uma fórmula mostra erro, como #VALOR!", "pla_formula"),
                                                 ("Os números não somam, parecem texto", "pla_texto"),
                                                 ("Não abre ou perdi dados", "pla_arquivo")]),
    "pla_formula": _adv("Confira se a célula da fórmula não tem letras ou espaços onde deveria haver número. Se mudou algo, "
                        "aperte Ctrl e Z para desfazer.", [], "pla_pede_ajuda"),
    "pla_texto": _adv("Selecione as células e troque o formato para Número no menu de formatação. Digite os valores de novo.",
                      [], "pla_pede_ajuda"),
    "pla_arquivo": _esc("Não salve por cima. Avise a TI ou quem cuida da planilha, e diga qual arquivo é."),
    "pla_pede_ajuda": _esc("Peça ajuda a quem cuida da planilha, mostrando a célula com problema."),

    # ---------------- Áudio
    "aud_0": _q("O som não sai de nada, ou só de um programa?", [("De nada", "aud_volume"), ("Só de um programa", "aud_programa")]),
    "aud_volume": _adv("Confira o ícone de volume, perto do relógio. Aumente e tire o mudo.", [], "aud_saida"),
    "aud_saida": _q("Você usa fone ou caixa de som?", [("Fone", "aud_fone"), ("Caixa de som", "aud_caixa")]),
    "aud_fone": _adv("Desconecte o fone e encaixe de novo, em outra entrada. Se tiver outro fone, teste com ele.", [], "aud_esc"),
    "aud_caixa": _adv("Confira se a caixa está ligada na tomada e no computador, e se o volume dela está alto.", [], "aud_esc"),
    "aud_programa": _adv("O problema está no programa. Feche e abra o programa de novo, e confira o volume dentro dele.", [],
                         "aud_esc"),
    "aud_esc": _esc("Peça à TI para verificar o aparelho de som."),

    # ---------------- Uso básico
    "bas_0": _q("O que você quer fazer?", [("Salvar um arquivo", "bas_salvar"), ("Encontrar um arquivo que sumiu", "bas_achar"),
                                             ("Outra coisa", "bas_outro")]),
    "bas_salvar": _adv("Use Arquivo e depois Salvar, ou aperte Ctrl e S. Escolha a pasta da equipe e dê um nome ao arquivo.", [],
                       "bas_outro"),
    "bas_achar": _adv("Abra o explorador de arquivos (o ícone de pasta na barra). Procure pelo nome do arquivo na caixa de busca, "
                      "no canto superior direito.", [], "bas_outro"),
    "bas_outro": _esc("A TI pode ensinar passo a passo em poucos minutos. Chame a TI e diga o que você quer fazer."),
}

NODES["seguranca"] = {"kind": "escalate", "text": SAFETY_TEXT, "options": [("Começar de novo", MENU)]}
NODES["nao_entendi"] = {
    "kind": "question",
    "text": "Não consegui entender o problema. Escolha um destes assuntos, ou tente descrever de outro jeito.",
    "options": [("Impressora", "start:impressora"), ("Internet ou Wi-Fi", "start:rede"),
                ("Teclado, mouse ou monitor", "start:perifericos"), ("Computador lento ou travado", "start:sistema"),
                ("Outro problema", "outro")],
}

FLOW_START = {
    "impressora": "imp_0", "perifericos": "per_0", "rede": "rede_0", "sistema": "sis_0",
    "pasta": "pas_0", "planilha": "pla_0", "audio": "aud_0", "basico": "bas_0",
    "alarme": "alarme_0", "nao_liga": "nl_0", "atalhos": "atalhos_0",
}

# Palavras que levam a um tema, usadas quando a pessoa descreve o problema.
FLOW_KEYWORDS = {
    "atalhos": ["atalho", "ctrl", "atalhos"],
    "alarme": ["apitando", "apita", "apito", "bipando", "alarme", "bipe", "beep"],
    "nao_liga": ["nao liga", "nao da sinal", "nao acende", "desliga sozinho"],
    "impressora": ["impressora", "imprimir", "imprime", "impressao", "toner", "tinta"],
    "perifericos": ["mouse", "teclado", "monitor", "tela preta", "sem imagem", "sem sinal"],
    "rede": ["internet", "rede", "wifi", "wi-fi", "sem conexao", "sem acesso"],
    "sistema": ["lento", "lentidao", "travou", "travado", "trava", "navegador", "pagina", "site", "carregar", "fora do ar"],
    "pasta": ["pasta", "compartilhada", "arquivos da equipe", "servidor"],
    "planilha": ["planilha", "excel", "formula", "celula"],
    "audio": ["som", "audio", "caixa de som", "fone", "volume", "mudo"],
    "basico": ["como salvar", "area de trabalho", "ligar o computador", "desligar o computador"],
}


def _payload(node_id: str) -> dict:
    node = NODES[node_id]
    return {
        "node_id": node_id,
        "kind": node["kind"],
        "text": node["text"],
        "steps": node.get("steps", []),
        "options": [label for label, _ in node.get("options", [])],
    }


def menu() -> dict:
    return _payload(MENU)


def start(flow_id: str) -> Optional[dict]:
    if flow_id not in FLOW_START:
        return None
    return _payload(FLOW_START[flow_id])


def step(node_id: str, option: int) -> Optional[dict]:
    """Avança a partir de um nó, pela opção escolhida (índice)."""
    node = NODES.get(node_id)
    if node is None or not (0 <= option < len(node.get("options", []))):
        return None
    _, target = node["options"][option]
    if target.startswith("start:"):
        return start(target.split(":", 1)[1])
    return _payload(target)


_STOP = {"de", "da", "do", "a", "o", "e", "ou", "um", "uma", "sem", "com", "para", "pra", "no", "na", "em", "por",
         "problema", "outro", "outra", "mensagem", "tela", "computador", "aparelho"}


def _tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z]+", normalize(text)) if len(w) >= 3 and w not in _STOP}


def _match_option(node: dict, text: str) -> Optional[int]:
    """Índice da opção cujas palavras mais aparecem no texto digitado."""
    text_tokens = _tokens(text)
    best, best_score = None, 0
    for index, (label, _) in enumerate(node.get("options", [])):
        score = len(_tokens(label) & text_tokens)
        if score > best_score:
            best, best_score = index, score
    return best


def answer_text(node_id: str, text: str) -> dict:
    """Resposta digitada: interpreta pelas regras do nó, pelas opções e, por fim, como dúvida nova."""
    node = NODES.get(node_id)
    normalized = normalize(text or "")
    if node is not None:
        for keywords, target in node.get("free_routes", []):
            if any(keyword in normalized for keyword in keywords):
                return _payload(target)
        if node.get("kind") in ("question", "menu"):
            index = _match_option(node, text)
            if index is not None:
                return step(node_id, index)
        if node.get("fallback"):
            return _payload(node["fallback"])
    return triage(text)


def triage(text: str) -> dict:
    """Descobre o problema a partir do que a pessoa escreveu."""
    normalized = normalize(text or "")
    if any(keyword in normalized for keyword in SAFETY_KEYWORDS):
        return _payload("seguranca")
    best, best_hits = None, 0
    for flow_id, keywords in FLOW_KEYWORDS.items():
        hits = sum(1 for k in keywords if k in normalized)
        if hits > best_hits:
            best, best_hits = flow_id, hits
    if best is None:
        return _payload("nao_entendi")
    return start(best)
