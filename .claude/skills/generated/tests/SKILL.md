---
name: tests
description: "Skill for the Tests area of tone. 654 symbols across 147 files."
---

# Tests

654 symbols | 147 files | Cohesion: 69%

## When to Use

- Working with code in `pipecat/`
- Understanding how test_user_mute_strategy, test_basic_idle_detection, test_active_listening_resets_idle work
- Modifying tests-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/tests/test_krisp_viva_filter.py` | tearDown, test_initialization_with_model_path, test_initialization_with_env_variable, test_initialization_without_model_path, test_initialization_with_invalid_extension (+40) |
| `pipecat/tests/test_context_aggregators.py` | check_message_content, test_se, test_ste, test_site, test_st1iest2e (+39) |
| `pipecat/tests/test_aic_filter.py` | MockProcessor, get_vad_context, process_async, MockModel, setUp (+37) |
| `pipecat/src/pipecat/frames/frames.py` | SystemFrame, UninterruptibleFrame, TTSTextFrame, FunctionCallResultProperties, FunctionCallResultFrame (+33) |
| `pipecat/tests/test_aic_vad.py` | test_initialization_without_factory, test_initialization_with_vad_params, test_voice_confidence_no_context, test_voice_confidence_speech_detected, test_voice_confidence_no_speech (+16) |
| `pipecat/tests/test_transcript_processor.py` | test_text_aggregation, test_empty_text_handling, test_interruption_handling, test_end_frame_handling, test_cancel_frame_handling (+11) |
| `pipecat/tests/test_user_turn_stop_strategy.py` | test_ste, test_site, test_st1iest2e, test_siet, test_sieit (+9) |
| `pipecat/tests/test_frame_processor.py` | test_interruption_and_wait, test_interruptible_frames, DelayTestFrameProcessor, test_uninterruptible_frames, TestUninterruptibleFrame (+7) |
| `pipecat/tests/test_service_switcher.py` | MockFrameProcessor, reset_counters, DummySystemFrame, setUp, test_init_with_manual_strategy (+7) |
| `pipecat/tests/test_context_aggregators_universal.py` | test_user_mute_strategies, test_default_user_turn_strategies, test_user_turn_stop_timeout_no_transcription, test_user_turn_stop_timeout_transcription, test_pending_transcription_emitted_on_end_frame (+6) |

## Entry Points

Start here when exploring this area:

- **`test_user_mute_strategy`** (Function) — `pipecat/tests/test_user_mute_strategy.py:26`
- **`test_basic_idle_detection`** (Function) — `pipecat/tests/test_user_idle_processor.py:21`
- **`test_active_listening_resets_idle`** (Function) — `pipecat/tests/test_user_idle_processor.py:52`
- **`test_idle_retry_callback`** (Function) — `pipecat/tests/test_user_idle_processor.py:96`
- **`test_idle_monitoring_stops_on_false_return`** (Function) — `pipecat/tests/test_user_idle_processor.py:136`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `DelayTestFrameProcessor` | Class | `pipecat/tests/test_frame_processor.py` | 132 |
| `TestUninterruptibleFrame` | Class | `pipecat/tests/test_frame_processor.py` | 163 |
| `ContextProcessor` | Class | `pipecat/tests/test_context_aggregators.py` | 498 |
| `SleepFrame` | Class | `pipecat/src/pipecat/tests/utils.py` | 27 |
| `UserIdleProcessor` | Class | `pipecat/src/pipecat/processors/user_idle_processor.py` | 26 |
| `TranscriptProcessor` | Class | `pipecat/src/pipecat/processors/transcript_processor.py` | 243 |
| `ProducerProcessor` | Class | `pipecat/src/pipecat/processors/producer_processor.py` | 27 |
| `ConsumerProcessor` | Class | `pipecat/src/pipecat/processors/consumer_processor.py` | 16 |
| `TurnTrackingObserver` | Class | `pipecat/src/pipecat/observers/turn_tracking_observer.py` | 28 |
| `SystemFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 147 |
| `UninterruptibleFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 189 |
| `TTSTextFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 410 |
| `FunctionCallResultProperties` | Class | `pipecat/src/pipecat/frames/frames.py` | 877 |
| `FunctionCallResultFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 890 |
| `CancelFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1033 |
| `FrameProcessorPauseUrgentFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1088 |
| `FrameProcessorResumeUrgentFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1104 |
| `InterruptionFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1119 |
| `StartInterruptionFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1132 |
| `UserStartedSpeakingFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1160 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Telephony_websocket → _WebSocketMessageIterator` | cross_community | 6 |
| `Telephony_websocket → Get` | cross_community | 5 |
| `Process_frame → Get_time` | cross_community | 5 |
| `Process_frame → FrameProcessed` | cross_community | 5 |
| `Process_frame → On_process_frame` | cross_community | 5 |
| `Process_frame → Start` | cross_community | 5 |
| `Process_frame → Stop` | cross_community | 5 |
| `Process_frame → Cancel` | cross_community | 5 |
| `Run_tts → To_dict` | cross_community | 5 |
| `Process_frame → Get_time` | cross_community | 5 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Foundational | 140 calls |
| Whisper | 25 calls |
| Aggregators | 17 calls |
| Cartesia | 17 calls |
| Frames | 14 calls |
| Turns | 7 calls |
| Daily | 7 calls |
| Services | 7 calls |

## How to Explore

1. `gitnexus_context({name: "test_user_mute_strategy"})` — see callers and callees
2. `gitnexus_query({query: "tests"})` — find related execution flows
3. Read key files listed above for implementation details
