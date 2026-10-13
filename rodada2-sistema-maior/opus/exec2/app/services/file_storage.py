"""Armazenamento seguro de anexos (resultados de exames)."""

import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings
from app.core.exceptions import InvalidInputError, NotFoundError, PayloadTooLargeError, UnsupportedMediaTypeError

# Tipo MIME -> (extensão, assinatura binária esperada no início do arquivo)
ALLOWED_TYPES: dict[str, tuple[str, tuple[bytes, ...]]] = {
    "application/pdf": (".pdf", (b"%PDF-",)),
    "image/png": (".png", (b"\x89PNG\r\n\x1a\n",)),
    "image/jpeg": (".jpg", (b"\xff\xd8\xff",)),
}

_CHUNK_SIZE = 64 * 1024
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._ -]")


@dataclass(frozen=True)
class StoredFile:
    relative_path: str
    original_name: str
    content_type: str
    size: int


def sanitize_filename(name: str | None) -> str:
    base = os.path.basename(name or "arquivo")
    cleaned = _SAFE_NAME_RE.sub("_", base).strip(" .")
    return cleaned[:100] or "arquivo"


class FileStorage:
    def __init__(self, base_dir: str | None = None, max_size: int | None = None) -> None:
        settings = get_settings()
        self.base_dir = Path(base_dir or settings.upload_dir).resolve()
        self.max_size = max_size or settings.max_upload_size_bytes

    def save(self, stream: BinaryIO, original_name: str | None, content_type: str | None, folder: str) -> StoredFile:
        if content_type not in ALLOWED_TYPES:
            raise UnsupportedMediaTypeError(
                "Tipo de arquivo não suportado. Envie PDF, PNG ou JPEG.",
                details={"permitidos": sorted(ALLOWED_TYPES)},
            )
        extension, signatures = ALLOWED_TYPES[content_type]
        target_dir = self.base_dir / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        relative = Path(folder) / f"{uuid.uuid4().hex}{extension}"
        target = self.base_dir / relative

        size = 0
        header = b""
        try:
            with open(target, "wb") as out:
                while chunk := stream.read(_CHUNK_SIZE):
                    if not header:
                        header = chunk[:16]
                    size += len(chunk)
                    if size > self.max_size:
                        raise PayloadTooLargeError(
                            f"Arquivo excede o tamanho máximo de {self.max_size // (1024 * 1024)} MB."
                        )
                    out.write(chunk)
            if size == 0:
                raise InvalidInputError("O arquivo enviado está vazio.")
            if not any(header.startswith(signature) for signature in signatures):
                raise UnsupportedMediaTypeError("O conteúdo do arquivo não corresponde ao tipo informado.")
        except Exception:
            target.unlink(missing_ok=True)
            raise

        return StoredFile(
            relative_path=relative.as_posix(),
            original_name=sanitize_filename(original_name),
            content_type=content_type,
            size=size,
        )

    def resolve(self, relative_path: str) -> Path:
        """Caminho absoluto do arquivo, garantindo que ele esteja dentro do diretório de uploads."""
        path = (self.base_dir / relative_path).resolve()
        if not path.is_relative_to(self.base_dir) or not path.is_file():
            raise NotFoundError("Arquivo não encontrado.")
        return path

    def delete(self, relative_path: str) -> None:
        path = (self.base_dir / relative_path).resolve()
        if path.is_relative_to(self.base_dir):
            path.unlink(missing_ok=True)
