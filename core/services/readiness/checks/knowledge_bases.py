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


class KnowledgeBaseEmbeddingModelConfiguredCheck(ShallowCheck):
    """An embedding model must be selected when KBs are attached.

    ``AgentConfig.knowledge_model_id`` is the FK the retrieval path uses to
    embed the user's turn before searching KB chunks. Without it, RAG has
    nothing to embed with and every KB question falls back to the base LLM —
    silently. Only relevant when the agent actually has KBs attached; a
    prompt-only agent doesn't need one.
    """

    id: ClassVar[str] = "knowledge_bases.embedding_model_configured"
    category: ClassVar[Category] = Category.KNOWLEDGE_BASES
    severity: ClassVar[Severity] = Severity.BLOCKER

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.knowledge_bases)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No knowledge bases attached — embedding model not required."

    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.models.model import Model

        knowledge_model_id = (
            getattr(ctx.config, "knowledge_model_id", None) if ctx.config else None
        )
        if knowledge_model_id is None:
            return self._fail(
                "Knowledge model (embedding) is not selected for this agent.",
                remediation=(
                    "Pick a knowledge model on the agent so retrieval can "
                    "embed the user's message before searching the KB."
                ),
            )
        model = (
            ctx.db.query(Model).filter(Model.id == knowledge_model_id).first()
        )
        if model is None:
            return self._fail(
                "Selected knowledge model no longer exists.",
                remediation="Pick a different knowledge model.",
                resource_ref=ResourceRef(
                    type="model", id=str(knowledge_model_id)
                ),
            )
        return self._pass(f"Knowledge (embedding) model: {model.name}")


class KnowledgeBaseEmbeddingKeyUsableCheck(ShallowCheck):
    """The embedding model's provider must have a usable API key in the org.

    Combines "key present" + "key decrypts" into one check — presence and
    decrypt are the same cost (one row query + one decrypt call), and
    separating them into two checks would double the drawer noise for a
    single "your embedding key is broken" story. Reuses the same key-lookup
    semantics as ``ContextBuilder._fetch_api_keys`` (service_type match →
    NULL-service_type fallback) so a green readiness means the retrieval
    path finds the same key at call time.
    """

    id: ClassVar[str] = "knowledge_bases.embedding_key_usable"
    category: ClassVar[Category] = Category.KNOWLEDGE_BASES
    severity: ClassVar[Severity] = Severity.BLOCKER

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.knowledge_bases) and (
            ctx.config is not None
            and getattr(ctx.config, "knowledge_model_id", None) is not None
        )

    def skip_reason(self, ctx: CheckContext) -> str:
        if not ctx.knowledge_bases:
            return "No knowledge bases attached."
        return "Embedding model not selected (see embedding-model check)."

    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.models.api_key import ApiKey
        from core.models.model import Model
        from core.utils.encryption import decrypt

        model = (
            ctx.db.query(Model)
            .filter(Model.id == ctx.config.knowledge_model_id)
            .first()
        )
        if model is None:
            # The sibling check already reports this — skip to avoid duplicate noise.
            return self._skip("Embedding model row missing (see model check).")

        api_key = (
            ctx.db.query(ApiKey)
            .filter(
                ApiKey.provider_id == model.provider_id,
                ApiKey.organization_id == ctx.org_id,
                ApiKey.is_active.is_(True),
                ApiKey.service_type == "llm",
            )
            .order_by(ApiKey.is_default.desc())
            .first()
        )
        if api_key is None:
            # Fall back to a NULL service_type key — same semantics as
            # ContextBuilder._fetch_api_keys (context.py:194-197).
            api_key = (
                ctx.db.query(ApiKey)
                .filter(
                    ApiKey.provider_id == model.provider_id,
                    ApiKey.organization_id == ctx.org_id,
                    ApiKey.is_active.is_(True),
                    ApiKey.service_type.is_(None),
                )
                .order_by(ApiKey.is_default.desc())
                .first()
            )

        if api_key is None:
            return self._fail(
                "No API key saved for the embedding provider.",
                remediation=(
                    "Open Services → the embedding provider and add a key so "
                    "KB retrieval can embed user turns."
                ),
                resource_ref=ResourceRef(
                    type="provider", id=str(model.provider_id)
                ),
            )
        try:
            decrypt(api_key.encrypted_key)
        except Exception:  # noqa: BLE001 — decrypt failure (rotated secret)
            return self._fail(
                "Embedding provider API key cannot be decrypted with the "
                "current server secret.",
                remediation=(
                    "The encryption secret has changed since this key was "
                    "saved. Re-enter the embedding provider's API key."
                ),
                resource_ref=ResourceRef(type="api_key", id=str(api_key.id)),
            )
        return self._pass("Embedding provider API key is present and decrypts.")


