# OpenAI LLM Execution Flow in Pipecat

Complete trace of how the OpenAI LLM processes input and returns output, starting from `get_llm_for_agent()` in `agent_factory_service.py`.

---

## Class Hierarchy

```
FrameProcessor                          # Base processor (frame_processor.py)
  └── AIService                         # AI service base (ai_services.py)
      └── LLMService                    # LLM-specific base (llm_service.py)
          └── BaseOpenAILLMService      # OpenAI base (openai/base_llm.py)
              └── OpenAILLMService      # Final class (openai/llm.py)
```

---

## Pipeline Layout (from `agent_factory_service.py`)

```
Transport Input → STT → [UserAggregator] → LLM → [LLMTextProcessor] → TTS → Transport Output → [AssistantAggregator]
```

---

## Phase 1: Instantiation

When `get_llm_for_agent()` calls `OpenAILLMService(api_key=..., model=...)`:

### Step 1 — `OpenAILLMService.__init__()`
**File:** `pipecat/services/openai/llm.py`

Accepts `model` (default `"gpt-4.1"`) and optional `params`. Calls parent.

### Step 2 — `BaseOpenAILLMService.__init__()`
**File:** `pipecat/services/openai/base_llm.py`

1. Calls `LLMService.__init__()` up the chain
2. Stores settings: `temperature`, `top_p`, `max_tokens`, `frequency_penalty`, `presence_penalty`, `seed`, etc.
3. Stores the model name via `self.set_model_name(model)`
4. **Creates the AsyncOpenAI client** via `self.create_client()`:
   ```python
   self._client = AsyncOpenAI(
       api_key=api_key,
       base_url=base_url,
       http_client=httpx.AsyncClient(
           limits=httpx.Limits(max_keepalive_connections=100, max_connections=1000)
       )
   )
   ```

### Step 3 — `LLMService.__init__()`
**File:** `pipecat/services/llm_service.py`

1. Initializes function call registry: `self._functions = {}`
2. Creates adapter: `self._adapter = OpenAILLMAdapter()` (converts universal context → OpenAI format)
3. Registers event handlers: `on_function_calls_started`, `on_completion_timeout`

### Step 4 — `AIService.__init__()` → `FrameProcessor.__init__()`

Sets up the frame processing pipeline infrastructure (input/output queues, metrics tracking).

**Result:** A fully configured `OpenAILLMService` instance with an API client ready to make calls.

---

## Phase 2: Context Aggregation (Before LLM)

### Step 5 — User speaks → STT produces `TranscriptionFrame`

The STT service converts speech to text and pushes a `TranscriptionFrame` downstream.

### Step 6 — `LLMUserAggregator` collects transcriptions
**File:** `pipecat/processors/aggregators/llm_response_universal.py`

The user aggregator:
1. Receives `UserStartedSpeakingFrame` → marks turn start
2. Accumulates `TranscriptionFrame` text parts in `self._aggregation`
3. Receives `UserStoppedSpeakingFrame` → marks turn end
4. Calls `push_aggregation()`:
   ```python
   async def push_aggregation(self):
       aggregation = self.aggregation_string()     # Join all text parts
       self._context.add_message({"role": "user", "content": aggregation})
       await self.push_context_frame()              # Push LLMContextFrame downstream
   ```

**Result:** An `LLMContextFrame` containing the full `LLMContext` (with all messages) flows downstream to the LLM.

---

## Phase 3: LLM Receives Context Frame

### Step 7 — `BaseOpenAILLMService.process_frame()`
**File:** `pipecat/services/openai/base_llm.py`

```python
async def process_frame(self, frame, direction):
    if isinstance(frame, LLMContextFrame):
        context = frame.context

        await self.push_frame(LLMFullResponseStartFrame())   # Signal: response starting
        await self.start_processing_metrics()
        await self._process_context(context)                  # ← MAIN CALL
        await self.stop_processing_metrics()
        await self.push_frame(LLMFullResponseEndFrame())      # Signal: response complete
```

---

## Phase 4: Building the API Request

