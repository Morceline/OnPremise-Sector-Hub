"""
services/document.py
----------------------
Leitor seguro de arquivos locais (PDF, DOCX, TXT), respeitando a
allowlist/blocklist de caminhos definida pelo gestor do setor (RF01).

Mudanças deste lote:
- `iter_safe_files()` lista os arquivos autorizados SEM ler o conteúdo. A
  sincronização incremental usa isso para comparar data/tamanho e só abrir
  o que mudou (abrir PDF é a parte cara).
- `extract_text(path, strict=True)` deixa a exceção subir, para a
  sincronização distinguir "arquivo realmente vazio" de "falha ao ler"
  (arquivo travado, corrompido). O modo padrão continua tolerante.
- Arquivos temporários do Office (`~$nome.docx`) são ignorados.
- Pastas permitidas que se sobrepõem não geram o mesmo arquivo duas vezes.
"""

import logging
import os
from pathlib import Path
from typing import Iterator, List, Set, TypedDict

from docx import Document
from pypdf import PdfReader

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}


class ExtractedDocument(TypedDict):
    source: str
    content: str


class SafeDocumentReader:
    def __init__(
        self,
        allowed_paths: List[str],
        blocked_paths: List[str],
        max_file_size_mb: int = 25,
    ):
        self.allowed_paths = [Path(p).resolve() for p in allowed_paths]
        self.blocked_paths = [Path(p).resolve() for p in blocked_paths]
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def _is_path_safe(self, file_path: Path) -> bool:
        """
        Um caminho só é seguro se:
        1. Não estiver dentro de nenhuma pasta/arquivo bloqueado, E
        2. Estiver dentro de alguma pasta permitida.

        O bloqueio é checado PRIMEIRO e tem prioridade: se um caminho está
        nas duas listas por engano, o bloqueio vence (fail-safe).
        """
        resolved_file = file_path.resolve()

        for blocked in self.blocked_paths:
            if resolved_file == blocked or blocked in resolved_file.parents:
                return False

        for allowed in self.allowed_paths:
            if resolved_file == allowed or allowed in resolved_file.parents:
                return True

        return False

    def iter_safe_files(self) -> Iterator[Path]:
        """Arquivos autorizados e de tipo suportado, sem abrir o conteúdo."""
        seen: Set[Path] = set()

        for base_path in self.allowed_paths:
            if not base_path.exists():
                logger.warning("Caminho permitido não existe, ignorando: %s", base_path)
                continue

            for root, _, files in os.walk(base_path):
                for file in files:
                    if file.startswith("~$"):  # arquivo temporário do Office
                        continue

                    file_path = Path(root) / file
                    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                        continue
                    if not self._is_path_safe(file_path):
                        continue

                    resolved = file_path.resolve()
                    if resolved in seen:  # pastas permitidas sobrepostas
                        continue
                    seen.add(resolved)
                    yield file_path

    def is_within_size_limit(self, path: Path) -> bool:
        try:
            return path.stat().st_size <= self.max_file_size_bytes
        except OSError:
            return False

    def load_and_extract(self) -> List[ExtractedDocument]:
        """Lê tudo de uma vez (modo tolerante). Mantido por compatibilidade."""
        extracted_documents: List[ExtractedDocument] = []

        for file_path in self.iter_safe_files():
            if not self.is_within_size_limit(file_path):
                logger.warning(
                    "Arquivo ignorado por exceder %s MB: %s",
                    self.max_file_size_bytes // (1024 * 1024),
                    file_path,
                )
                continue

            text = self.extract_text(file_path)
            if text.strip():
                extracted_documents.append({"source": str(file_path), "content": text})

        return extracted_documents

    def extract_text(self, file_path: Path, strict: bool = False) -> str:
        """
        Extrai o texto de um arquivo. Com `strict=True` a exceção sobe (a
        sincronização usa isso para marcar o arquivo como "erro" e tentar de
        novo depois); sem `strict`, falhas viram texto vazio + log.
        """
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            reader_fn = self._pdf_text
        elif suffix in (".docx", ".doc"):
            reader_fn = self._docx_text
        elif suffix in (".txt", ".md"):
            reader_fn = self._txt_text
        else:
            return ""

        if strict:
            return reader_fn(file_path)

        try:
            return reader_fn(file_path)
        except Exception:
            logger.exception("Falha ao ler arquivo: %s", file_path)
            return ""

    # Compatibilidade com o nome antigo.
    def _extract_text(self, file_path: Path) -> str:
        return self.extract_text(file_path)

    @staticmethod
    def _pdf_text(path: Path) -> str:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    @staticmethod
    def _docx_text(path: Path) -> str:
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)

    @staticmethod
    def _txt_text(path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")
