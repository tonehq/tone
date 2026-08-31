"""Unit tests for the readiness probe helpers and probe functions.

Source: core/services/readiness/probes.py + core/services/readiness/checks/tools.py
        + core/services/readiness/checks/mcp_servers.py

Kept independent from the API-level integration tests in test_agent_readiness.py.
Those exercise the whole request path against a real DB; this file drills into
the pipecat-facing probe internals with mocks so provider outages, ErrorFrame
handling, transcript assertion, WAV loading and HTTP probing can be verified
without any live LLM/STT/TTS/HTTP dependency.

Async style: tests call `asyncio.run(probe(...))` so we don't need
pytest-asyncio (not in requirements). The probes are self-contained coroutines
so this is safe.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


# ─── Fakes shared across probe tests ──────────────────────────────────────────


class _FakeAsyncStream:
    """Async iterator that yields a fixed list of frames.

    Used as the return value for mocked ``service.run_stt`` / ``run_tts`` so
    each test controls exactly which frame shapes the probe sees.
    """

    def __init__(self, frames):
        self._frames = list(frames)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._frames:
            raise StopAsyncIteration
        return self._frames.pop(0)


def _fake_spec_ctx(service_type: str = "stt"):
    """Build a minimal duck-typed CheckContext for a single-service probe.

    The probes read ``ctx.<service>.provider``, ``.decrypted_key``,
    ``.model``, ``.settings``. Everything else on CheckContext is untouched.
    """
    leg = SimpleNamespace(
        settings={"sample_rate": 16000},
        provider_id="pid",
        model_id="mid",
        provider=SimpleNamespace(slug="testprovider"),
        model=SimpleNamespace(name="test-model"),
        api_key=SimpleNamespace(),
        decrypted_key="fake-key",
    )
    ctx = SimpleNamespace(**{service_type: leg})
    return ctx


# ─── URL shape (shallow tool check) ───────────────────────────────────────────


class TestUrlShapeProblem:
    """`_url_shape_problem` guards the shallow ToolsUsableCheck against
    malformed URLs so the badge fails fast without a network call."""

    def test_empty_urls_flagged(self):
        from core.services.readiness.checks.tools import _url_shape_problem
        for empty in (None, "", "   "):
            assert _url_shape_problem(empty) == "no URL"

    def test_missing_scheme_flagged(self):
        from core.services.readiness.checks.tools import _url_shape_problem
        assert _url_shape_problem("foo.com") == "URL scheme must be http/https"

    def test_wrong_scheme_flagged(self):
        from core.services.readiness.checks.tools import _url_shape_problem
        assert _url_shape_problem("htps://foo.com") == "URL scheme must be http/https"
        assert _url_shape_problem("ftp://foo.com") == "URL scheme must be http/https"

    def test_missing_host_flagged(self):
        from core.services.readiness.checks.tools import _url_shape_problem
        assert _url_shape_problem("http://") == "URL missing host"

    def test_wellformed_returns_none(self):
        from core.services.readiness.checks.tools import _url_shape_problem
        for good in (
            "http://example.com",
            "https://example.com",
            "HTTPS://Example.com",  # urlparse normalises scheme
            "https://example.com/api?x=1",
        ):
            assert _url_shape_problem(good) is None, good


# ─── STT audio helpers (probe internals) ──────────────────────────────────────


class TestStttAudioLoader:
    """Verify the bundled WAV is loadable + resampling stays honest."""

    def test_asset_loads_at_16k_mono_pcm16(self):
        from core.services.readiness.probes import _load_probe_pcm16
        _load_probe_pcm16.cache_clear()
        loaded = _load_probe_pcm16()
        # If a maintainer removes the WAV, this test tells them clearly.
        assert loaded is not None, "probe_sample.wav missing from assets/"
        pcm, rate, full_wav = loaded
        assert rate == 16000
        # Full WAV must be strictly larger than raw PCM (the RIFF header).
        assert len(full_wav) > len(pcm) >= 100_000
        # Duration must stay within the 5-10s window the STT probe expects.
        duration_s = len(pcm) / (rate * 2)
        assert 5.0 <= duration_s <= 10.0, f"WAV duration {duration_s:.2f}s outside 5-10s window"

    def test_resample_to_different_rate(self):
        """Streaming services get resampled headerless PCM."""
        from core.services.readiness.probes import _load_stt_audio

        class FakeStreamingSTT:  # Class name NOT in _HTTP_STT_SERVICE_CLASSES
            pass

        stub = FakeStreamingSTT()
        pcm_16k, real_16k = _load_stt_audio(16000, stub)
        pcm_8k, real_8k = _load_stt_audio(8000, stub)
        assert real_16k and real_8k, "using_real_audio flag should be True when WAV present"
        # 8kHz is half of 16kHz → resampled buffer is roughly half the byte count.
        ratio = len(pcm_8k) / len(pcm_16k)
        assert 0.45 < ratio < 0.55, f"8kHz resample ratio {ratio:.2f} not ~0.5"

    def test_http_service_gets_full_wav(self):
        """Whisper-family HTTP services need the full WAV file with header —
        raw PCM without a container gets rejected as "could not decode"."""
        from core.services.readiness.probes import _load_stt_audio

        class OpenAISTTService:  # Name matches _HTTP_STT_SERVICE_CLASSES
            pass

        stub = OpenAISTTService()
        blob, real = _load_stt_audio(16000, stub)
        assert real is True
        assert blob[:4] == b"RIFF", "HTTP STTs must receive the WAV RIFF header"

    def test_silence_fallback_when_asset_missing(self):
        """When _load_probe_pcm16 returns None, we fall back to silence
        + flip the ``using_real_audio`` flag so the probe knows not to
        assert on transcription."""
        from core.services.readiness.probes import _load_stt_audio
        with patch("core.services.readiness.probes._load_probe_pcm16", return_value=None):
            pcm, real = _load_stt_audio(16000, object())
            assert real is False
            assert pcm == b"\x00\x00" * 8000  # 0.5s of PCM16 silence


# ─── Frame extractors ─────────────────────────────────────────────────────────


class TestTranscriptExtractor:
    def test_returns_text_when_present(self):
        from core.services.readiness.probes import _extract_transcript_text
        frame = SimpleNamespace(text="the quick brown fox")
        assert _extract_transcript_text(frame, ()) == "the quick brown fox"

    def test_rejects_whitespace_only(self):
        """A provider emitting ' ' between chunks isn't a real transcript."""
        from core.services.readiness.probes import _extract_transcript_text
        for empty in (SimpleNamespace(text=" "), SimpleNamespace(text=""), SimpleNamespace(text="\n\n")):
            assert _extract_transcript_text(empty, ()) is None

    def test_rejects_frame_without_text(self):
        from core.services.readiness.probes import _extract_transcript_text
        assert _extract_transcript_text(SimpleNamespace(), ()) is None


