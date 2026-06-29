# Model Pricing Reference

A clean reference for how cost is calculated across LLM, STT, and TTS providers.

---

## LLM — 20 Providers

### The 16 Standard Providers

All 16 share the same billing structure: two token counts × two rates.

- **Unit:** Per 1M tokens
- **Formula:**
  ```
  cost = (input_tokens × input_rate + output_tokens × output_rate) ÷ 1,000,000
  ```
- **Rule of thumb:** Output tokens are 3–5× pricier than input
- **Reference:** 1M tokens ≈ 750K English words

**Providers:** OpenAI, Anthropic, Groq, Cohere, Azure, DeepSeek, Qwen, Cerebras, Grok, Fireworks AI, Together AI, AWS Bedrock, OpenRouter, NVIDIA NIM, SambaNova, Ollama

> **Note:** Ollama uses the same formula but is effectively free — it runs locally on your GPU.

### The 4 Different Ones

#### 1. Google

Same per-token billing, with extras:
- **Gemma models (8 total)** — Free (open-weights served by Google)
- **Gemini 2.5 Pro & 3.1 Pro** — Double rate when context exceeds 200K tokens
- **Cost:** Normal token formula, but check which model and context tier

#### 2. Perplexity

Tokens + extra search fee:
- Per-token billing like standard providers
- Plus a per-request fee for the live web search
- **Formula:**
  ```
  cost = token_cost + (num_requests × search_fee)
  ```

#### 3. OpenAI Realtime (S2S)

Priced in **audio tokens**, not text tokens:
- 1 second of audio ≈ 128 audio tokens
- 1 minute of voice exchange ≈ 7,680 audio tokens
- **Formula:**
  ```
  cost = (audio_seconds × 128 × rate) ÷ 1,000,000
  ```
- Text tokens (system prompt, function calls) billed separately at normal text rates

#### 4. Gemini Live (S2S)

Same model as OpenAI Realtime:
- ~128 audio tokens per second of speech
- Audio in and audio out billed separately
- Text tokens priced normally on the side

### LLM Mental Model

| Group | Rule |
|---|---|
| 16 standard providers | Count words in + words out × rate |
| Google | Same, but Gemma = free; long-context surcharge over 200K |
| Perplexity | Same, plus extra search fee per call |
| Realtime / Live (2) | Audio tokens (~128/sec) instead of text tokens |

---

## STT — 15 Providers

### The 11 Standard Providers

Every model bills by **audio duration only** (input audio length). Transcript output is free.

- **Unit:** Per minute OR per hour of audio
- **Formula:**
  ```
  cost = audio_duration × rate
  ```
- Single counter — just the length of the audio you send in
- Output text (transcript) is never charged

**Providers:** OpenAI, Groq, Cartesia, Soniox, Gladia, Google Chirp, Speechmatics, Sarvam, Hathora, SambaNova, Azure

### The 4 Different Ones

#### 1. Deepgram

Same model billed at different rates depending on mode:

| Mode | Example Rate |
|---|---|
| Pre-recorded (batch) | $0.0043 / min |
| Streaming (real-time) | $0.0077 / min |
| Multilingual streaming | $0.0092 / min |

#### 2. AssemblyAI

- **Universal-3 RT-Pro** charges by WebSocket session duration (how long the connection stays open), not actual audio minutes

#### 3. Soniox

- **stt-rt (realtime)** vs **stt-async (batch)** charge different rates
- v3 / v4 / v5 each have their own tier

#### 4. ElevenLabs

| Mode | Rate |
|---|---|
| scribe_v2 (batch) | $0.22 / hr |
| scribe_v2_realtime | $0.39 / hr |

---

## TTS — 23 Providers

### The 15 Standard Providers

Every model bills by **input text length only** (characters you send). Generated audio is free.

- **Unit:** Per 1M characters (some use per 1K characters)
- **Formula:**
  ```
  cost = len(text) × rate
  ```
- Single counter — just the character count of your text
- Output audio length is never charged
- Character count includes spaces and punctuation

**Providers:** Deepgram, Groq, Hathora, Rime, Inworld, OpenAI (older voices), LMNT, Hume, AWS Polly (per voice tier), Azure (per voice tier), Speechmatics, Sarvam, Fish (UTF-8 bytes ≈ chars), PlayHT, Async AI

### The 8 Different Ones

#### 1. AWS Polly

Voice tier matters — 4× gap between tiers:

| Tier | Rate (per 1M chars) |
|---|---|
| Standard | $4.80 |
| Neural | $19.20 |

#### 2. Azure

Multiple tiers per 1M chars:

| Tier | Rate |
|---|---|
| Neural | $15 |
| DragonHD Flash | $15 |
| DragonHD | $22 |

#### 3. Google

Wide spread across voice tiers:

| Tier | Rate (per 1M chars) |
|---|---|
| WaveNet | $4 |
| Neural2 | $16 |
| Chirp 3 HD | $30 |
| Studio | $160 |

> **Gemini TTS** is priced in tokens, not characters — unit mix inside the same provider.

#### 4. MiniMax

HD variants ($50–100 per 1M) vs non-HD differ significantly.

#### 5. Cartesia

Credit / subscription model:
- Buy a credit pack
- 1 credit ≈ 1 character
- Effective cost varies by plan

#### 6. ElevenLabs

Same credit model as Cartesia:
- Pack-based pricing
- 1 credit ≈ 1 character

#### 7. Resemble AI

- Billed **per second of generated audio**, not per character (opposite of the standard model)

#### 8. NVIDIA / Camb AI

- Self-hosted / GPU-based pricing
- No per-character API rate

---

## Quick Summary

| Category | Standard Unit | Outliers |
|---|---|---|
| **LLM** | Per 1M tokens (input + output) | Google (Gemma free, long-context surcharge), Perplexity (+ search fee), OpenAI Realtime & Gemini Live (audio tokens ~128/sec) |
| **STT** | Per minute or hour of input audio | Deepgram (mode-based), AssemblyAI (session duration), Soniox (rt vs async + versions), ElevenLabs (batch vs realtime) |
| **TTS** | Per 1M input characters | AWS / Azure / Google (voice tiers), MiniMax (HD vs non-HD), Cartesia / ElevenLabs (credit packs), Resemble (per audio second), NVIDIA / Camb AI (self-hosted) |
