# Writing a Pipecat service class

When no class exists for a vendor, write one here — this repo already does, in
`core/services/pipeline/`. Do not edit the `tone-pipecat` fork for a single vendor.

Existing examples to copy from, in order of how close they are to what you need:

| File | Class | Base | Shape |
|---|---|---|---|
| `parakeet_stt_service.py` | `ParakeetSTTService` | `SegmentedSTTService` | HTTP, one request per utterance |
| `granite_stt_service.py` | `GraniteWebSocketSTTService` | `WebsocketSTTService` | Streaming, partial/final over WS |
| `cosyvoice_tts_service.py` | `CosyVoiceTTSService` | `TTSService` | HTTP TTS |
| `qwen_tts_service.py` | `QwenWebSocketTTSService` | `TTSService` | WS TTS |
| `mistral_self_hosted_llm_service.py` | — | OpenAI-compatible LLM | Self-hosted LLM |

Naming: `core/services/pipeline/<vendor>_<kind>_service.py`, class `<Vendor><Kind>Service`.

## Pick the base class from the transport, not the vendor

- STT, one request per utterance → `SegmentedSTTService`
- STT, streaming partial/final → `WebsocketSTTService`
- TTS → `TTSService`
- LLM speaking the OpenAI wire format → no class at all; use the `build_llm` fallback

## Required surface

`SegmentedSTTService` — `__init__`, `can_generate_metrics`, `async run_stt(audio) -> AsyncGenerator[Frame, None]`.

`WebsocketSTTService` — the above plus the lifecycle the base class calls:
`start(StartFrame)`, `stop(EndFrame)`, `cancel(CancelFrame)`, and the private
`_connect` / `_disconnect` / `_connect_websocket` / `_disconnect_websocket` /
`_get_websocket` / `_receive_messages` / `_handle_transcription` pattern that
`GraniteWebSocketSTTService` implements. Copy that structure rather than inventing one —
the base class expects those hooks.

`TTSService` — `__init__`, `can_generate_metrics`, `async set_model`, `async set_voice`,
`async run_tts(text, context_id="") -> AsyncGenerator[Frame, None]`, and a
`get_voices(cls, api_key="")` classmethod when the vendor exposes a voice list.

## Rules

- **Match the neighbouring file.** Same import order, same frame types, same error
  handling, same `__str__`. Read the closest example end to end before writing.
- **Every `except` logs a full traceback** with `logger.exception`. Never swallow, never
  drop `asyncio.CancelledError`. Expected control-flow cases use `logger.debug`.
- **Yield frames, never return them.** `run_stt` and `run_tts` are async generators.
- **Do not add comments.** Name things so the code reads without them.
- Take `base_url` and `sample_rate` through the constructor so the factory branch can
  pass them from metadata.
- Add an `InputParams` inner class only if the vendor genuinely has tunable parameters.
  If you skip it, `build_input_params` returns `None` and every `meta_data_schema` field
  is dropped — so then seed no metadata fields either, rather than fields that do nothing.

## After writing it

1. Add the `build_*` branch that constructs it (`factory-patterns.md`).
2. `inspect_pipecat.py core.services.pipeline.<module>.<Class>` — confirm the constructor
   and `InputParams` are what the seed entry assumes. Run with `PYTHONPATH=.`
3. Construct it through the real `build_*` with a representative spec and assert the URL,
   model and sample rate that come out.