class TestErrorFrameExtractor:
    """Regression test for the exact production bug this file was born to catch:
    pipecat WS providers surface auth/quota failures via ErrorFrame in the
    stream, not by raising. Probes MUST detect these or a Fish Audio 402
    silently passes readiness."""

    def test_isinstance_path_returns_error_message(self):
        from core.services.readiness.probes import _extract_error_frame_message
        from pipecat.frames.frames import ErrorFrame
        frame = ErrorFrame(error="server rejected WebSocket connection: HTTP 402")
        msg = _extract_error_frame_message(frame, ErrorFrame)
        assert msg and "402" in msg

    def test_duck_typed_fallback_when_pipecat_import_fails(self):
        """When ErrorFrame class isn't importable (e.g. pipecat missing at
        readiness-check time), the duck-typed fallback still catches any
        class whose name ends in ErrorFrame and carries an ``.error`` attr."""
        from core.services.readiness.probes import _extract_error_frame_message

        class FakeErrorFrame:
            error = "HTTP 402"

        msg = _extract_error_frame_message(FakeErrorFrame(), None)
        assert msg == "HTTP 402"

    def test_non_error_frame_returns_none(self):
        from core.services.readiness.probes import _extract_error_frame_message
        from pipecat.frames.frames import ErrorFrame
        assert _extract_error_frame_message(SimpleNamespace(audio=b"\x00"), ErrorFrame) is None
        assert _extract_error_frame_message(SimpleNamespace(text="hi"), None) is None


# ─── TTS probe (the primary regression surface) ───────────────────────────────


