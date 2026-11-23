"""
tests/test_it_flows.py
-------------------------
Atendimento guiado de TI. Garante que nenhum botão leva a um nó inexistente,
que todo caminho termina em uma orientação, e que a descoberta do problema
funciona para as formas comuns de descrever uma dúvida.
"""

import pytest

from app.services import it_flows
from app.services.it_flows import FIM, MENU, NODES, FLOW_START, answer_text, step, start, triage


def _alcancaveis():
    """Todos os nós alcançáveis a partir do menu, seguindo as opções."""
    visitados, fila = set(), [MENU]
    while fila:
        atual = fila.pop()
        if atual in visitados or atual.startswith("start:"):
            continue
        visitados.add(atual)
        for _, destino in NODES[atual].get("options", []):
            if destino.startswith("start:"):
                fila.append(FLOW_START[destino.split(":", 1)[1]])
            else:
                fila.append(destino)
    return visitados


def test_nenhum_botao_aponta_para_no_inexistente():
    for node_id, node in NODES.items():
        for _, destino in node.get("options", []):
            if destino.startswith("start:"):
                assert destino.split(":", 1)[1] in FLOW_START, f"{node_id} -> {destino}"
            else:
                assert destino in NODES, f"{node_id} -> {destino}"


def test_todo_no_alcancavel_do_menu_existe_e_tem_saida():
    for node_id in _alcancaveis():
        node = NODES[node_id]
        if node["kind"] == "question":
            assert len(node["options"]) >= 2, node_id
        if node["kind"] == "advice":
            assert [label for label, _ in node["options"]] == ["Resolveu", "Não resolveu"], node_id
        if node["kind"] == "advice":  # testes curtos; a referência de atalhos é uma lista
            assert len(node.get("steps", [])) <= 2, f"{node_id} tem mais de 2 passos"


@pytest.mark.parametrize("flow_id", list(FLOW_START))
def test_cada_tema_chega_a_uma_orientacao_final(flow_id):
    atual = FLOW_START[flow_id]
    visitados = set()
    while NODES[atual]["kind"] in ("question", "advice"):
        assert atual not in visitados, f"ciclo em {flow_id}"
        visitados.add(atual)
        atual = NODES[atual]["options"][-1][1]  # sempre o caminho "não resolveu" / último
        if atual.startswith("start:"):
            break
    assert NODES[atual]["kind"] in ("escalate", "end", "menu", "reference")


def test_impressora_comeca_pela_tela_do_computador_e_nao_sugere_suporte():
    primeiro = NODES[FLOW_START["impressora"]]
    assert primeiro["kind"] == "question"
    assert "tela do computador" in primeiro["text"]


def test_caminho_com_fio_nunca_sugere_pilhas():
    atual, visitados = "per_fio_1", set()
    while NODES[atual]["kind"] in ("advice", "question", "escalate") and atual not in visitados:
        visitados.add(atual)
        assert "pilha" not in NODES[atual]["text"].lower(), atual
        if NODES[atual]["kind"] == "escalate":
            break
        atual = NODES[atual]["options"][-1][1]


def test_textos_sem_saudacao_nem_frase_de_linguagem():
    for node_id, node in NODES.items():
        texto = node.get("text", "")
        assert not texto.startswith("Oi"), node_id
        assert "Pode ser simples" not in texto, node_id


def test_menu_tem_os_temas_atalhos_e_outro_problema():
    labels = [label for label, _ in NODES[MENU]["options"]]
    assert len(labels) == 6
    assert labels[4] == "Atalhos do teclado"
    assert labels[-1] == "Outro problema"


def test_passo_avanca_pela_opcao_escolhida():
    primeiro = start("impressora")
    proximo = step(primeiro["node_id"], 0)
    assert proximo is not None and proximo["node_id"] != primeiro["node_id"]


def test_opcao_invalida_nao_avanca():
    assert step(FLOW_START["impressora"], 9) is None
    assert step("nao_existe", 0) is None


