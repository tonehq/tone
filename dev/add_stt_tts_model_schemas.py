"""
Add per-model meta_data_schema to dev-data.json for STT and TTS providers.

Run: python dev/add_stt_tts_model_schemas.py
"""

import json
import copy
import os

# ── Schema field templates ──────────────────────────────────────────────────

F = {
    # ── STT common fields ───────────────────────────────────────────────
    "language": {
        "name": "language", "data_type": "string", "type": "select",
        "format": "string", "validator": None, "required": 0,
        "description": "Language for transcription",
    },
    "language_code": {
        "name": "language_code", "data_type": "string", "type": "select",
        "format": "string", "validator": None, "required": 0,
        "description": "Language code for transcription",
    },
    "languages": {
        "name": "languages", "data_type": "string", "type": "select",
        "format": "string", "validator": None, "required": 0,
        "description": "Language(s) for transcription",
    },
    "prompt": {
        "name": "prompt", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Optional prompt to guide transcription",
    },
    "temperature": {
        "name": "temperature", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.0, "max": 1.0}, "required": 0,
        "description": "Controls randomness. Range: 0.0 to 1.0",
    },
    "sample_rate": {
        "name": "sample_rate", "data_type": "integer", "type": "input number",
        "format": "integer", "validator": {"min": 8000}, "required": 0,
        "description": "Audio sample rate in Hz",
    },

    # ── Deepgram STT ────────────────────────────────────────────────────
    "punctuate": {
        "name": "punctuate", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Add punctuation to transcripts",
    },
    "smart_format": {
        "name": "smart_format", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Apply smart formatting (dates, numbers, etc.)",
    },
    "profanity_filter": {
        "name": "profanity_filter", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Filter profanity from transcript",
    },
    "diarize": {
        "name": "diarize", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Enable speaker diarization",
    },
    "filler_words": {
        "name": "filler_words", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Include filler words (um, uh) in transcript",
    },
    "keywords": {
        "name": "keywords", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Comma-separated keywords to boost recognition",
    },
    "endpointing": {
        "name": "endpointing", "data_type": "integer", "type": "input number",
        "format": "integer", "validator": {"min": 10}, "required": 0,
        "description": "Endpointing duration in milliseconds",
    },
    "utterance_end_ms": {
        "name": "utterance_end_ms", "data_type": "integer", "type": "input number",
        "format": "integer", "validator": {"min": 0}, "required": 0,
        "description": "Silence duration to trigger utterance end (ms)",
    },
    "no_delay": {
        "name": "no_delay", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Minimize latency at cost of accuracy",
    },
    "dictation": {
        "name": "dictation", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Enable dictation mode",
    },
    "numerals": {
        "name": "numerals", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Convert numbers to digits",
    },
    "interim_results": {
        "name": "interim_results", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Enable interim (partial) results",
    },

    # ── Speechmatics STT ────────────────────────────────────────────────
    "turn_detection_mode": {
        "name": "turn_detection_mode", "data_type": "string", "type": "select",
        "format": "string", "validator": None, "required": 0,
        "description": "Turn detection mode", "options": ["adaptive", "off"],
    },
    "operating_point": {
        "name": "operating_point", "data_type": "string", "type": "select",
        "format": "string", "validator": None, "required": 0,
        "description": "Operating point", "options": ["standard", "enhanced"],
    },
    "max_delay": {
        "name": "max_delay", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.1, "max": 10.0}, "required": 0,
        "description": "Maximum delay for transcription (seconds)",
    },
    "end_of_utterance_silence_trigger": {
        "name": "end_of_utterance_silence_trigger", "data_type": "float",
        "type": "input number", "format": "float",
        "validator": {"min": 0.0}, "required": 0,
        "description": "Silence duration to trigger end of utterance (seconds)",
    },
    "end_of_utterance_max_delay": {
        "name": "end_of_utterance_max_delay", "data_type": "float",
        "type": "input number", "format": "float",
        "validator": {"min": 0.0}, "required": 0,
        "description": "Max delay for end of utterance detection (seconds)",
    },
    "domain": {
        "name": "domain", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Domain for transcription",
    },
    "enable_diarization": {
        "name": "enable_diarization", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Enable speaker diarization",
    },
    "speaker_sensitivity": {
        "name": "speaker_sensitivity", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.0, "max": 1.0}, "required": 0,
        "description": "Speaker sensitivity for diarization",
    },
    "max_speakers": {
        "name": "max_speakers", "data_type": "integer", "type": "input number",
        "format": "integer", "validator": {"min": 1}, "required": 0,
        "description": "Maximum number of speakers",
    },
    "prefer_current_speaker": {
        "name": "prefer_current_speaker", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Prefer current speaker in diarization",
    },
    "include_partials": {
        "name": "include_partials", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Include partial transcripts",
    },
    "split_sentences": {
        "name": "split_sentences", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Split transcript into sentences",
    },

    # ── AssemblyAI STT ──────────────────────────────────────────────────
    "speech_model": {
        "name": "speech_model", "data_type": "string", "type": "select",
        "format": "string", "validator": None, "required": 0,
        "description": "Speech model to use",
        "options": ["universal-streaming-english", "universal-streaming-multilingual"],
    },
    "word_finalization_max_wait_time": {
        "name": "word_finalization_max_wait_time", "data_type": "integer",
        "type": "input number", "format": "integer",
        "validator": {"min": 0}, "required": 0,
        "description": "Max wait time for word finalization (ms)",
    },
    "end_of_turn_confidence_threshold": {
        "name": "end_of_turn_confidence_threshold", "data_type": "float",
        "type": "input number", "format": "float",
        "validator": {"min": 0.0, "max": 1.0}, "required": 0,
        "description": "Confidence threshold for end-of-turn detection",
    },
    "keyterms_prompt": {
        "name": "keyterms_prompt", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Key terms to guide transcription (comma-separated)",
    },

    # ── Soniox STT ──────────────────────────────────────────────────────
    "language_hints": {
        "name": "language_hints", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Language hints for transcription",
    },
    "language_hints_strict": {
        "name": "language_hints_strict", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Strictly enforce language hints",
    },
    "enable_speaker_diarization": {
        "name": "enable_speaker_diarization", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Enable speaker diarization",
    },
    "enable_language_identification": {
        "name": "enable_language_identification", "data_type": "boolean",
        "type": "radio", "format": "boolean", "validator": None, "required": 0,
        "description": "Enable language identification",
    },

    # ── ElevenLabs STT ──────────────────────────────────────────────────
    "commit_strategy": {
        "name": "commit_strategy", "data_type": "string", "type": "select",
        "format": "string", "validator": None, "required": 0,
        "description": "Commit strategy for transcription",
    },
    "vad_silence_threshold_secs": {
        "name": "vad_silence_threshold_secs", "data_type": "float",
        "type": "input number", "format": "float",
        "validator": {"min": 0.0}, "required": 0,
        "description": "VAD silence threshold in seconds",
    },
    "vad_threshold": {
        "name": "vad_threshold", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.0, "max": 1.0}, "required": 0,
        "description": "VAD detection threshold",
    },
    "min_speech_duration_ms": {
        "name": "min_speech_duration_ms", "data_type": "integer",
        "type": "input number", "format": "integer",
        "validator": {"min": 0}, "required": 0,
        "description": "Minimum speech duration in ms",
    },
    "min_silence_duration_ms": {
        "name": "min_silence_duration_ms", "data_type": "integer",
        "type": "input number", "format": "integer",
        "validator": {"min": 0}, "required": 0,
        "description": "Minimum silence duration in ms",
    },
    "include_timestamps": {
        "name": "include_timestamps", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Include timestamps in transcript",
    },
    "enable_logging": {
        "name": "enable_logging", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Enable ElevenLabs logging",
    },
    "include_language_detection": {
        "name": "include_language_detection", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Include language detection",
    },

    # ── Cartesia STT ────────────────────────────────────────────────────
    # (language + sample_rate already defined above)

    # ── Gladia STT ──────────────────────────────────────────────────────
    "region": {
        "name": "region", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Region for the service",
    },
    "enable_vad": {
        "name": "enable_vad", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Enable voice activity detection",
    },
    "maximum_duration_without_endpointing": {
        "name": "maximum_duration_without_endpointing", "data_type": "integer",
        "type": "input number", "format": "integer",
        "validator": {"min": 0}, "required": 0,
        "description": "Max duration without endpointing (ms)",
    },

    # ── Google STT ──────────────────────────────────────────────────────
    "enable_automatic_punctuation": {
        "name": "enable_automatic_punctuation", "data_type": "boolean",
        "type": "radio", "format": "boolean", "validator": None, "required": 0,
        "description": "Add punctuation to transcripts automatically",
    },
    "enable_spoken_punctuation": {
        "name": "enable_spoken_punctuation", "data_type": "boolean",
        "type": "radio", "format": "boolean", "validator": None, "required": 0,
        "description": "Include spoken punctuation in transcript",
    },
    "enable_spoken_emojis": {
        "name": "enable_spoken_emojis", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Include spoken emojis in transcript",
    },
    "enable_word_time_offsets": {
        "name": "enable_word_time_offsets", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Include timing information for each word",
    },
    "enable_word_confidence": {
        "name": "enable_word_confidence", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Include confidence scores for each word",
    },
    "enable_interim_results": {
        "name": "enable_interim_results", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Stream partial recognition results",
    },
    "enable_voice_activity_events": {
        "name": "enable_voice_activity_events", "data_type": "boolean",
        "type": "radio", "format": "boolean", "validator": None, "required": 0,
        "description": "Detect voice activity in audio",
    },
    "use_separate_recognition_per_channel": {
        "name": "use_separate_recognition_per_channel", "data_type": "boolean",
        "type": "radio", "format": "boolean", "validator": None, "required": 0,
        "description": "Process each audio channel separately",
    },

    # ── Azure STT ───────────────────────────────────────────────────────
    "endpoint_id": {
        "name": "endpoint_id", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Custom Speech endpoint ID",
    },

    # ── Sarvam STT ──────────────────────────────────────────────────────
    "vad_signals": {
        "name": "vad_signals", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Enable VAD signals",
    },
    "high_vad_sensitivity": {
        "name": "high_vad_sensitivity", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Enable high VAD sensitivity",
    },

    # ── Nvidia STT ──────────────────────────────────────────────────────
    # (just language)

    # ═════════════════════════════════════════════════════════════════════
    # TTS fields
    # ═════════════════════════════════════════════════════════════════════

    "speed": {
        "name": "speed", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.25, "max": 4.0}, "required": 0,
        "description": "Speech speed multiplier",
    },
    "speed_0_7_1_2": {
        "name": "speed", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.7, "max": 1.2}, "required": 0,
        "description": "Speech speed. Range: 0.7 to 1.2",
    },
    "speed_0_5_2": {
        "name": "speed", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.5, "max": 2.0}, "required": 0,
        "description": "Speech speed. Range: 0.5 to 2.0",
    },
    "instructions": {
        "name": "instructions", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Natural language instructions to control voice style, accent, emotion",
    },

    # ── ElevenLabs TTS ──────────────────────────────────────────────────
    "stability": {
        "name": "stability", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.0, "max": 1.0}, "required": 0,
        "description": "Voice stability control. Range: 0.0 to 1.0",
    },
    "similarity_boost": {
        "name": "similarity_boost", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.0, "max": 1.0}, "required": 0,
        "description": "Similarity boost control. Range: 0.0 to 1.0",
    },
    "style": {
        "name": "style", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.0, "max": 1.0}, "required": 0,
        "description": "Style control for voice expression. Range: 0.0 to 1.0",
    },
    "use_speaker_boost": {
        "name": "use_speaker_boost", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Enable speaker boost enhancement",
    },
    "auto_mode": {
        "name": "auto_mode", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Enable automatic mode optimization",
    },
    "enable_ssml_parsing": {
        "name": "enable_ssml_parsing", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Parse SSML tags in text",
    },

    # ── Cartesia TTS ────────────────────────────────────────────────────
    "emotion": {
        "name": "emotion", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Emotion control for voice",
    },

    # ── MiniMax TTS ─────────────────────────────────────────────────────
    "volume": {
        "name": "volume", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0, "max": 10}, "required": 0,
        "description": "Volume level",
    },
    "pitch": {
        "name": "pitch", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Voice pitch adjustment",
    },

    # ── Rime TTS ────────────────────────────────────────────────────────
    "speed_alpha": {
        "name": "speed_alpha", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.5, "max": 2.0}, "required": 0,
        "description": "Speed alpha control. Range: 0.5 to 2.0",
    },
    "reduce_latency": {
        "name": "reduce_latency", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Reduce latency at cost of quality",
    },
    "pause_between_brackets": {
        "name": "pause_between_brackets", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Add pauses between bracketed text",
    },
    "phonemize_between_brackets": {
        "name": "phonemize_between_brackets", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Phonemize text between brackets",
    },

    # ── Sarvam TTS ──────────────────────────────────────────────────────
    "sarvam_pitch": {
        "name": "pitch", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": -0.75, "max": 0.75}, "required": 0,
        "description": "Voice pitch. Range: -0.75 to 0.75",
    },
    "pace_v2": {
        "name": "pace", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.3, "max": 3.0}, "required": 0,
        "description": "Speech pace. Range: 0.3 to 3.0",
    },
    "pace_v3": {
        "name": "pace", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.5, "max": 2.0}, "required": 0,
        "description": "Speech pace. Range: 0.5 to 2.0",
    },
    "loudness": {
        "name": "loudness", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.3, "max": 3.0}, "required": 0,
        "description": "Loudness. Range: 0.3 to 3.0",
    },
    "enable_preprocessing": {
        "name": "enable_preprocessing", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Enable text preprocessing",
    },
    "sarvam_temperature": {
        "name": "temperature", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.01, "max": 1.0}, "required": 0,
        "description": "Temperature. Range: 0.01 to 1.0",
    },

    # ── Fish TTS ────────────────────────────────────────────────────────
    "latency": {
        "name": "latency", "data_type": "string", "type": "select",
        "format": "string", "validator": None, "required": 0,
        "description": "Latency mode", "options": ["normal", "balanced"],
    },
    "normalize": {
        "name": "normalize", "data_type": "boolean", "type": "radio",
        "format": "boolean", "validator": None, "required": 0,
        "description": "Normalize audio output",
    },
    "prosody_speed": {
        "name": "prosody_speed", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.5, "max": 2.0}, "required": 0,
        "description": "Prosody speed. Range: 0.5 to 2.0",
    },
    "prosody_volume": {
        "name": "prosody_volume", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.0, "max": 2.0}, "required": 0,
        "description": "Prosody volume. Range: 0.0 to 2.0",
    },

    # ── Inworld TTS ─────────────────────────────────────────────────────
    "speaking_rate": {
        "name": "speaking_rate", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.25, "max": 4.0}, "required": 0,
        "description": "Speaking rate. Range: 0.25 to 4.0",
    },

    # ── Hume TTS ────────────────────────────────────────────────────────
    "description": {
        "name": "description", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Acting instructions to control voice emotion and style",
    },
    "trailing_silence": {
        "name": "trailing_silence", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.0, "max": 5.0}, "required": 0,
        "description": "Trailing silence duration in seconds",
    },

    # ── Nvidia TTS ──────────────────────────────────────────────────────
    "quality": {
        "name": "quality", "data_type": "integer", "type": "input number",
        "format": "integer", "validator": {"min": 1, "max": 40}, "required": 0,
        "description": "Audio quality level",
    },

    # ── Camb TTS ────────────────────────────────────────────────────────
    "user_instructions": {
        "name": "user_instructions", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Instructions to control voice style",
    },

    # ── AWS Polly TTS ───────────────────────────────────────────────────
    "engine": {
        "name": "engine", "data_type": "string", "type": "select",
        "format": "string", "validator": None, "required": 0,
        "description": "TTS engine type",
        "options": ["standard", "neural", "long-form", "generative"],
    },
    "polly_pitch": {
        "name": "pitch", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Voice pitch adjustment (e.g., +10%, -5Hz, high). Standard engine only.",
    },
    "rate": {
        "name": "rate", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Speech rate (e.g., slow, fast, 125%)",
    },
    "polly_volume": {
        "name": "volume", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Volume level (e.g., loud, soft, +6dB)",
    },

    # ── Google TTS ──────────────────────────────────────────────────────
    "location": {
        "name": "location", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Google Cloud location",
    },
    "google_speaking_rate": {
        "name": "speaking_rate", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.25, "max": 2.0}, "required": 0,
        "description": "Speaking rate. Range: 0.25 to 2.0",
    },

    # ── Azure TTS ───────────────────────────────────────────────────────
    "emphasis": {
        "name": "emphasis", "data_type": "string", "type": "select",
        "format": "string", "validator": None, "required": 0,
        "description": "Emphasis level", "options": ["strong", "moderate", "reduced"],
    },
    "azure_pitch": {
        "name": "pitch", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Voice pitch adjustment (e.g., +10%, high)",
    },
    "azure_rate": {
        "name": "rate", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Speech rate (e.g., 1.0, slow, fast)",
    },
    "role": {
        "name": "role", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Voice role (e.g., YoungAdultFemale)",
    },
    "azure_style": {
        "name": "style", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Speaking style (e.g., cheerful, sad, excited)",
    },
    "style_degree": {
        "name": "style_degree", "data_type": "float", "type": "input number",
        "format": "float", "validator": {"min": 0.01, "max": 2.0}, "required": 0,
        "description": "Intensity of speaking style. Range: 0.01 to 2.0",
    },
    "azure_volume": {
        "name": "volume", "data_type": "string", "type": "input text",
        "format": "string", "validator": None, "required": 0,
        "description": "Volume level (e.g., +20%, loud, x-soft)",
    },

    # ── Neuphonic TTS ───────────────────────────────────────────────────
    # (just speed)

    # ── Speechmatics TTS ────────────────────────────────────────────────
    # (no params)
}