### Step 8 — `_process_context()` → `_stream_chat_completions_universal_context()`
**File:** `pipecat/services/openai/base_llm.py`

```python
async def _process_context(self, context):
    chunk_stream = await self._stream_chat_completions_universal_context(context)
    # ... then iterates the stream (Phase 5)
```

### Step 9 — Adapter converts universal context → OpenAI format
**File:** `pipecat/adapters/services/open_ai_adapter.py`

```python
async def _stream_chat_completions_universal_context(self, context: LLMContext):
    adapter = self.get_llm_adapter()  # OpenAILLMAdapter

    # Convert universal messages/tools → OpenAI-specific format
    params: OpenAILLMInvocationParams = adapter.get_llm_invocation_params(context)
    # params = { "messages": [...], "tools": [...], "tool_choice": ... }

    chunks = await self.get_chat_completions(params)
    return chunks
```

The adapter:
- Converts `LLMContext` messages to OpenAI's `ChatCompletionMessageParam` format
- Converts `ToolsSchema` to OpenAI's `ChatCompletionToolParam` format
- Passes through `tool_choice`

### Step 10 — Build final parameters
**Method:** `build_chat_completion_params()`

```python
params = {
    "model": self.model_name,         # e.g. "gpt-4.1"
    "stream": True,                    # Always streaming
    "stream_options": {"include_usage": True},
    "temperature": ...,
    "top_p": ...,
    "max_tokens": ...,
    "max_completion_tokens": ...,
    "frequency_penalty": ...,
    "presence_penalty": ...,
    "seed": ...,
    "messages": [...],                 # From adapter
    "tools": [...],                    # From adapter (if any)
    "tool_choice": ...,                # From adapter (if any)
}
```

### Step 11 — Make the OpenAI API call
**Method:** `get_chat_completions()`

```python
async def get_chat_completions(self, params_from_context):
    params = self.build_chat_completion_params(params_from_context)

    # With optional timeout + retry
    chunks = await self._client.chat.completions.create(**params)
    return chunks   # AsyncStream[ChatCompletionChunk]
```

**Result:** A streaming async iterator of `ChatCompletionChunk` objects from the OpenAI API.

---

## Phase 5: Processing the Streaming Response

### Step 12 — Iterate chunks in `_process_context()`
**File:** `pipecat/services/openai/base_llm.py`

```python
async for chunk in chunk_stream:

    # A. Usage metrics (last chunk typically)
    if chunk.usage:
        tokens = LLMTokenUsage(
            prompt_tokens=chunk.usage.prompt_tokens,
            completion_tokens=chunk.usage.completion_tokens,
            total_tokens=chunk.usage.total_tokens,
        )
        await self.start_llm_usage_metrics(tokens)

    # B. Skip empty chunks
    if not chunk.choices or not chunk.choices[0].delta:
        continue

    # C. FUNCTION CALL chunks → accumulate name + arguments
    if chunk.choices[0].delta.tool_calls:
        tool_call = chunk.choices[0].delta.tool_calls[0]
        function_name += tool_call.function.name or ""
        arguments += tool_call.function.arguments or ""
        tool_call_id = tool_call.id or tool_call_id

    # D. TEXT chunks → push downstream IMMEDIATELY
    elif chunk.choices[0].delta.content:
        await self.push_frame(LLMTextFrame(chunk.choices[0].delta.content))
```

**Key insight:** Text is pushed downstream **one chunk at a time** as `LLMTextFrame`. This enables the TTS to start generating speech before the full response is complete (low latency).

### Step 13 — After stream ends: handle function calls (if any)

```python
if function_name and arguments:
    function_calls = [
        FunctionCallFromLLM(
            context=context,
            tool_call_id=tool_id,
            function_name=function_name,
            arguments=json.loads(arguments),   # Parse accumulated JSON
        )
    ]
    await self.run_function_calls(function_calls)
```

Function calls execute registered handlers, get results, add results back to context, and optionally trigger another LLM inference round.

---

## Phase 6: Downstream Processing

### Step 14 — `LLMTextFrame` flows through `LLMTextProcessor`

Text processor may apply any text transformations before forwarding to TTS.

