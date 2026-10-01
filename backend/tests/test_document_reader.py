"""
tests/test_document_reader.py
--------------------------------
Cobre a regra de segurança mais crítica do projeto: o SafeDocumentReader
NUNCA pode ler um arquivo fora da allowlist, e o bloqueio deve sempre
vencer em caso de conflito com a allowlist.
"""

from pathlib import Path

from app.services.document import SafeDocumentReader


def test_arquivo_dentro_da_pasta_permitida_e_seguro(tmp_path: Path):
    allowed_dir = tmp_path / "manuais"
    allowed_dir.mkdir()
    file_path = allowed_dir / "politica.txt"
    file_path.write_text("conteudo")

    reader = SafeDocumentReader(allowed_paths=[str(allowed_dir)], blocked_paths=[])

    assert reader._is_path_safe(file_path) is True


def test_arquivo_fora_de_qualquer_pasta_permitida_e_bloqueado(tmp_path: Path):
    allowed_dir = tmp_path / "manuais"
    allowed_dir.mkdir()
    outro_dir = tmp_path / "financeiro_confidencial"
    outro_dir.mkdir()
    file_path = outro_dir / "salarios.txt"
    file_path.write_text("sigiloso")

    reader = SafeDocumentReader(allowed_paths=[str(allowed_dir)], blocked_paths=[])

    assert reader._is_path_safe(file_path) is False


def test_blocklist_tem_prioridade_sobre_allowlist(tmp_path: Path):
    """Caso crítico: uma subpasta confidencial DENTRO de uma pasta permitida
    deve continuar bloqueada — o bloqueio sempre vence."""
    allowed_dir = tmp_path / "manuais"
    allowed_dir.mkdir()
    confidential_subdir = allowed_dir / "diretoria"
    confidential_subdir.mkdir()
    file_path = confidential_subdir / "estrategia.txt"
    file_path.write_text("confidencial")

    reader = SafeDocumentReader(
        allowed_paths=[str(allowed_dir)],
        blocked_paths=[str(confidential_subdir)],
    )

    assert reader._is_path_safe(file_path) is False


def test_load_and_extract_ignora_pastas_bloqueadas_e_le_permitidas(tmp_path: Path):
    allowed_dir = tmp_path / "manuais"
    allowed_dir.mkdir()
    blocked_subdir = allowed_dir / "rh_confidencial"
    blocked_subdir.mkdir()

    (allowed_dir / "boas_vindas.txt").write_text("Bem-vindo ao setor.")
    (blocked_subdir / "salarios.txt").write_text("Dados sigilosos de salário.")

    reader = SafeDocumentReader(allowed_paths=[str(allowed_dir)], blocked_paths=[str(blocked_subdir)])
    docs = reader.load_and_extract()

    sources = [d["source"] for d in docs]
    assert any("boas_vindas.txt" in s for s in sources)
    assert not any("salarios.txt" in s for s in sources)


def test_arquivo_acima_do_limite_de_tamanho_e_ignorado(tmp_path: Path):
    allowed_dir = tmp_path / "manuais"
    allowed_dir.mkdir()
    big_file = allowed_dir / "grande.txt"
    big_file.write_text("x" * 2000)  # ~2000 bytes

    # Limite de 0 MB força qualquer arquivo a ser considerado "grande demais".
    reader = SafeDocumentReader(allowed_paths=[str(allowed_dir)], blocked_paths=[], max_file_size_mb=0)
    docs = reader.load_and_extract()

    assert docs == []


def test_pasta_permitida_inexistente_nao_quebra_a_leitura(tmp_path: Path):
    caminho_inexistente = tmp_path / "nao_existe"

    reader = SafeDocumentReader(allowed_paths=[str(caminho_inexistente)], blocked_paths=[])

    # Não deve lançar exceção, apenas retornar lista vazia.
    assert reader.load_and_extract() == []
