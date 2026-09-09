# Turn Detection

Turn detection decides when the caller has finished speaking so the agent can answer. It is selectable per agent and runs inside the Pipecat pipeline as a user-turn stop strategy, next to the voice activity detector, which is selectable the same way.

## Where it is configured

- UI: Agent editor → **Voice** → **Turn detection** card. Pick a model; the card shows that model's own fields. Save or publish the version as usual.
- API: the `turn_settings` JSON column (`config.turn_settings`) on every agent config write, for example

  ```json
  {
    "turn_detection": { "provider": "livekit", "model_type": "multilingual", "unfinished_timeout": 3 },
    "vad": { "provider": "ten", "stop_secs": 0.3, "speaking_max_secs": 10 }
  }
  ```

  `GET /api/v1/agent/turn-settings/options` returns the turn-detection models and the VAD models the server currently offers (each with the `meta_data_schema` the UI renders and the backend validates), the defaults for both, and the VAD threshold schema. Unknown providers or out-of-range values are rejected with the same `400 {"message": "Validation failed", "errors": {"turn_settings": {...}}}` shape as the LLM/STT/TTS settings.
- Omitting `turn_settings`, or either key inside it, keeps the historical behaviour: Smart Turn v3, Silero VAD and the threshold values that used to be hardcoded in the builder.

The column is copied into the Redis-cached pipeline payload (`PAYLOAD_FORMAT_VERSION` v10), so editing it invalidates the agent's cached pipeline like any other config change. Migration `690c618340d6` only adds the column; an agent configured before it existed falls back to the defaults until its turn detection is selected again.

## Voice activity detection

A VAD runs in front of every detector and decides when the caller starts and stops speaking. The model is chosen per agent in `turn_settings.vad.provider`; the thresholds below apply to whichever model is selected and live next to it. Blank fields keep the defaults.

| Field | Default | Allowed | Meaning |
|---|---|---|---|
| `confidence` | 0.7 | 0.3 to 1 | Speech probability above which audio counts as the caller talking |
| `start_secs` | 0.2 | 0.1 to 2 | Continuous speech before the caller counts as speaking |
| `stop_secs` | 0.2 | 0.1 to 3 | Silence before the caller counts as done speaking |
| `min_volume` | 0.6 | 0 to 1 | Minimum audio level for speech detection |
| `speaking_max_secs` | 8 | 3 to 60 | Longest continuous speech before the pipeline forces a stop on noisy phone lines |

The lower bounds exist because values under them end the caller's turn on line noise: on test calls with `confidence` 0.1, `start_secs` and `stop_secs` 0.05 and `speaking_max_secs` 1, 82 percent of LLM requests were cancelled before a reply and 33 of 40 turns were logged as interruptions.

### VAD models

| Slug | Model | Sample rates | Needs on the call workers |
|---|---|---|---|
| `silero` (default) | Silero ONNX bundled with Pipecat | 8 and 16 kHz | Nothing |
| `ten` | TEN VAD (Apache 2.0), faster speech-to-silence transitions than Silero; telephony audio at 8 kHz is upsampled to the model's 16 kHz | 8 and 16 kHz | `pip install git+https://github.com/TEN-framework/ten-vad.git` in the worker image. Field: `hop_size` (160 or 256 samples) |
| `krisp_viva` | Krisp VIVA VAD, licensed | 8, 16, 32, 44.1 and 48 kHz | The `krisp_audio` wheel from the Krisp developer portal (sdk.krisp.ai), `KRISP_VIVA_API_KEY` from the same portal and `KRISP_VIVA_VAD_MODEL_PATH` pointing at the downloaded `krisp-viva-vad-v2.kef`. Field: `frame_duration` (10, 20 or 30 ms) |
| `aic_quail` | ai-coustics Quail VAD, licensed; the model downloads on first use | 16 kHz | `pip install "pipecat-ai[aic]"` and `AIC_SDK_LICENSE` from developers.ai-coustics.io. Field: `model_id` (default `quail-vad-2.0-xxs-16khz`) |

A model is offered in the agent editor and accepted by validation only while its package, and for the licensed ones its key or model path, is present on the server, the same rule as the TEN turn detector. An agent already configured for a model the worker cannot load fails at pipeline build with a message naming the missing package or variable.

Adding a model: create a `VADProvider` subclass in `core/services/pipeline/vad/` with a slug, display name, description, `meta_data_schema`, optional `available()` gate and a `build(params)` that returns a Pipecat `VADAnalyzer`, then add it to `VAD_PROVIDERS` in `factory.py`. The catalog endpoint, validation, UI fields and builder pick it up without further changes.

## Models

