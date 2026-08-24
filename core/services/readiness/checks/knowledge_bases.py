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


class KnowledgeBaseEmbeddingModelConfiguredCheck(ShallowCheck):
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

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.knowledge_bases)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No knowledge bases attached — embedding model not required."

    async def run(self, ctx: CheckContext) -> CheckResult:
        # Per-KB "incomplete ingestion" collector. A KB is INCOMPLETE when
        # its active_run doesn't declare an embedding_model — the retrieval
        # groupby key (``vector_store, provider, model, dims``) would blow up
        # or silently drop the KB from search.
        incomplete: List[Tuple[Any, str]] = []
        for kb in ctx.knowledge_bases:
            active_run = kb.active_run() if hasattr(kb, "active_run") else None
            if active_run is None:
                # KB has no ingestion run at all — ``KnowledgeBasesReadyCheck``
                # already surfaces "no upload / not ready", so don't double-report.
                continue
            model_slug = (getattr(active_run, "embedding_model", None) or "").strip()
            if not model_slug:
                incomplete.append((kb, "no embedding model recorded"))
                continue

        if incomplete:
            parts = [f"'{kb.name}' ({reason})" for kb, reason in incomplete[:3]]
            if len(incomplete) > 3:
                parts.append(f"+{len(incomplete) - 3} more")
            return self._fail(
                f"KB ingestion is incomplete: {', '.join(parts)}. Retrieval "
                f"cannot embed the query without the ingestion's embedding model.",
                remediation=(
                    "Re-run ingestion for the affected KB(s) with a valid "
                    "embedding provider + model."
                ),
                resource_ref=ResourceRef(
                    type="knowledge_base", id=str(incomplete[0][0].id)
                ),
            )
        return self._pass(
            f"All {len(ctx.knowledge_bases)} KB(s) declare an embedding model."
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
            return self._skip(
                "No attached KB has a complete ingestion run to check the key for."
            )

        missing: List[Tuple[str, List[Any]]] = []  # (provider, kbs)
        for provider, kbs in kbs_by_provider.items():
            try:
                key = ProviderKeyService.get_key(ctx.db, ctx.org_id, provider)
            except Exception:  # noqa: BLE001 — decrypt failure inside get_key
                # get_key returns None on missing key; a raise here means the
                # ciphertext itself is un-decryptable (rotated JWT_SECRET_KEY),
                # which is a different actionable failure worth flagging.
                missing.append((provider, kbs))
                continue
            if not key:
                missing.append((provider, kbs))

        if missing:
            parts = []
            for provider, kbs in missing[:3]:
                kb_names = ", ".join(kb.name for kb in kbs[:2])
                more_kbs = f" +{len(kbs) - 2} more" if len(kbs) > 2 else ""
                parts.append(f"'{provider}' (used by {kb_names}{more_kbs})")
            if len(missing) > 3:
                parts.append(f"+{len(missing) - 3} more providers")
            return self._fail(
                f"Embedding provider API key missing or unreadable: "
                f"{'; '.join(parts)}. Retrieval will fail for these KBs.",
                remediation=(
                    "Open Services → the affected provider and add (or "
                    "re-enter) an active API key."
                ),
            )
        return self._pass(
            f"API key available for all {len(kbs_by_provider)} KB embedding "
            f"provider(s)."
        )


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

        # Two or more distinct spaces — surface the groups so the operator
        # can decide whether to re-ingest one KB with the other's model.
        parts = [
            f"{provider}/{model} ({', '.join(kb.name for kb in kbs[:2])}"
            f"{' +' + str(len(kbs) - 2) + ' more' if len(kbs) > 2 else ''})"
            for (provider, model, _dims), kbs in list(by_space.items())[:3]
        ]
        if len(by_space) > 3:
            parts.append(f"+{len(by_space) - 3} more spaces")
        return self._fail(
            f"Attached KBs use different embedding spaces: {'; '.join(parts)}. "
            f"Retrieval will embed the query once per space (extra latency + "
            f"cost) and results are only comparable within each space.",
            remediation=(
                "Re-ingest KBs so they all share one embedding provider + "
                "model, or detach the KBs whose space differs from the rest."
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