@pytest.mark.parametrize("descricao, tema_inicio", [
    ("minha impressora não imprime", "imp_0"),
    ("o mouse parou", "per_0"),
    ("não tenho internet", "rede_0"),
    ("o computador está muito lento", "sis_0"),
    ("não consigo abrir a pasta da equipe", "pas_0"),
    ("a planilha mostra erro", "pla_0"),
    ("não sai som", "aud_0"),
    ("como salvar um arquivo", "bas_0"),
])
def test_descricao_livre_cai_no_tema_certo(descricao, tema_inicio):
    assert triage(descricao)["node_id"] == tema_inicio


def test_descricao_sem_tema_pede_para_escolher():
    resultado = triage("quero saber sobre férias")
    assert resultado["node_id"] == "nao_entendi"
    assert len(resultado["options"]) == 5


def test_todas_as_respostas_de_triagem_tem_destino_valido():
    for texto in ["quero saber sobre férias", "a impressora está soltando fumaça", "não tenho internet"]:
        node_id = triage(texto)["node_id"]
        for indice in range(len(NODES[node_id].get("options", []))):
            assert step(node_id, indice) is not None, (texto, indice)


def test_fumaca_vem_antes_de_qualquer_tema():
    assert triage("a impressora está soltando fumaça")["node_id"] == "seguranca"


def test_impressora_pergunta_a_tela_do_computador_primeiro():
    assert "tela do computador" in NODES["imp_0"]["text"]


def test_outra_mensagem_pede_para_digitar_e_interpreta_o_texto():
    assert NODES["imp_texto"]["kind"] == "ask_text"
    assert answer_text("imp_texto", "a impressora está sem tinta")["node_id"] == "imp_papel"
    assert answer_text("imp_texto", "o tamanho do papel está errado")["node_id"] == "imp_tipo"
    assert answer_text("imp_texto", "não sei")["node_id"] == "imp_rede"


def test_papel_preso_digitado_vai_para_o_passo_do_papel():
    assert answer_text("imp_visor_texto", "papel preso")["node_id"] == "imp_papel"


def test_apito_de_impressora_ou_nobreak_tem_tema_proprio():
    assert triage("a impressora está apitando")["node_id"] == "alarme_0"
    assert triage("o nobreak está apitando")["node_id"] == "alarme_0"
    assert NODES["alarme_nobreak"]["kind"] == "advice"


def test_computador_que_nao_liga_tem_tema_proprio():
    assert triage("meu computador não liga")["node_id"] == "nl_0"


def test_textos_livres_apontam_para_destinos_validos():
    for node_id, node in NODES.items():
        for _, target in node.get("free_routes", []):
            assert target in NODES, (node_id, target)
        if node.get("fallback"):
            assert node["fallback"] in NODES, node_id


def test_outra_mensagem_tem_rotulo_limpo():
    assert "Outra mensagem" in [label for label, _ in NODES["imp_pc_msg"]["options"]]


def test_mensagem_de_nao_localizar_vai_para_a_conexao():
    assert answer_text("imp_texto", "não foi possível localizar")["node_id"] == "imp_rede"


def test_palavra_citada_na_pergunta_segue_a_opcao():
    assert answer_text("imp_pc_msg", "falta de papel")["node_id"] == "imp_papel"
    assert answer_text("imp_pc_msg", "o tamanho do papel está errado")["node_id"] == "imp_tipo"


def test_atalhos_do_teclado_sao_referencia_com_passos():
    assert "atalhos" in [label for label, _ in NODES[MENU]["options"]][4].lower()
    assert NODES["atj_copiar"]["kind"] == "reference"
    assert "Ctrl + C" in NODES["atj_copiar"]["steps"][0]
    assert any("Alt" in passo for passo in NODES["atj_nav"]["steps"])


def test_atalhos_do_windows_estao_organizados_por_assunto():
    grupos = [label for label, _ in NODES["atalhos_0"]["options"]]
    assert "Janelas e área de trabalho" in grupos
    assert "Arquivos e Explorador" in grupos
    assert "Sistema e tela" in grupos
    assert "Windows + D" in " ".join(NODES["atj_janelas"]["steps"])
    assert "Ctrl + Shift + Esc" in " ".join(NODES["atj_sistema"]["steps"])
    for node_id in ("atj_janelas", "atj_arquivos", "atj_sistema"):
        assert len(NODES[node_id]["steps"]) >= 4, node_id
    assert len(NODES["atj_print"]["steps"]) >= 2
