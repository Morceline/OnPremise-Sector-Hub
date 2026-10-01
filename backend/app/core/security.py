"""
core/security.py
------------------
Garante que SOMENTE alguém autorizado (efetivo da empresa, com uma chave
própria) possa alterar a configuração do setor (RF04 do Sprint 2).

Decisão de arquitetura: chave compartilhada por setor, comparada
por hash — em vez de um sistema de login completo (usuários + JWT).
Motivo: hoje cada instalação atende UM setor com UM responsável de
configuração por vez; um sistema de login completo seria sobre-engenharia
nesta fase. Se no futuro várias pessoas do mesmo setor precisarem de
permissões diferentes entre si, o próximo passo natural é evoluir para
JWT por usuário (documentado no README).

"""

import hashlib
import hmac

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def require_manager_key(x_manager_key: str = Header(default="")) -> None:
    """
    Dependência do FastAPI usada em rotas sensíveis (salvar configuração,
    alterar allowlist/blocklist etc).

    Uso:
        @router.post("/save", dependencies=[Depends(require_manager_key)])
    """
    settings = get_settings()

    if not settings.manager_key_hash:
        # Instalação ainda não definiu uma chave -> bloqueia por padrão.
        # Evita o erro clássico de "esqueci de configurar e deixei aberto".
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Nenhuma chave de gestor foi configurada nesta instalação. "
                "Defina MANAGER_KEY_HASH no arquivo .env antes de usar esta rota."
            ),
        )

    if not x_manager_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cabeçalho 'X-Manager-Key' é obrigatório para esta operação.",
        )

    provided_hash = _hash_key(x_manager_key)

    # compare_digest evita timing attacks na comparação dos hashes.
    if not hmac.compare_digest(provided_hash, settings.manager_key_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chave de gestor inválida.",
        )
