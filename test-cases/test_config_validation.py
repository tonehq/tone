"""Unit tests for shared.config env-var validation.

Covers the fail-fast contract in `Settings._validate_required`:
  - Tier A (MANDATORY_KEYS) is enforced in every env.
  - Tier B (MANDATORY_PROD_KEYS) is added when ENV is not in DEV_ENV_NAMES.
  - INSECURE_PLACEHOLDERS are treated as unset.
  - Missing keys emit a CRITICAL loguru line naming each one and raise
    SystemExit(1) so the pod never binds.

Tests instantiate a fresh `Settings()` per case (bypassing the module-level
singleton) with monkeypatched env vars. `get_infisical_secrets` is stubbed so
Infisical is never contacted.
"""

import io
import re
import sys
import os
import pytest
from loguru import logger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import shared.config as config


# --- Tier A baseline (satisfies every MANDATORY_KEYS entry) -----------------

def _tier_a_env() -> dict[str, str]:
    """One legit value per Tier A key. Kept in-sync with MANDATORY_KEYS."""
    return {
        # Core auth + identity
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/tone",
        "JWT_SECRET_KEY": "a-real-secret-64-chars-long-not-the-placeholder",
        "ENV": "dev",
        "DEFAULT_ORG_ID": "00000000-0000-0000-0000-000000000001",
        "LOG_LEVEL": "INFO",
        # HTTP surface
        "COOKIE_SAMESITE": "lax",
        "CORS_ALLOW_ORIGINS": "http://localhost:3000",
        "CORS_ALLOW_ORIGIN_REGEX": r"https://([a-z0-9-]+\.)*trytone\.ai",
        "APPLICATION_URL": "http://localhost:3000",
        "BASE_API_URL": "http://localhost:8000/api/v1",
        # Call/worker routing
        "CALL_WORKER_PREFIX": "tone-call-worker",
        "OUTBOUND_CALL_WORKER_PREFIX": "tone-outbound-call-worker",
        "OUTBOUND_CALL_HEADLESS_SERVICE": "tone-outbound-call-headless",
        "OUTBOUND_CALL_WORKER_PORT": "8080",
        "POD_SYNC_NAMESPACE": "staging",
        "MAX_CONCURRENT_CALLS": "2",
        # Loki per-call sync tuning
        "LOKI_SYNC_DELAY_SECONDS": "120",
        "LOKI_SYNC_PRE_BUFFER_SECONDS": "30",
        "LOKI_SYNC_POST_BUFFER_SECONDS": "60",
        "LOKI_SYNC_PAGE_LIMIT": "5000",
        "LOKI_SYNC_MAX_PAGES": "50",
        "LOKI_SYNC_HTTP_TIMEOUT": "30",
        "LOKI_SYNC_MAX_RETRIES": "5",
        # RAG
        "DEFAULT_PARSER": "docling",
        "DEFAULT_TOKENISER": "docling_hybrid",
        "DEFAULT_EMBEDDING_PROVIDER": "openai",
        "DEFAULT_EMBEDDING_MODEL": "text-embedding-3-small",
        "DEFAULT_EMBEDDING_DIMENSIONS": "1536",
        "DEFAULT_VECTOR_STORE": "pgvector",
        # Eval
        "EVAL_AUTO_RUN_ENABLED": "true",
        "EVAL_GENERATION_MODEL": "gpt-4o",
        "EVAL_ANSWER_MODEL": "gpt-4o",
        "EVAL_JUDGE_MODEL": "gpt-4o",
        "EVAL_TOP_K": "8",
        "EVAL_MAX_CONTEXT_CHARS": "60000",
        "EVAL_JUDGE_ENGINE": "deepeval",
        "EVAL_METRIC_THRESHOLD": "0.7",
        "EVAL_METRICS_ENABLED": "faithfulness,answer_relevancy",
        "AGENT_LLM_EVAL_METRICS_ENABLED": (
            "answer_relevancy,bias,toxicity,persona_adherence,instruction_following"
        ),
    }


def _tier_b_env() -> dict[str, str]:
    return {
        "INFISICAL_TOKEN": "tok",
        "INFISICAL_PROJECT_ID": "pid",
        "REDIS_URL": "redis://redis.svc:6379/0",
        "LOKI_URL": "https://loki/api/v1/push",
        "GRAFANA_API_KEY": "gk",
        "R2_ACCESS_KEY_ID": "ak",
        "R2_SECRET_ACCESS_KEY": "sk",
        "R2_BUCKET_NAME": "bucket",
        "R2_ENDPOINT_URL": "https://r2.example.com",
        "BASE_CALL_URL": "https://api.example.com",
    }