class TestProbeTts:
    """Exercise every branch of probe_tts. Mocks pipecat via
    ``service_factory.build_tts`` so no live provider is required."""

    def _run(self, service):
        """Call probe_tts against a fake service. Returns ProbeResult."""
        from core.services.readiness import probes
        ctx = _fake_spec_ctx("tts")
        with patch.object(probes, "_build_spec", return_value={
            "provider_name": "fake_tts",
            "api_key": "k",
            "model_name": "m",
            "metadata": {},
            "model_meta_data": {},
        }):
            from core.services.pipeline import service_factory
            with patch.object(service_factory, "build_tts", return_value=service):
                return asyncio.run(probes.probe_tts(ctx))

    def test_pass_on_audio_frame(self):
        """Healthy TTS emits a TTSAudioRawFrame with audio bytes → PASS."""
        from pipecat.frames.frames import TTSAudioRawFrame
        audio_frame = TTSAudioRawFrame(audio=b"\x00\x01", sample_rate=24000, num_channels=1)
        service = MagicMock()
        service.run_tts = MagicMock(return_value=_FakeAsyncStream([audio_frame]))
        result = self._run(service)
        assert result.ok is True
        assert "synthesised" in result.message.lower()

    def test_fail_on_error_frame(self):
        """Regression: Fish Audio HTTP 402 arrives as an ErrorFrame in the
        stream; probe MUST fail with the provider's message, not soft-pass."""
        from pipecat.frames.frames import ErrorFrame
        err = ErrorFrame(error="server rejected WebSocket connection: HTTP 402")
        service = MagicMock()
        service.run_tts = MagicMock(return_value=_FakeAsyncStream([err]))
        result = self._run(service)
        assert result.ok is False
        assert "402" in result.message

    def test_fail_on_no_audio(self):
        """Regression: previously returned a soft PASS on an empty stream —
        now a real sentence probe MUST produce audio to be considered healthy."""
        service = MagicMock()
        service.run_tts = MagicMock(return_value=_FakeAsyncStream([]))
        result = self._run(service)
        assert result.ok is False
        assert "no audio" in result.message.lower()

    def test_fail_when_construction_raises(self):
        """A broken client construction (bad API key at init time) → clear FAIL."""
        from core.services.readiness import probes
        ctx = _fake_spec_ctx("tts")
        with patch.object(probes, "_build_spec", return_value={
            "provider_name": "fake_tts", "api_key": "k", "model_name": "m",
            "metadata": {}, "model_meta_data": {},
        }):
            from core.services.pipeline import service_factory
            with patch.object(service_factory, "build_tts", side_effect=RuntimeError("bad key")):
                result = asyncio.run(probes.probe_tts(ctx))
        assert result.ok is False
        assert "bad key" in result.message


# ─── STT probe ────────────────────────────────────────────────────────────────


class TestProbeStt:
    """Exercise every branch of probe_stt. Same mocking pattern as TTS."""

    def _run(self, service):
        from core.services.readiness import probes
        ctx = _fake_spec_ctx("stt")
        with patch.object(probes, "_build_spec", return_value={
            "provider_name": "fake_stt", "api_key": "k", "model_name": "m",
            "metadata": {}, "model_meta_data": {},
        }):
            from core.services.pipeline import service_factory
            with patch.object(service_factory, "build_stt", return_value=service):
                return asyncio.run(probes.probe_stt(ctx))

    def test_pass_on_transcription_frame(self):
        """Healthy STT emits TranscriptionFrame with real text → PASS with snippet."""
        from pipecat.frames.frames import TranscriptionFrame
        frame = TranscriptionFrame(text="the quick brown fox", user_id="u", timestamp="t")
        service = MagicMock()
        service.run_stt = MagicMock(return_value=_FakeAsyncStream([frame]))
        result = self._run(service)
        assert result.ok is True
        assert "transcribed" in result.message.lower()
        assert "the quick brown fox" in result.message

    def test_pass_on_interim_transcription_frame(self):
        """Providers that only emit interims (streaming-only) still pass."""
        from pipecat.frames.frames import InterimTranscriptionFrame
        frame = InterimTranscriptionFrame(text="hello world", user_id="u", timestamp="t")
        service = MagicMock()
        service.run_stt = MagicMock(return_value=_FakeAsyncStream([frame]))
        result = self._run(service)
        assert result.ok is True
        assert "hello world" in result.message

    def test_fail_on_error_frame(self):
        """Regression: WS-STT auth/quota failures arrive as ErrorFrame."""
        from pipecat.frames.frames import ErrorFrame
        err = ErrorFrame(error="invalid api key")
        service = MagicMock()
        service.run_stt = MagicMock(return_value=_FakeAsyncStream([err]))
        result = self._run(service)
        assert result.ok is False
        assert "invalid api key" in result.message.lower()

    def test_fail_on_no_frames_with_real_audio(self):
        """WAV was present but provider returned nothing → clear FAIL."""
        service = MagicMock()
        service.run_stt = MagicMock(return_value=_FakeAsyncStream([]))
        result = self._run(service)
        assert result.ok is False
        assert "no frames" in result.message.lower()

    def test_fail_on_frames_without_transcript(self):
        """Frames arrived but none carried text (whitespace-only) → FAIL with
        language/model hint since that's the usual culprit."""
        service = MagicMock()
        # Non-error, non-transcript frames — e.g. audio ack frames with empty
        # text — must not fool the assertion.
        frame = SimpleNamespace(text=" ")
        service.run_stt = MagicMock(return_value=_FakeAsyncStream([frame, frame]))
        result = self._run(service)
        assert result.ok is False
        assert "no transcript" in result.message.lower()


