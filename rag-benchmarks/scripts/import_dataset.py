"""Import a standard-dataset RAG benchmark (HotpotQA, TAT-QA, EManual, ...) into
the same KB pipeline customers use — but with pre-authored gold Q&A so runs are
apples-to-apples comparable across model / parser / embedder swaps.

For each document in ``rag-benchmarks/<key>/docs/``:
  1. Create the ``Upload`` + ``KnowledgeBase`` via ``UploadService`` (no defer yet).
  2. Pre-seed the ``evals`` rows from ``qa.jsonl`` via ``EvalService.import_eval``
     (one row per question).
  3. Fire ``enqueue_upload(...)`` so ingestion runs. When the pipeline finishes,
     the existing ``eval_ingestion_run`` auto-task calls
     ``EvalService.get_or_generate_eval`` which short-circuits when questions
     already exist — no LLM question generation, straight to ``run_eval``
     against gold Q&A.

Dataset folder layout expected under ``rag-benchmarks/<key>/``:
    docs/<doc_filename>.<ext>           # one file per KB (any format ingestion supports)
    qa.jsonl                            # one JSON per line — see _load_qa

qa.jsonl per-line schema (matches what ``_score_one_question`` reads):
    {
      "id": "q1",
      "doc_filename": "doc-A.txt",       # which doc in docs/ this Q belongs to
      "category": "single-hop",          # optional; defaults to "unknown"
      "question": "...",
      "expected_answer": "...",
      "expected_source_snippet": "..."   # optional but strongly recommended
    }

Usage:
    python rag-benchmarks/scripts/import_dataset.py <key>
    python rag-benchmarks/scripts/import_dataset.py stub --org-id <uuid>
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BENCHMARKS_ROOT = REPO_ROOT / "rag-benchmarks"


def _dataset_dir(key: str) -> Path:
    path = BENCHMARKS_ROOT / key
    if not path.is_dir():
        raise SystemExit(f"Dataset folder not found: {path}")
    docs_dir = path / "docs"
    qa_path = path / "qa.jsonl"
    if not docs_dir.is_dir():
        raise SystemExit(f"Missing docs/ folder: {docs_dir}")
    if not qa_path.is_file():
        raise SystemExit(f"Missing qa.jsonl: {qa_path}")
    return path


def _load_qa(qa_path: Path) -> dict[str, list[dict]]:
    """Return a ``{doc_filename: [questions]}`` map. Groups questions by their
    ``doc_filename`` so each KB gets exactly the questions authored against it —
    which is what makes retrieval hit-rate meaningful."""
    by_doc: dict[str, list[dict]] = {}
    with qa_path.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{qa_path}:{lineno}: invalid JSON — {exc}")
            doc = row.get("doc_filename")
            if not doc:
                raise SystemExit(f"{qa_path}:{lineno}: missing doc_filename")
            question = {
                "id": str(row.get("id") or f"q{lineno}"),
                "category": row.get("category", "unknown"),
                "question": row.get("question", ""),
                "expected_answer": row.get("expected_answer", ""),
                "expected_source_snippet": row.get("expected_source_snippet", ""),
                "notes": row.get("notes", ""),
            }
            by_doc.setdefault(doc, []).append(question)
    return by_doc


def _resolve_org_id(explicit: str | None) -> UUID:
    from shared.config import settings

    raw = explicit or settings.DEFAULT_ORG_ID
    return UUID(str(raw))


async def _import_one_doc(
    *,
    key: str,
    doc_path: Path,
    questions: list[dict],
    org_id: UUID,
) -> tuple[str, str, int]:
    """Wire one doc through the pipeline. Returns
    ``(upload_id, kb_id, question_count)``."""
    from core.database.session import SessionLocal
    from core.services.evals.eval_service import EvalService
    from core.services.ingestion_queue import enqueue_upload
    from core.services.upload_service import UploadService

    source_key = f"benchmark:{key}"
    kb_name = f"benchmark:{key}:{doc_path.name}"

    db = SessionLocal()
    try:
        svc = UploadService(db, org_id=org_id)
        upload, kb, run = await svc.create_upload_from_file(
            file_path=doc_path,
            file_name=doc_path.name,
            kb_name=kb_name,
            kb_meta_data={"source": source_key, "benchmark_key": key},
            upload_meta_data={"source": source_key},
            enqueue_ingestion=False,
        )
        eval_set = EvalService().import_eval(
            db,
            upload_id=upload.id,
            org_id=org_id,
            questions=questions,
            source_key=source_key,
        )
        # Ingestion fires AFTER the question rows are pre-seeded — the auto-run
        # task then finds them and skips LLM question generation.
        await enqueue_upload(upload.id, org_id, run.id)
        return str(upload.id), str(kb.id), eval_set.question_count
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "key",
        help="Dataset folder name under rag-benchmarks/ (e.g. 'hotpotqa-mini', 'stub')",
    )
    parser.add_argument(
        "--org-id",
        default=None,
        help="Organization UUID. Defaults to settings.DEFAULT_ORG_ID (single-tenant).",
    )
    args = parser.parse_args()

    dataset_dir = _dataset_dir(args.key)
    qa_by_doc = _load_qa(dataset_dir / "qa.jsonl")
    org_id = _resolve_org_id(args.org_id)

    docs = sorted(p for p in (dataset_dir / "docs").iterdir() if p.is_file())
    if not docs:
        raise SystemExit(f"No documents found under {dataset_dir / 'docs'}")

    missing = [p.name for p in docs if p.name not in qa_by_doc]
    if missing:
        print(
            f"warning: {len(missing)} doc(s) have no matching qa.jsonl rows and will be skipped: {missing}",
            file=sys.stderr,
        )

    print(f"importing dataset={args.key} docs={len(docs)} org_id={org_id}")

    for doc_path in docs:
        questions = qa_by_doc.get(doc_path.name)
        if not questions:
            continue
        upload_id, kb_id, question_count = asyncio.run(
            _import_one_doc(
                key=args.key,
                doc_path=doc_path,
                questions=questions,
                org_id=org_id,
            )
        )
        print(
            f"  ✔ {doc_path.name} → upload={upload_id} kb={kb_id} questions={question_count}"
        )

    print("done — ingestion is running in the background; auto-eval will score against gold Q&A when it completes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
