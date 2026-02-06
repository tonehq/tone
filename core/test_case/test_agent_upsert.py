"""
Individual test cases for creating agents with specific LLM, STT, TTS combinations.

Each test case creates one agent with:
- One specific LLM provider
- One specific STT provider  
- One specific TTS provider

Usage:
    python test_agent_combinations.py
"""

"""
Things done:
The database entries for LLM, STT, TTS are updated based on the classes available in the code. There is some doubts need to be checked in this.
If the llm, stt,tts are there, their id would be added in test cases else 0 will be added.
According to the classes available in agent_factory_service.py, the test cases are created.
"""

# To fix the import error for pipecat
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


import asyncio
from core.database.session import SessionLocal
from core.services.agent_service import AgentService
from core.services.agent_factory_service import AgentFactoryService
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
    FastAPIWebsocketClient
)
from fastapi import WebSocket
from starlette.websockets import WebSocketState

#small webrtc
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport, SmallWebRTCClient, SmallWebRTCConnection
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.base_transport import TransportParams


class MockSmallWebRTCConnection(SmallWebRTCConnection):
    async def connect(self):
        print("Mock connect called")

    async def disconnect(self):
        print("Mock disconnect called")

    def is_connected(self):
        return True

    def audio_input_track(self):
        return None  # or mock audio track

    def video_input_track(self):
        return None  # or mock video track

    def screen_video_input_track(self):
        return None


class FakeWebSocket(WebSocket):
    """Fake WebSocket to use for testing with FastAPIWebsocketTransport."""

    def __init__(self):
        self.client_state = WebSocketState.CONNECTED
        self._messages = asyncio.Queue()

    async def receive(self):
        """Simulate receiving a message."""
        return await self._messages.get()

    async def send_text(self, data):
        print("Sent text:", data)

    async def send_bytes(self, data):
        print("Sent bytes:", data)

    async def close(self, code=1000):
        self.client_state = WebSocketState.DISCONNECTED
        print("WebSocket closed")

    async def add_message(self, message):
        """Queue a message to be received."""
        await self._messages.put(message)



async def create_factory_service_for_smallwebrtc(db, agent):
    try:
        agent_factory = AgentFactoryService(db)
        messages = ["Hello agent!", "How are you?", "End of conversation"]

        params = TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        video_in_enabled=True,
        video_out_enabled=True,
        audio_in_channels=1,
        audio_in_sample_rate=16000,
        audio_out_sample_rate=16000,
        video_out_width=640,
        video_out_height=480,
    )

        mock_connection = MockSmallWebRTCConnection()
        transport = SmallWebRTCTransport(mock_connection, params)

        await agent_factory.run_bot_for_agent(agent=agent["id"], transport=transport, runner_args={})

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def create_factory_service_for_websocket(db, agent):
    try:
        agent_factory = AgentFactoryService(db)
        ws = FakeWebSocket()

        params = FastAPIWebsocketParams(
        add_wav_header=False,
        session_timeout=None,
        )

        client = FastAPIWebsocketClient(ws, callbacks=None)  
        transport = FastAPIWebsocketTransport(websocket=ws, params=params)

        runner_args_data = {
            "websocket": "mock_websocket",
            "body": {"agent_id": agent["id"]}
        }

        runner_args = runner_args_data

        await agent_factory.run_bot_for_agent(agent["id"], transport, runner_args)
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()





async def create_test_agent(db, name: str, llm_service_id: int, stt_service_id: int, tts_service_id: int, created_by: int = 1, transport_type: str = "smallwebrtc"):
    """Helper to create an agent with specific LLM, STT, TTS."""
    agent_data = {
        "name": name,
        "description": name,
        "system_prompt": "You are a helpful assistant.",
        "first_message": "Hello! How can I help you today?",
        "llm_service_id": llm_service_id,
        "stt_service_id": stt_service_id,
        "tts_service_id": tts_service_id,
        "agent_type": "inbound",
    }
    service = AgentService(db)
    agent = service.upsert_agent(agent_data, created_by=created_by)

    if transport_type == "smallwebrtc":
        print("into transport_type smallwebrtc")
        await create_factory_service_for_smallwebrtc(db, agent)
    elif transport_type == "websocket":
        print("into transport_type websocket")
        await create_factory_service_for_websocket(db, agent)