# ─── Tool GET probe (deep tools.reachable) ────────────────────────────────────


class _StubTool:
    """Duck-typed Tool row for _probe_tool (ToolReachableCheck internals)."""

    def __init__(self, url="https://api.example.com", auth_type="none", auth_config=None):
        self.id = "tool-id"
        self.name = "TestTool"
        self.url = url
        self.method = "GET"
        self.auth_type = auth_type
        self.auth_config = auth_config or {}
        self.tool_type = "custom"
        self.is_active = True


class TestToolReachableProbe:
    """The tool GET probe classifies HTTP responses into buckets the drawer
    can render meaningfully. Strict 2xx pass; 401/403 flagged as auth reject;
    other non-2xx as HTTP status; network errors as unreachable."""

    def _probe(self, response_or_exc):
        """Invoke ToolReachableCheck._probe_tool against a stub httpx client."""
        from core.services.readiness.checks.tools import ToolReachableCheck
        check = ToolReachableCheck()

        client = MagicMock()
        if isinstance(response_or_exc, Exception):
            client.get = AsyncMock(side_effect=response_or_exc)
        else:
            client.get = AsyncMock(return_value=response_or_exc)

        tool = _StubTool()
        return asyncio.run(check._probe_tool(client, tool))

    def test_pass_on_2xx(self):
        resp = MagicMock(status_code=204)
        assert self._probe(resp) is None  # None == PASS in the probe contract

    def test_fail_on_401_401(self):
        resp = MagicMock(status_code=401)
        reason = self._probe(resp)
        assert reason is not None and "401" in reason and "auth" in reason.lower()

    def test_fail_on_403(self):
        resp = MagicMock(status_code=403)
        reason = self._probe(resp)
        assert reason is not None and "403" in reason and "auth" in reason.lower()

    def test_fail_on_500(self):
        resp = MagicMock(status_code=500)
        reason = self._probe(resp)
        assert reason is not None and "500" in reason

    def test_fail_on_network_error(self):
        reason = self._probe(httpx.ConnectError("dns lookup failed"))
        assert reason is not None and "respond" in reason.lower()


class TestOAuthFailureReason:
    """`oauth_failure_reason` maps verbose provider token errors to a short,
    action-oriented clause; unknown text falls back to `humanize_reason`."""

    def _fn(self):
        from core.services.readiness.checks._messages import oauth_failure_reason

        return oauth_failure_reason

    def test_invalid_grant_maps_to_expired(self):
        fn = self._fn()
        raw = (
            "token refresh failed for 'google_calendar' (invalid_grant: Token "
            "has been expired or revoked.). Refresh token expired — reconnect."
        )
        assert fn(raw) == "its login has expired, reconnect the account"

    def test_scope_error_maps_to_permissions(self):
        assert "permissions" in self._fn()("insufficient scope: missing calendar")

    def test_unauthorized_maps_to_denied(self):
        assert "denied" in self._fn()("401 Unauthorized invalid_client")

    def test_unknown_error_falls_back_to_humanized(self):
        # A plain transport error isn't an OAuth case — humanized, not mapped.
        assert self._fn()("Connection refused") == "connection refused"