def make_schema(field_keys):
    """Build a meta_data_schema array from field key list."""
    return [copy.deepcopy(F[k]) for k in field_keys]


# ── STT model classifiers ───────────────────────────────────────────────────

DEEPGRAM_COMMON = ["language", "punctuate", "smart_format", "profanity_filter",
                   "diarize", "filler_words", "endpointing", "utterance_end_ms",
                   "no_delay", "dictation", "numerals", "interim_results"]

STT_MODEL_SCHEMAS = {}


def classify_stt(provider_name, model_name):
    """Return field keys for an STT model."""

    if provider_name == "deepgram":
        if model_name.startswith("nova-3"):
            return DEEPGRAM_COMMON  # nova-3 doesn't support keywords (uses keyterm, not in builder)
        else:
            return DEEPGRAM_COMMON + ["keywords"]  # nova-2 supports keywords

    if provider_name == "openai":
        return ["language", "prompt", "temperature"]

    if provider_name == "groq":
        return ["language", "prompt", "temperature"]

    if provider_name == "sarvam":
        return ["prompt", "vad_signals", "high_vad_sensitivity"]

    if provider_name == "assemblyai":
        if "3-Pro" in model_name or "3-pro" in model_name:
            return ["language", "speech_model", "word_finalization_max_wait_time",
                    "end_of_turn_confidence_threshold", "keyterms_prompt"]
        else:
            return ["language", "speech_model", "word_finalization_max_wait_time",
                    "end_of_turn_confidence_threshold"]

    if provider_name == "cartesia":
        return ["language", "sample_rate"]

    if provider_name == "soniox":
        return ["language_hints", "language_hints_strict",
                "enable_speaker_diarization", "enable_language_identification"]

    if provider_name == "elevenlabs":
        return ["language_code", "commit_strategy", "vad_silence_threshold_secs",
                "vad_threshold", "min_speech_duration_ms", "min_silence_duration_ms",
                "include_timestamps", "enable_logging", "include_language_detection"]

    if provider_name == "gladia":
        return ["region", "sample_rate", "endpointing",
                "maximum_duration_without_endpointing", "enable_vad"]

    if provider_name == "nvidia":
        return ["language"]

    if provider_name == "speechmatics":
        return ["language", "turn_detection_mode", "operating_point", "max_delay",
                "end_of_utterance_silence_trigger", "end_of_utterance_max_delay",
                "domain", "enable_diarization", "speaker_sensitivity", "max_speakers",
                "prefer_current_speaker", "include_partials", "split_sentences",
                "sample_rate"]

    if provider_name == "google":
        return ["languages", "enable_automatic_punctuation", "enable_spoken_punctuation",
                "enable_spoken_emojis", "profanity_filter", "enable_word_time_offsets",
                "enable_word_confidence", "enable_interim_results",
                "enable_voice_activity_events", "use_separate_recognition_per_channel"]

    if provider_name == "azure":
        return ["region", "language", "sample_rate", "endpoint_id"]

    if provider_name == "hathora":
        return ["language"]

    if provider_name == "sambanova":
        return ["language", "prompt", "temperature"]

    return []