# ============================================================
# TEST CASE 1: OpenAI LLM + Deepgram STT + Cartesia TTS
# ============================================================
async def test_case_1():
    """OpenAI LLM + Deepgram STT + Cartesia TTS"""
    print("\n" + "="*60)
    print("TEST CASE 1: OpenAI LLM + Deepgram STT + Cartesia TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = await create_test_agent(
            db=db,
            name="Test Agent 18",
            llm_service_id=1,  # OpenAI
            stt_service_id=35,  # Deepgram
            tts_service_id=5,  # Cartesia
            transport_type="websocket"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ============================================================
# TEST CASE 2: Anthropic LLM + Deepgram STT + ElevenLabs TTS
# ============================================================
async def test_case_2():
    """Anthropic LLM + Deepgram STT + ElevenLabs TTS"""
    print("\n" + "="*60)
    print("TEST CASE 2: Anthropic LLM + Deepgram STT + ElevenLabs TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent Anthropic-Deepgram-ElevenLabs",
            llm_service_id=11,  # Anthropic
            stt_service_id=35,  # Deepgram
            tts_service_id=49,  # ElevenLabs
            transport_type="websocket"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ============================================================
# TEST CASE 3: Groq LLM + OpenAI STT + OpenAI TTS
# ============================================================
async def test_case_3():
    """Groq LLM + groq + OpenAI TTS"""
    print("\n" + "="*60)
    print("TEST CASE 3: Groq LLM + groq + OpenAI TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent Groq - groq - OpenAI",
            llm_service_id=14,  # Groq
            stt_service_id=48,  # groq
            tts_service_id=27,  # OpenAI
            transport_type="websocket"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ============================================================
# TEST CASE 4: OpenRouter LLM + Groq STT + PlayHT TTS
# ============================================================
async def test_case_4():
    """OpenRouter LLM + Groq STT + PlayHT TTS"""
    print("\n" + "="*60)
    print("TEST CASE 4: OpenRouter LLM + Groq STT + PlayHT TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent OpenRouter-Groq-PlayHT",
            llm_service_id=36,  # OpenRouter
            stt_service_id=0,  # Groq
            tts_service_id=29,  # PlayHT
            transport_type="smallwebrtc"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ============================================================
# TEST CASE 5: Google LLM + Google STT + Google TTS
# ============================================================
async def test_case_5():
    """Google LLM + Google STT + Google TTS"""
    print("\n" + "="*60)
    print("TEST CASE 5: Google LLM + Google STT + Google TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent Google-Google-Google",
            llm_service_id=39,  # Google 
            stt_service_id=34,  # Google
            tts_service_id=7,  # Google
            transport_type="smallwebrtc"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ============================================================
# TEST CASE 6: AWS Bedrock LLM + Azure STT + AWS Polly TTS
# ============================================================
async def test_case_6():
    """AWS Bedrock LLM + Azure STT + word TTS"""
    print("\n" + "="*60)
    print("TEST CASE 6: AWS Bedrock LLM + Azure STT + word TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent AWSBedrock-Azure-word",
            llm_service_id=37,  # AWS Bedrock
            stt_service_id=6,  # Azure
            tts_service_id=50,  # word
            transport_type="websocket"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ============================================================
# TEST CASE 7: Gemini Live LLM + Nvidia STT + Nvidia TTS
# ============================================================
async def test_case_7():
    """Gemini Live LLM + Nvidia STT + Nvidia TTS"""
    print("\n" + "="*60)
    print("TEST CASE 7: Gemini Live LLM + Nvidia STT + Nvidia TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent GeminiLive-Nvidia-Nvidia",
            llm_service_id=13,  # Gemini Live 
            stt_service_id=8,  # Nvidia
            tts_service_id=26,  # Nvidia
            transport_type="smallwebrtc"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ============================================================
# TEST CASE 8: OpenAI Realtime LLM + Sarvam STT + Sarvam TTS
# ============================================================
async def test_case_8():
    """OpenAI Realtime LLM + Sarvam STT + Sarvam TTS"""
    print("\n" + "="*60)
    print("TEST CASE 8: OpenAI Realtime LLM + Sarvam STT + Sarvam TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent OpenAIRealtime-Sarvam-Sarvam",
            llm_service_id=41,  # OpenAI Realtime 
            stt_service_id=9,  # Sarvam
            tts_service_id=31,  # Sarvam
            transport_type="websocket"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ============================================================
# TEST CASE 9: Grok Realtime LLM + Speechmatics STT + Speechmatics TTS
# ============================================================
async def test_case_9():
    """Grok Realtime LLM + Speechmatics STT + Speechmatics TTS"""
    print("\n" + "="*60)
    print("TEST CASE 9: Grok Realtime LLM + Speechmatics STT + Speechmatics TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent GrokRealtime-Speechmatics-Speechmatics",
            llm_service_id=44,  # Grok Realtime 
            stt_service_id=10,  # Speechmatics
            tts_service_id=32,  # Speechmatics
            transport_type="websocket"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ============================================================
# TEST CASE 10: Ultravox Realtime LLM + Deepgram STT + Deepgram TTS
# ============================================================
async def test_case_10():
    """Ultravox Realtime LLM + Deepgram STT + Deepgram TTS"""
    print("\n" + "="*60)
    print("TEST CASE 10: Ultravox Realtime LLM + Deepgram STT + Deepgram TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent UltravoxRealtime-Deepgram-Deepgram",
            llm_service_id=42,  # Ultravox Realtime
            stt_service_id=35,   # Deepgram
            tts_service_id=4,  # Deepgram
            transport_type="smallwebrtc"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ============================================================
# TEST CASE 11: OpenAI LLM + Deepgram STT + Groq TTS
# ============================================================
async def test_case_11():
    """OpenAI LLM + Deepgram STT + Groq TTS"""
    print("\n" + "="*60)
    print("TEST CASE 11: OpenAI LLM + Deepgram STT + Groq TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent OpenAI-Deepgram-Groq",
            llm_service_id=1,   # OpenAI
            stt_service_id=35,   # Deepgram
            tts_service_id=20,  # Groq
            transport_type="smallwebrtc"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ============================================================
# TEST CASE 12: Anthropic LLM + OpenAI STT + Rime TTS
# ============================================================
async def test_case_12():
    """Anthropic LLM + deepgram_sagemaker + Rime TTS"""
    print("\n" + "="*60)
    print("TEST CASE 12: Anthropic LLM + deepgram_sagemaker + Rime TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent Anthropic - deepgram_sagemaker - Rime",
            llm_service_id=11,   # Anthropic
            stt_service_id=47,   # deepgram_sagemaker
            tts_service_id=30,  # Rime
            transport_type="smallwebrtc"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ============================================================
# TEST CASE 13: Groq LLM + Deepgram STT + XTTS TTS
# ============================================================
async def test_case_13():
    """Groq LLM + Deepgram STT + XTTS TTS"""
    print("\n" + "="*60)
    print("TEST CASE 13: Groq LLM + Deepgram STT + XTTS TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent Groq-Deepgram-XTTS",
            llm_service_id=14,   # Groq
            stt_service_id=35,   # Deepgram
            tts_service_id=33,  # XTTS
            transport_type="smallwebrtc"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def test_case_14():
    """aws_nova_sonic + openai + aws_polly TTS"""
    print("\n" + "="*60)
    print("TEST CASE 14: aws_nova_sonic + openai + aws_polly TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent aws_nova_sonic - openai - aws_polly",
            llm_service_id=38,   # aws_nova_sonic
            stt_service_id=45,   # openai
            tts_service_id=16,  # aws_polly
            transport_type="smallwebrtc"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

async def test_case_15():
    """base_openai + segmented + asyncai_http TTS"""
    print("\n" + "="*60)
    print("TEST CASE 15: base_openai + segmented STT + asyncai_http TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent base_openai - segmented - asyncai_http ",
            llm_service_id=40,   # base_openai
            stt_service_id=46,   # segmented
            tts_service_id=15,  # asyncai_http TTS
            transport_type="smallwebrtc"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def test_case_16():
    """openai_realtime_beta + sarvam + camb"""
    print("\n" + "="*60)
    print("TEST CASE 16: openai_realtime_beta + sarvam STT + camb TTS")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent openai_realtime_beta - sarvam - camb ",
            llm_service_id=43,   # openai_realtime_beta
            stt_service_id=9,   # sarvam
            tts_service_id=17,  # camb
            transport_type="smallwebrtc"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def test_case_17():
    """grok_realtime + sarvam + cartesia_http"""
    print("\n" + "="*60)
    print("TEST CASE 17: grok_realtime + sarvam STT + cartesia_http")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent grok_realtime - sarvam - cartesia_http ",
            llm_service_id=44,   # grok_realtime 
            stt_service_id=9,   # sarvam
            tts_service_id=52,  # cartesia_http
            transport_type="smallwebrtc"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

    
async def test_case_18():
    """openai_realtime_beta + sarvam + google_http"""
    print("\n" + "="*60)
    print("TEST CASE 18: openai_realtime_beta + sarvam STT + google_http")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent openai_realtime_beta - sarvam - google_http ",
            llm_service_id=43,   # openai_realtime_beta 
            stt_service_id=9,   # sarvam
            tts_service_id=51,  # google_http
            transport_type="websocket"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()    


async def test_case_19():
    """ultravox_realtime + Deepgram + google_http"""
    print("\n" + "="*60)
    print("TEST CASE 19: ultravox_realtime + sarvam STT + google_http")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent ultravox_realtime - sarvam - google_http ",
            llm_service_id=42,   # ultravox_realtime 
            stt_service_id=35,   # Deepgram
            tts_service_id=51,  # google_http
            transport_type="websocket"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()     

async def test_case_20():
    """openai_realtime + Deepgram + elevenlabs"""
    print("\n" + "="*60)
    print("TEST CASE 20: openai_realtime + Deepgram STT + elevenlabs")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent openai_realtime - sarvam - elevenlabs ",
            llm_service_id=41,   # openai_realtime
            stt_service_id=35,   # Deepgram
            tts_service_id=49,  # elevenlabs
            transport_type="websocket"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()   


async def test_case_21():
    """base_openai + Deepgram + hathora"""
    print("\n" + "="*60)
    print("TEST CASE 21: base_openai + Deepgram STT + hathora")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent openai_realtime_beta - Deepgram - hathora ",
            llm_service_id=40,   # base_openai 
            stt_service_id=35,   # Deepgram
            tts_service_id=21,  # hathora
            transport_type="websocket"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()       


async def test_case_22():
    """google + azure + minimax_http"""
    print("\n" + "="*60)
    print("TEST CASE 22: google + sarvam STT + minimax_http")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent openai_realtime_beta - azure - minimax_http ",
            llm_service_id=39,   # google 
            stt_service_id=6,   # azure
            tts_service_id=22,  # minimax_http
            transport_type="websocket"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()           

async def test_case_23():
    """aws_nova_sonic + azure + neuphonic_http"""
    print("\n" + "="*60)
    print("TEST CASE 23: aws_nova_sonic + azure STT + neuphonic_http")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent aws_nova_sonic - sarvam - neuphonic_http ",
            llm_service_id=38,   # aws_nova_sonic
            stt_service_id=6,   # azure
            tts_service_id=23,  # neuphonic_http
            transport_type="websocket"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()      


async def test_case_24():
    """openrouter + azure + piper"""
    print("\n" + "="*60)
    print("TEST CASE 24: openrouter + azure STT + piper")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent openai_realtime_beta - sarvam - piper ",
            llm_service_id=36,   # openrouter 
            stt_service_id=6,   # azure
            tts_service_id=28,  # piper
            transport_type="websocket"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()    


async def test_case_25():
    """aws_bedrock + azure + playht_http"""
    print("\n" + "="*60)
    print("TEST CASE 25: aws_bedrock + azure STT + playht_http")
    print("="*60)
    
    db = SessionLocal()
    try:
        result = create_test_agent(
            db=db,
            name="Agent openai_realtime_beta - azure - playht_http ",
            llm_service_id=37,   # aws_bedrock
            stt_service_id=6,   # azure
            tts_service_id=29,  # playht_http
            transport_type="websocket"
        )
        print(f"✓ Agent created: ID={result['id']}, Name={result['name']}")
        print(f"  LLM: {result.get('llm_service_id')}, STT: {result.get('stt_service_id')}, TTS: {result.get('tts_service_id')}")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()    



# ============================================================
# MAIN - Run all test cases
# ============================================================
async def run_all_tests():
    """Run all test cases."""
    print("\n" + "="*60)
    print("RUNNING ALL AGENT COMBINATION TEST CASES")
    print("="*60)
    
    results = []

    # await testing_agent_for_websocket()
    # await testing_agent_for_smallwebrtc()


    results.append(("Test Case 1", await test_case_1()))
    # results.append(("Test Case 2", await test_case_2()))
    # results.append(("Test Case 3", await test_case_3()))
    # results.append(("Test Case 4", await test_case_4()))
    # results.append(("Test Case 5", await test_case_5()))
    # results.append(("Test Case 6", await test_case_6()))
    # results.append(("Test Case 7", await test_case_7()))
    # results.append(("Test Case 8", await test_case_8()))
    # results.append(("Test Case 9", await test_case_9()))
    # results.append(("Test Case 10", await test_case_10()))
    # results.append(("Test Case 11", await test_case_11()))
    # results.append(("Test Case 12", await test_case_12()))
    # results.append(("Test Case 13", await test_case_13()))
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r is not None)
    failed = sum(1 for _, r in results if r is None)
    
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {len(results)}")


if __name__ == "__main__":
    # Run single test case:
    # test_case_1()
    
    # Or run all:
    asyncio.run(run_all_tests())