class TestHumanizeReasonNoMidWordCut:
    """`humanize_reason` must never chop a word mid-way (the "publish the…"
    bug) — it prefers the first sentence and cuts at a word boundary."""

    def _fn(self):
        from core.services.readiness.checks._messages import humanize_reason

        return humanize_reason

    def test_prefers_first_sentence(self):
        raw = (
            "the upstream provider rejected the request and returned an "
            "unexpected error code. Please retry later and contact support "
            "if the problem continues."
        )
        out = self._fn()(raw)
        assert out.startswith("the upstream provider rejected the request")
        assert "Please retry" not in out

    def test_long_single_sentence_cuts_on_word_boundary(self):
        raw = "word " * 60  # ~300 chars, no sentence break
        out = self._fn()(raw)
        assert out.endswith("…") and not out.endswith("wor…")


class TestToolsUsablePerTool:
    """The shallow structural check emits one plain-English row per broken
    tool (turned off / bad URL), not one joined string."""

    def _check(self):
        from core.services.readiness.checks.tools import ToolsUsableCheck

        return ToolsUsableCheck()

    def _tool(self, tid, name, *, active=True, url="https://api.example.com", ttype="custom"):
        return SimpleNamespace(
            id=tid, name=name, is_active=active, tool_type=ttype, url=url,
        )

    def test_disabled_and_bad_url_each_get_a_row(self):
        check = self._check()
        good = self._tool("g", "Good")
        off = self._tool("o", "Off", active=False)
        bad = self._tool("b", "Bad", url="   ")
        results = asyncio.run(check.run(SimpleNamespace(tools=[good, off, bad])))
        assert len(results) == 2
        by_id = {r.check_id: r for r in results}
        assert by_id["tools.usable:o"].message.lower().count("turned off") == 1
        assert "Bad" in by_id["tools.usable:b"].message
        assert all(r.status.value == "fail" for r in results)

    def test_all_usable_single_pass(self):
        check = self._check()
        results = asyncio.run(check.run(SimpleNamespace(tools=[self._tool("g", "Good")])))
        assert len(results) == 1 and results[0].status.value == "pass"


class TestToolReachableFilter:
    """The check itself skips write-method / MCP / inactive tools so
    side-effectful endpoints are never called."""

    def _is_probeable(self, **overrides):
        from core.services.readiness.checks.tools import ToolReachableCheck
        tool = _StubTool()
        for k, v in overrides.items():
            setattr(tool, k, v)
        return ToolReachableCheck._is_probeable(tool)

    def test_get_custom_active_probeable(self):
        assert self._is_probeable() is True

    def test_post_skipped(self):
        assert self._is_probeable(method="POST") is False

    def test_delete_skipped(self):
        assert self._is_probeable(method="DELETE") is False

    def test_mcp_type_skipped(self):
        assert self._is_probeable(tool_type="mcp") is False

    def test_inactive_skipped(self):
        assert self._is_probeable(is_active=False) is False

    def test_empty_url_skipped(self):
        assert self._is_probeable(url="") is False


# ─── MCP HTTP-layer probe ─────────────────────────────────────────────────────


class TestMcpServerHttpReachable:
    """Verifies the L4 reachability leg of the merged ``McpServerReachableCheck``
    is *lenient* — any HTTP response (even 405) proves the server is up. Only a
    transport error counts as unreachable. The strict correctness check is the
    handshake leg (``_handshake`` → ``validate_mcp_connection``)."""

    def _make_server(self, url="https://mcp.example.com"):
        return SimpleNamespace(
            id="s1", name="MCP", server_url=url, transport_type="sse",
            auth_type="none", auth_config={}, meta_data=None,
            oauth_connection_id=None, app_integration_id=None,
        )

    def _reachable(self, *, response=None, exc=None):
        """Run the merged check's HTTP-reachability leg with a mocked client.

        Returns the ``(reachable, reason)`` tuple ``_http_reachable`` produces.
        """
        from core.services.readiness.checks.mcp_servers import McpServerReachableCheck

        check = McpServerReachableCheck()
        svc = MagicMock()
        svc._resolve_oauth_headers = MagicMock(return_value={})
        client = MagicMock()
        if exc is not None:
            client.get = AsyncMock(side_effect=exc)
        else:
            client.get = AsyncMock(return_value=response)
        return asyncio.run(check._http_reachable(svc, client, self._make_server()))

    def test_pass_on_any_http_response(self):
        """SSE endpoints often return 405 to a bare GET — still counts as up."""
        for status in (200, 302, 404, 405, 501):
            reachable, reason = self._reachable(response=MagicMock(status_code=status))
            assert reachable is True, f"status {status} should be reachable"
            assert reason is None

    def test_fail_on_connect_error(self):
        reachable, reason = self._reachable(exc=httpx.ConnectError("dns fail"))
        assert reachable is False
        assert reason is not None and "respond" in reason.lower()


