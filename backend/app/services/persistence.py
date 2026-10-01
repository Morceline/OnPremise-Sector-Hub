"""
services/persistence.py
--------------------------
Persiste a configuração ativa do setor em um arquivo JSON local.

Optamos por um arquivo JSON simples em vez de um banco de dados (SQLite,
Postgres) porque existe exatamente UMA configuração ativa por instalação —
um banco relacional seria complexidade desnecessária para um PC básico de
usuário. A escrita é atômica (grava em um arquivo temporário e faz
`os.replace`) para evitar corromper o arquivo em caso de queda de energia
no meio da escrita.
"""

import json
import os
from pathlib import Path
from typing import Optional

from app.models.config import SectorConfig


def save_active_config(config: SectorConfig, path: str) -> None:
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = target_path.with_suffix(".tmp")
    tmp_path.write_text(config.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp_path, target_path)  # operação atômica no mesmo filesystem


def load_active_config(path: str) -> Optional[SectorConfig]:
    target_path = Path(path)
    if not target_path.exists():
        return None

    try:
        data = json.loads(target_path.read_text(encoding="utf-8"))
        return SectorConfig(**data)
    except (json.JSONDecodeError, ValueError):
        # Arquivo corrompido não deve derrubar a aplicação inteira —
        # tratamos como "sem configuração ainda".
        return None
