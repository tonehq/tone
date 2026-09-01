"""Shared language-code resolver for readiness checks.

Every language-aware check (STT language, TTS language, STT model-match,
TTS model-match, TTS voice-match) needs the same lookup: "what language
code is this agent configured for on this leg (STT / TTS)?"

The resolution mirrors ``service_resolver._build_service_specs``: the
per-leg JSONB settings key (``language_code`` → ``language``) wins, with
the AgentConfig-level ``language_id`` FK as fallback so agents that set
language once at the top level don't have to duplicate the code in each
JSONB blob.

Kept in its own module (rather than inlined into ``_common.py``) because
the language checks don't fit the leg-spec mixin shape in ``_common``;
they consume the leg spec + the agent config + a DB session.
"""

from __future__ import annotations

from typing import Optional, Set

from core.services.readiness.base import CheckContext


def resolve_language_code(ctx: CheckContext, settings_attr: str) -> Optional[str]:
    """Return the effective language code (e.g. ``"en"``, ``"hi"``) for a leg,
    or ``None`` if nothing is configured.

    ``settings_attr`` is the ``CheckContext`` attribute holding the leg spec:
    either ``"stt"`` or ``"tts"``. The lookup order:

    1. JSONB settings on the leg — the per-leg override wins.
    2. ``AgentConfig.language_id`` FK → ``ModelLanguage.name``.
    3. ``None`` when nothing is configured.

    The FK-resolved value is cached on the ``ctx`` under a private
    attribute so multiple checks in one readiness run share a single
    ``SELECT name FROM model_languages`` query. The setattr is guarded
    (dataclass slots or immutable ctx would raise) — caching is an
    optimization, not correctness-critical.
    """
    spec = getattr(ctx, settings_attr, None)
    if spec is not None:
        settings = spec.settings or {}
        raw = settings.get("language_code") or settings.get("language")
        if raw:
            code = str(raw).strip()
            if code:
                return code

    config = getattr(ctx, "config", None)
    if config is None:
        return None
    language_id = getattr(config, "language_id", None)
    if language_id is None:
        return None

    cached = getattr(ctx, "_readiness_lang_code_cache", None)
    if cached is not None and language_id in cached:
        return cached[language_id]

    from core.models.model_language import ModelLanguage

    code = (
        ctx.db.query(ModelLanguage.name)
        .filter(ModelLanguage.id == language_id)
        .scalar()
    )
    if code:
        code = str(code).strip() or None

    # ``CheckContext`` is a plain (non-slotted) dataclass — setattr always
    # succeeds. Kept simple: no try/except, no silent swallow. If the
    # dataclass is ever converted to slots/frozen, this write will raise
    # loudly and force us to add the cache field explicitly on the class
    # rather than fail silently and degrade to N-queries.
    if cached is None:
        cached = {}
        ctx._readiness_lang_code_cache = cached  # type: ignore[attr-defined]
    cached[language_id] = code

    return code


def resolve_supported_languages(ctx: CheckContext, leg: str) -> Optional[Set[str]]:
    """Return the set of language names (lowercased) the leg's model declares
    support for, ``None`` when the model has NO seeded language metadata (no
    ``ModelLanguage`` rows), or ``None`` when the leg has no resolved model.

    ``leg`` is ``"stt"`` or ``"tts"``. This is the single source for the
    "which languages does this model support?" lookup shared by the STT and TTS
    ``model_language_match`` checks — previously each check issued the identical
    ``SELECT name FROM model_languages WHERE model_id = … AND is_active`` query
    inline (DRY + the checks-touch-the-DB concern). Mirrors
    :func:`resolve_language_code`: rows are read once per model and cached on
    ``ctx`` so both checks in one readiness run share a single query per model.

    The ``None`` vs empty-set distinction is deliberate and preserves the
    callers' original behavior: ``None`` means "metadata not seeded → skip"
    (the old ``if not rows`` branch), while a returned set (membership test)
    drives the pass/fail decision.
    """
    spec = getattr(ctx, leg, None)
    model = getattr(spec, "model", None) if spec is not None else None
    if model is None:
        return None

    cache = getattr(ctx, "_readiness_model_langs_cache", None)
    if cache is not None and model.id in cache:
        return cache[model.id]

    from core.models.model_language import ModelLanguage

    rows = (
        ctx.db.query(ModelLanguage.name)
        .filter(
            ModelLanguage.model_id == model.id,
            ModelLanguage.is_active.is_(True),
        )
        .all()
    )
    # No rows at all ⇒ metadata not seeded (skip). Rows present ⇒ the supported
    # set (may be empty only if names are blank, which the schema disallows).
    supported: Optional[Set[str]] = (
        {str(r[0]).strip().lower() for r in rows if r[0]} if rows else None
    )

    if cache is None:
        cache = {}
        ctx._readiness_model_langs_cache = cache  # type: ignore[attr-defined]
    cache[model.id] = supported

    return supported
