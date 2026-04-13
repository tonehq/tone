# Working Service Providers

> **Last updated:** 2026-04-06
> **Source:** test_llm_models.py, test_stt_models.py, TTS_Provider_Voice_Model_Language_Matrix.md

---

## LLM Providers

| ID | Name | Display Name | Status |
|----|------|-------------|--------|
| 1 | openai | OpenAI | Working |
| 2 | groq | Groq | Working |
| 3 | anthropic | Anthropic | Working |
| 6 | cerebras | Cerebras | Working |
| 15 | fireworks | Fireworks AI | Working |

## STT Providers

| ID | Name | Display Name | Status |
|----|------|-------------|--------|
| 18 | deepgram | Deepgram | Working |
| 19 | openai | OpenAI | Working |
| 20 | groq | Groq | Working |
| 21 | sarvam | Sarvam | Working |
| 23 | cartesia | Cartesia | Working |
| 24 | soniox | Soniox | Working |
| 25 | elevenlabs | ElevenLabs | Working |
| 26 | gladia | Gladia | Working |
| 29 | nvidia | NVIDIA | Working |
| 30 | speechmatics | Speechmatics | Working |

## TTS Providers

| ID | Name | Display Name | Status |
|----|------|-------------|--------|
| 33 | cartesia | Cartesia | Working |
| 35 | deepgram | Deepgram | Needs testing |
| 36 | groq | Groq | Working |
| 38 | minimax | MiniMax | Working |
| 39 | rime | Rime | Working |
| 40 | sarvam | Sarvam | Working |
| 42 | inworld | Inworld | Working |
| 43 | openai | OpenAI | Working |
| 46 | neuphonic | Neuphonic | Working |
| 47 | lmnt | LMNT | Working |
| 48 | hume | Hume AI | Working |
| 49 | elevenlabs | ElevenLabs | Working |
| 50 | camb | Camb AI | Working |
| 51 | asyncai_http | Async AI | Working |
| 55 | speechmatics | Speechmatics | Working |

## Not Working / Issues

| ID | Name | Type | Issue |
|----|------|------|-------|
| 5 | openrouter | LLM | Needs credits |
| 8 | deepseek | LLM | Needs credits |
| 11 | grok | LLM | Permission issue |
| 14 | nvidia_nim | LLM | Issues |
| 22 | assemblyai | STT | Issues |
| 27 | hathora | STT | API endpoint 404 |
| 28 | sambanova | STT | No API key |
| 31 | google | STT | No API key |
| 32 | azure | STT | No API key |
| 34 | playht | TTS | Not configured |
| 37 | hathora | TTS | Not configured |
| 41 | fish | TTS | Not configured |
| 44 | resemble | TTS | Not configured |
| 45 | nvidia | TTS | Not configured |
| 52 | aws_polly | TTS | Not configured |
| 53 | google_base | TTS | Not configured |
| 54 | azure | TTS | Not configured |







After final testing by me, working LLM, STT and TTS
LLM:
Openai
Groq (llama-3.3-70b-versatile)
Anthropic(claude-opus-4-6)
Fireworks AI (accounts/fireworks/models/llama-v3p3-70b-instruct)
 
TTS:
Cartesia
Hathora
Minimax
Rime
Sarvam
Inworld
OpenAI
Neuphonic
LMNT
Camb AI
Speechmatics
 
STT:
Deepgram
OpenAI
Groq
Sarvam ( check language alone)
Cartesia
Elevenlabs
Gladia
Speechmatics