# service_factory.py branch patterns

All three builders live in `core/services/pipeline/service_factory.py` and receive the
same resolved spec:

```python
spec = {provider_name, api_key, model_name, metadata, model_meta_data}
```

Each builder unpacks it, then runs a flat chain of `if provider_name == "...":` branches
inside one `try`. Insert new branches alongside the existing ones — never before the
unpack, never in a helper outside this module.

## Two shared helpers

`build_input_params(ServiceClass, metadata)` — filters metadata to the class's
`InputParams` fields and constructs it. **Anything not an InputParams field is dropped
silently.** It retries field-by-field on validation failure so one bad value cannot wipe
every other setting.

`_url_kwargs(metadata, kwarg="base_url")` — returns `{kwarg: url}` when
`metadata["base_url"]` is set, else `{}` so the Pipecat class keeps its own default.
**The kwarg name varies by provider** — Pipecat is inconsistent:

| Pipecat expects | Providers |
|---|---|
| `base_url` | most |
| `url` | several websocket services |
| `api_endpoint_base_url` | AssemblyAI |
| `server` | NVIDIA STT |

Check with `inspect_pipecat.py` before choosing.

---

## LLM — OpenAI-compatible (no branch, the default case)

Most LLM vendors need **no branch at all**. `build_llm` falls through to
`BaseOpenAILLMService`; add two entries to the maps in that fallback:

```python
default_models = {
    ...
    "yourvendor": "yourvendor-model-v1",
}
default_base_urls = {
    ...
    "yourvendor": "https://api.yourvendor.com/v1",
}
```

Always try this before writing a branch.

## LLM — dedicated SDK

```python
if provider_name == "yourvendor":
    from pipecat.services.yourvendor.llm import YourVendorLLMService
    return YourVendorLLMService(
        api_key=api_key,
        model=model or "yourvendor-default",
        params=build_input_params(YourVendorLLMService, metadata),
        **_url_kwargs(metadata),
    )
```

To force a default the caller did not set, mutate `metadata` before building params —
this is how `anthropic` turns on prompt caching:

```python
    if "enable_prompt_caching" not in metadata:
        metadata["enable_prompt_caching"] = True
```

## STT

No generic fallback exists on this layer. Every provider needs a branch.

```python
if provider_name == "yourvendor":
    from pipecat.services.yourvendor.stt import YourVendorSTTService
    kwargs = {}
    if metadata.get("sample_rate") is not None:
        kwargs["sample_rate"] = metadata["sample_rate"]
    if model:
        kwargs["model"] = model
    return YourVendorSTTService(
        api_key=api_key,
        params=build_input_params(YourVendorSTTService, metadata),
        **kwargs,
        **_url_kwargs(metadata),   # pick the right kwarg name
    )
```

If `inspect_pipecat.py` shows the class has **no `model` argument**, model selection goes
through a side channel and passing `model` does nothing. NVIDIA is the live example:

```python
    return NvidiaSTTService(
        api_key=api_key,
        model_function_map={
            "function_id": model_meta.get("function_id"),
            "model_name": model,
        },
        params=build_input_params(NvidiaSTTService, metadata),
    )
```

## TTS

Same rule — always a branch. If the service is HTTP-based it needs an `aiohttp` session,
created **inside the branch**, immediately before construction. A session created earlier
leaks when a later import fails; `_close_unused_session` cleans up only what was never
handed to a constructed service.

```python
if provider_name == "yourvendor":
    from pipecat.services.yourvendor.tts import YourVendorTTSService
    session = aiohttp.ClientSession()          # HTTP services only
    return YourVendorTTSService(
        api_key=api_key,
        voice_id=tts_voice_id,
        model=model or "yourvendor-tts-1",
        aiohttp_session=session,               # HTTP services only
        params=build_input_params(YourVendorTTSService, metadata),
        **_url_kwargs(metadata),
    )
```

Some TTS classes take `settings=` rather than `params=`, and have no `InputParams` at
all — `XAITTSService` is one. `inspect_pipecat.py` shows which.

## Checklist

- [ ] Branch key matches `name` in `dev-data.json` exactly
- [ ] `_url_kwargs` uses the kwarg name this class expects
- [ ] Model actually reaches the service (not a side-channel class)
- [ ] Every `meta_data_schema` field name is a real `InputParams` field
- [ ] HTTP TTS creates its session inside the branch
- [ ] `except` blocks log with `logger.exception` — never a bare swallow
