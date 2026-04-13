# Model Benchmarks Reference

> Benchmarks for all LLM, STT, and TTS providers/models used in Tone's `dev-data.json`.
> Last updated: April 2026

---

## Table of Contents

- [LLM Benchmarks — Quality](#llm-benchmarks)
- [LLM Benchmarks — Latency & Speed](#llm-latency--speed-benchmarks)
- [STT Benchmarks](#stt-benchmarks)
- [TTS Benchmarks](#tts-benchmarks)
- [Sources](#sources)

---

## LLM Benchmarks

### OpenAI

| Model | MMLU | HumanEval/Coding | Arena ELO | Context Window | Notes |
|-------|------|-------------------|-----------|----------------|-------|
| gpt-4o | 88.7% | 90.2% | ~1350 | 128K | Flagship multimodal model |
| gpt-4o-mini | 82.0% | 87.2% | ~1270 | 128K | Cost-efficient; outperforms Gemini Flash & Claude Haiku on MMLU |
| gpt-4-turbo | 86.5% | 67.0% | ~1310 | 128K | Predecessor to 4o; weaker on coding |
| gpt-4.1 | 90.2% | 94.5% | N/A | 1M | SWE-bench 54.6% |
| gpt-5 | ~90.2% | ~90.5% | ~1484 | 128K–1M | SWE-bench 74.9%; AIME 94.6% |
| o1 | 91.8% | 89.3% | ~1370 | 200K | Reasoning model; MATH 96.4% |
| o3 | 92.9% | 87.4% | N/A | 200K | Reasoning model; MATH 97.8%; GPQA 82.8% |
| o3-mini | 85.9% | 96.3% | ~1340 | 200K | Efficient reasoning; high variant: 97.6% HumanEval |
| o4-mini | 90.0% | 97.3% | N/A | 200K | High variant: 99.3% HumanEval, MATH 98.2% |

### Anthropic

| Model | MMLU | HumanEval/Coding | Arena ELO | Context Window | Notes |
|-------|------|-------------------|-----------|----------------|-------|
| claude-opus-4-6 | 90.5% | ~97.8% | 1504 (thinking) / 1549 (coding) | 1M | #1 Arena overall & coding; GPQA 91.3%; SWE-bench 80.8% |
| claude-sonnet-4-6 | 89.3% | ~98% | 1523 (coding) | 1M | SWE-bench 79.6%; GPQA 74.1% |
| claude-opus-4-5 | ~90.8% | ~93% | ~1465 (coding) | 200K | SWE-bench 80.9%; MMLU-Pro 90% |
| claude-sonnet-4-5 | 89.3% | 97.6% | ~1491 (coding, thinking) | 200K | HumanEval leaderboard leader |
| claude-haiku-4-5 | 90.8% | N/A | N/A | 200K | 3x faster than Sonnet; AIME 80.7% |

### Google

| Model | MMLU | HumanEval/Coding | Arena ELO | Context Window | Notes |
|-------|------|-------------------|-----------|----------------|-------|
| gemini-2.5-pro | 88.6% | N/A | ~1450 | 1M | AIME 2024: 92%; AIME 2025: 83% |
| gemini-2.5-flash | 88.4% | N/A | ~1380 | 1M | GPQA 82.8%; AIME 88%; cost-efficient |
| gemini-2.5-flash-lite | N/A | N/A | N/A | 1M | ~75% of Flash capability at 30% cost |

### Meta (Llama — via Groq, SambaNova, Together, etc.)

| Model | MMLU | HumanEval/Coding | Arena ELO | Context Window | Notes |
|-------|------|-------------------|-----------|----------------|-------|
| llama-3.1-8b | 73.0% | 72.6% | N/A | 128K | Open-weight; smallest Llama 3.1 |
| llama-3.3-70b | 86.0% | 88.0% | ~1250 | 128K | Improved coding over 3.1-70B |

### DeepSeek

| Model | MMLU | HumanEval/Coding | Arena ELO | Context Window | Notes |
|-------|------|-------------------|-----------|----------------|-------|
| deepseek-chat (V3) | 87.1% | 82.6% | ~1320 | 128K | MoE architecture; GSM8K 89.3% |
| deepseek-reasoner (R1) | 90.8% | N/A | ~1360 | 128K | Chain-of-thought; AIME 2025: 87.5%; GPQA 81.0% |

### Other LLM Providers

| Provider | Model | MMLU | HumanEval/Coding | Arena ELO | Context Window | Notes |
|----------|-------|------|-------------------|-----------|----------------|-------|
| Alibaba | qwen3-max (235B MoE) | ~83.9% | N/A | N/A | 262K (ext. to 1M) | Open-weight; LiveCodeBench v6: 83.6% |
| xAI | grok-4 | 86.6% | ~98% | 1491 | 256K (Fast: 2M) | GPQA Diamond 88% (all-time high); AIME ~93% |
| Mistral | mistral-large-3 | 85.5% | ~92% | ~1290 | 256K | 675B MoE; open-weight; strong multilingual |
| Mistral | mistral-small-3.1 | 79.0% | 74.0% | N/A | 128K | 24B params; fits 16GB RAM at Q4 |
| Perplexity | sonar | N/A | N/A | N/A | 127K | Search-augmented; SimpleQA F-score 0.773 |
| Perplexity | sonar-pro | N/A | N/A | N/A | 200K | Search-augmented; SimpleQA F-score 0.858 |

### LLM Key Observations

- **MMLU is saturated** — most frontier models score 88–93%. GPQA Diamond and AIME are now better differentiators.
- **o4-mini-high achieves 99.3% HumanEval** — highest coding score of any model.
- **Claude Opus 4.6 Thinking holds #1 on LMSYS Arena** (ELO 1504 overall, 1549 coding).
- **Context windows have expanded** — GPT-4.1, Claude 4.6, Gemini 2.5, and Grok 4 Fast all support 1M–2M tokens.

---

## LLM Latency & Speed Benchmarks

> TTFT = Time to First Token. TPS = Tokens per second (output). Total Latency = approximate time for a 500-token response.
> Reasoning models (o1, o3, o4-mini, GPT-5, Gemini 2.5 Pro) have high TTFT due to internal chain-of-thought "thinking" time.

### OpenAI

| Model | TTFT (ms) | Output Speed (tok/s) | Total Latency (~500 tok) | Notes |
|-------|-----------|---------------------|--------------------------|-------|
| gpt-4o | 970 | 102.1 | ~6.5s | Azure variant: 2.29s TTFT, 71.3 t/s |
| gpt-4o-mini | 3,360 | 31.4 | ~19s | Slow on OpenAI API; Azure much faster: 1.67s TTFT, 99.4 t/s |
| gpt-4.1 | 910 | 117.2 | ~5.2s | Strong balanced perf |
| gpt-5 (high) | 87,660 | 81.9 | ~94s | Reasoning model; very high TTFT due to extended thinking |
| o1 | 33,970 | 104.3 | ~39s | Reasoning model |
| o3-mini | 7,120 | 137.6 | ~10.7s | Fast output for a reasoning model |
| o4-mini (high) | 43,880 | 121.5 | ~48s | Reasoning model; high TTFT but strong throughput |

### Anthropic

| Model | TTFT (ms) | Output Speed (tok/s) | Total Latency (~500 tok) | Notes |
|-------|-----------|---------------------|--------------------------|-------|
| claude-opus-4-6 | 1,820 | 38.6 | ~15s | "Fast Mode" available at 2.5x speed |
| claude-sonnet-4-6 | 1,080–1,680 | 41.6–44.1 | ~13s | Google Vertex lowest TTFT (1.08s) |
| claude-opus-4-5 | 1,460 | 52.2 | ~11s | Reasoning variant: 13.03s TTFT, 63.9 t/s |
| claude-sonnet-4-5 | 1,350 | 36.9 | ~15s | Below-avg output speed |
| claude-haiku-4-5 | 639 | 95.4 | ~6s | Fastest TTFT of any major model; up to 135 t/s on long prompts |

### Google

| Model | TTFT (ms) | Output Speed (tok/s) | Total Latency (~500 tok) | Notes |
|-------|-----------|---------------------|--------------------------|-------|
| gemini-2.5-pro | 34,510 | 112.0 | ~39s | Reasoning model; very high TTFT |
| gemini-2.5-flash | 520 | 220.0 | ~2.8s | Excellent speed/latency combo |
| gemini-2.5-flash-lite | 290–410 | 392.8 | ~1.6s | Ultra-fast; up to 887 t/s reported |

### DeepSeek

| Model | TTFT (ms) | Output Speed (tok/s) | Total Latency (~500 tok) | Notes |
|-------|-----------|---------------------|--------------------------|-------|
| deepseek-chat (V3) | 7,000 | 34.0 | ~21s | Via DeepInfra: 820ms TTFT, 97 t/s |
| deepseek-reasoner (R1) | 7,000+ | ~34 | ~22s+ | Reasoning model; similar throughput to V3 |

### xAI / Grok

| Model | TTFT (ms) | Output Speed (tok/s) | Total Latency (~500 tok) | Notes |
|-------|-----------|---------------------|--------------------------|-------|
| grok-4 | 10,540 | 50.9 | ~20s | Reasoning model |
| grok-4 (fast, non-reasoning) | 540 | 124.3 | ~4.6s | Much faster non-reasoning variant |

### Mistral

| Model | TTFT (ms) | Output Speed (tok/s) | Total Latency (~500 tok) | Notes |
|-------|-----------|---------------------|--------------------------|-------|
| mistral-large-3 | 4,410 | 37.4 | ~18s | Notably slow output for its tier |
| mistral-small-3.1 | 280–910 | 121.0 | ~4.4s | Google Vertex TTFT as low as 180ms |

### Perplexity

| Model | TTFT (ms) | Output Speed (tok/s) | Total Latency (~500 tok) | Notes |
|-------|-----------|---------------------|--------------------------|-------|
| sonar-pro | 1,510 | 123.7 | ~5.5s | Includes search/retrieval overhead |
| sonar-3.1-small | 160 | 148.0 | N/A | Very fast TTFT |
| sonar-3.1-large | 360 | 58.0 | N/A | Larger variant, slower throughput |

### Meta Llama — Speed by Inference Provider

> Same model, very different speed depending on where it's hosted.

#### Llama 3.1 8B

| Provider | Output Speed (tok/s) | Notes |
|----------|---------------------|-------|
| Cerebras | 2,197.7 | Wafer-scale engine; fastest by far |
| Groq | 668.6 | LPU architecture |
| SambaNova | 634.5 | SN40L/SN50 chips |
| FriendliAI | 304.9 | GPU-optimized serving |
| Azure | 207.6 | Cloud GPU |
| Fireworks | ~200 | GPU-optimized |
| Together | ~150 | GPU-based |

#### Llama 3.3 70B

| Provider | TTFT (ms) | Output Speed (tok/s) | Notes |
|----------|-----------|---------------------|-------|
| Groq | 800 | 315.6 | Speculative decoding variant: 1,665 t/s |
| SambaNova | N/A | 294.1 | Competitive with Groq |
| Fireworks | 600 | N/A | Tied for lowest TTFT |
| Google Vertex | 600 | N/A | Tied for lowest TTFT |

### LLM Latency Key Observations

- **Best for voice agents (low TTFT):** Gemini 2.5 Flash-Lite (290ms), Claude Haiku 4.5 (639ms), Gemini 2.5 Flash (520ms), GPT-4.1 (910ms)
- **Fastest throughput (first-party):** Gemini 2.5 Flash-Lite (393–887 t/s), Gemini 2.5 Flash (220 t/s), o3-mini (137.6 t/s)
- **Fastest throughput (inference providers):** Cerebras (2,198 t/s), Groq speculative (1,665 t/s), Groq (668 t/s)
- **Reasoning models are slow to start:** GPT-5 (88s), o4-mini (44s), Gemini 2.5 Pro (34.5s) — not ideal for real-time voice

---

## STT Benchmarks

| Provider | Model | WER (AA-WER / LibriSpeech) | Languages | Streaming | Latency | Notes |
|----------|-------|---------------------------|-----------|-----------|---------|-------|
| **Deepgram** | Nova-3 | 5.4% AA-WER; ~2.2% LS clean | 47+ | Yes | Sub-300ms | Fastest commercial API (~113x RT). 54% WER reduction over nearest competitor |
| **Deepgram** | Nova-2-General | 5.5% AA-WER | 36 | Yes | Sub-300ms | Predecessor to Nova-3 |
| **OpenAI** | whisper-1 | ~4.2% AA-WER; ~2.7% LS clean | 57+ | No (batch) | High | Hosted Whisper Large v2; open-source base |
| **OpenAI** | gpt-4o-transcribe | ~4.1% AA-WER; ~2.5% LS clean | 50+ | Yes (Realtime API) | Moderate | Best accuracy among OpenAI STT models |
| **OpenAI** | gpt-4o-mini-transcribe | N/A | 50+ | Yes (Realtime API) | Lower | Cost-optimized; slightly lower accuracy |
| **Groq** | whisper-large-v3-turbo | ~4.8% AA-WER | 57+ | No (batch) | Ultra-low (216–252x RT) | Fastest Whisper inference available |
| **Groq** | whisper-large-v3 | ~2.7% LS clean | 57+ | No (batch) | Very low (164x RT) | Full Whisper v3 on LPU hardware |
| **AssemblyAI** | Universal-3-Pro | 3.2% AA-WER; 5.6% mean (26 datasets) | 99 | Yes (8.14% WER streaming) | ~61x RT | Lowest streaming WER among major providers |
| **AssemblyAI** | Universal-2 | ~2.4% LS clean | 99 | Yes | N/A | Broad language coverage |
| **Cartesia** | ink-whisper | ~19% WER (phone calls) | 57+ (trained on 98) | Yes | Fastest TTCT streaming | Optimized for conversational/real-time; dynamic chunking |
| **Soniox** | stt-rt-v4 | ~6.5% EN; 1.29% voice-agent benchmark | 60+ | Yes | 249ms median | Purpose-built for real-time voice agents |
| **ElevenLabs** | scribe_v2 | 2.3% AA-WER; 93.5% FLEURS accuracy | 90+ | Yes (Realtime variant) | ~150ms | Lowest WER on Artificial Analysis leaderboard |
| **Gladia** | solaria-1 | ~6% WER avg; 29% lower WER than competitors on conversational | 100+ | Yes | 103ms partial, 270ms avg | First universal multilingual model; strong code-switching |
| **Google** | chirp_3 | ~2.5% LS clean | 100+ | Yes | N/A | Speaker diarization and auto language detection |
| **Google** | chirp_2 | ~9.8–11.6% AA-WER | 100+ | No (batch) | N/A | Batch-only; accuracy varies by dataset |
| **Azure** | Universal Language Model | ~13–23% WER (varies) | 100+ | Yes | N/A | Broad language support; MAI-Transcribe-1 (3.0% AA-WER) is newer |
| **Azure** | Whisper | ~4.2% AA-WER | 57+ | No (batch) | N/A | Azure-hosted OpenAI Whisper; custom fine-tuning available |
| **Speechmatics** | Enhanced Operating Point | ~4.3% AA-WER | 55+ | Yes | +734ms over Deepgram baseline | Higher accuracy than Standard at cost of speed |
| **NVIDIA** | Parakeet-TDT-0.6B-v2 | 1.69% / 3.19% LS clean/other | English only | No (self-hosted) | RTFx 3,386x (batch) | Open-source; top of HuggingFace Open ASR Leaderboard |
| **NVIDIA** | Parakeet-TDT-0.6B-v3 | 1.93% / 3.59% LS clean/other | 25 (EU languages) | No (self-hosted) | Similar to v2 | Multilingual extension; open-source |
| **Sarvam** | Saarika v2.5 | ~13.58% WER (VISTAAR avg) | 11 Indian languages + EN | Yes | N/A | Specialized for Indian languages; being deprecated |
| **SambaNova** | Whisper-Large-v3 | ~2% clean / ~12% noisy | 57+ | No (batch) | 245x RT | Fastest Whisper hosting alongside Groq |

### STT Key Observations

- **Best accuracy (commercial):** ElevenLabs Scribe v2 (2.3% AA-WER) and AssemblyAI Universal-3-Pro (3.2% AA-WER)
- **Best accuracy (open-source):** NVIDIA Parakeet-TDT-0.6B-v2 (1.69% LibriSpeech clean)
- **Fastest inference:** NVIDIA Parakeet self-hosted (3,386x RT), Groq Whisper (252x RT), SambaNova (245x RT)
- **Lowest streaming latency:** Cartesia ink-whisper (fastest TTCT), ElevenLabs Scribe v2 (~150ms), Soniox stt-rt-v4 (249ms)
- **Most languages:** Gladia Solaria-1 (100+), Google Chirp 3 (100+), AssemblyAI (99)

### STT Important Caveats

1. **WER varies dramatically by dataset.** LibriSpeech clean is read speech in quiet conditions — real-world conversational audio typically yields 2–5x higher WER.
2. **AA-WER** (Artificial Analysis WER) uses Common Voice v16.1 with diverse accents and noise — more representative of production conditions.
3. **Self-reported vs independent benchmarks differ.** Vendor-reported numbers are often lower than independent evaluations.
4. **Streaming WER is typically higher** than batch/pre-recorded WER for the same model due to limited lookahead context.

---

## TTS Benchmarks

| Provider | Model | MOS / Quality | Latency (TTFB) | Languages | Voices | Streaming | Notes |
|----------|-------|--------------|-----------------|-----------|--------|-----------|-------|
| **Cartesia** | Sonic 3 | ELO 1,054 | ~40ms TTFA | 42 | Prebuilt + 3s voice cloning | Yes | 60+ emotional tones; state-space architecture |
| **Cartesia** | Sonic 2 | N/A | ~90ms | 15 | Prebuilt + voice cloning | Yes | Predecessor to Sonic 3 |
| **Cartesia** | Sonic Turbo | N/A | ~40ms | 15 | Same as Sonic 2 | Yes | Half-latency variant of Sonic 2 |
| **ElevenLabs** | eleven_v3 | ELO ~1,108; MOS ~3.83 | Higher; not real-time suited | 32+ | 380+ library voices | Yes | Most expressive model |
| **ElevenLabs** | eleven_multilingual_v2 | ELO 1,108 | ~300ms+ | 29 | 380+ | Yes | Flagship multilingual model |
| **ElevenLabs** | eleven_flash_v2_5 | N/A | ~75ms | 32 | 380+ | Yes | Lowest-latency ElevenLabs model |
| **ElevenLabs** | eleven_turbo_v2_5 | N/A | ~75–100ms | 32 | 380+ | Yes | Functionally equivalent to flash, slightly higher latency |
| **PlayHT** | PlayDialog | N/A | N/A | 30+ | Multiple + voice cloning | Yes | Flagship conversational/multi-turn model |
| **PlayHT** | Play3.0-mini | N/A | ~143ms | 30+ | Multiple + voice cloning | Yes | 28% faster inference than Play 2.0 |
| **Deepgram** | Aura-2 | N/A | ~90ms; P95 <200ms | 7 | 40+ English voices | Yes | Built in Rust; #1 in Coval real-time benchmarks |
| **Deepgram** | Aura | N/A | ~250ms | 2 | 20+ | Yes | First-gen; English-centric |
| **OpenAI** | tts-1 | ELO 1,106 | ~250ms | 57 | 9 voices | Yes | Low-latency variant; MP3/Opus/AAC/FLAC/WAV/PCM |
| **OpenAI** | tts-1-hd | N/A | Higher than tts-1 | 57 | 9 | Yes | Higher fidelity audio output |
| **OpenAI** | gpt-4o-mini-tts | MOS >4.0 | ~250ms | 32 | 9 + steerable instructions | Yes | Instruction-steerable tone/style |
| **Hume AI** | Octave 1 | N/A | ~300ms+ | 2 | Voice design from text prompts | Yes | Emotion-aware; voice cloning from 15s audio |
| **Hume AI** | Octave 2 | ELO 1,046 | <200ms | 11 | 60+ prebuilt + prompt-designed | Yes | 40% faster, 50% cheaper than Octave 1 |
| **LMNT** | Blizzard | N/A | 150–200ms | 24 | Multiple + 5s voice cloning | Yes | Mid-sentence voice switching; unlimited concurrency |
| **Rime** | Arcana | N/A | ~80ms model / ~200ms cloud | 4 | 40+ (18 EN accents) | Yes | Trained on real customer service data |
| **Rime** | Mist v2 | N/A | ~100ms on-prem / ~225ms cloud | 4 | Multiple | Yes | Powers tens of millions of production calls/month |
| **MiniMax** | Speech 2.8 HD | ELO #1 (mid-2025) | ~300ms+ | Multiple | Multiple + voice cloning | Yes | Studio-grade fidelity; top arena ELO for quality |
| **MiniMax** | Speech 2.8 Turbo | N/A | ~200ms; <250ms | Multiple | Multiple + voice cloning | Yes | Speed-optimized variant |
| **Fish Audio** | Speech 1.5/1.6 | ELO 1,339 | <150ms | 13 | 2M+ community; 10s cloning | Yes | Open-source weights available |
| **Resemble AI** | tts-v4 / Chatterbox | 63.75% preference vs ElevenLabs | <200ms | Multiple | Custom voice cloning | Yes | 350M-param turbo; open-source Chatterbox |
| **Neuphonic** | neu_hq | N/A | <25ms (cloud) | 4 | Multiple + 3s voice cloning | Yes | Ultra-low latency cloud TTS |
| **Inworld** | TTS-1.5 Max | ELO 1,236 (#1 AA, Mar 2026) | <250ms P90 | 15 | Custom + voice cloning | Yes | 30% more expressive, 40% lower WER vs prior gen |
| **Inworld** | TTS-1.5 Mini | N/A | <130ms P90 | 15 | Custom | Yes | Lightweight low-latency variant |
| **Camb AI** | MARS8-Flash | CER 5.67%; PQ 7.45 | ~100ms | 150+ | Multiple + voice cloning | Yes | Ultra-low latency for real-time agents |
| **Camb AI** | MARS8-Pro | 0.87 speaker similarity; PQ 7.45 | 800ms–2s | 150+ | Multiple + voice cloning | Yes | High-fidelity; suited for dubbing/production |
| **Google Cloud** | Chirp 3 HD | N/A | Up to 3.5s (long text) | 31 | 8 styles per language | Yes | Advanced audio controls |
| **Google Cloud** | Studio | N/A | ~200–400ms | Limited (EN) | ~4 | Yes | Designed for news/broadcast |
| **Google Cloud** | Neural2 | N/A | ~100–200ms | 40+ | 100+ | Yes | Good price/performance |
| **Azure** | Dragon HD | N/A | ~354ms+ | 19 GA languages | 30 HD voices | Yes | LM-enhanced context; auto-emotion detection |
| **Azure** | Neural | N/A | ~100–200ms | 150+ | 600+ | Yes | Fastest Azure tier; massive coverage |
| **AWS Polly** | Generative | ELO 1,060 | ~100ms–1s | 20+ locales | 43 voices | Yes | Bidirectional streaming (Mar 2026) |
| **AWS Polly** | Neural | N/A | ~100–300ms | 30+ | 60+ | Yes | Mid-tier quality |
| **AWS Polly** | Standard | N/A | ~50–100ms | 40+ | 60+ | Yes | Lowest latency; concatenative synthesis |
| **Speechmatics** | TTS | N/A | ~150ms | EN (US, UK) | Limited | Yes | Focus on reliability/clarity |
| **NVIDIA** | Magpie TTS | N/A | Self-hosted (varies) | 9 | 2+ per language | Yes | Up to 64 concurrent streams |
| **NVIDIA** | FastPitch+HiFiGAN | N/A | Self-hosted (varies) | 1 (EN-US) | Limited | Yes | Legacy mel-spectrogram + vocoder pipeline |
| **Groq** | Orpheus v1 | N/A | N/A | EN, Arabic | Multiple | Yes | Community-driven; early stage |

### TTS Key Observations

- **Lowest latency:** Neuphonic (<25ms cloud), Cartesia Sonic 3/Turbo (~40ms), ElevenLabs Flash v2.5 (~75ms)
- **Highest quality (ELO):** Inworld TTS-1.5 Max (1,236), Fish Audio 1.5 (1,339), ElevenLabs Multilingual v2 (1,108), OpenAI tts-1 (1,106)
- **Most languages:** Camb AI MARS8 (150+), Azure Neural (150+), OpenAI (57), Cartesia Sonic 3 (42)
- **Most voices:** Azure Neural (600+), ElevenLabs (380+), Fish Audio (2M+ community)
- **All providers support streaming** in some form (WebSocket, chunked HTTP, or gRPC)

---

## Sources

### LLM Sources
- [OpenAI Simple-Evals (GitHub)](https://github.com/openai/simple-evals)
- [OpenAI GPT-4o mini announcement](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/)
- [OpenAI Introducing GPT-4.1](https://openai.com/index/gpt-4-1/)
- [OpenAI Introducing GPT-5](https://openai.com/index/introducing-gpt-5/)
- [LMSYS Chatbot Arena April 2026 Rankings](https://aidevdayindia.org/blogs/lmsys-chatbot-arena-current-rankings/)
- [Anthropic Claude Opus 4.6](https://www.anthropic.com/claude/opus)
- [Claude Benchmarks 2026 (MorphLLM)](https://www.morphllm.com/claude-benchmarks)
- [Claude Opus 4.6 vs Sonnet 4.6 Comparison](https://zoer.ai/posts/zoer/claude-opus-4-6-vs-sonnet-4-6-benchmark-comparison)
- [Gemini 2.5 Pro Developer Guide (Helicone)](https://www.helicone.ai/blog/gemini-2.5-full-developer-guide)
- [Gemini 2.5 Flash (LLM Stats)](https://llm-stats.com/models/gemini-2.5-flash)
- [Meta Llama 3.1 Eval Details (GitHub)](https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/eval_details.md)
- [DeepSeek V3 (Hugging Face)](https://huggingface.co/deepseek-ai/DeepSeek-V3)
- [Qwen3 Technical Report (arXiv)](https://arxiv.org/html/2505.09388v1)
- [xAI Grok 4 Models and Pricing](https://docs.x.ai/developers/models)
- [Mistral Large 3 Docs](https://docs.mistral.ai/models/mistral-large-3-25-12)
- [Perplexity Sonar Pro Blog](https://www.perplexity.ai/hub/blog/new-sonar-search-modes-outperform-openai-in-cost-and-performance)
- [Klu LLM Leaderboard 2026](https://klu.ai/llm-leaderboard)

### LLM Latency Sources
- [Artificial Analysis - LLM Leaderboard](https://artificialanalysis.ai/leaderboards/models)
- [LLM API Latency Benchmarks 2026 - Kunal Ganglani](https://www.kunalganglani.com/blog/llm-api-latency-benchmarks-2026)
- [BenchLM - LLM Speed & Latency Comparison](https://benchlm.ai/llm-speed)
- [Artificial Analysis - Model Providers](https://artificialanalysis.ai/models/) (individual model pages for GPT-4o, GPT-4.1, GPT-5, o1, o3-mini, o4-mini, Claude Opus/Sonnet/Haiku, Gemini, DeepSeek, Grok, Mistral, Sonar Pro)
- [Groq - Llama 3.3 70B Benchmark](https://groq.com/blog/new-ai-inference-speed-benchmark-for-llama-3-3-70b-powered-by-groq)
- [Cerebras - Llama 3.1 405B at 969 t/s](https://markets.financialcontent.com/wral/article/tokenring-2026-1-1-cerebras-shatters-inference-records)
- [DeepInfra - DeepSeek V3.2 Benchmarks](https://deepinfra.com/blog/deepseek-v3-2-api-benchmarks)

### STT Sources
- [Deepgram STT Benchmarks](https://deepgram.com/learn/speech-to-text-benchmarks)
- [Deepgram Nova-3 Announcement](https://deepgram.com/learn/introducing-nova-3-speech-to-text-api)
- [OpenAI Next-Gen Audio Models](https://openai.com/index/introducing-our-next-generation-audio-models/)
- [Groq Whisper Large v3 at 164x](https://groq.com/blog/groq-runs-whisper-large-v3-at-a-164x-speed-factor)
- [AssemblyAI Benchmarks](https://www.assemblyai.com/benchmarks)
- [AssemblyAI Universal-3-Pro](https://www.assemblyai.com/universal-3-pro)
- [Cartesia Ink STT Models](https://docs.cartesia.ai/build-with-cartesia/stt-models)
- [Soniox Benchmarks](https://soniox.com/benchmarks)
- [ElevenLabs Scribe v2](https://elevenlabs.io/blog/introducing-scribe-v2)
- [Gladia Solaria-1](https://www.gladia.io/solaria)
- [Google Chirp 3 Docs](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3)
- [Azure Speech-to-Text Overview](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-to-text)
- [Speechmatics Languages & Models](https://docs.speechmatics.com/features/accuracy-language-packs)
- [NVIDIA Parakeet-TDT-0.6B-v2 (HuggingFace)](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2)
- [Sarvam Saarika Docs](https://docs.sarvam.ai/api-reference-docs/getting-started/models/saarika)
- [SambaNova Whisper-Large-v3 Blog](https://sambanova.ai/blog/introducing-whisper-large-v3)
- [Artificial Analysis STT Leaderboard](https://artificialanalysis.ai/speech-to-text)

### TTS Sources
- [Inworld 2026 TTS Benchmarks](https://inworld.ai/resources/best-voice-ai-tts-apis-for-real-time-voice-agents-2026-benchmarks)
- [Cartesia Sonic 3 Docs](https://docs.cartesia.ai/build-with-cartesia/tts-models/latest)
- [ElevenLabs Models Documentation](https://elevenlabs.io/docs/overview/models)
- [Deepgram Aura-2 Introduction](https://deepgram.com/learn/introducing-aura-2-enterprise-text-to-speech)
- [OpenAI TTS Documentation](https://developers.openai.com/api/docs/models/gpt-4o-mini-tts)
- [Hume AI Octave 2 Launch](https://www.hume.ai/blog/octave-2-launch)
- [Rime Arcana Introduction](https://rime.ai/resources/introducing-arcana/)
- [MiniMax on Artificial Analysis](https://artificialanalysis.ai/text-to-speech/model-families/minimax-hailou)
- [Fish Audio S2 Pro](https://openaudios1.com/)
- [Camb AI MARS8 Technical Report](https://www.camb.ai/blog-post/mars8-technical-report)
- [Inworld TTS-1.5 Announcement](https://inworld.ai/blog/introducing-inworld-tts-1-5)
- [Neuphonic TTS](https://www.neuphonic.com/text-to-speech)
- [Google Chirp 3 HD Docs](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd)
- [Azure Dragon HD Announcement](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/)
- [AWS Polly Generative Expansion](https://aws.amazon.com/about-aws/whats-new/2026/03/amazon-polly-expands-TTS-new-voices-and-bidirectional-streaming/)
- [NVIDIA Riva Magpie TTS](https://build.nvidia.com/nvidia/magpie-tts-multilingual/modelcard)
- [Artificial Analysis ElevenLabs](https://artificialanalysis.ai/text-to-speech/model-families/elevenlabs)
- [Resemble AI Chatterbox (GitHub)](https://github.com/resemble-ai/chatterbox)
