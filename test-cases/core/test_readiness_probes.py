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
        assert reason is not None and "unreachable" in reason.lower()


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
    """Verifies the L4 MCP probe is *lenient* — any HTTP response (even 405)
    proves the server is up. Only network errors fail. The strict correctness
    check lives in McpServerReachableCheck (list_tools handshake)."""

    def _make_server(self, url="https://mcp.example.com"):
        return SimpleNamespace(
            id="s1", name="MCP", server_url=url, transport_type="sse",
            auth_type="none", auth_config={},
        )

    def _run(self, mocked_client_ctx):
        from core.services.readiness.checks.mcp_servers import McpServerHttpReachableCheck
        check = McpServerHttpReachableCheck()
        ctx = SimpleNamespace(mcp_servers=[self._make_server()])

        with patch("httpx.AsyncClient", return_value=mocked_client_ctx):
            return asyncio.run(check.run(ctx))

    def _client_ctx(self, *, response=None, exc=None):
        """Build the async-context-manager stub httpx.AsyncClient() returns."""
        client = MagicMock()
        if exc is not None:
            client.get = AsyncMock(side_effect=exc)
        else:
            client.get = AsyncMock(return_value=response)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=None)
        return ctx

    def test_pass_on_any_http_response(self):
        """SSE endpoints often return 405 to a bare GET — still counts as up."""
        for status in (200, 302, 404, 405, 501):
            result = self._run(self._client_ctx(response=MagicMock(status_code=status)))
            assert result.status.value == "pass", f"status {status} should pass"

    def test_fail_on_connect_error(self):
        result = self._run(self._client_ctx(exc=httpx.ConnectError("dns fail")))
        assert result.status.value == "fail"
        assert "unreachable" in result.message.lower()
