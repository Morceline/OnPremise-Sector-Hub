"""
tests/conftest.py
--------------------
Fixtures compartilhadas por toda a suíte de testes.

Princípio geral: os testes NUNCA devem depender de Qdrant ou Ollama reais
rodando na máquina. Tudo que fala com esses serviços é substituído por
mocks/fakes — isso garante que `pytest` rode em qualquer lugar (inclusive
no CI do GitHub Actions, que não tem Qdrant/Ollama instalados) de forma
rápida e determinística.
"""

import hashlib
import os
from pathlib import Path

import pytest

# Variáveis de ambiente de teste precisam existir ANTES de qualquer import
# que leia `get_settings()`, então setamos aqui no topo do conftest.
os.environ.setdefault("MANAGER_KEY_HASH", hashlib.sha256(b"chave-de-teste").hexdigest())
os.environ.setdefault("FEEDBACK_ENABLED", "false")


@pytest.fixture
def manager_key() -> str:
    """A chave em texto puro cujo hash foi setado em MANAGER_KEY_HASH acima."""
    return "chave-de-teste"


@pytest.fixture
def tmp_active_config_path(tmp_path: Path, monkeypatch) -> str:
    """Redireciona o caminho de persistência da configuração ativa para um
    diretório temporário isolado por teste, evitando que um teste afete o outro
    (e evitando escrever no repositório de verdade)."""
    from app.core.config import get_settings

    path = tmp_path / "active_config.json"
    get_settings.cache_clear()
    monkeypatch.setenv("ACTIVE_CONFIG_PATH", str(path))
    get_settings.cache_clear()
    yield str(path)
    get_settings.cache_clear()
