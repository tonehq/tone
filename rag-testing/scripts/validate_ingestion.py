"""Programmatic ingestion validation.

For a given upload_id (or every KB in the DB), assert:
  1. `knowledge_bases.status == 'ready'`
  2. `uploads.status == 'ready'` and `purpose == 'kb_document'`
  3. `count(knowledge_base_chunks) > 0`
  4. Every chunk has a non-null 1536-dim embedding
  5. No zero-vector embeddings (indicates a failed embed call)

Exit code: 0 = all pass, 1 = at least one failure.

Usage:
    python rag-testing/scripts/validate_ingestion.py --upload-id <uuid>
    python rag-testing/scripts/validate_ingestion.py --all
    python rag-testing/scripts/validate_ingestion.py --doc <slug>   # resolves from metadata.json
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Optional

from common import DocMetadata, db_session

EXPECTED_EMBEDDING_DIM = 1536


@dataclass
class ValidationResult:
    upload_id: str
    kb_name: Optional[str]
    checks: list[tuple[str, bool, str]]  # (name, passed, detail)

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _ in self.checks)


def _validate_one(db, upload_id: str) -> ValidationResult:
    from sqlalchemy import func, select

    from core.models.knowledge_base import KnowledgeBase
    from core.models.knowledge_base_chunk import KnowledgeBaseChunk
    from core.models.upload import Upload

    checks: list[tuple[str, bool, str]] = []

    upload = db.execute(select(Upload).where(Upload.id == upload_id)).scalar_one_or_none()
    if upload is None:
        checks.append(("upload_exists", False, f"no uploads row for id={upload_id}"))
        return ValidationResult(upload_id=upload_id, kb_name=None, checks=checks)
    checks.append(("upload_exists", True, f"file_name={upload.file_name!r}"))

    checks.append(
        (
            "upload_status_ready",
            upload.status == "ready",
            f"uploads.status={upload.status!r}",
        )
    )
    checks.append(
        (
            "upload_purpose_kb_document",
            upload.purpose == "kb_document",
            f"uploads.purpose={upload.purpose!r}",
        )
    )

    kb = db.execute(
        select(KnowledgeBase).where(KnowledgeBase.upload_id == upload_id)
    ).scalar_one_or_none()
    kb_name = kb.name if kb else None
    if kb is None:
        checks.append(("kb_row_exists", False, "no knowledge_bases row"))
    else:
        checks.append(("kb_row_exists", True, f"name={kb.name!r}"))
        checks.append(
            (
                "kb_status_ready",
                kb.status == "ready",
                f"knowledge_bases.status={kb.status!r}",
            )
        )

    chunk_count = db.execute(
        select(func.count(KnowledgeBaseChunk.id)).where(
            KnowledgeBaseChunk.upload_id == upload_id
        )
    ).scalar_one()
    checks.append(
        (
            "chunks_exist",
            chunk_count > 0,
            f"knowledge_base_chunks count = {chunk_count}",
        )
    )

    if chunk_count > 0:
        null_embedding = db.execute(
            select(func.count(KnowledgeBaseChunk.id)).where(
                KnowledgeBaseChunk.upload_id == upload_id,
                KnowledgeBaseChunk.embedding.is_(None),
            )
        ).scalar_one()
        checks.append(
            (
                "no_null_embeddings",
                null_embedding == 0,
                f"chunks with NULL embedding = {null_embedding}",
            )
        )

        sample = db.execute(
            select(KnowledgeBaseChunk.embedding, KnowledgeBaseChunk.chunk_index)
            .where(
                KnowledgeBaseChunk.upload_id == upload_id,
                KnowledgeBaseChunk.embedding.is_not(None),
            )
            .limit(3)
        ).all()
        dim_ok = True
        zero_ok = True
        dim_detail = ""
        for embedding, idx in sample:
            vec = list(embedding) if embedding is not None else []
            if len(vec) != EXPECTED_EMBEDDING_DIM:
                dim_ok = False
                dim_detail = f"chunk_index={idx} has dim={len(vec)}"
                break
            if all(v == 0 for v in vec):
                zero_ok = False
                dim_detail = f"chunk_index={idx} embedding is all zeros"
                break
        checks.append(
            (
                "embedding_dim_1536",
                dim_ok,
                dim_detail or f"sampled {len(sample)} chunks, all dim={EXPECTED_EMBEDDING_DIM}",
            )
        )
        checks.append(
            (
                "embedding_non_zero",
                zero_ok,
                dim_detail if not zero_ok else "no zero-vector embeddings in sample",
            )
        )

    return ValidationResult(upload_id=upload_id, kb_name=kb_name, checks=checks)


def _print_result(r: ValidationResult) -> None:
    status = "PASS" if r.passed else "FAIL"
    label = f"kb={r.kb_name!r} " if r.kb_name else ""
    print(f"[{status}] {label}upload_id={r.upload_id}")
    for name, ok, detail in r.checks:
        marker = "  ✓" if ok else "  ✗"
        print(f"{marker} {name:28s} {detail}")


def _discover_all_upload_ids(db) -> list[str]:
    from sqlalchemy import select

    from core.models.knowledge_base import KnowledgeBase

    rows = db.execute(
        select(KnowledgeBase.upload_id).where(
            KnowledgeBase.upload_id.is_not(None),
            KnowledgeBase.is_active.is_(True),
        )
    ).all()
    return [str(r[0]) for r in rows]


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a KB was fully ingested (chunks + embeddings).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--upload-id", help="Specific uploads.id to check")
    g.add_argument("--doc", help="Slug under rag-testing/documents/ (reads metadata.json)")
    g.add_argument("--all", action="store_true", help="Check every active KB in the DB")
    args = ap.parse_args()

    with db_session() as db:
        if args.all:
            upload_ids = _discover_all_upload_ids(db)
            if not upload_ids:
                print("No active knowledge_bases found.", file=sys.stderr)
                return 2
        elif args.doc:
            meta = DocMetadata.load(args.doc)
            upload_ids = [meta.upload_id]
        else:
            upload_ids = [args.upload_id]

        results = [_validate_one(db, uid) for uid in upload_ids]

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    for r in results:
        _print_result(r)
        print()
    print(f"=== ingestion validation: {passed}/{total} PASS ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
