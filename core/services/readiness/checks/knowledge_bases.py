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

from typing import Any, ClassVar, Dict, List, Optional, Tuple

from loguru import logger

from core.services.readiness.base import CheckContext, ShallowCheck
from core.services.readiness.checks._messages import quote
from core.services.readiness.checks._per_resource import (
    PerResourceCheck,
    ResourceProblem,
)
from core.services.readiness.schemas import (
    Category,
    CheckResult,
    ResourceRef,
    Severity,
)


class KnowledgeBasesReadyCheck(PerResourceCheck, ShallowCheck):
    """Every attached KB must be ingested end-to-end (KB row, upload, chunks)."""

    id: ClassVar[str] = "knowledge_bases.ready"
    category: ClassVar[Category] = Category.KNOWLEDGE_BASES
    severity: ClassVar[Severity] = Severity.WARNING
    resource_ref_type: ClassVar[str] = "knowledge_base"

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.knowledge_bases)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No knowledge bases attached."

    def _resources(self, ctx: CheckContext) -> List[Any]:
        return ctx.knowledge_bases

    def _summary_message(self, count: int) -> str:
        return f"{count} knowledge base(s) attached."

    async def _check_one(
        self, ctx: CheckContext, kb: Any, shared: Any
    ) -> Optional[ResourceProblem]:
        reason = _kb_not_ready_reason(ctx.db, kb)
        if reason is None:
            return None
        return ResourceProblem(
            f"{quote(kb.name)} isn't ready to use — {reason}.",
            remediation=(
                "Wait for ingestion to finish, or re-upload the document if it "
                "failed."
            ),
        )


class KnowledgeBaseEmbeddingModelConfiguredCheck(PerResourceCheck, ShallowCheck):
    """Every attached KB must have a complete ingestion run declaring which
    embedding model was used.

    Reads from ``KB.active_run()`` (the ingestion run row that owns the KB's
    stored vectors) — NOT from ``AgentConfig.knowledge_model_id``. The
    retrieval path in ``document_tool_service.handle_read_document`` uses the
    ingestion run's ``embedding_provider`` / ``embedding_model`` /
    ``embedding_dimensions`` to build the embedder that encodes the user's
    query; ``knowledge_model_id`` is not consulted at call time. Validating
    the field retrieval actually uses is the only way this check reflects
    real behavior.

    Only relevant when the agent has KBs attached; a prompt-only agent
    doesn't need embeddings at all.
    """

    id: ClassVar[str] = "knowledge_bases.embedding_model_configured"
    category: ClassVar[Category] = Category.KNOWLEDGE_BASES
    severity: ClassVar[Severity] = Severity.BLOCKER
    resource_ref_type: ClassVar[str] = "knowledge_base"

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.knowledge_bases)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No knowledge bases attached — embedding model not required."

    def _resources(self, ctx: CheckContext) -> List[Any]:
        return ctx.knowledge_bases

    def _summary_message(self, count: int) -> str:
        return f"All {count} KB(s) declare an embedding model."

    async def _check_one(
        self, ctx: CheckContext, kb: Any, shared: Any
    ) -> Optional[ResourceProblem]:
        # A KB is INCOMPLETE when its active_run doesn't declare an
        # embedding_model — retrieval can't embed the query without it.
        active_run = kb.active_run() if hasattr(kb, "active_run") else None
        if active_run is None:
            # KB has no ingestion run at all — ``KnowledgeBasesReadyCheck``
            # already surfaces "no upload / not ready", so don't double-report.
            return None
        model_slug = (getattr(active_run, "embedding_model", None) or "").strip()
        if model_slug:
            return None
        return ResourceProblem(
            f"{quote(kb.name)} can't be searched — its ingestion didn't record "
            "an embedding model.",
            remediation=(
                "Re-run ingestion for this knowledge base with a valid "
                "embedding provider and model."
            ),
        )