# ─── MCP per-server messaging (one clear row per server) ──────────────────────


class TestMcpServerReachablePerServer:
    """The merged deep check emits at most ONE plain-English row per server:
    "Can't reach …" when the box is down, or "responded, but the connection
    failed …" when it's up but the handshake fails. Each row carries a unique
    per-server ``check_id`` so the drawer renders them as separate rows."""

    def _check(self):
        from core.services.readiness.checks.mcp_servers import McpServerReachableCheck

        return McpServerReachableCheck()

    def _server(self, sid="s1", name="Gmail"):
        return SimpleNamespace(
            id=sid, name=name, server_url="https://mcp.example.com", is_active=True,
            transport_type="sse", auth_type="none", auth_config={}, meta_data=None,
            oauth_connection_id=None, app_integration_id=None,
        )

    def test_healthy_server_yields_no_row(self):
        check = self._check()
        check._http_reachable = AsyncMock(return_value=(True, None))
        check._handshake = AsyncMock(return_value=None)
        result = asyncio.run(check._probe_server(MagicMock(), MagicMock(), self._server()))
        assert result is None

    def test_unreachable_server_single_row(self):
        check = self._check()
        check._http_reachable = AsyncMock(return_value=(False, "the server didn't respond"))
        check._handshake = AsyncMock(return_value=None)
        result = asyncio.run(
            check._probe_server(MagicMock(), MagicMock(), self._server(name="Gmail"))
        )
        assert result.status.value == "fail"
        assert "Can't reach" in result.message and "Gmail" in result.message
        assert result.check_id == "mcp_servers.reachable:s1"
        assert result.resource_ref.type == "mcp_server" and result.resource_ref.id == "s1"

    def test_handshake_failure_single_row(self):
        check = self._check()
        check._http_reachable = AsyncMock(return_value=(True, None))
        check._handshake = AsyncMock(return_value="invalid credentials")
        result = asyncio.run(
            check._probe_server(MagicMock(), MagicMock(), self._server(sid="s2", name="Slack"))
        )
        assert result.status.value == "fail"
        assert "Slack" in result.message and "invalid credentials" in result.message
        assert result.check_id == "mcp_servers.reachable:s2"


class TestMcpServersConfiguredPerServer:
    """Shallow static check — one row per server that's missing a URL or turned
    off; healthy servers collapse into a single pass row."""

    def _check(self):
        from core.services.readiness.checks.mcp_servers import McpServersConfiguredCheck

        return McpServersConfiguredCheck()

    def test_missing_url_flagged_once(self):
        check = self._check()
        good = SimpleNamespace(id="g", name="Good", server_url="https://x", is_active=True)
        bad = SimpleNamespace(id="b", name="Bad", server_url="   ", is_active=True)
        results = asyncio.run(check.run(SimpleNamespace(mcp_servers=[good, bad])))
        assert len(results) == 1
        assert results[0].status.value == "fail"
        assert "Bad" in results[0].message
        assert results[0].check_id == "mcp_servers.configured:b"

    def test_inactive_server_flagged(self):
        check = self._check()
        off = SimpleNamespace(id="o", name="Off", server_url="https://x", is_active=False)
        results = asyncio.run(check.run(SimpleNamespace(mcp_servers=[off])))
        assert len(results) == 1
        assert results[0].status.value == "fail" and "turned off" in results[0].message

    def test_all_configured_single_pass(self):
        check = self._check()
        good = SimpleNamespace(id="g", name="Good", server_url="https://x", is_active=True)
        results = asyncio.run(check.run(SimpleNamespace(mcp_servers=[good])))
        assert len(results) == 1 and results[0].status.value == "pass"


# ─── Regression tests for the five gaps fixed in this session ────────────────


