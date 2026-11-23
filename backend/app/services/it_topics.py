"""
services/it_topics.py
-----------------------
Conteúdo FIXO e revisado de dúvidas de TI. Quando a dúvida casa com um tema,
a resposta vem daqui, sem passar pelo modelo: o conteúdo é o que foi definido
pela equipe, não o que o modelo inventa. Dúvidas que não casam com nenhum tema
seguem para o modelo, com regras de linguagem simples.

Regra fixa: qualquer sinal de fumaça, queimado, faísca ou fogo vem antes de
tudo e manda desligar e chamar a TI.
"""

from typing import List, Optional

from app.services.query_normalizer import normalize

SAFETY_KEYWORDS = ["fumaca", "cheiro de queimado", "queimado", "faisca", "fogo", "choque", "pegando fogo"]
SAFETY_TEXT = (
    "Pare agora. Desligue o aparelho da tomada, afaste as pessoas da área e chame a TI imediatamente. "
    "Não tente consertar nada que esteja queimado ou com fumaça."
)

TOPICS = [
    {
        "id": "impressora",
        "title": "Impressora não imprime",
        "keywords": ["impressora", "imprimir", "imprime", "impressao", "toner", "tinta", "papel preso"],
        "questions": [
            "A luz da impressora está acesa?",
            "Os cabos de energia e de USB ou rede estão bem encaixados?",
            "O papel está na bandeja, no tamanho certo?",
        ],
        "steps": [
            "Desligue a impressora da tomada, espere 10 segundos e ligue de novo.",
            "Veja o visor da impressora. Se aparecer aviso de papel preso ou falta de tinta, resolva o que ele indica.",
            "Tente imprimir um texto simples, como um documento do Bloco de Notas.",
        ],
        "escalation": "Se mesmo assim não imprimir, peça ajuda à TI. Antes, anote a mensagem do visor e diga se outro "
                      "computador do setor consegue imprimir.",
    },
    {
        "id": "perifericos",
        "title": "Teclado, mouse ou monitor não funcionam",
        "keywords": ["mouse", "teclado", "monitor", "tela preta", "sem imagem", "sem sinal"],
        "questions": [
            "O mouse ou o teclado tem fio? Se tiver, o cabo está bem encaixado?",
            "Se for sem fio, as pilhas foram trocadas recentemente?",
            "A luz do monitor está acesa?",
        ],
        "steps": [
            "Tire o cabo do mouse ou do teclado e coloque em outra entrada USB do computador.",
            "Se houver um mouse ou teclado reserva no setor, teste com ele para saber se o problema é o aparelho.",
            "Confira se o cabo de força e o cabo de vídeo do monitor estão bem conectados.",
        ],
        "escalation": "Se continuar sem funcionar, peça a troca do aparelho para a TI.",
    },
    {
        "id": "sistema",
        "title": "Sistema ou site travou, ou o computador está lento",
        "keywords": ["lento", "lentidao", "travou", "travado", "trava", "navegador", "pagina", "site", "carregar",
                     "fora do ar", "demora"],
        "questions": [
            "A página está em branco, com erro de 'fora do ar', ou só demora para carregar?",
            "Isso acontece com outros colegas do setor ou só no seu computador?",
            "O mouse se move, ou o computador está totalmente travado?",
        ],
        "steps": [
            "Atualize a página: aperte F5, ou feche e abra o navegador de novo.",
            "Feche os programas e as abas que você não está usando.",
            "Se o mouse não se move, segure o botão de ligar até desligar, espere 5 segundos e ligue de novo.",
        ],
        "escalation": "Se o erro continuar, anote a mensagem da tela e chame a TI. Se o sistema do setor estiver fora do "
                      "ar para todos, avise a TI, porque o problema não é do seu computador.",
    },
    {
        "id": "rede",
        "title": "Sem internet ou Wi-Fi",
        "keywords": ["internet", "rede", "wifi", "wi-fi", "sem conexao", "sem acesso", "cabo de rede"],
        "questions": [
            "No canto da tela, perto do relógio, o ícone da rede mostra um X vermelho ou aviso de 'sem acesso'?",
            "Os computadores vizinhos também estão sem internet?",
            "Você usa cabo ou Wi-Fi?",
        ],
        "steps": [
            "Se usa cabo, confira se ele está bem encaixado no computador e na tomada de rede da parede.",
            "Se usa Wi-Fi, confira se a rede correta do órgão está selecionada.",
            "Reinicie o computador para ele se conectar de novo.",
        ],
        "escalation": "Se o problema for no setor inteiro, chame a equipe de TI ou de redes. Se for só no seu computador, "
                      "a TI resolve com mais segurança.",
    },
    {
        "id": "pasta",
        "title": "Não consigo abrir a pasta da equipe",
        "keywords": ["pasta", "compartilhada", "arquivos da equipe", "servidor"],
        "questions": [
            "Você consegue navegar na internet, mas não abre os arquivos da pasta da equipe?",
            "Outros colegas também não conseguem abrir a pasta?",
            "A pasta sumiu, ou só demora para abrir?",
        ],
        "steps": [
            "Feche a janela da pasta e abra de novo pelo atalho.",
            "Reinicie o seu computador para restabelecer a ligação com a pasta.",
            "Se ela estiver só lenta, espere alguns minutos, porque arquivos grandes demoram para abrir.",
        ],
        "escalation": "Se a pasta não abrir para ninguém, chame a TI com urgência. Diga que a pasta do setor está "
                      "indisponível, para a TI verificar o computador que guarda os arquivos.",
    },
    {
        "id": "planilha",
        "title": "Problema em planilha",
        "keywords": ["planilha", "excel", "formula", "celula", "valor!", "ref!"],
        "questions": [
            "A planilha abre, mas uma fórmula mostra erro, como #VALOR! ou #REF!?",
            "O número aparece alinhado à esquerda, como se fosse texto?",
            "Você tem uma cópia salva da planilha antes da mudança?",
        ],
        "steps": [
            "Confira se o número foi digitado sem letras ou espaços e se a célula está no formato de número.",
            "Para desfazer a última mudança, aperte Ctrl e Z ao mesmo tempo.",
            "Se a fórmula estiver confusa, compare com a de uma linha que funciona.",
        ],
        "escalation": "Se a planilha não abrir ou perder dados, não salve por cima. Avise a TI ou o responsável pela planilha.",
    },
    {
        "id": "audio",
        "title": "Sem som",
        "keywords": ["som", "audio", "caixa de som", "fone", "volume", "mudo"],
        "questions": [
            "O volume do computador está no zero ou no mudo?",
            "Você usa fone ou caixa de som? A caixa está ligada na tomada?",
            "O som funciona em outro programa, como um vídeo?",
        ],
        "steps": [
            "Clique no ícone de volume, perto do relógio: aumente e tire o mudo.",
            "No mesmo ícone, escolha a saída de som e veja se o seu fone ou caixa aparece.",
            "Desconecte o fone e conecte de novo.",
        ],
        "escalation": "Se nenhuma caixa ou fone tocar, peça à TI para verificar o aparelho.",
    },
    {
        "id": "basico",
        "title": "Dúvida básica de uso do computador",
        "keywords": ["como salvar", "area de trabalho", "ligar o computador", "desligar o computador", "nao sei usar"],
        "questions": [
            "O que você queria fazer quando a dúvida apareceu?",
            "Apareceu alguma mensagem na tela? Qual?",
        ],
        "steps": [
            "Anote a mensagem exata que aparece na tela, ou tire uma foto dela.",
            "Feche a janela com o X e tente de novo, com calma.",
            "Se não souber como fazer, peça à TI que ensine passo a passo.",
        ],
        "escalation": "Quando for só para aprender, a TI pode ensinar em alguns minutos.",
    },
]


def _best_topic(text: str) -> Optional[dict]:
    normalized = normalize(text or "")
    best, best_hits = None, 0
    for topic in TOPICS:
        hits = sum(1 for keyword in topic["keywords"] if keyword in normalized)
        if hits > best_hits:
            best, best_hits = topic, hits
    return best


def answer_for(text: str) -> Optional[str]:
    """Resposta fixa para a dúvida, ou None se nenhum tema casa com ela."""
    if any(keyword in normalize(text or "") for keyword in SAFETY_KEYWORDS):
        return SAFETY_TEXT
    topic = _best_topic(text)
    if topic is None:
        return None
    perguntas = "\n".join(f"- {q}" for q in topic["questions"])
    passos = "\n".join(f"{i}. {s}" for i, s in enumerate(topic["steps"], start=1))
    return (f"{topic['title']}\n\nAntes, responda para você:\n{perguntas}\n\n"
            f"Tente, nesta ordem:\n{passos}\n\n{topic['escalation']}")


def list_titles() -> List[dict]:
    return [{"id": t["id"], "title": t["title"]} for t in TOPICS]
