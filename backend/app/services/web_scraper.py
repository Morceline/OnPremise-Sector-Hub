"""
services/web_scraper.py
--------------------------
Permite que o gestor cadastre links específicos (allowed_web_urls) que o
bot pode consultar como fonte de conhecimento externo — de forma
CONTROLADA, para evitar alucinação e vazamento (o bot NUNCA navega livre
pela web, só acessa exatamente os links autorizados pelo gestor).

Fluxo:
1. O gestor cadastra URLs específicas no painel de configuração.
2. Ao salvar a configuração, cada URL autorizada é baixada, o texto
   principal é extraído (BeautifulSoup) e tratado como mais um "documento"
   que entra no mesmo pipeline de chunking + indexação dos arquivos locais.
3. Isso significa que o bot só "sabe" o que está literalmente no HTML
   daquela página no momento da sincronização — nada de busca aberta.
"""

import logging
from typing import List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def is_url_allowed(url: str, allowed_urls: List[str]) -> bool:
    """
    Um link só é permitido se corresponder exatamente a uma URL da allowlist
    OU pertencer ao mesmo domínio de uma URL autorizada. Fail-safe: se a
    allowlist estiver vazia, nada é permitido.
    """
    if not allowed_urls:
        return False

    target = urlparse(url)

    for allowed in allowed_urls:
        allowed_parsed = urlparse(str(allowed))
        if url == str(allowed):
            return True
        if target.netloc and target.netloc == allowed_parsed.netloc and target.path.startswith(allowed_parsed.path):
            return True

    return False


async def fetch_url_content(
    url: str,
    http_client: httpx.AsyncClient,
    max_chars: int = 20_000,
    timeout: float = 15.0,
) -> Optional[str]:
    """
    Baixa uma URL e extrai texto legível (remove scripts/estilos/menus).
    Retorna None em caso de falha — o chamador deve simplesmente pular essa
    fonte em vez de quebrar toda a sincronização.
    """
    try:
        response = await http_client.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        logger.warning("Falha ao buscar URL autorizada: %s", url)
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = " ".join(soup.get_text(separator=" ").split())
    return text[:max_chars] if text else None