class KnowledgeBaseEmbeddingMatchCheck(ShallowCheck):
    """Every attached KB's active ingestion run must use the SAME embedding
    model as the agent's ``knowledge_model_id``.

    RAG only works when the query embedding lives in the SAME vector space as
    the stored chunk embeddings. If a KB was ingested with
    ``text-embedding-3-small`` but the agent's ``knowledge_model_id`` resolves
    to ``text-embedding-ada-002``, the query vector has different dimensions
    (or a different geometry) than the stored vectors — retrieval returns
    semantically wrong results, silently, with no error at call time.

    Skipped when the KB has no ``active_run_ref`` (KB not ingested — already
    reported by ``KnowledgeBasesReadyCheck``) or when the agent has no
    ``knowledge_model_id`` (already reported by the embedding-model check).
    """

    id: ClassVar[str] = "knowledge_bases.embedding_model_matches"
    category: ClassVar[Category] = Category.KNOWLEDGE_BASES
    severity: ClassVar[Severity] = Severity.BLOCKER

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.knowledge_bases) and (
            ctx.config is not None
            and getattr(ctx.config, "knowledge_model_id", None) is not None
        )

    def skip_reason(self, ctx: CheckContext) -> str:
        if not ctx.knowledge_bases:
            return "No knowledge bases attached."
        return "Embedding model not selected (see embedding-model check)."

    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.models.model import Model

        agent_model = (
            ctx.db.query(Model)
            .filter(Model.id == ctx.config.knowledge_model_id)
            .first()
        )
        if agent_model is None:
            # Sibling check reports the missing model row; skip to avoid noise.
            return self._skip("Embedding model row missing (see model check).")
        agent_model_slug = (getattr(agent_model, "name", None) or "").strip()
        if not agent_model_slug:
            # Seed data anomaly — model row exists but has no name/slug. Can't
            # meaningfully compare; skip rather than fail every attached KB.
            return self._skip("Agent's embedding model has no slug — cannot compare.")

        mismatches: List[Tuple[Any, str]] = []
        for kb in ctx.knowledge_bases:
            active_run = kb.active_run() if hasattr(kb, "active_run") else None
            if active_run is None:
                # KB not ingested yet — KnowledgeBasesReadyCheck already flags it.
                continue
            kb_slug = (getattr(active_run, "embedding_model", None) or "").strip()
            if not kb_slug:
                # Legacy run row without slug metadata — can't compare, don't false-flag.
                continue
            if not _slugs_equivalent(kb_slug, agent_model_slug):
                mismatches.append((kb, kb_slug))

        if mismatches:
            parts = [
                f"'{kb.name}' indexed with '{slug}'"
                for kb, slug in mismatches[:3]
            ]
            if len(mismatches) > 3:
                parts.append(f"+{len(mismatches) - 3} more")
            return self._fail(
                f"Knowledge base embedding-model mismatch: agent uses "
                f"'{agent_model_slug}' but "
                + ", ".join(parts)
                + ". Retrieval will return wrong results.",
                remediation=(
                    "Either switch the agent's knowledge model to match, or "
                    "re-ingest the KB(s) with the agent's current model."
                ),
                resource_ref=ResourceRef(
                    type="knowledge_base", id=str(mismatches[0][0].id)
                ),
            )
        return self._pass(
            f"All {len(ctx.knowledge_bases)} KB(s) match the agent's "
            f"embedding model '{agent_model_slug}'."
        )


def _slugs_equivalent(a: str, b: str) -> bool:
    """Case-insensitive slug comparison that tolerates a provider prefix.

    Ingestion layers occasionally record embeddings as ``"openai/text-embedding-
    3-small"`` (provider-prefixed) while ``Model.name`` stores the bare
    ``"text-embedding-3-small"``. Both refer to the SAME vector space, and the
    strict equality check would false-flag every affected KB. We compare after
    stripping a single leading ``provider/`` segment on either side; anything
    still different genuinely IS different (different model = different
    dimensions = broken retrieval).
    """
    def _strip_prefix(s: str) -> str:
        s = s.strip().lower()
        return s.split("/", 1)[1] if "/" in s else s

    return _strip_prefix(a) == _strip_prefix(b)


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
