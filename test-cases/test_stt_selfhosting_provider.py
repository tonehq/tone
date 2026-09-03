"""Regression tests for the `test-stt-selfhosting` STT provider branch.

`build_stt` is a long `if provider_name == ...` chain whose failure modes are all
*silent*: a wrong slug, a dropped model id or a falsy API key produce no error —
the agent simply starts with no STT and the call goes deaf. These tests pin the
four values that have to agree for this provider to work.

No network: `GraniteWebSocketSTTService` opens its websocket in `start()`, not in
`__init__`, so construction alone contacts nothing and the tests stay deterministic.
"""

import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.services.pipeline.service_factory import build_stt
from core.services.pipeline.service_resolver import _make_service_spec

PROVIDER_SLUG = "test-stt-selfhosting"
MODEL_NAME = "test-stt-selfhosting"
SEEDED_URL = "wss://testselfhosting.com/ws"


def _spec(**overrides) -> dict:
    """A resolved spec as `_make_service_spec` would produce it for this provider."""
    spec = {
        "provider_name": PROVIDER_SLUG,
        "api_key": "selfhosted-placeholder",
        "model_name": MODEL_NAME,
        "metadata": {"base_url": SEEDED_URL, "sample_rate": 16000},
        "model_meta_data": {},
    }
    spec.update(overrides)
    return spec


def test_builds_the_granite_websocket_service():
    """The branch resolves to a real service rather than falling through to None."""
    svc = build_stt(_spec())
    assert svc is not None, "provider fell through build_stt and would leave the agent deaf"
    assert type(svc).__name__ == "GraniteWebSocketSTTService"


def test_seeded_base_url_is_used_verbatim():
    """`Model.base_url` reaches the service; it is not replaced by a class default."""
    svc = build_stt(_spec())
    assert svc._url == SEEDED_URL


def test_model_id_reaches_the_service():
    """Regression for the reason this branch uses Granite over NvidiaWebSocketService.

    `NvidiaWebSocketService` takes no `model=` argument, so every seeded model id
    would silently collapse to the class default (the live `nvidia` STT bug). If
    this branch is ever repointed at that class, this assertion fails.
    """
    svc = build_stt(_spec(model_name="some-other-weights"))
    assert svc._settings.model == "some-other-weights"


def test_sample_rate_is_forwarded():
    svc = build_stt(_spec(metadata={"base_url": SEEDED_URL, "sample_rate": 8000}))
    assert svc._init_sample_rate == 8000


def test_falls_back_to_default_url_when_base_url_absent():
    """A model row with no base_url must still build, not raise."""
    svc = build_stt(_spec(metadata={}))
    assert svc is not None
    assert svc._url.startswith("wss://")


@pytest.mark.parametrize(
    "wrong_slug",
    [
        "test_stt_selfhosting",   # underscores: what _slugify can never produce
        "Test STT Selfhosting",   # the display name, not the slug
        "test-stt-selfhosted",    # near miss
    ],
)
def test_only_the_exact_slug_matches(wrong_slug):
    """The factory keys off `provider.slug` with no normalization.

    `_slugify` maps `_` -> `-`, so an underscore slug is unreachable; the resolver
    passes the slug through verbatim. A mismatch returns None — no exception, no
    log line the caller sees — which is exactly the trap this pins.
    """
    assert build_stt(_spec(provider_name=wrong_slug)) is None


@pytest.mark.parametrize("falsy_key", [None, "", 0])
def test_missing_api_key_yields_no_spec(falsy_key):
    """A self-hosted provider still needs a non-empty key.

    `_make_service_spec` returns None on a falsy api_key, so the service is never
    built and the agent runs without STT. This is why the branch is seeded with a
    placeholder credential even though the server is unauthenticated.
    """
    provider = SimpleNamespace(slug=PROVIDER_SLUG, display_name="Test STT Selfhosting")
    assert _make_service_spec(provider, MODEL_NAME, falsy_key, {}) is None


def test_spec_is_built_when_key_present():
    provider = SimpleNamespace(slug=PROVIDER_SLUG, display_name="Test STT Selfhosting")
    spec = _make_service_spec(provider, MODEL_NAME, "placeholder", {"base_url": SEEDED_URL})
    assert spec is not None
    assert spec["provider_name"] == PROVIDER_SLUG
    assert build_stt(spec) is not None
