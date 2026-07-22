"""Shared helpers for the RAG evaluation scripts.

Loads project settings, opens DB sessions, resolves per-doc metadata, and writes
timestamped run outputs. Reuses the production `RAGPipeline` + `PgVectorStore`
+ `OpenAIEmbedder` primitives — no re-implementation.
"""
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
                f"Missing {path}. Create it with keys: upload_id, org_id (optional), "
                "source_file, ingested_at."
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


def resolve_source_file(doc_slug: str, meta: Optional[DocMetadata] = None) -> Path:
    d = doc_dir(doc_slug)
    if meta and meta.source_file:
        p = d / meta.source_file
        if p.exists():
            return p
    for name in ("source.pdf", "source.md", "source.txt", "source.docx", "source.html"):
        p = d / name
        if p.exists():
            return p
    candidates = [p for p in d.glob("source.*") if p.is_file()]
    if candidates:
        return candidates[0]
    raise FileNotFoundError(
        f"No source file found in {d}. Place the doc as source.pdf|.md|.txt|.docx|.html "
        f"or set source_file in metadata.json."
    )


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


def read_prompt(name: str) -> str:
    p = PROMPTS_DIR / name
    if not p.exists():
        raise FileNotFoundError(f"Prompt file not found: {p}")
    return p.read_text()


def render_prompt(template: str, **values: str) -> str:
    out = template
    for key, val in values.items():
        out = out.replace("{{" + key + "}}", val)
    return out


def list_all_docs() -> list[str]:
    if not DOCS_DIR.exists():
        return []
    return sorted(
        d.name
        for d in DOCS_DIR.iterdir()
        if d.is_dir() and (d / "metadata.json").exists()
    )


def load_settings():
    """Import late so PYTHONPATH is set up before pulling project settings."""
    from shared.config import settings as _settings

    return _settings


def openai_client(api_key: Optional[str] = None):
    """Return an OpenAI client using the project's key by default."""
    import openai

    key = api_key or os.getenv("OPENAI_API_KEY") or load_settings().OPENAI_API_KEY
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set (env or shared.config).")
    return openai.OpenAI(api_key=key)


@contextmanager
def db_session() -> Iterator:
    from core.database.session import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def build_retrieval_pipeline(db_session_obj):
    """Assemble a RAGPipeline wired to the SAME embedder + pgvector store as prod.

    Chunker/reader are unused for retrieval but the pipeline requires them; the
    defaults are harmless (nothing gets ingested here).
    """
    from core.services.rag.embedders import OpenAIEmbedder
    from core.services.rag.pipeline import RAGPipeline
    from core.services.rag.vector_stores.pgvector_store import PgVectorStore

    settings = load_settings()
    key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set — cannot embed query.")
    return RAGPipeline(
        embedder=OpenAIEmbedder(api_key=key),
        store=PgVectorStore(session=db_session_obj),
    )


def write_run_result(doc_slug: str, payload: dict) -> Path:
    results_dir = doc_dir(doc_slug) / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    fname = f"run-{now_iso()}.json"
    out_path = results_dir / fname
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return out_path


def write_questions(doc_slug: str, payload: dict) -> Path:
    d = doc_dir(doc_slug)
    d.mkdir(parents=True, exist_ok=True)
    out_path = d / "questions.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return out_path


def load_questions(doc_slug: str) -> dict:
    p = doc_dir(doc_slug) / "questions.json"
    if not p.exists():
        raise FileNotFoundError(
            f"{p} not found. Run: python rag-testing/scripts/generate_questions.py --doc {doc_slug}"
        )
    return json.loads(p.read_text())


def extract_document_text(path: Path) -> str:
    """Extract plain text from a source doc using the same readers as ingestion."""
    from core.services.rag.readers import CompositeReader

    content_type = guess_content_type(path)
    document = CompositeReader().read_path(str(path), content_type)
    return document.text
