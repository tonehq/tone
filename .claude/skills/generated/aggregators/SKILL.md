---
name: aggregators
description: "Skill for the Aggregators area of tone. 161 symbols across 28 files."
---

# Aggregators

161 symbols | 28 files | Cohesion: 61%

## When to Use

- Working with code in `pipecat/`
- Understanding how create_context_aggregator, create_context_aggregator, create_context_aggregator work
- Modifying aggregators-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/src/pipecat/processors/aggregators/llm_response.py` | LLMUserAggregatorParams, LLMAssistantAggregatorParams, __init__, LLMAssistantContextAggregator, process_frame (+44) |
| `pipecat/src/pipecat/processors/aggregators/llm_response_universal.py` | LLMAssistantAggregatorParams, LLMContextAggregator, __init__, LLMUserAggregator, _get_context_frame (+41) |
| `pipecat/src/pipecat/processors/aggregators/llm_context.py` | from_openai_context, create_audio_message, add_message, add_audio_frames_message, add_image_frame_message (+3) |
| `pipecat/src/pipecat/processors/aggregators/openai_llm_context.py` | get_llm_adapter, set_llm_adapter, to_standard_messages, get_messages_for_persistent_storage, from_messages (+2) |
| `pipecat/src/pipecat/frames/frames.py` | LLMMessagesUpdateFrame, OpenAILLMContextAssistantTimestampFrame, LLMMessagesFrame, EmulateUserStartedSpeakingFrame, EmulateUserStoppedSpeakingFrame (+2) |
| `pipecat/src/pipecat/services/anthropic/llm.py` | AnthropicContextAggregatorPair, create_context_aggregator, from_openai_context, AnthropicAssistantContextAggregator, get_messages_for_persistent_storage (+1) |
| `pipecat/src/pipecat/services/aws/llm.py` | AWSBedrockContextAggregatorPair, from_openai_context, AWSBedrockAssistantContextAggregator, create_context_aggregator, get_messages_for_persistent_storage (+1) |
| `pipecat/tests/test_context_aggregators_universal.py` | test_llm_run, test_llm_messages_append_run, test_llm_messages_update, test_llm_messages_update_run |
| `pipecat/src/pipecat/services/openai/llm.py` | OpenAIContextAggregatorPair, create_context_aggregator, handle_function_call_in_progress |
| `pipecat/src/pipecat/services/aws/nova_sonic/context.py` | get_messages_for_persistent_storage, flush_aggregated_user_text, flush_aggregated_assistant_text |

## Entry Points

Start here when exploring this area:

- **`create_context_aggregator`** (Function) — `pipecat/src/pipecat/services/llm_service.py:226`
- **`create_context_aggregator`** (Function) — `pipecat/src/pipecat/services/ultravox/llm.py:528`
- **`create_context_aggregator`** (Function) — `pipecat/src/pipecat/services/openai_realtime_beta/openai.py:770`
- **`create_context_aggregator`** (Function) — `pipecat/src/pipecat/services/openai/llm.py:88`
- **`create_context_aggregator`** (Function) — `pipecat/src/pipecat/services/grok/llm.py:183`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `OpenAIContextAggregatorPair` | Class | `pipecat/src/pipecat/services/openai/llm.py` | 29 |
| `GrokContextAggregatorPair` | Class | `pipecat/src/pipecat/services/grok/llm.py` | 32 |
| `GoogleContextAggregatorPair` | Class | `pipecat/src/pipecat/services/google/llm.py` | 219 |
| `AnthropicContextAggregatorPair` | Class | `pipecat/src/pipecat/services/anthropic/llm.py` | 72 |
| `AnthropicAssistantContextAggregator` | Class | `pipecat/src/pipecat/services/anthropic/llm.py` | 1094 |
| `AWSBedrockContextAggregatorPair` | Class | `pipecat/src/pipecat/services/aws/llm.py` | 74 |
| `AWSBedrockAssistantContextAggregator` | Class | `pipecat/src/pipecat/services/aws/llm.py` | 617 |
| `LLMUserAggregatorParams` | Class | `pipecat/src/pipecat/processors/aggregators/llm_response.py` | 66 |
| `LLMAssistantAggregatorParams` | Class | `pipecat/src/pipecat/processors/aggregators/llm_response.py` | 91 |
| `LLMAssistantContextAggregator` | Class | `pipecat/src/pipecat/processors/aggregators/llm_response.py` | 781 |
| `LLMMessagesUpdateFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 809 |
| `UserResponseAggregator` | Class | `pipecat/src/pipecat/processors/aggregators/user_response.py` | 18 |
| `LLMAssistantAggregatorParams` | Class | `pipecat/src/pipecat/processors/aggregators/llm_response_universal.py` | 96 |
| `LLMContextAggregator` | Class | `pipecat/src/pipecat/processors/aggregators/llm_response_universal.py` | 162 |
| `LLMUserAggregator` | Class | `pipecat/src/pipecat/processors/aggregators/llm_response_universal.py` | 282 |
| `OpenAILLMContextAssistantTimestampFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 489 |
| `LLMMessagesFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 744 |
| `EmulateUserStartedSpeakingFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1206 |
| `EmulateUserStoppedSpeakingFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1231 |
| `AnthropicUserContextAggregator` | Class | `pipecat/src/pipecat/services/anthropic/llm.py` | 1068 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Process_frame → Append_text` | cross_community | 6 |
| `Process_frame → Should_interrupt` | cross_community | 6 |
| `Process_frame → _check_started` | cross_community | 6 |
| `Process_frame → Add_message` | cross_community | 6 |
| `Process_frame → InterruptionTaskFrame` | cross_community | 5 |
| `Process_frame → Reset` | cross_community | 5 |
| `Process_frame → OpenAILLMContextFrame` | cross_community | 5 |
| `Process_frame → _run_handler` | cross_community | 4 |
| `Process_frame → Create_task` | cross_community | 4 |
| `Process_frame → Get_time` | cross_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Foundational | 32 calls |
| Openai_realtime_beta | 11 calls |
| Daily | 6 calls |
| Tests | 5 calls |
| Whisper | 4 calls |
| Processors | 3 calls |
| Cartesia | 3 calls |
| Smallwebrtc | 2 calls |

## How to Explore

1. `gitnexus_context({name: "create_context_aggregator"})` — see callers and callees
2. `gitnexus_query({query: "aggregators"})` — find related execution flows
3. Read key files listed above for implementation details
