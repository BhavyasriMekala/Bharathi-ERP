"""Load stored file bytes for Bharathi OCR (server-side only)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.file_storage import StoredFile
from app.services.storage.object_store import blob_exists, get_bytes


def load_stored_file_bytes(db: Session, stored_file: StoredFile) -> tuple[bytes, str]:
    if not stored_file.storage_key or not blob_exists(stored_file.storage_key):
        raise ValueError("File blob is not available in storage")
    data = get_bytes(stored_file.storage_key)
    mime = (stored_file.mime_type or "application/octet-stream").strip().lower()
    return data, mime