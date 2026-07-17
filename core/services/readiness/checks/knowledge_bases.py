"""Attached knowledge bases — each linked KB must be fully ingested and
have at least one indexed chunk available for retrieval.

Per-resource sub-check. A KB that's still ingesting doesn't break the call,
it just means the agent can't quote from it yet — so WARNING severity.

The old check only looked at ``Upload.status``, which meant a KB could be
reported "ready" while its own row was still ``processing`` / ``failed``,
or while zero chunks had actually been indexed. This version verifies the
full retrieval chain that a real call depends on:

    KnowledgeBase.status == "ready"
        └─ upload_id is set
            └─ Upload.status == "ready"
                └─ at least one KnowledgeBaseChunk exists for that upload

Any break in the chain → not ready, with a specific reason surfaced in the
failure message so the user can tell "still processing" from "failed" from
"empty KB with no upload".
"""

from __future__ import annotations

from typing import Any, ClassVar, List, Optional, Tuple

from core.services.readiness.base import CheckContext, ShallowCheck
from core.services.readiness.schemas import (
    Category,
    CheckResult,
    ResourceRef,
    Severity,
)


class KnowledgeBasesReadyCheck(ShallowCheck):
    """Every attached KB must be ingested end-to-end (KB row, upload, chunks)."""

    id: ClassVar[str] = "knowledge_bases.ready"
    category: ClassVar[Category] = Category.KNOWLEDGE_BASES
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.knowledge_bases)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No knowledge bases attached."

    async def run(self, ctx: CheckContext) -> CheckResult:
        not_ready: List[Tuple[Any, str]] = []
        for kb in ctx.knowledge_bases:
            reason = _kb_not_ready_reason(ctx.db, kb)
            if reason is not None:
                not_ready.append((kb, reason))

        if not_ready:
            # Include per-KB reasons so the drawer can show "processing" vs
            # "failed" vs "no document uploaded" instead of one flat error.
            parts = [f"{kb.name} ({reason})" for kb, reason in not_ready[:3]]
            if len(not_ready) > 3:
                parts.append(f"+{len(not_ready) - 3} more")
            return self._fail(
                f"Knowledge base(s) not ready: {', '.join(parts)}.",
                remediation=(
                    "Wait for ingestion to finish, re-upload failed documents, "
                    "or upload content to empty knowledge bases."
                ),
                resource_ref=ResourceRef(
                    type="knowledge_base", id=str(not_ready[0][0].id)
                ),
            )
        return self._pass(f"{len(ctx.knowledge_bases)} knowledge base(s) attached.")


def _kb_not_ready_reason(db, kb) -> Optional[str]:
    """Return ``None`` when ``kb`` is fully ready for retrieval, else a short
    reason string used verbatim in the check's failure message.

    The chain a live call needs, in order:

    1. ``KnowledgeBase.status == "ready"`` — the ingestion pipeline flips this
       to ``processing`` while chunking/embedding is in flight and to
       ``failed`` if it errors out. Anything but ``ready`` is not usable.
    2. ``KnowledgeBase.upload_id`` is set — a KB with no upload is empty; a
       call would retrieve nothing. The old check silently passed these.
    3. ``Upload.status == "ready"`` — the source document itself finished
       processing at the storage/parsing layer.
    4. At least one ``KnowledgeBaseChunk`` for that ``upload_id`` — chunks +
       embeddings are what retrieval actually queries. A "ready" upload with
       zero chunks (parser produced nothing, or ingestion crashed after
       flipping status) would fail silently in production.

    Imports are function-local to keep import-time light — matches the file
    style and the pattern used across ``core.services.readiness.checks``.
    """
    from core.models.knowledge_base_chunk import KnowledgeBaseChunk
    from core.models.upload import Upload

    # 1. KB row's own status.
    kb_status = (getattr(kb, "status", None) or "").strip().lower()
    if kb_status and kb_status != "ready":
        return kb_status  # e.g. "processing", "failed"

    # 2. Must have an upload attached.
    upload_id = getattr(kb, "upload_id", None)
    if not upload_id:
        return "no document uploaded"

    # 3. Upload row must exist and be ready.
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if upload is None:
        return "upload row missing"
    upload_status = (getattr(upload, "status", None) or "").strip().lower()
    if upload_status != "ready":
        # Preserve the raw provider-side status so the user knows whether to
        # wait (processing) or act (failed).
        return f"upload {upload_status or 'unknown'}"

    # 4. Chunks must exist for retrieval to return anything. Cheap presence
    # check — LIMIT 1 via ``first()`` on the indexed ``upload_id`` FK.
    has_chunk = (
        db.query(KnowledgeBaseChunk.id)
        .filter(KnowledgeBaseChunk.upload_id == upload_id)
        .first()
        is not None
    )
    if not has_chunk:
        return "no chunks indexed"

    return None
