import os
from pathlib import Path
from typing import List
from pypdf import PdfReader
from docx import Document

class SafeDocumentReader:
    def __init__(self, allowed_paths: List[str], blocked_paths: List[str]):
        self.allowed_paths = [Path(p).resolve() for p in allowed_paths]
        self.blocked_paths = [Path(p).resolve() for p in blocked_paths]

    def _is_path_safe(self, file_path: Path) -> bool:
        resolved_file = file_path.resolve()

        # 1. Verifica se o arquivo está dentro de alguma pasta bloqueada
        for blocked in self.blocked_paths:
            if resolved_file == blocked or blocked in resolved_file.parents:
                return False

        # 2. Verifica se o arquivo está dentro de alguma pasta permitida
        for allowed in self.allowed_paths:
            if resolved_file == allowed or allowed in resolved_file.parents:
                return True

        return False

    def load_and_extract(self) -> List[dict]:
        extracted_documents = []

        for base_path in self.allowed_paths:
            if not base_path.exists():
                continue

            for root, _, files in os.walk(base_path):
                for file in files:
                    file_path = Path(root) / file

                    if not self._is_path_safe(file_path):
                        continue

                    text = ""
                    if file_path.suffix.lower() == ".pdf":
                        text = self._read_pdf(file_path)
                    elif file_path.suffix.lower() in [".docx", ".doc"]:
                        text = self._read_docx(file_path)
                    elif file_path.suffix.lower() == ".txt":
                        text = self._read_txt(file_path)

                    if text.strip():
                        extracted_documents.append({
                            "source": str(file_path),
                            "content": text
                        })

        return extracted_documents

    def _read_pdf(self, path: Path) -> str:
        try:
            reader = PdfReader(str(path))
            return "\n".join([page.extract_text() or "" for page in reader.pages])
        except Exception:
            return ""

    def _read_docx(self, path: Path) -> str:
        try:
            doc = Document(str(path))
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception:
            return ""

    def _read_txt(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""