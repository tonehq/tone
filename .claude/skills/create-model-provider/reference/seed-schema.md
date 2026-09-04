# dev-data.json schema

Top-level keys: `llm_providers`, `stt_providers`, `tts_providers`, `built_in_tools`.
`dev/seed.py` reads this and creates `ModelProvider`, `Model`, `ModelVoice`,
`ModelLanguage` and `ApiKey` rows.

## Provider entry

```json
{
  "name": "yourvendor",
  "provider_type": "tts",
  "display_name": "Your Vendor",
  "description": "Your Vendor",
  "api_key_env": "YOURVENDOR_API_KEY",
  "models": [ ... ],
  "meta_data_schema": [ ... ],
  "voices": [ ... ],
  "status": "active"
}
```

| Key | Notes |
|---|---|
| `name` | Lowercase slug. **Must equal the `service_factory.py` branch key.** |
| `provider_type` | `stt` \| `llm` \| `tts`. Must match the bucket it sits in. |
| `description` | No " LLM"/" STT"/" TTS" suffix — seed strips it. A vendor in two layers gets **one** provider row and keeps only the first bucket's description, so keep it layer-neutral. |
| `api_key_env` | Read by `dev/seed_org.py` from the environment. Unset → skipped silently → provider visible in the UI and 401s on use. |
| `voices` | TTS only. |
| `status` | `active` \| `inactive`. |

## Model entry

```json
{
  "name": "yourvendor-tts-1",
  "base_url": "https://api.yourvendor.com/v1/speech",
  "meta_data": { "model": "yourvendor-tts-1" },
  "meta_data_schema": [ ... ]
}
```

`meta_data.model` is required — the factory passes `meta_data` through, so without it
the vendor API receives no model id. `base_url` is optional; when present it reaches the
constructor via `_url_kwargs`.

## Metadata field (the UI form control)

```json
{
  "name": "speed",
  "data_type": "float",
  "type": "input number",
  "format": "float",
  "validator": { "min": 0.5, "max": 2.0 },
  "required": 0,
  "description": "Speech speed multiplier. Default: 1.0",
  "default": 1.0
}
```

`data_type` / `format`: `string` `integer` `float` `boolean` `array`
`type`: `input` `input text` `input number` `select` `multiselect` `radio`

**`name` must be a real `InputParams` field on the Pipecat class.** `build_input_params()`
drops everything else without warning — the control renders and does nothing. Verify with
`inspect_pipecat.py`, enforce with `validate_provider.py --service`.

`default` is a UI hint only; the factory does not apply it. If the service genuinely
needs a value, set it in the branch.

## Voice entry (TTS)

```json
{
  "name": "Expressive Narrator",
  "voice_id": "English_expressive_narrator",
  "description": "An expressive adult male voice.",
  "gender": null, "language": null, "accent": null, "sample_url": null,
  "language_list": ["English", "Hindi", "Tamil"]
}
```

`language_list` is effectively required: `ModelLanguage` rows are derived from it, so an
empty list means an empty language picker.

## Seeding

```bash
python dev/seed.py        # providers, models, voices, languages, keys, tools
```

Idempotent — existing rows are skipped, not updated. **Editing an existing entry in
`dev-data.json` does not change a row already in the DB.** To change one, update it
directly or use the targeted scripts in `dev/` (`reseed_models_voices.py`,
`update_model_meta_data_schema.py`).