class TestReadinessGapsRegression:
    """Guards the five gap-fixes: BLOCKER severity on provider-reachable
    checks, S2S LLM applies-gate + defensive probe_llm guard, probe_stt
    hard-fail on missing WAV, runner-exception surfacing in probe_in_pipeline,
    and credential-shaped 400 classification in _summarise_error."""

    def test_provider_reachable_checks_are_blocker_severity(self):
        from core.services.readiness.checks.llm import LLMProviderReachableCheck
        from core.services.readiness.checks.stt import STTProviderReachableCheck
        from core.services.readiness.checks.tts import TTSProviderReachableCheck
        from core.services.readiness.schemas import Severity
        assert LLMProviderReachableCheck.severity == Severity.BLOCKER
        assert STTProviderReachableCheck.severity == Severity.BLOCKER
        assert TTSProviderReachableCheck.severity == Severity.BLOCKER

    def test_llm_provider_reachable_skips_when_s2s(self):
        from core.services.readiness.checks.llm import LLMProviderReachableCheck
        check = LLMProviderReachableCheck()
        ctx = SimpleNamespace(
            is_s2s=True,
            llm=SimpleNamespace(
                provider=SimpleNamespace(slug="openai_realtime"),
                decrypted_key="k",
            ),
        )
        assert check.applies(ctx) is False
        assert "audio session" in check.skip_reason(ctx).lower()

    def test_probe_llm_defensively_fails_on_s2s_provider(self):
        from core.services.readiness import probes
        ctx = _fake_spec_ctx("llm")
        ctx.llm.provider = SimpleNamespace(slug="openai_realtime")
        with patch.object(probes, "_build_spec", return_value={
            "provider_name": "openai_realtime", "api_key": "k",
            "model_name": "m", "metadata": {}, "model_meta_data": {},
        }):
            from core.services.pipeline import service_factory
            with patch.object(service_factory, "build_llm", return_value=MagicMock()):
                result = asyncio.run(probes.probe_llm(ctx))
        assert result.ok is False
        assert "audio session" in result.message.lower()

    def test_probe_stt_fails_when_bundled_wav_missing(self):
        from core.services.readiness import probes
        ctx = _fake_spec_ctx("stt")
        with patch.object(probes, "_build_spec", return_value={
            "provider_name": "fake_stt", "api_key": "k", "model_name": "m",
            "metadata": {}, "model_meta_data": {},
        }):
            from core.services.pipeline import service_factory
            with patch.object(service_factory, "build_stt", return_value=MagicMock()), \
                 patch.object(probes, "_load_probe_pcm16", return_value=None), \
                 patch(
                     "core.services.readiness.probe_pipeline.probe_in_pipeline",
                     new=AsyncMock(return_value=(False, None, None)),
                 ):
                result = asyncio.run(probes.probe_stt(ctx))
        assert result.ok is False
        lower = result.message.lower()
        assert "bundled probe wav missing" in lower or "probe unavailable" in lower

    def test_probe_in_pipeline_surfaces_runner_exception(self):
        from core.services.readiness import probe_pipeline
        from pipecat.frames.frames import EndFrame, TTSSpeakFrame
        from pipecat.pipeline.task import PipelineParams

        async def _raise(self, task):
            raise RuntimeError("invalid api key")

        with patch(
            "pipecat.pipeline.runner.PipelineRunner.run",
            new=_raise,
        ):
            ok, frame, err_msg = asyncio.run(probe_pipeline.probe_in_pipeline(
                MagicMock(),
                [TTSSpeakFrame(text="hi"), EndFrame()],
                lambda f: False,
                params=PipelineParams(enable_metrics=False),
                timeout_s=2.0,
                provider="fake",
            ))
        assert ok is False
        assert frame is None
        assert err_msg is not None
        assert "invalid api key" in err_msg.lower()
        assert "no target frame observed" not in err_msg.lower()

    def test_summarise_error_classifies_credential_shaped_400s_as_auth(self):
        from core.services.readiness.probes import _summarise_error

        anthropic_msg = _summarise_error("anthropic", Exception("Bad credentials for request"))
        assert "rejected the api key" in anthropic_msg.lower()

        google_msg = _summarise_error(
            "google", Exception("API key not valid. Please pass a valid API key.")
        )
        assert "rejected the api key" in google_msg.lower()

        openai_exc = type("E", (Exception,), {"status_code": 401})("unauthorized")
        openai_msg = _summarise_error("openai", openai_exc)
        assert "rejected the api key" in openai_msg.lower()

        # Sanity: quota phrasing still routes to the credit bucket.
        groq_msg = _summarise_error("groq", Exception("You exceeded your current quota"))
        assert "credit" in groq_msg.lower() or "quota" in groq_msg.lower()
