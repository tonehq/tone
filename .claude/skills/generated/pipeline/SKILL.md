---
name: pipeline
description: "Skill for the Pipeline area of tone. 85 symbols across 30 files."
---

# Pipeline

85 symbols | 30 files | Cohesion: 60%

## When to Use

- Working with code in `pipecat/`
- Understanding how get_tenant_context, get_current_user_id, receive work
- Modifying pipeline-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/src/pipecat/pipeline/task.py` | _create_tasks, _maybe_start_idle_task, _wait_for_pipeline_start, _wait_for_pipeline_end, wait_for_cancel (+17) |
| `pipecat/src/pipecat/pipeline/task_observer.py` | on_process_frame, on_push_frame, _send_to_proxy, TaskObserver, Proxy (+5) |
| `pipecat/src/pipecat/pipeline/pipeline.py` | PipelineSource, __init__, PipelineSink, setup, _setup_processors (+2) |
| `pipecat/src/pipecat/pipeline/sync_parallel_pipeline.py` | SyncFrame, process_frame, wait_for_sync, SyncParallelPipelineSource, __init__ (+1) |
| `pipecat/src/pipecat/pipeline/runner.py` | __init__, _setup_sigint, _setup_sigterm, _sig_handler, _sig_cancel |
| `pipecat/src/pipecat/pipeline/service_switcher.py` | __init__, ServiceSwitcherFilter, _make_pipeline_definitions, _make_pipeline_definition |
| `core/context.py` | get_tenant_context, get_current_user_id |
| `core/test_case/test_agent_upsert.py` | receive, add_message |
| `pipecat/src/pipecat/processors/frame_processor.py` | get, put |
| `pipecat/src/pipecat/processors/metrics/sentry.py` | setup, _sentry_task_handler |

## Entry Points

Start here when exploring this area:

- **`get_tenant_context`** (Function) — `core/context.py:16`
- **`get_current_user_id`** (Function) — `core/context.py:28`
- **`receive`** (Function) — `core/test_case/test_agent_upsert.py:72`
- **`user_id`** (Function) — `core/services/base.py:21`
- **`get`** (Function) — `pipecat/src/pipecat/processors/frame_processor.py:123`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `SyncFrame` | Class | `pipecat/src/pipecat/pipeline/sync_parallel_pipeline.py` | 27 |
| `TaskObserver` | Class | `pipecat/src/pipecat/pipeline/task_observer.py` | 41 |
| `IdleFrameObserver` | Class | `pipecat/src/pipecat/pipeline/task.py` | 64 |
| `SystemClock` | Class | `pipecat/src/pipecat/clocks/system_clock.py` | 13 |
| `BaseClock` | Class | `pipecat/src/pipecat/clocks/base_clock.py` | 11 |
| `TurnTraceObserver` | Class | `pipecat/src/pipecat/utils/tracing/turn_trace_observer.py` | 32 |
| `GoogleRTVIProcessor` | Class | `pipecat/src/pipecat/services/google/rtvi.py` | 91 |
| `RTVIProcessor` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 1324 |
| `CustomAddObserver2` | Class | `pipecat/tests/test_pipeline.py` | 146 |
| `PipelineSource` | Class | `pipecat/src/pipecat/pipeline/pipeline.py` | 20 |
| `PipelineSink` | Class | `pipecat/src/pipecat/pipeline/pipeline.py` | 54 |
| `Proxy` | Class | `pipecat/src/pipecat/pipeline/task_observer.py` | 24 |
| `HeartbeatFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1793 |
| `ServiceSwitcherFilter` | Class | `pipecat/src/pipecat/pipeline/service_switcher.py` | 124 |
| `SyncParallelPipelineSource` | Class | `pipecat/src/pipecat/pipeline/sync_parallel_pipeline.py` | 37 |
| `SyncParallelPipelineSink` | Class | `pipecat/src/pipecat/pipeline/sync_parallel_pipeline.py` | 69 |
| `get_tenant_context` | Function | `core/context.py` | 16 |
| `get_current_user_id` | Function | `core/context.py` | 28 |
| `receive` | Function | `core/test_case/test_agent_upsert.py` | 72 |
| `user_id` | Function | `core/services/base.py` | 21 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Process_frame → Put` | cross_community | 6 |
| `Run_tts → Put` | cross_community | 6 |
| `Process_frame → Get` | cross_community | 6 |
| `Start → Get` | cross_community | 5 |
| `Start → Get` | cross_community | 5 |
| `Run_tts → Put` | cross_community | 4 |
| `Run_tts → Put` | cross_community | 4 |
| `Run_tts → Put` | cross_community | 3 |
| `Run_tts → Put` | cross_community | 3 |
| `Run_tts → Put` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Foundational | 13 calls |
| Tests | 4 calls |
| Daily | 3 calls |
| Tracing | 2 calls |
| Processors | 2 calls |
| Asyncio | 1 calls |
| Google | 1 calls |
| Smallwebrtc | 1 calls |

## How to Explore

1. `gitnexus_context({name: "get_tenant_context"})` — see callers and callees
2. `gitnexus_query({query: "pipeline"})` — find related execution flows
3. Read key files listed above for implementation details
