"""Attached knowledge bases — each linked KB must have ready content.

Per-resource sub-check. A KB that's still ingesting doesn't break the call,
it just means the agent can't quote from it yet — so WARNING severity.
"""

from __future__ import annotations

from typing import ClassVar

from core.services.readiness.base import CheckContext, ShallowCheck
from core.services.readiness.schemas import (
    Category,
    CheckResult,
    ResourceRef,
    Severity,
)


class KnowledgeBasesReadyCheck(ShallowCheck):
    """Every attached KB must exist and have at least one ready upload."""

    id: ClassVar[str] = "knowledge_bases.ready"
    category: ClassVar[Category] = Category.KNOWLEDGE_BASES
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.knowledge_bases)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No knowledge bases attached."

    async def run(self, ctx: CheckContext) -> CheckResult:
        not_ready = [
            kb for kb in ctx.knowledge_bases
            if not _kb_has_ready_upload(ctx.db, kb)
        ]
        if not_ready:
            names = ", ".join(kb.name for kb in not_ready[:3])
            return self._fail(
                f"Knowledge base(s) not ready: {names}.",
                remediation=(
                    "Wait for ingestion to finish, or upload documents to "
                    "these knowledge bases."
                ),
                resource_ref=ResourceRef(
                    type="knowledge_base", id=str(not_ready[0].id)
                ),
            )
        return self._pass(f"{len(ctx.knowledge_bases)} knowledge base(s) attached.")


def _kb_has_ready_upload(db, kb) -> bool:
    """Best-effort readiness read for one KB row. If the KB has an ``upload_id``
    FK, check that ``Upload.status == "ready"``; else assume ready to avoid
    false negatives on KB schemas that link uploads differently."""
    upload_id = getattr(kb, "upload_id", None)
    if not upload_id:
        return True
    from core.models.upload import Upload

    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if upload is None:
        return False
    return getattr(upload, "status", None) == "ready"
