"""Unit tests for the telephony-free "test" transport backing /ws/test.

Source:
  core/services/transport/test_provider.py  (TestTransport + RawPCMSerializer)
  core/services/transport/base.py            (TelephonyTransport.build)
  core/serializers/raw_pcm.py                (RawPCMSerializer)

Async tests use asyncio.run (repo has no pytest-asyncio).
"""

import asyncio
from types import SimpleNamespace

import pytest

from core.serializers.raw_pcm import RawPCMSerializer
from core.services.transport import get_telephony_provider
from core.services.transport.base import TelephonyTransport
from core.services.transport.test_provider import (DEFAULT_TEST_SAMPLE_RATE,
                                                   TestTransport)


class TestProviderRegistration:
    def test_registered_under_test_slug(self):
        provider = get_telephony_provider("test")
        assert isinstance(provider, TestTransport)
        assert provider.transport_type == "test"

    def test_create_serializer_returns_raw_pcm(self):
        ser = TestTransport().create_serializer({"sample_rate": 8000})
        assert isinstance(ser, RawPCMSerializer)
        assert ser._sample_rate == 8000

    def test_create_serializer_defaults_rate(self):
        ser = TestTransport().create_serializer({})
        assert isinstance(ser, RawPCMSerializer)
        assert ser._sample_rate == DEFAULT_TEST_SAMPLE_RATE

    def test_resolve_from_to_is_noop(self):
        call_data = {"from": "", "to": ""}
        asyncio.run(TestTransport().resolve_from_to(call_data))
        assert call_data == {"from": "", "to": ""}


class TestBuildPath:
    """The /ws/test handler pre-seeds call_data + transport_type so build() skips the
    Twilio frame parser and wires a RawPCMSerializer — verify that end to end."""

    def _runner_args(self, body):
        return SimpleNamespace(body=body, websocket=SimpleNamespace(client=None))

    def test_build_with_agent_id_body(self):
        from pipecat.transports.websocket.fastapi import \
            FastAPIWebsocketTransport

        uid = "11111111-2222-3333-4444-555555555555"
        body = {
            "transport_type": "test",
            "agent_id": uid,
            "call_data": {
                "from": "", "to": "", "body": {"agent_id": uid},
                "stream_id": "s", "call_id": "c", "sample_rate": 16000,
            },
        }
        ra = self._runner_args(body)
        transport = asyncio.run(TelephonyTransport().build(ra))

        assert isinstance(transport, FastAPIWebsocketTransport)
        ser = transport._params.serializer
        assert isinstance(ser, RawPCMSerializer)
        assert ser._sample_rate == 16000
        # audio both ways, no WAV header (raw PCM stream)
        assert transport._params.audio_in_enabled and transport._params.audio_out_enabled
        assert transport._params.add_wav_header is False
        # agent_id + transport_type stay on the body for get_agent_for_call / call-log.
        assert ra.body["agent_id"] == uid
        assert ra.body["transport_type"] == "test"

    def test_build_promotes_agent_id_from_call_data(self):
        """When only call_data['body']['agent_id'] is set, build() promotes it top-level."""
        uid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        body = {
            "transport_type": "test",
            "call_data": {
                "from": "", "to": "", "body": {"agent_id": uid},
                "stream_id": "s", "call_id": "c", "sample_rate": 16000,
            },
        }
        ra = self._runner_args(body)
        asyncio.run(TelephonyTransport().build(ra))
        assert ra.body["agent_id"] == uid

    def test_build_phone_number_leaves_to_intact(self):
        body = {
            "transport_type": "test",
            "call_data": {
                "from": "", "to": "+19894742667", "body": {},
                "stream_id": "s", "call_id": "c", "sample_rate": 16000,
            },
        }
        ra = self._runner_args(body)
        asyncio.run(TelephonyTransport().build(ra))
        assert ra.body["call_data"]["to"] == "+19894742667"
        assert "agent_id" not in ra.body
