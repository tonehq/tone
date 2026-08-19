"""Shared fixtures for all API test cases (Core and EE)."""

import sys
import os

# ── Preseed strict-env-only mandatory keys ──────────────────────────────────
# shared/config.py carries NO code-side defaults; Settings() aborts the
# process if any MANDATORY_KEYS entry is missing. Any test module that
# transitively imports `settings` (e.g. via `core.middleware.auth`) would
# tank test collection unless the env carries the full Tier A set. We inject
# safe test-only defaults here BEFORE the first import that could touch
# settings — `setdefault` so the real .env / CI env still wins when set.
_TEST_ENV_DEFAULTS = {
    "ENV": "test",
    "DATABASE_URL": "postgresql://user:pass@localhost:5432/tone_test",
    "JWT_SECRET_KEY": "test-jwt-secret-not-the-placeholder-value",
    "DEFAULT_ORG_ID": "00000000-0000-0000-0000-000000000001",
    "LOG_LEVEL": "INFO",
    "COOKIE_SAMESITE": "lax",
    "CORS_ALLOW_ORIGINS": "http://localhost:3000",
    "CORS_ALLOW_ORIGIN_REGEX": r"https://([a-z0-9-]+\.)*trytone\.ai",
    "APPLICATION_URL": "http://localhost:3000",
    "BASE_API_URL": "http://localhost:8000/api/v1",
    "CALL_WORKER_PREFIX": "tone-call-worker",
    "OUTBOUND_CALL_WORKER_PREFIX": "tone-outbound-call-worker",
    "OUTBOUND_CALL_HEADLESS_SERVICE": "tone-outbound-call-headless",
    "OUTBOUND_CALL_WORKER_PORT": "8080",
    "POD_SYNC_NAMESPACE": "test",
    "MAX_CONCURRENT_CALLS": "2",
    "LOKI_SYNC_DELAY_SECONDS": "120",
    "LOKI_SYNC_PRE_BUFFER_SECONDS": "30",
    "LOKI_SYNC_POST_BUFFER_SECONDS": "60",
    "LOKI_SYNC_PAGE_LIMIT": "5000",
    "LOKI_SYNC_MAX_PAGES": "50",
    "LOKI_SYNC_HTTP_TIMEOUT": "30",
    "LOKI_SYNC_MAX_RETRIES": "5",
    "DEFAULT_PARSER": "docling",
    "DEFAULT_TOKENISER": "docling_hybrid",
    "DEFAULT_EMBEDDING_PROVIDER": "openai",
    "DEFAULT_EMBEDDING_MODEL": "text-embedding-3-small",
    "DEFAULT_EMBEDDING_DIMENSIONS": "1536",
    "DEFAULT_VECTOR_STORE": "pgvector",
    "EVAL_AUTO_RUN_ENABLED": "true",
    "EVAL_GENERATION_MODEL": "gpt-4o",
    "EVAL_ANSWER_MODEL": "gpt-4o",
    "EVAL_JUDGE_MODEL": "gpt-4o",
    "EVAL_TOP_K": "8",
    "EVAL_MAX_CONTEXT_CHARS": "60000",
    "EVAL_JUDGE_ENGINE": "deepeval",
    "EVAL_METRIC_THRESHOLD": "0.7",
    "EVAL_METRICS_ENABLED": (
        "faithfulness,answer_relevancy,contextual_precision,"
        "contextual_recall,contextual_relevancy,hallucination,correctness"
    ),
}
for _k, _v in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_k, _v)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import time
from unittest.mock import MagicMock
from fastapi.security import HTTPAuthorizationCredentials

from core.middleware.auth import JWTClaims


def make_claims(
    user_id: int = 1,
    org_id: str = "550e8400-e29b-41d4-a716-446655440000",
    role: str = "member",
    email: str = "test@example.com",
) -> JWTClaims:
    """Build a JWTClaims instance with sensible defaults."""
    now = int(time.time())
    return JWTClaims(
        user_id=user_id,
        org_id=org_id,
        role=role,
        email=email,
        iat=now,
        exp=now + 3600,
    )


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    db.query.return_value = db
    db.filter.return_value = db
    db.first.return_value = None
    db.all.return_value = []
    db.commit.return_value = None
    db.refresh.return_value = None
    db.add.return_value = None
    db.delete.return_value = None
    db.count.return_value = 0
    return db


@pytest.fixture
def member_claims():
    return make_claims(role="member")


@pytest.fixture
def admin_claims():
    return make_claims(role="admin")


@pytest.fixture
def owner_claims():
    return make_claims(role="owner")


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}


def _fake_security():
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")


def _override_auth(claims: JWTClaims):
    def _override():
        return claims
    return _override
