from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from src.cris.config import get_settings
from src.cris.core.models import FIRDocument, infer_file_type


def scan_dataset(root: Path | None = None, limit: int | None = 100) -> list[FIRDocument]:
    settings = get_settings()
    base = root or Path(settings.data_dir)
    if not base.exists():
        return []

    docs: list[FIRDocument] = []
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".pdf", ".jpg", ".jpeg", ".png"}:
            continue
        docs.append(
            FIRDocument(
                doc_id=path.stem,
                source_path=str(path),
                file_name=path.name,
                file_type=infer_file_type(path),
                file_hash=compute_file_hash(path),
                last_modified=_last_modified_iso(path),
            )
        )
        if limit is not None and len(docs) >= limit:
            break
    return docs


def describe_uploads(uploaded_files: Iterable) -> list[dict]:
    rows = []
    for item in uploaded_files:
        rows.append(
            {
                "name": item.name,
                "size_bytes": getattr(item, "size", None),
                "mime": getattr(item, "type", None),
            }
        )
    return rows


def compute_file_hash(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _last_modified_iso(path: Path) -> str | None:
    try:
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return modified.isoformat()
    except OSError:
        return None