def _fresh_settings(monkeypatch, env: dict[str, str]):
    for key in list(os.environ):
        monkeypatch.delenv(key, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(config, "get_infisical_secrets", lambda: {})
    return config.Settings()


@pytest.fixture
def capture_stderr():
    """In-memory sink so we can assert on the CRITICAL line."""
    buf = io.StringIO()
    sink_id = logger.add(buf, level="CRITICAL", format="{level}|{message}")
    try:
        yield buf
    finally:
        logger.remove(sink_id)


# --- Happy paths -------------------------------------------------------------

def test_dev_env_boots_with_full_tier_a(monkeypatch):
    settings = _fresh_settings(monkeypatch, _tier_a_env())
    assert settings.DATABASE_URL == "postgresql://user:pass@localhost:5432/tone"
    assert settings.DEFAULT_ORG_ID == "00000000-0000-0000-0000-000000000001"


def test_production_env_boots_with_tier_a_plus_tier_b(monkeypatch):
    env = _tier_a_env() | _tier_b_env()
    env["ENV"] = "production"
    settings = _fresh_settings(monkeypatch, env)
    assert settings.LOKI_URL == "https://loki/api/v1/push"
    assert settings.BASE_CALL_URL == "https://api.example.com"


# --- Tier A: every key individually required in dev --------------------------

@pytest.mark.parametrize("dropped", list(config.MANDATORY_KEYS))
def test_dropping_any_tier_a_key_aborts(monkeypatch, capture_stderr, dropped):
    env = _tier_a_env()
    env.pop(dropped)
    with pytest.raises(SystemExit) as exc:
        _fresh_settings(monkeypatch, env)
    assert exc.value.code == 1
    assert dropped in capture_stderr.getvalue()


# --- Tier B: enforced only in deployed envs ----------------------------------

def test_dev_env_ignores_tier_b(monkeypatch):
    """Dev env boots with Tier A alone even when Tier B is entirely absent."""
    settings = _fresh_settings(monkeypatch, _tier_a_env())
    assert settings.LOKI_URL == ""
    assert settings.R2_BUCKET_NAME == ""


def test_production_env_flags_every_missing_tier_b_key(monkeypatch, capture_stderr):
    env = _tier_a_env()
    env["ENV"] = "production"
    with pytest.raises(SystemExit):
        _fresh_settings(monkeypatch, env)
    log = capture_stderr.getvalue()
    for key in config.MANDATORY_PROD_KEYS:
        assert key in log, f"expected {key} to be flagged as missing"


# --- INSECURE_PLACEHOLDERS ---------------------------------------------------

def test_insecure_jwt_placeholder_rejected(monkeypatch, capture_stderr):
    env = _tier_a_env()
    env["JWT_SECRET_KEY"] = "your-secret-key-here"
    with pytest.raises(SystemExit):
        _fresh_settings(monkeypatch, env)
    assert "JWT_SECRET_KEY" in capture_stderr.getvalue()


def test_insecure_redis_placeholder_rejected_in_prod(monkeypatch, capture_stderr):
    env = _tier_a_env() | _tier_b_env()
    env["ENV"] = "production"
    env["REDIS_URL"] = "redis://localhost:6379/0"
    with pytest.raises(SystemExit):
        _fresh_settings(monkeypatch, env)
    assert "REDIS_URL" in capture_stderr.getvalue()


# --- Error line shape --------------------------------------------------------

def test_error_line_names_env_and_count(monkeypatch, capture_stderr):
    with pytest.raises(SystemExit):
        _fresh_settings(monkeypatch, {"ENV": "staging"})
    log = capture_stderr.getvalue()
    assert "ENV=staging" in log
    # Every Tier A key minus ENV (which we did set) + every Tier B key.
    match = re.search(r"missing (\d+) required env", log)
    assert match, f"missing-count phrase not found in: {log!r}"
    expected = (len(config.MANDATORY_KEYS) - 1) + len(config.MANDATORY_PROD_KEYS)
    assert int(match.group(1)) == expected


# --- Raw-value semantics: legitimate 0 / False must NOT be flagged -----------
# These keys intentionally stay OFF MANDATORY_KEYS (empty is a valid "off"
# value per code comments), so the app must boot when they are unset.

def test_optional_zero_int_knobs_do_not_trip_validator(monkeypatch):
    """MAX_CONCURRENT_OUTBOUND_CALLS/OUTBOUND_BG_WORKERS empty = 0 = off."""
    env = _tier_a_env()
    # explicitly do NOT set the optional knobs
    settings = _fresh_settings(monkeypatch, env)
    assert settings.MAX_CONCURRENT_OUTBOUND_CALLS == 0
    assert settings.OUTBOUND_BG_WORKERS == 0


def test_optional_bool_flags_default_false_when_unset(monkeypatch):
    settings = _fresh_settings(monkeypatch, _tier_a_env())
    assert settings.POD_PINNING_ENABLED is False
    assert settings.ENABLE_WS_TEST_ENDPOINT is False
    assert settings.WS_BRIDGE_ALLOW_INLINE is False
    assert settings.SKIP_LICENSE_CHECK is False
