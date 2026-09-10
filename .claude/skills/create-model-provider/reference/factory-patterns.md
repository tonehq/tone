# service_factory.py branch patterns

All three builders live in `core/services/pipeline/service_factory.py` and receive the
same resolved spec:

```python
spec = {provider_name, api_key, model_name, metadata, model_meta_data}
```

Each builder unpacks it, then runs a flat chain of `if provider_name == "...":` branches
inside one `try`. Insert new branches alongside the existing ones — never before the
unpack, never in a helper outside this module.

## Shared helpers

`build_input_params(ServiceClass, metadata)` — filters metadata to the class's
`InputParams` fields and constructs it. **Anything not an InputParams field is dropped
silently.** It retries field-by-field on validation failure so one bad value cannot wipe
every other setting.

`build_settings(SettingsClass, metadata, **overrides)` — the `settings=` equivalent, for
newer Pipecat services configured through a `Settings` dataclass. **Where a class accepts
both, `settings` wins and `params` is ignored entirely** (`OpenAILLMService.__init__`
applies the settings delta last), so a branch that passes `params=` to such a class
discards every user setting without an error. Check with `inspect_pipecat.py`; if the
class exposes `Settings`, configure it through this helper. `overrides` win over metadata —
pass the model name from the DB row here so a stray metadata key cannot shadow it.

`build_llm_settings(SettingsClass, metadata, provider_name, **overrides)` — use this
instead of `build_settings` for an **LLM**. Same behavior, plus it routes request-level
knobs the `Settings` class does not declare (`LLM_REQUEST_EXTRA_FIELDS`:
`reasoning_effort`, `reasoning_format`, `reasoning_enabled`) through the provider's adapter
in `LLM_REQUEST_EXTRAS` into `Settings.extra`, which Pipecat merges into the chat request.
A knob the class *does* declare needs no adapter — Sarvam declares `reasoning_effort`, so it
passes through as a normal field. A provider with no adapter simply gets no `extra`.

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
all — `XAITTSService` is one. `inspect_pipecat.py` shows which; configure those through
`build_settings`.

### Hosted TTS — no new branch, no new service class

A vendor whose speech API is a plain JSON request-response endpoint does **not** get a
branch or a service class. Add its slug to `HOSTED_TTS_PROVIDERS` and it is served by the
shared `HostedTTSService` (`core/services/pipeline/hosted_tts_service.py`). Every wire
detail lives on the model row instead of in code — `base_url`, plus `text_field`,
`model_field`, `voice_field`, `audio_field` or `audio_url_field`, `strip_wav_header`,
`extra_body`, `extra_headers` in `meta_data`. A new hosted vendor is **one slug + one seed
entry**, nothing in `build_tts`. Reach for a dedicated branch only when the vendor needs
streaming, a websocket, or an SDK.

## Checklist

- [ ] Branch key matches `name` in `dev-data.json` exactly
- [ ] `_url_kwargs` uses the kwarg name this class expects
- [ ] Model actually reaches the service (not a side-channel class)
- [ ] Every `meta_data_schema` field name is a real `InputParams` / `Settings` field — or,
      for an LLM request knob, is in `LLM_REQUEST_EXTRA_FIELDS` and mapped by the provider's
      `LLM_REQUEST_EXTRAS` adapter (`validate_provider.py` enforces this)
- [ ] A class exposing `Settings` is configured through `build_settings` /
      `build_llm_settings` — never `params=`
- [ ] A JSON request-response TTS vendor is a `HOSTED_TTS_PROVIDERS` slug, not a new branch
- [ ] HTTP TTS creates its session inside the branch
- [ ] `except` blocks log with `logger.exception` — never a bare swallow
