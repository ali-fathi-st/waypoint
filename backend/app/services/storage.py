"""
Private file storage for uploaded résumés and cover letters.

Files go in STORAGE_DIR (default backend/storage/, which git ignores), named
by document id, never by the name you uploaded them with. Nothing here is
served to the browser: the API returns metadata only.

To move to cloud storage later (S3, Azure Blob), replace these three
functions; nothing else needs to change.
"""

import io
import zipfile
from pathlib import Path

from app.config import get_settings

MAX_BYTES = 5 * 1024 * 1024
PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _root() -> Path:
    root = Path(get_settings().storage_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def detect_type(data: bytes) -> str | None:
    """Check the file's contents, not its name: PDF or Word .docx, else None."""
    if data.startswith(b"%PDF-"):
        return PDF
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if "word/document.xml" in z.namelist():
                    return DOCX
        except zipfile.BadZipFile:
            return None
    return None


def save(key: str, data: bytes) -> None:
    (_root() / key).write_bytes(data)


def delete(key: str) -> None:
    (_root() / key).unlink(missing_ok=True)


def delete_all() -> None:
    for path in _root().iterdir():
        if path.is_file() and not path.name.startswith("."):
            path.unlink()
