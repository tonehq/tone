"""Generate an Excel file of 50 LLM/STT/TTS combinations for call-log benchmarking.

Provider/model names and IDs below were verified against the running Neon DB
(`service_providers` + `models` tables) on 2026-04-09.

Columns:
  llm_service_provider_id, llm_service_provider_name, llm_model_id, llm_model_name,
  stt_service_provider_id, stt_service_provider_name, stt_model_id, stt_model_name,
  tts_service_provider_id, tts_service_provider_name, tts_model_id, tts_model_name,
  call_log_id, metrics, transcription, to_number
"""
import random
from pathlib import Path

from openpyxl import Workbook

# --- Provider/model catalog (verified against DB) --------------------------
# Each tuple: (provider_id, provider_name, model_id, model_name)

LLMS = [
    (58, "openai",    548, "gpt-4o-mini"),
    (59, "groq",      559, "llama-3.3-70b-versatile"),
    (60, "anthropic", 564, "claude-opus-4-6"),
    (72, "fireworks", 847, "accounts/fireworks/models/llama-v3p3-70b-instruct"),
]

# NOTE: sarvam STT (saarika:v2.5) removed — factory requires `language` metadata.
# speechmatics STT removed — factory ignores model name.
# elevenlabs uses scribe_v2_realtime because the factory forces that variant.
STT = [
    (77, "deepgram",   936, "nova-3"),
    (78, "openai",     952, "gpt-4o-transcribe"),
    (79, "groq",       954, "whisper-large-v3-turbo"),
    (82, "cartesia",   960, "ink-whisper"),
    (84, "elevenlabs", 967, "scribe_v2_realtime"),
    (85, "gladia",     968, "solaria-1"),
]

TTS = [
    (92,  "cartesia",  1008, "sonic-2"),
    (96,  "hathora",   1017, "hexgrad-kokoro-82m"),
    # minimax removed — requires group_id in model_meta which agents won't have.
    (98,  "rime",      1027, "mistv2"),
    (99,  "sarvam",    1030, "bulbul:v2"),
    (101, "inworld",   1034, "inworld-tts-1.5-max"),
    (102, "openai",    1038, "gpt-4o-mini-tts"),
    (105, "neuphonic", 1048, "neu_hq"),
    (106, "lmnt",      1049, "Blizzard"),
    (109, "camb",      1056, "MARS-Flash"),
    # speechmatics TTS removed — factory ignores model name.
]

HEADERS = [
    "llm_service_provider_id", "llm_service_provider_name", "llm_model_id", "llm_model_name",
    "stt_service_provider_id", "stt_service_provider_name", "stt_model_id", "stt_model_name",
    "tts_service_provider_id", "tts_service_provider_name", "tts_model_id", "tts_model_name",
    "call_log_id", "status", "metrics", "transcription", "to_number",
]

TOTAL = 50


def build_combinations():
    """Build 50 combos that cover every provider at least once, then random fill."""
    rng = random.Random(42)
    combos = []

    max_len = max(len(LLMS), len(TTS), len(STT))
    for i in range(max_len):
        combos.append((
            LLMS[i % len(LLMS)],
            STT[i % len(STT)],
            TTS[i % len(TTS)],
        ))

    seen = {(l[0], s[0], t[0]) for l, s, t in combos}
    while len(combos) < TOTAL:
        pick = (rng.choice(LLMS), rng.choice(STT), rng.choice(TTS))
        key = (pick[0][0], pick[1][0], pick[2][0])
        if key in seen:
            continue
        seen.add(key)
        combos.append(pick)

    return combos[:TOTAL]


def main():
    wb = Workbook()
    ws = wb.active
    ws.title = "combinations"
    ws.append(HEADERS)

    for llm, stt, tts in build_combinations():
        ws.append([
            llm[0], llm[1], llm[2], llm[3],
            stt[0], stt[1], stt[2], stt[3],
            tts[0], tts[1], tts[2], tts[3],
            "", "", "", "", "",
        ])

    widths = [12, 22, 10, 55, 12, 22, 10, 26, 12, 22, 10, 24, 14, 12, 14, 14, 16]
    for idx, w in enumerate(widths, start=1):
        col = ws.cell(row=1, column=idx).column_letter
        ws.column_dimensions[col].width = w

    out = Path(__file__).resolve().parent.parent / "docs" / "call_combinations.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