### Step 15 — TTS receives text chunks

Each `LLMTextFrame` is converted to speech audio and pushed to the transport output.

### Step 16 — `LLMAssistantAggregator` collects the response
**File:** `pipecat/processors/aggregators/llm_response_universal.py`

1. Receives `LLMFullResponseStartFrame` → marks response start
2. Accumulates each `LLMTextFrame` text in `self._aggregation`
3. Receives `LLMFullResponseEndFrame` → calls `push_aggregation()`:
   ```python
   aggregation = self.aggregation_string()   # Full response text
   self._context.add_message({"role": "assistant", "content": aggregation})
   ```

**Result:** The complete assistant response is added to the conversation context for the next turn.

---

## Complete Frame Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PIPELINE FLOW                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [Transport Input]                                                  │
│       │                                                             │
│       ▼                                                             │
│  [STT Service]                                                      │
│       │  TranscriptionFrame("Hello, how are you?")                  │
│       ▼                                                             │
│  [LLMUserAggregator]                                                │
│       │  1. Accumulates transcription text                          │
│       │  2. On turn end: adds user message to LLMContext            │
│       │  3. Pushes LLMContextFrame                                  │
│       ▼                                                             │
│  [OpenAILLMService]                                                 │
│       │  1. Receives LLMContextFrame                                │
│       │  2. Pushes LLMFullResponseStartFrame                        │
│       │  3. Converts context → OpenAI params (via adapter)          │
│       │  4. Calls OpenAI API (streaming)                            │
│       │  5. For each text chunk → pushes LLMTextFrame               │
│       │  6. For function calls → accumulates, then executes         │
│       │  7. Pushes LLMFullResponseEndFrame                          │
│       ▼                                                             │
│  [LLMTextProcessor]                                                 │
│       │  LLMTextFrame("I'm")                                        │
│       │  LLMTextFrame(" doing")                                     │
│       │  LLMTextFrame(" great")                                     │
│       │  LLMTextFrame("!")                                          │
│       ▼                                                             │
│  [TTS Service]                                                      │
│       │  Converts text chunks → audio frames                        │
│       ▼                                                             │
│  [Transport Output]                                                 │
│       │  Sends audio to user                                        │
│       ▼                                                             │
│  [LLMAssistantAggregator]                                           │
│       │  1. Accumulates all LLMTextFrame text                       │
│       │  2. On LLMFullResponseEndFrame: adds assistant message      │
│       │     to LLMContext for next conversation turn                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

| Pattern | Why |
|---|---|
| **Streaming text immediately** | Each text chunk is pushed as `LLMTextFrame` right away, so TTS can start speaking before the full LLM response is done. Minimizes time-to-first-byte. |
| **Accumulating function calls** | Function name + JSON arguments arrive across multiple chunks. They must be fully assembled before execution. |
| **Adapter pattern** | `OpenAILLMAdapter` isolates OpenAI-specific message formatting. The core pipeline uses universal `LLMContext`, making it easy to swap providers. |
| **Aggregator pair** | User aggregator collects speech into one message. Assistant aggregator collects LLM output into one message. Both maintain the `LLMContext` conversation history. |
| **Frame-based architecture** | All data (text, audio, control signals) flows as typed Frame objects. Processors only handle frames they care about and pass everything else through. |

---

## Error Handling

```python
# In process_frame():
try:
    await self._process_context(context)
except httpx.TimeoutException:
    await self._call_event_handler("on_completion_timeout")
finally:
    await self.push_frame(LLMFullResponseEndFrame())  # Always sent, even on error
```

- **Timeout**: Configurable retry with `retry_on_timeout` + `retry_timeout_secs`
- **API errors**: Caught and logged; `LLMFullResponseEndFrame` still sent so pipeline doesn't hang
- **Missing functions**: Warned but not fatal; pipeline continues

---

## Metrics Tracked

| Metric | When |
|---|---|
| **TTFB** (Time To First Byte) | Start → first text chunk received |
| **Processing time** | Start → all chunks processed |
| **Token usage** | Prompt tokens, completion tokens, cached tokens, reasoning tokens |
