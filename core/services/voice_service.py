import sys
from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()

# When run as script (e.g. python3 core/services/voice_service.py), project root is not on path.
_project_root = Path(__file__).resolve().parents[2]
if _project_root not in sys.path:
    sys.path.insert(0, str(_project_root))

from typing import AsyncGenerator

from sqlalchemy.orm import Session
import boto3
import requests

from pipecat.frames.frames import Frame
from pipecat.services.tts_service import TTSService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.openai.tts import OpenAITTSService

def main():
    service = ElevenLabsTTSService(api_key=os.getenv("ELEVENLABS_API_KEY"))
    voices = service.get_voices()
    print(voices)
    
    service = OpenAITTSService(api_key=os.getenv("OPENAI_API_KEY"))
    voices = service.get_voices()
    print(voices)


if __name__ == "__main__":
    main()
    


