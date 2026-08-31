"""Unit tests for DeepCheckCache key normalization.

Source: core/services/readiness/cache.py

Guards the publish-invalidation fix: the deep-run WRITE path builds the cache
key from resolved ``UUID`` objects while the publish-INVALIDATE path passes the
raw request strings. If ``key()`` didn't canonicalise its inputs, a
differently-cased/formatted id would produce a different key, ``invalidate``
would miss, and a stale deep report could be served for up to the TTL.
"""

from __future__ import annotations

from uuid import UUID

from core.services.readiness.cache import DeepCheckCache


ORG = UUID("11111111-1111-1111-1111-111111111111")
AGENT = UUID("22222222-2222-2222-2222-222222222222")
CONFIG = UUID("33333333-3333-3333-3333-333333333333")


class TestDeepCheckCacheKey:
    def test_uuid_and_raw_string_match(self):
        """A resolved UUID and its raw string form build the SAME key."""
        assert DeepCheckCache.key(ORG, AGENT, CONFIG) == DeepCheckCache.key(
            str(ORG), str(AGENT), str(CONFIG)
        )

    def test_uppercase_string_is_canonicalised(self):
        """Upper-cased request ids still match the lowercase-canonical write."""
        assert DeepCheckCache.key(ORG, AGENT, CONFIG) == DeepCheckCache.key(
            str(ORG).upper(), str(AGENT).upper(), str(CONFIG).upper()
        )

    def test_none_config_is_stable_and_distinct(self):
        """None (resolved-active-config) is stable and never collides with a
        real id."""
        assert DeepCheckCache.key(ORG, AGENT, None) == DeepCheckCache.key(
            str(ORG), str(AGENT), None
        )
        assert DeepCheckCache.key(ORG, AGENT, None) != DeepCheckCache.key(
            ORG, AGENT, CONFIG
        )

    def test_distinct_configs_stay_distinct(self):
        other = UUID("44444444-4444-4444-4444-444444444444")
        assert DeepCheckCache.key(ORG, AGENT, CONFIG) != DeepCheckCache.key(
            ORG, AGENT, other
        )

    def test_non_uuid_value_falls_back_to_str(self):
        # A non-UUID component (shouldn't happen, but must not crash).
        assert DeepCheckCache.key("org-slug", AGENT, CONFIG) == DeepCheckCache.key(
            "org-slug", str(AGENT), str(CONFIG)
        )
