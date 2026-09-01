"""Unit tests for the shared model-language-support resolver and the STT/TTS
``model_language_match`` checks that consume it.

These lock the behavior of ``resolve_supported_languages`` — extracted so the
STT and TTS checks stop each issuing the identical ``ModelLanguage`` query
inline (DRY + "checks don't touch the DB directly"). The important invariants:

* ``None`` return  ⇒ "metadata not seeded" (the old ``if not rows`` skip path),
* a returned set   ⇒ drives the pass/fail language-membership decision,
* one query per model per run (the resolver caches on ``ctx``), shared by both
  the STT and TTS checks.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from core.services.readiness.checks._language import resolve_supported_languages
from core.services.readiness.checks.stt import STTModelLanguageMatchCheck
from core.services.readiness.checks.tts import TTSModelLanguageMatchCheck
from core.services.readiness.schemas import Status


class _FakeDB:
    """Minimal stand-in for a SQLAlchemy Session that records how many queries
    ran, so the caching assertion is real."""

    def __init__(self, rows):
        self._rows = rows
        self.query_count = 0

    def query(self, *args, **kwargs):
        self.query_count += 1
        return self

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self._rows


def _leg(model_id=None, name="model-x", *, language_code=None):
    settings = {"language_code": language_code} if language_code else {}
    model = SimpleNamespace(id=model_id, name=name) if model_id else None
    return SimpleNamespace(model=model, settings=settings)


def _ctx(db, *, stt=None, tts=None):
    # Real object (not MagicMock) so the ``getattr(ctx, "_..._cache", None)``
    # cache-miss check behaves — a MagicMock would auto-create a truthy attr.
    return SimpleNamespace(
        db=db,
        org_id="org-uuid",
        config=SimpleNamespace(language_id=None),
        stt=stt or _leg(),
        tts=tts or _leg(),
        is_s2s=False,
    )


class TestResolveSupportedLanguages:
    def test_returns_lowercased_set_from_rows(self):
        db = _FakeDB([("EN",), ("Hi",), ("es",)])
        ctx = _ctx(db, stt=_leg("m1"))
        assert resolve_supported_languages(ctx, "stt") == {"en", "hi", "es"}

    def test_no_rows_returns_none_not_empty_set(self):
        # None is the "metadata not seeded → skip" signal; must NOT collapse to
        # an empty set (which would read as "supports nothing → fail").
        ctx = _ctx(_FakeDB([]), stt=_leg("m1"))
        assert resolve_supported_languages(ctx, "stt") is None

    def test_missing_model_returns_none_without_query(self):
        db = _FakeDB([("en",)])
        ctx = _ctx(db, stt=_leg())  # no model
        assert resolve_supported_languages(ctx, "stt") is None
        assert db.query_count == 0

    def test_result_is_cached_per_model(self):
        db = _FakeDB([("en",)])
        ctx = _ctx(db, stt=_leg("m1"))
        first = resolve_supported_languages(ctx, "stt")
        second = resolve_supported_languages(ctx, "stt")
        assert first == second == {"en"}
        assert db.query_count == 1  # second call served from the per-run cache

    def test_distinct_models_each_query_once(self):
        db = _FakeDB([("en",)])
        ctx = _ctx(db, stt=_leg("m1"), tts=_leg("m2"))
        resolve_supported_languages(ctx, "stt")
        resolve_supported_languages(ctx, "tts")
        assert db.query_count == 2


class TestModelLanguageMatchChecks:
    """The STT and TTS checks share identical shape; assert both drive off the
    resolver's None/set contract."""

    def _run(self, check, ctx):
        return asyncio.run(check.run(ctx))

    def test_stt_pass_when_language_supported(self):
        ctx = _ctx(_FakeDB([("en",), ("hi",)]), stt=_leg("m1", "whisper", language_code="en"))
        result = self._run(STTModelLanguageMatchCheck(), ctx)
        assert result.status == Status.PASS

    def test_stt_fail_when_language_unsupported(self):
        ctx = _ctx(_FakeDB([("fr",)]), stt=_leg("m1", "whisper", language_code="en"))
        result = self._run(STTModelLanguageMatchCheck(), ctx)
        assert result.status == Status.FAIL

    def test_stt_skip_when_metadata_not_seeded(self):
        ctx = _ctx(_FakeDB([]), stt=_leg("m1", "whisper", language_code="en"))
        result = self._run(STTModelLanguageMatchCheck(), ctx)
        assert result.status == Status.SKIPPED

    def test_tts_pass_when_language_supported(self):
        ctx = _ctx(_FakeDB([("en",)]), tts=_leg("m2", "eleven", language_code="EN"))
        result = self._run(TTSModelLanguageMatchCheck(), ctx)
        assert result.status == Status.PASS

    def test_tts_skip_when_metadata_not_seeded(self):
        ctx = _ctx(_FakeDB([]), tts=_leg("m2", "eleven", language_code="en"))
        result = self._run(TTSModelLanguageMatchCheck(), ctx)
        assert result.status == Status.SKIPPED
