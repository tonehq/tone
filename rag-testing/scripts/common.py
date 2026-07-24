"""Shared helpers for the RAG eval CLI wrappers.

Storage (questions.json + run-*.json files) moved into Postgres — the CLI
scripts persist through ``EvalService``, so this module only carries what
`bootstrap_from_db.py` and `validate_ingestion.py` still need."""

from __future__ import annotations

import json
import mimetypes
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
RAG_TESTING_ROOT = REPO_ROOT / "rag-testing"
DOCS_DIR = RAG_TESTING_ROOT / "documents"
PROMPTS_DIR = RAG_TESTING_ROOT / "prompts"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _isoformat_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def now_iso() -> str:
    return _isoformat_utc(datetime.now(timezone.utc))


@dataclass
class DocMetadata:
    doc_slug: str
    upload_id: str
    org_id: Optional[str] = None
    source_file: Optional[str] = None
    ingested_at: Optional[str] = None

    @classmethod
    def load(cls, doc_slug: str) -> "DocMetadata":
        path = DOCS_DIR / doc_slug / "metadata.json"
        if not path.exists():
            raise FileNotFoundError(
                f"Missing {path}. Run bootstrap_from_db.py --write first."
            )
        raw = json.loads(path.read_text())
        return cls(
            doc_slug=doc_slug,
            upload_id=raw["upload_id"],
            org_id=raw.get("org_id"),
            source_file=raw.get("source_file"),
            ingested_at=raw.get("ingested_at"),
        )


def doc_dir(doc_slug: str) -> Path:
    return DOCS_DIR / doc_slug


def guess_content_type(path: Path) -> str:
    ctype, _ = mimetypes.guess_type(str(path))
    if ctype:
        return ctype
    ext = path.suffix.lower()
    return {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".html": "text/html",
    }.get(ext, "application/octet-stream")


def list_all_docs() -> list[str]:
    if not DOCS_DIR.exists():
        return []
    return sorted(
        d.name
        for d in DOCS_DIR.iterdir()
        if d.is_dir() and (d / "metadata.json").exists()
    )


def load_settings():
    from shared.config import settings as _settings

    return _settings


@contextmanager
def db_session() -> Iterator:
    from core.database.session import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
