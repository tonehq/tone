"""Check which LLM/STT/TTS providers are importable on the current environment."""
imports = {
    "LLM openai": "from pipecat.services.openai.llm import OpenAILLMService",
    "LLM groq": "from pipecat.services.groq.llm import GroqLLMService",
    "LLM anthropic": "from pipecat.services.anthropic import AnthropicLLMService",
    "LLM fireworks": "from pipecat.services.fireworks import FireworksLLMService",
    "STT deepgram": "from pipecat.services.deepgram.stt import DeepgramSTTService",
    "STT openai": "from pipecat.services.openai.stt import OpenAISTTService",
    "STT groq": "from pipecat.services.groq.stt import GroqSTTService",
    "STT cartesia": "from pipecat.services.cartesia.stt import CartesiaSTTService",
    "STT elevenlabs": "from pipecat.services.elevenlabs.stt import ElevenLabsSTTService",
    "STT gladia": "from pipecat.services.gladia.stt import GladiaSTTService",
    "TTS cartesia": "from pipecat.services.cartesia.tts import CartesiaTTSService",
    "TTS hathora": "from pipecat.services.hathora.tts import HathoraTTSService",
    "TTS rime": "from pipecat.services.rime.tts import RimeHttpTTSService",
    "TTS sarvam": "from pipecat.services.sarvam.tts import SarvamHttpTTSService",
    "TTS inworld": "from pipecat.services.inworld.tts import InworldTTSService",
    "TTS openai": "from pipecat.services.openai.tts import OpenAITTSService",
    "TTS neuphonic": "from pipecat.services.neuphonic.tts import NeuphonicHttpTTSService",
    "TTS lmnt": "from pipecat.services.lmnt.tts import LMNTTTSService",
    "TTS camb": "from pipecat.services.camb.tts import CambTTSService",
}

for name, stmt in imports.items():
    try:
        exec(stmt)
        print(f"{name}: OK")
    except Exception as e:
        print(f"{name}: FAIL - {e}")
