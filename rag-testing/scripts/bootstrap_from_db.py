"""Scan the DB for every active KnowledgeBase and register each one in
`rag-testing/documents/<slug>/` with a `metadata.json`.

This makes the eval suite auto-discoverable: any KB that exists in the DB but
does not yet have a folder here is created empty (metadata only). The user
still has to drop the `source.pdf` (or equivalent) into that folder before
question generation.

Idempotency: any doc whose folder already contains `questions.json` is treated
as "already set up" and skipped entirely (metadata + source download both
skipped). Use `--rerun` to reprocess those.

Usage:
    python rag-testing/scripts/bootstrap_from_db.py              # dry run
    python rag-testing/scripts/bootstrap_from_db.py --write      # actually write metadata.json files
    python rag-testing/scripts/bootstrap_from_db.py --write --overwrite  # replace existing metadata.json
    python rag-testing/scripts/bootstrap_from_db.py --write --download-source  # also pull the file from R2
    python rag-testing/scripts/bootstrap_from_db.py --write --download-source --rerun  # process even if questions.json exists
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import DOCS_DIR, db_session, now_iso

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str, upload_id: str) -> str:
    base = _SLUG_RE.sub("-", name.lower()).strip("-") or "kb"
    return f"{base}-{upload_id[:8]}"


def _discover(db) -> list[dict]:
    from sqlalchemy import select

    from core.models.knowledge_base import KnowledgeBase
    from core.models.upload import Upload

    rows = db.execute(
        select(
            KnowledgeBase.id,
            KnowledgeBase.name,
            KnowledgeBase.status,
            KnowledgeBase.upload_id,
            KnowledgeBase.organization_id,
            KnowledgeBase.created_at,
            Upload.file_name,
            Upload.file_path,
        )
        .join(Upload, Upload.id == KnowledgeBase.upload_id, isouter=True)
        .where(
            KnowledgeBase.is_active.is_(True),
            KnowledgeBase.upload_id.is_not(None),
        )
        .order_by(KnowledgeBase.created_at.desc())
    ).all()
    return [
        {
            "kb_id": str(r.id),
            "kb_name": r.name,
            "kb_status": r.status,
            "upload_id": str(r.upload_id),
            "org_id": str(r.organization_id) if r.organization_id else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "file_name": r.file_name,
            "file_path": r.file_path,
        }
        for r in rows
    ]


def _local_source_name(file_name: str | None) -> str:
    """Choose `source.<ext>` for the local copy, derived from the original file_name."""
    if not file_name or "." not in file_name:
        return "source.pdf"
    ext = file_name.rsplit(".", 1)[-1].lower()
    return f"source.{ext}"


def _download_source(entry: dict, folder: Path, *, overwrite: bool) -> str:
    """Pull the file from R2 into <folder>/source.<ext>. Returns a status string."""
    if not entry.get("file_path"):
        return "no file_path in DB"

    local_name = _local_source_name(entry.get("file_name"))
    dest = folder / local_name
    if dest.exists() and not overwrite:
        return f"source present ({local_name})"

    try:
        from core.services.r2_storage_service import R2StorageService

        blob = R2StorageService().download_file(entry["file_path"])
    except Exception as e:
        return f"R2 download failed: {type(e).__name__}: {e}"

    dest.write_bytes(blob)
    return f"downloaded {local_name} ({len(blob):,} bytes)"


def _write_metadata(entry: dict, *, overwrite: bool) -> tuple[Path, Path, str]:
    slug = _slugify(entry["kb_name"] or "kb", entry["upload_id"])
    folder = DOCS_DIR / slug
    folder.mkdir(parents=True, exist_ok=True)
    metadata_path = folder / "metadata.json"

    if metadata_path.exists() and not overwrite:
        return metadata_path, folder, "skipped (exists)"

    local_source = _local_source_name(entry.get("file_name"))
    payload = {
        "doc_slug": slug,
        "upload_id": entry["upload_id"],
        "org_id": entry["org_id"],
        "kb_id": entry["kb_id"],
        "kb_name": entry["kb_name"],
        "kb_status": entry["kb_status"],
        "source_file": local_source,
        "original_file_name": entry["file_name"],
        "ingested_at": entry["created_at"],
        "bootstrapped_at": now_iso(),
    }
    metadata_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    # Detect whether a source file is already sitting in the folder.
    existing_sources = [p.name for p in folder.glob("source.*") if p.is_file()]
    if existing_sources:
        action = "written (source present)"
    else:
        action = "written (needs source file)"
    return metadata_path, folder, action


def main() -> int:
    ap = argparse.ArgumentParser(description="Register every DB KnowledgeBase into rag-testing/documents/.")
    ap.add_argument("--write", action="store_true", help="Actually write metadata.json (default: dry run)")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing metadata.json files")
    ap.add_argument(
        "--download-source",
        action="store_true",
        help="Also download each doc's file from R2 into documents/<slug>/source.<ext>",
    )
    ap.add_argument(
        "--rerun",
        action="store_true",
        help="Reprocess docs even if questions.json already exists (default: skip them)",
    )
    args = ap.parse_args()

    with db_session() as db:
        entries = _discover(db)

    if not entries:
        print("No active knowledge_bases with an upload_id found in the DB.", file=sys.stderr)
        return 2

    print(f"[bootstrap] found {len(entries)} active KB(s) in DB")
    written = 0
    skipped = 0
    needs_source: list[str] = []

    downloaded = 0
    already_done = 0
    download_failures: list[str] = []

    for entry in entries:
        slug = _slugify(entry["kb_name"] or "kb", entry["upload_id"])
        folder = DOCS_DIR / slug
        questions_present = (folder / "questions.json").exists()

        if not args.write:
            marker = "done" if questions_present else "new "
            print(
                f"  [dry] {marker} {slug:40s} kb={entry['kb_name']!r} upload={entry['upload_id'][:8]}"
            )
            if questions_present:
                already_done += 1
            continue

        if questions_present and not args.rerun:
            already_done += 1
            print(f"  {slug:40s} already set up (questions.json present) — pass --rerun to redo")
            continue

        path, folder, action = _write_metadata(entry, overwrite=args.overwrite)
        print(f"  {slug:40s} {action}  ({path.relative_to(DOCS_DIR.parent)})")
        if "written" in action:
            written += 1
        if action.startswith("skipped"):
            skipped += 1

        if args.download_source:
            dl_status = _download_source(entry, folder, overwrite=args.overwrite)
            print(f"    ↳ {dl_status}")
            if dl_status.startswith("downloaded"):
                downloaded += 1
            elif dl_status.startswith("R2 download failed") or dl_status == "no file_path in DB":
                download_failures.append(f"{slug}: {dl_status}")
                needs_source.append(slug)
        elif "needs source" in action:
            needs_source.append(slug)

    if args.write:
        print(
            f"\n[bootstrap] wrote={written} skipped={skipped} "
            f"downloaded={downloaded} already_done={already_done}"
        )
        if download_failures:
            print(f"[bootstrap] {len(download_failures)} R2 download issue(s):")
            for f in download_failures:
                print(f"    {f}")
        if needs_source and not args.download_source:
            print(f"[bootstrap] {len(needs_source)} folder(s) still need a source file placed:")
            for slug in needs_source:
                print(f"    rag-testing/documents/{slug}/source.<ext>")
    else:
        print(
            f"\n[bootstrap] dry run only. {already_done} already set up. "
            "Re-run with --write to process new docs. Add --rerun to redo already-set-up docs."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