| Slug | How it decides | Runs | Needs |
|---|---|---|---|
| `smart_turn` (default) | Audio model on the last seconds of speech | In the call worker, CPU | Nothing, the model ships with Pipecat |
| `livekit` | Language model on the transcript plus recent conversation | In the call worker, CPU | One-time ~400 MB download from Hugging Face |
| `ten` | 7B language model on the transcript, answering `finished` / `unfinished` / `wait` | On a GPU host you run | An OpenAI-compatible endpoint, see below |

For every model the builder logs one line at pipeline build: `[pipeline-builder] turn detection ready provider=... settings=...`. Text-based models log each verdict at DEBUG under `[turn-detection]` and emit Pipecat `TurnMetricsData` like Smart Turn.

### Smart Turn v3

Pipecat's bundled `LocalSmartTurnAnalyzerV3`. Fields: `confidence_threshold` (default 0.7) and `stop_secs` (default 0.8). The telephony fallback that ends a turn after 0.6 s of transcript silence stays active for this model only, because the text-based models carry their own `unfinished_timeout`.

### LiveKit Turn Detector

Port of `livekit-plugins-turn-detector`: repo `livekit/turn-detector`, revision `v0.4.1-intl` (multilingual) or `v1.2.2-en` (deprecated English-only), INT8 ONNX model run with onnxruntime on one CPU thread. The last six turns of the conversation (assistant and user, taken from the live `LLMContext`) plus the current transcript are rendered with the Qwen chat template, left-truncated to 128 tokens, and the model returns the probability that the turn is over. The verdict is compared with the per-language threshold the model ships in `languages.json` (en 0.011, hi 0.0398, zh 0.0066, ...). The language comes from the transcript when the STT reports one, otherwise from the `language` field, otherwise from the agent's STT language; an unsupported language ends the turn immediately.

Fields: `model_type`, `threshold` (override, leave empty for the tuned value), `language`, `unfinished_timeout` (default 3 s), `max_history_turns` (default 6).

First use downloads `onnx/model_q8.onnx`, `tokenizer.json` and `languages.json` into the Hugging Face cache (`HF_HOME`, default `~/.cache/huggingface`) and loads the session once per worker process. To pay that cost at worker start instead of on the first call:

```bash
TURN_DETECTION_PRELOAD=livekit
```

Call workers need outbound access to `huggingface.co` the first time, or a pre-populated cache baked into the image.

License: the model weights are published under the LiveKit Model License, which permits use only together with the LiveKit Agents framework. Running them inside this pipeline is outside that grant; confirm with LiveKit or legal before shipping this option to customers.

### TEN Turn Detection

`TEN-framework/TEN_Turn_Detection` (Apache 2.0) is a Qwen2.5-7B fine-tune, about 15 GB in bf16. It cannot run inside the call worker; TEN's own framework talks to it over an OpenAI-compatible chat completions API, and this integration does the same.

What is required to enable it:

1. A GPU host (roughly 16 GB of VRAM for bf16, less with a quantised variant) serving the model with an OpenAI-compatible `/v1/chat/completions` endpoint. Any server works; a typical choice on the GPU host is vLLM:

   ```bash
   vllm serve TEN-framework/TEN_Turn_Detection --served-model-name TEN_Turn_Detection --port 8000
   ```

   Nothing is installed on the API or call-worker machines.
2. Network access from the call workers to that host, with latency well under the `request_timeout` (default 2 s).
3. Environment on the API and call workers:

   ```bash
   TEN_TURN_DETECTION_BASE_URL=http://<gpu-host>:8000/v1   # required
   TEN_TURN_DETECTION_API_KEY=<token>                      # optional, blank sends "TEN_Turn_Detection"
   TEN_TURN_DETECTION_MODEL=TEN_Turn_Detection             # optional, blank sends "TEN_Turn_Detection"
   ```

The `ten` option appears in the agent editor and passes validation only while `TEN_TURN_DETECTION_BASE_URL` is set. An agent already configured for TEN on a server without the URL fails at pipeline build with `TEN turn detection requires TEN_TURN_DETECTION_BASE_URL`.

Protocol, matching the reference TEN extension: after every final transcript the accumulated turn text (punctuation stripped unless `strip_punctuation` is off) is sent as a single user message with `max_tokens=1`, `temperature=0.1`, `top_p=0.1`. `finished` ends the turn, `unfinished` keeps listening until `unfinished_timeout` (default 5 s) or more speech, `wait` keeps the turn open with no timeout. A timeout or HTTP error ends the turn immediately and pauses further requests for 10 s, so a dead endpoint never adds its timeout to every turn.

Fields: `unfinished_timeout`, `request_timeout`, `strip_punctuation`.

## Adding a model

Create a `TurnDetector` subclass in `core/services/pipeline/turn_detection/` with a slug, display name, description, `meta_data_schema`, optional `available()` gate and a `build()` that returns Pipecat stop strategies, then add it to `TURN_DETECTORS` in `factory.py`. The catalog endpoint, validation, UI fields and builder pick it up without further changes.