class KnowledgeBaseEmbeddingKeyUsableCheck(ShallowCheck):
    """Every KB's ingestion embedding provider must have a usable API key in
    the org.

    The retrieval path calls ``ProviderKeyService.get_key(db, org_id,
    provider_slug)`` at call time to obtain the API key for whichever provider
    a KB was ingested with. Match that lookup here so a green readiness means
    retrieval WILL find a usable key. Grouped per-provider so N KBs sharing
    one provider produce ONE lookup instead of N. Skipped for KBs that lack a
    complete ingestion run — the sibling check reports that separately.
    """

    id: ClassVar[str] = "knowledge_bases.embedding_key_usable"
    category: ClassVar[Category] = Category.KNOWLEDGE_BASES
    severity: ClassVar[Severity] = Severity.BLOCKER

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.knowledge_bases)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No knowledge bases attached — no embedding provider to check."

    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.services.rag.provider_keys import ProviderKeyService

        # Group KBs by their ingestion provider — one key lookup per distinct
        # provider, no matter how many KBs use it.
        kbs_by_provider: Dict[str, List[Any]] = {}
        for kb in ctx.knowledge_bases:
            active_run = kb.active_run() if hasattr(kb, "active_run") else None
            if active_run is None:
                continue
            provider = (getattr(active_run, "embedding_provider", None) or "").strip()
            if not provider:
                # Sibling check surfaces this as "ingestion incomplete".
                continue
            kbs_by_provider.setdefault(provider, []).append(kb)

        if not kbs_by_provider:
            return [self._skip(
                "No attached KB has a complete ingestion run to check the key for."
            )]

        results: List[CheckResult] = []
        for provider, kbs in kbs_by_provider.items():
            try:
                key = ProviderKeyService.get_key(ctx.db, ctx.org_id, provider)
            except Exception:  # noqa: BLE001 — decrypt failure inside get_key
                # get_key returns None on missing key; a raise here means the
                # ciphertext itself is un-decryptable (rotated JWT_SECRET_KEY) —
                # a real misconfiguration, not expected control flow, so capture
                # the full traceback (per logging standards) rather than a
                # message-only debug line. The user still sees the same
                # "no usable key" row.
                logger.exception(
                    "[readiness] embedding key lookup/decrypt failed for provider '{}'",
                    provider,
                )
                key = None
            if key:
                continue
            kb_names = ", ".join(quote(kb.name) for kb in kbs[:2])
            more_kbs = f" and {len(kbs) - 2} more" if len(kbs) > 2 else ""
            results.append(
                self._fail(
                    f"The “{provider}” embedding provider has no usable API "
                    f"key — search won't work for {kb_names}{more_kbs}.",
                    remediation=(
                        f"Open Services → {provider} and add (or re-enter) an "
                        "active API key."
                    ),
                    check_id=self._result_id(provider),
                )
            )
        if results:
            return results
        return [self._pass(
            f"API key available for all {len(kbs_by_provider)} KB embedding "
            f"provider(s)."
        )]


class KnowledgeBaseEmbeddingMatchCheck(ShallowCheck):
    """All attached KBs should share the same embedding model.

    ``document_tool_service.handle_read_document`` groups uploads by
    ``(vector_store, provider, model, dims)`` and embeds the user's query ONCE
    per group using that group's embedding model. If two KBs are ingested with
    different embedding models, the query gets embedded in each group's vector
    space — technically correct per-group, but each embed is a real API call
    and results are only comparable within a group. Flagging this as WARNING
    so the operator knows retrieval quality/latency is impacted, without
    blocking publish for agents that intentionally mix providers.
    """

    id: ClassVar[str] = "knowledge_bases.embedding_model_matches"
    category: ClassVar[Category] = Category.KNOWLEDGE_BASES
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.knowledge_bases)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No knowledge bases attached."

    async def run(self, ctx: CheckContext) -> CheckResult:
        # Group KBs by embedding "space" — ``(provider, model, dimensions)``.
        # These are exactly the fields ``document_tool_service`` groups by,
        # so a single group means "one query embedding covers everything";
        # multiple groups mean "N embeddings + N searches per call".
        by_space: Dict[Tuple[str, str, Any], List[Any]] = {}
        for kb in ctx.knowledge_bases:
            active_run = kb.active_run() if hasattr(kb, "active_run") else None
            if active_run is None:
                continue
            provider = (getattr(active_run, "embedding_provider", None) or "").strip()
            model = (getattr(active_run, "embedding_model", None) or "").strip()
            if not provider or not model:
                # Reported by ``embedding_model_configured``.
                continue
            dims = getattr(active_run, "embedding_dimensions", None)
            by_space.setdefault((provider, model.lower(), dims), []).append(kb)

        if len(by_space) <= 1:
            # Zero groups → nothing to compare (sibling check already
            # reports incomplete ingestion). One group → all KBs agree.
            if not by_space:
                return self._skip("No attached KB has a complete ingestion run.")
            (provider, model, _dims), _ = next(iter(by_space.items()))
            return self._pass(
                f"All {len(ctx.knowledge_bases)} KB(s) share one embedding "
                f"space: {provider}/{model}."
            )

        # Two or more distinct spaces — one set-level warning (this is a
        # comparison across all KBs, not a per-KB problem).
        return self._fail(
            f"Your knowledge bases were built with {len(by_space)} different "
            "embedding models, so search runs separately for each group — "
            "slower and more expensive, and results can't be ranked together.",
            remediation=(
                "Re-ingest the knowledge bases so they all use one embedding "
                "provider and model, or detach the ones that differ."
            ),
        )


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
        if kb_status == "failed":
            return "ingestion failed"
        return f"it's still {kb_status}"

    # 2. Must have an upload attached.
    upload_id = getattr(kb, "upload_id", None)
    if not upload_id:
        return "no document has been uploaded"

    # 3. Upload row must exist and be ready.
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if upload is None:
        return "its uploaded document is missing"
    upload_status = (getattr(upload, "status", None) or "").strip().lower()
    if upload_status != "ready":
        # Preserve the raw provider-side status so the user knows whether to
        # wait (processing) or act (failed).
        if upload_status == "failed":
            return "its document failed to process"
        return f"its document is still {upload_status or 'processing'}"

    # 4. Chunks must exist for retrieval to return anything. Cheap presence
    # check — LIMIT 1 via ``first()`` on the indexed ``upload_id`` FK.
    has_chunk = (
        db.query(KnowledgeBaseChunk.id)
        .filter(KnowledgeBaseChunk.upload_id == upload_id)
        .first()
        is not None
    )
    if not has_chunk:
        return "nothing was indexed from its document"

    return None
