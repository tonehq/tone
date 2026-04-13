---
name: processors
description: "Skill for the Processors area of tone. 145 symbols across 69 files."
---

# Processors

145 symbols | 69 files | Cohesion: 68%

## When to Use

- Working with code in `pipecat/`
- Understanding how stop, cancel, cleanup work
- Modifying processors-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/src/pipecat/processors/frame_processor.py` | FrameProcessorQueue, __init__, cancel_task, queue_frame, pause_processing_system_frames (+19) |
| `pipecat/src/pipecat/services/tts_service.py` | stop, cancel, _stop_words_task, _stop_audio_context_task, say (+4) |
| `pipecat/src/pipecat/processors/transcript_processor.py` | _emit_update, process_frame, _emit_aggregated_assistant_text, _emit_aggregated_thought, BaseTranscriptProcessor (+2) |
| `pipecat/src/pipecat/processors/consumer_processor.py` | __init__, process_frame, _stop, _cancel, _start (+1) |
| `pipecat/src/pipecat/processors/user_idle_processor.py` | __init__, _wrap_callback, _stop, cleanup |
| `core/processors/call_end_detector.py` | _build_end_pattern, __init__, CallEndDetectorProcessor |
| `core/processors/audio_recorder.py` | __init__, save, _save_audio |
| `pipecat/src/pipecat/services/simli/video.py` | InputParams, __init__, _stop |
| `pipecat/src/pipecat/processors/aggregators/dtmf_aggregator.py` | __init__, cleanup, _stop_aggregation_task |
| `pipecat/src/pipecat/services/inworld/tts.py` | stop, cancel, _disconnect |

## Entry Points

Start here when exploring this area:

- **`stop`** (Function) — `pipecat/src/pipecat/services/tts_service.py:332`
- **`cancel`** (Function) — `pipecat/src/pipecat/services/tts_service.py:343`
- **`cleanup`** (Function) — `pipecat/src/pipecat/processors/idle_frame_processor.py:71`
- **`cancel_task`** (Function) — `pipecat/src/pipecat/processors/frame_processor.py:491`
- **`process_frame`** (Function) — `pipecat/src/pipecat/processors/consumer_processor.py:46`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `FrameProcessorQueue` | Class | `pipecat/src/pipecat/processors/frame_processor.py` | 86 |
| `InputParams` | Class | `pipecat/src/pipecat/services/simli/video.py` | 46 |
| `InputParams` | Class | `pipecat/src/pipecat/services/mem0/memory.py` | 44 |
| `SentryMetrics` | Class | `pipecat/src/pipecat/processors/metrics/sentry.py` | 24 |
| `FrameProcessorMetrics` | Class | `pipecat/src/pipecat/processors/metrics/frame_processor_metrics.py` | 26 |
| `TranscriptionMessage` | Class | `pipecat/src/pipecat/frames/frames.py` | 530 |
| `ThoughtTranscriptionMessage` | Class | `pipecat/src/pipecat/frames/frames.py` | 566 |
| `TranscriptionUpdateFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 592 |
| `MetricsCollectorProcessor` | Class | `core/processors/metrics_collector.py` | 15 |
| `CallEndDetectorProcessor` | Class | `core/processors/call_end_detector.py` | 38 |
| `LLMTextProcessor` | Class | `pipecat/src/pipecat/processors/aggregators/llm_text_processor.py` | 30 |
| `BaseTranscriptProcessor` | Class | `pipecat/src/pipecat/processors/transcript_processor.py` | 36 |
| `UserTranscriptProcessor` | Class | `pipecat/src/pipecat/processors/transcript_processor.py` | 65 |
| `stop` | Function | `pipecat/src/pipecat/services/tts_service.py` | 332 |
| `cancel` | Function | `pipecat/src/pipecat/services/tts_service.py` | 343 |
| `cleanup` | Function | `pipecat/src/pipecat/processors/idle_frame_processor.py` | 71 |
| `cancel_task` | Function | `pipecat/src/pipecat/processors/frame_processor.py` | 491 |
| `process_frame` | Function | `pipecat/src/pipecat/processors/consumer_processor.py` | 46 |
| `stop` | Function | `pipecat/src/pipecat/services/hume/tts.py` | 202 |
| `cancel` | Function | `pipecat/src/pipecat/services/hume/tts.py` | 212 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Process_frame → _run_handler` | cross_community | 10 |
| `Process_frame → Create_task` | cross_community | 10 |
| `Process_frame → _run_handler` | cross_community | 8 |
| `Process_frame → Create_task` | cross_community | 8 |
| `Process_frame → Get_time` | cross_community | 8 |
| `Process_frame → FrameProcessed` | cross_community | 8 |
| `Process_frame → On_process_frame` | cross_community | 8 |
| `Run_tts → _run_handler` | cross_community | 8 |
| `Run_tts → Create_task` | cross_community | 8 |
| `Process_frame → ErrorFrame` | cross_community | 8 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Foundational | 22 calls |
| Services | 9 calls |
| Tests | 8 calls |
| Cartesia | 8 calls |
| Pipeline | 7 calls |
| Loggers | 2 calls |
| Daily | 2 calls |
| Turns | 2 calls |

## How to Explore

1. `gitnexus_context({name: "stop"})` — see callers and callees
2. `gitnexus_query({query: "processors"})` — find related execution flows
3. Read key files listed above for implementation details