# ── TTS model classifiers ───────────────────────────────────────────────────

def classify_tts(provider_name, model_name):
    """Return field keys for a TTS model."""

    if provider_name == "openai":
        if "gpt-4o" in model_name:
            return ["instructions", "speed"]
        else:
            return ["speed"]

    if provider_name == "elevenlabs":
        if model_name == "eleven_v3":
            return ["stability", "similarity_boost", "style", "speed_0_7_1_2",
                    "auto_mode", "enable_ssml_parsing"]
        else:
            return ["stability", "similarity_boost", "style", "use_speaker_boost",
                    "speed_0_7_1_2", "auto_mode", "enable_ssml_parsing"]

    if provider_name == "cartesia":
        if model_name == "sonic-3":
            return ["speed", "emotion"]
        else:
            return ["speed"]

    if provider_name == "deepgram":
        return []  # no configurable params

    if provider_name == "groq":
        return ["speed"]

    if provider_name == "minimax":
        return ["speed", "volume", "pitch", "emotion"]

    if provider_name == "rime":
        return ["speed_alpha", "reduce_latency", "pause_between_brackets",
                "phonemize_between_brackets"]

    if provider_name == "sarvam":
        if "v2" in model_name:
            return ["sarvam_pitch", "pace_v2", "loudness", "enable_preprocessing"]
        else:
            return ["pace_v3", "sarvam_temperature", "enable_preprocessing"]

    if provider_name == "fish":
        return ["latency", "normalize", "prosody_speed", "prosody_volume"]

    if provider_name == "inworld":
        return ["sarvam_temperature", "speaking_rate"]

    if provider_name == "resemble":
        return []  # no configurable params

    if provider_name == "nvidia":
        return ["quality"]

    if provider_name == "neuphonic":
        return ["speed"]

    if provider_name == "lmnt":
        return []  # no configurable params

    if provider_name == "hume":
        return ["description", "speed_0_5_2", "trailing_silence"]

    if provider_name == "camb":
        return ["user_instructions"]

    if provider_name == "asyncai_http":
        return []  # no configurable params

    if provider_name == "aws_polly":
        if model_name == "standard":
            return ["region", "engine", "polly_pitch", "rate", "polly_volume"]
        else:
            return ["region", "engine", "rate", "polly_volume"]

    if provider_name == "google":
        return ["location", "google_speaking_rate"]

    if provider_name == "azure":
        if "DragonHD" in model_name or "Dragon" in model_name:
            return ["region", "azure_rate", "azure_volume", "azure_style"]
        elif "Neural" in model_name and "Custom" not in model_name and "Embedded" not in model_name:
            return ["region", "emphasis", "azure_pitch", "azure_rate", "role",
                    "azure_style", "style_degree", "azure_volume"]
        else:
            return ["region", "azure_rate", "azure_volume"]

    if provider_name == "speechmatics":
        return []  # no configurable params

    if provider_name == "playht":
        return ["speed"]

    if provider_name == "hathora":
        return ["speed"]

    return []


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "dev-data.json")

    with open(json_path, "r") as f:
        data = json.load(f)

    modified = 0

    for provider in data.get("stt_providers", []):
        provider_name = provider["name"]
        for model in provider.get("models", []):
            field_keys = classify_stt(provider_name, model["name"])
            model["meta_data_schema"] = make_schema(field_keys)
            modified += 1

    for provider in data.get("tts_providers", []):
        provider_name = provider["name"]
        for model in provider.get("models", []):
            field_keys = classify_tts(provider_name, model["name"])
            model["meta_data_schema"] = make_schema(field_keys)
            modified += 1

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Done. Added meta_data_schema to {modified} STT/TTS models.")


if __name__ == "__main__":
    main()
