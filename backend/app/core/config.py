"""
core/config.py
----------------
Centraliza TODAS as variáveis de ambiente do projeto em um único lugar,
usando Pydantic Settings. Isso evita o antipadrão de espalhar
`os.getenv(...)` por vários arquivos (como estava em rag_engine.py e chat.py
na versão anterior), o que dificulta manutenção e testes.

Qualquer novo parâmetro de configuração deve ser adicionado AQUI,
nunca direto com os.getenv em outro módulo.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Infraestrutura local (Qdrant / Ollama) ---
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    ollama_host: str = "http://localhost:11434"

    # Modelos usados. Deixar configurável evita hardcode espalhado pelo código
    # e facilita trocar o modelo (ex: para um Qwen maior) sem mexer em lógica.
    llm_model: str = "qwen2.5:3b"
    embedding_model: str = "nomic-embed-text"
    embedding_dimension: int = 768  # dimensão de saída do nomic-embed-text

    # --- CORS: origens do widget desktop autorizadas a chamar a API ---
    # Tauri v2 usa origens diferentes por sistema operacional:
    #   Windows/Android -> http://tauri.localhost (https://... se useHttpsScheme=true)
    #   macOS/Linux     -> tauri://localhost
    # Em desenvolvimento, o Vite serve em http://localhost:1420.
    # Para sobrescrever via .env use JSON: CORS_ORIGINS=["http://localhost:1420"]
    cors_origins: List[str] = [
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
        "http://localhost:1420",
    ]

    # --- Segurança: chave do gestor/setor (RF04) ---
    # Armazenamos apenas o HASH da chave, nunca a chave em texto puro.
    # Gerar com: python -c "import hashlib; print(hashlib.sha256(b'SUA_CHAVE').hexdigest())"
    manager_key_hash: str = ""

    # --- Feedback por e-mail (opt-in/opt-out) ---
    feedback_enabled: bool = True
    feedback_email_to: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True

    # --- Limites de segurança / performance (PC básico do usuário) ---
    max_file_size_mb: int = 25
    max_web_fetch_chars: int = 20_000
    request_timeout_seconds: float = 60.0
    embedding_timeout_seconds: float = 15.0

    # --- Sincronização incremental (catálogo + varredura periódica) ---
    # Decisão de arquitetura: varredura periódica em vez de "tempo real".
    # Eventos de arquivo são pouco confiáveis entre Windows, volumes do
    # Docker e pastas de rede, e fontes online não avisam mudanças; um
    # único mecanismo periódico serve para todas as fontes e agrupa as
    # mudanças (menos disputa de CPU com o Ollama respondendo o chat).
    sync_enabled: bool = True
    sync_interval_minutes: int = 15          # varredura das pastas locais
    web_refresh_minutes: int = 60            # releitura das URLs autorizadas
    sync_startup_delay_seconds: float = 20.0  # espera após subir (Ollama/Qdrant prontos)
    sync_error_retry_hours: float = 6.0      # reintento de arquivos que deram erro
    catalog_db_path: str = "app/data/catalog.db"

    # Persistência da configuração ativa do setor em JSON local.
    # Preferido a um banco relacional pois existe apenas UMA config ativa
    # por instalação/setor — SQLite/Postgres seriam over-engineering aqui.
    active_config_path: str = "app/data/active_config.json"
    feedback_log_path: str = "app/data/feedback_log.jsonl"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Singleton simples: evita reler o .env a cada request."""
    return Settings()
