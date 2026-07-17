# Readiness probe assets

## `probe_sample.wav` — bundled STT audio

The STT deep probe (`core/services/readiness/probes.py:probe_stt`) feeds this
file into the pipecat STT service and asserts a non-empty transcript is
returned. It's the same signal a real call generates, minus a live caller —
which is the whole point of a readiness check.

### Required format

| Property     | Value                             |
| ------------ | --------------------------------- |
| Container    | WAV (RIFF)                        |
| Encoding     | PCM 16-bit signed little-endian   |
| Channels     | Mono (1)                          |
| Sample rate  | 16000 Hz                          |
| Duration     | 5–8 seconds                       |
| Content      | Clear English speech, no music, no background noise |
| Size         | ≈160–256 KB (no LFS required)     |

Suggested phrase: **`"The quick brown fox jumps over the lazy dog."`** — a
Harvard-standard sentence, phonetically diverse, safe across every STT
provider we integrate with.

### Sourcing the file

Any of these works — the STT probe only cares about the encoding constraints
above, not who spoke the words:

```bash
# macOS — record yourself in QuickTime, export mono @ 16kHz, or:
say -o /tmp/probe.aiff "The quick brown fox jumps over the lazy dog."
afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/probe.aiff probe_sample.wav

# Linux — espeak + sox
espeak "The quick brown fox jumps over the lazy dog." -w /tmp/probe.wav
sox /tmp/probe.wav -r 16000 -c 1 -b 16 probe_sample.wav

# Or grab any CC0 clip and re-encode with ffmpeg:
ffmpeg -i input.mp3 -ar 16000 -ac 1 -c:a pcm_s16le probe_sample.wav
```

Drop the resulting `probe_sample.wav` next to this README. The probe will pick
it up automatically on the next deep readiness call — no code changes needed.

### Fallback behavior

If the file is missing, the STT probe falls back to a 0.5s PCM16 silence
buffer and reports:

> `"<provider> STT accepted the request (bundled probe WAV missing — silence-only probe)."`

That still verifies the pipecat client constructs, auth passes, and the WS/HTTP
session opens — but does **not** exercise the transcription model itself. Ship
the WAV to enable the stronger check.
