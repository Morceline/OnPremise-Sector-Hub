"""
core/config.py
----------------
Centraliza TODAS as variáveis de ambiente do projeto em um único lugar,
usando Pydantic Settings.

Qualquer novo parâmetro de configuração deve ser adicionado AQUI,
nunca direto com os.getenv em outro módulo.
"""

from functools import lru_cache

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
