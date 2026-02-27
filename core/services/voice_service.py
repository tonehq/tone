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
from pipecat.services.azure.tts import AzureTTSService
from pipecat.services.asyncai.tts import AsyncAIHttpTTSService
from pipecat.services.camb.tts import CambTTSService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.playht.tts import PlayHTTTSService
from pipecat.services.deepgram.tts import DeepgramHttpTTSService
from pipecat.services.groq.tts import GroqTTSService
from pipecat.services.hathora.tts import HathoraTTSService
from pipecat.services.minimax.tts import MiniMaxHttpTTSService
from pipecat.services.rime.tts import RimeHttpTTSService
from pipecat.services.sarvam.tts import SarvamHttpTTSService
from pipecat.services.speechmatics.tts import SpeechmaticsTTSService
from pipecat.services.google.tts import GoogleHttpTTSService
from pipecat.services.aws.tts import AWSPollyTTSService
from pipecat.services.neuphonic.tts import NeuphonicHttpTTSService
from pipecat.services.hume.tts import HumeTTSService
from pipecat.services.inworld.tts import InworldTTSService
from pipecat.services.lmnt.tts import LmntTTSService
from pipecat.services.resembleai.tts import ResembleAITTSService
from pipecat.services.nvidia.tts import NvidiaTTSService


def main():
    import json

    # Each provider returns a list of voices in the common format:
    # name, voice_id, description, gender, language, sample_url, accent

    # ============ working code, need to check the response difference alone =======================================================
    # voices = ElevenLabsTTSService.get_voices(api_key=os.getenv("ELEVENLABS_API_KEY"))
    # print("elevenlabs voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = OpenAITTSService.get_voices(api_key=os.getenv("OPENAI_API_KEY"))
    # print("openai voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = AsyncAIHttpTTSService.get_voices(api_key=os.getenv("ASYNC_API_KEY"))
    # print("asyncai voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = CambTTSService.get_voices(api_key=os.getenv("CAMB_API_KEY"))
    # print("camb voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = CartesiaTTSService.get_voices(api_key=os.getenv("CARTESIA_API_KEY"))
    # print("cartesia voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = DeepgramHttpTTSService.get_voices(api_key=os.getenv("DEEPGRAM_API_KEY"))
    # print("deepgram voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = GroqTTSService.get_voices(api_key=os.getenv("GROQ_API_KEY"))
    # print("groq voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = MiniMaxHttpTTSService.get_voices(api_key=os.getenv("MINIMAX_API_KEY"))
    # print("minimax voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = RimeHttpTTSService.get_voices(api_key=os.getenv("RIME_API_KEY"))
    # print("rime voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = SarvamHttpTTSService.get_voices(api_key=os.getenv("SARVAM_API_KEY"))
    # print("sarvam voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = AWSPollyTTSService.get_voices(api_key=os.getenv("AWS_API_KEY"))
    # print("aws polly voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = NeuphonicHttpTTSService.get_voices(api_key=os.getenv("NEUPHONIC_API_KEY"))
    # print("neuphonic voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = InworldTTSService.get_voices(api_key=os.getenv("INWORLD_API_KEY"))
    # print("inworld voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = LmntTTSService.get_voices(api_key=os.getenv("LMNT_API_KEY"))
    # print("lmnt voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = ResembleAITTSService.get_voices(api_key=os.getenv("RESEMBLE_API_KEY"))
    # print("resemble voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = NvidiaTTSService.get_voices(api_key=os.getenv("NVIDIA_API_KEY"))
    # print("nvidia voices (first):", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = HumeTTSService.get_voices(api_key=os.getenv("HUME_API_KEY"))
    # print("hume voices result", json.dumps(voices[0] if voices else {}, indent=2))

    # voices = SpeechmaticsTTSService.get_voices(api_key=os.getenv("SPEECHMATICS_API_KEY"))
    # print("speechmatics voices (first):", json.dumps(voices[0] if voices else {}, indent=2))


    # ============================ Some issues in getting response from some providers =======================================================

    #facing issue in getting response timeout issue
    # voices = PlayHTTTSService.get_voices(api_key=os.getenv("PLAYHT_API_KEY"))
    # print("playht voices", voices)

    # Not working facing issue
    # voices = GoogleHttpTTSService.get_voices(api_key="jherfkfjwzfhiweijvpijefvjierj")
    # print("google voices (first):", json.dumps(voices[0] if voices else {}, indent=2))



    # ============================ Voices as individual files =======================================================
    #has json file in dev/azure-voices.yaml
    # voices = AzureTTSService.get_voices(api_key=os.getenv("AZURE_API_KEY"))
    # print("azure voices", voices)

    #has json file in dev/piper-voices.json
    #voices = PiperTTSService.get_voices(api_key=os.getenv("PIPER_API_KEY"))
    #print("piper voices", voices)

    #has json file in dev/hathora-voices.yaml
    # voices = HathoraTTSService.get_voices(api_key=os.getenv("HATHORA_API_KEY")) # Not implemented yet
    # print("hathora voices", voices)


    # ============================ voices needed to check =======================================================
    # Has more voices , check these API's.
    # API's to get default voices = https://fish.audio/app/default-voices/
    # API to get all voices = https://docs.fish.audio/api-reference/endpoint/model/list-models
    #voices = FishTTSService.get_voices(api_key=os.getenv("FISH_API_KEY"))
    #print("fish voices", voices)


if __name__ == "__main__":
    main()
    





#LLM provided by openAI all models
# gpt-4-0613
# gpt-4
# gpt-3.5-turbo
# gpt-5.2-codex
# gpt-4o-mini-tts-2025-12-15
# gpt-realtime-mini-2025-12-15
# gpt-audio-mini-2025-12-15
# chatgpt-image-latest
# davinci-002
# babbage-002
# gpt-3.5-turbo-instruct
# gpt-3.5-turbo-instruct-0914
# dall-e-3
# dall-e-2
# gpt-4-1106-preview
# gpt-3.5-turbo-1106
# tts-1-hd
# tts-1-1106
# tts-1-hd-1106
# text-embedding-3-small
# text-embedding-3-large
# gpt-4-0125-preview
# gpt-4-turbo-preview
# gpt-3.5-turbo-0125
# gpt-4-turbo
# gpt-4-turbo-2024-04-09
# gpt-4o
# gpt-4o-2024-05-13
# gpt-4o-mini-2024-07-18
# gpt-4o-mini
# gpt-4o-2024-08-06
# chatgpt-4o-latest
# gpt-4o-audio-preview
# gpt-4o-realtime-preview
# omni-moderation-latest
# omni-moderation-2024-09-26
# gpt-4o-realtime-preview-2024-12-17
# gpt-4o-audio-preview-2024-12-17
# gpt-4o-mini-realtime-preview-2024-12-17
# gpt-4o-mini-audio-preview-2024-12-17
# o1-2024-12-17
# o1
# gpt-4o-mini-realtime-preview
# gpt-4o-mini-audio-preview
# o3-mini
# o3-mini-2025-01-31
# gpt-4o-2024-11-20
# gpt-4o-search-preview-2025-03-11
# gpt-4o-search-preview
# gpt-4o-mini-search-preview-2025-03-11
# gpt-4o-mini-search-preview
# gpt-4o-transcribe
# gpt-4o-mini-transcribe
# o1-pro-2025-03-19
# o1-pro
# gpt-4o-mini-tts
# o3-2025-04-16
# o4-mini-2025-04-16
# o3
# o4-mini
# gpt-4.1-2025-04-14
# gpt-4.1
# gpt-4.1-mini-2025-04-14
# gpt-4.1-mini
# gpt-4.1-nano-2025-04-14
# gpt-4.1-nano
# gpt-image-1
# codex-mini-latest
# gpt-4o-realtime-preview-2025-06-03
# gpt-4o-audio-preview-2025-06-03
# o4-mini-deep-research
# gpt-4o-transcribe-diarize
# o4-mini-deep-research-2025-06-26
# gpt-5-chat-latest
# gpt-5-2025-08-07
# gpt-5
# gpt-5-mini-2025-08-07
# gpt-5-mini
# gpt-5-nano-2025-08-07
# gpt-5-nano
# gpt-audio-2025-08-28
# gpt-realtime
# gpt-realtime-2025-08-28
# gpt-audio
# gpt-5-codex
# gpt-image-1-mini
# gpt-5-pro-2025-10-06
# gpt-5-pro
# gpt-audio-mini
# gpt-audio-mini-2025-10-06
# gpt-5-search-api
# gpt-realtime-mini
# gpt-realtime-mini-2025-10-06
# sora-2
# sora-2-pro
# gpt-5-search-api-2025-10-14
# gpt-5.1-chat-latest
# gpt-5.1-2025-11-13
# gpt-5.1
# gpt-5.1-codex
# gpt-5.1-codex-mini
# gpt-5.1-codex-max
# gpt-image-1.5
# gpt-5.2-2025-12-11
# gpt-5.2
# gpt-5.2-pro-2025-12-11
# gpt-5.2-pro
# gpt-5.2-chat-latest
# gpt-4o-mini-transcribe-2025-12-15
# gpt-4o-mini-transcribe-2025-03-20
# gpt-4o-mini-tts-2025-03-20
# gpt-3.5-turbo-16k
# tts-1
# whisper-1
# text-embedding-ada-002



#Open router all models
# ['qwen/qwen3-max-thinking', 'openrouter/aurora-alpha', 'openrouter/pony-alpha', 'anthropic/claude-opus-4.6', 'qwen/qwen3-coder-next', 'openrouter/free', 'stepfun/step-3.5-flash:free', 'arcee-ai/trinity-large-preview:free', 'moonshotai/kimi-k2.5', 'upstage/solar-pro-3:free', 'minimax/minimax-m2-her', 'writer/palmyra-x5', 'liquid/lfm-2.5-1.2b-thinking:free', 'liquid/lfm-2.5-1.2b-instruct:free', 'openai/gpt-audio', 'openai/gpt-audio-mini', 'z-ai/glm-4.7-flash', 'openai/gpt-5.2-codex', 'allenai/molmo-2-8b', 'allenai/olmo-3.1-32b-instruct', 'bytedance-seed/seed-1.6-flash', 'bytedance-seed/seed-1.6', 'minimax/minimax-m2.1', 'z-ai/glm-4.7', 'google/gemini-3-flash-preview', 'mistralai/mistral-small-creative', 'allenai/olmo-3.1-32b-think', 'xiaomi/mimo-v2-flash', 'nvidia/nemotron-3-nano-30b-a3b:free', 'nvidia/nemotron-3-nano-30b-a3b', 'openai/gpt-5.2-chat', 'openai/gpt-5.2-pro', 'openai/gpt-5.2', 'mistralai/devstral-2512', 'relace/relace-search', 'z-ai/glm-4.6v', 'nex-agi/deepseek-v3.1-nex-n1', 'essentialai/rnj-1-instruct', 'openrouter/bodybuilder', 'openai/gpt-5.1-codex-max', 'amazon/nova-2-lite-v1', 'mistralai/ministral-14b-2512', 'mistralai/ministral-8b-2512', 'mistralai/ministral-3b-2512', 'mistralai/mistral-large-2512', 'arcee-ai/trinity-mini:free', 'arcee-ai/trinity-mini', 'deepseek/deepseek-v3.2-speciale', 'deepseek/deepseek-v3.2', 'prime-intellect/intellect-3', 'tngtech/tng-r1t-chimera:free', 'tngtech/tng-r1t-chimera', 'anthropic/claude-opus-4.5', 'allenai/olmo-3-32b-think', 'allenai/olmo-3-7b-instruct', 'allenai/olmo-3-7b-think', 'google/gemini-3-pro-image-preview', 'x-ai/grok-4.1-fast', 'google/gemini-3-pro-preview', 'deepcogito/cogito-v2.1-671b', 'openai/gpt-5.1', 'openai/gpt-5.1-chat', 'openai/gpt-5.1-codex', 'openai/gpt-5.1-codex-mini', 'kwaipilot/kat-coder-pro', 'moonshotai/kimi-k2-thinking', 'amazon/nova-premier-v1', 'perplexity/sonar-pro-search', 'mistralai/voxtral-small-24b-2507', 'openai/gpt-oss-safeguard-20b', 'nvidia/nemotron-nano-12b-v2-vl:free', 'nvidia/nemotron-nano-12b-v2-vl', 'minimax/minimax-m2', 'qwen/qwen3-vl-32b-instruct', 'liquid/lfm2-8b-a1b', 'liquid/lfm-2.2-6b', 'ibm-granite/granite-4.0-h-micro', 'openai/gpt-5-image-mini', 'anthropic/claude-haiku-4.5', 'qwen/qwen3-vl-8b-thinking', 'qwen/qwen3-vl-8b-instruct', 'openai/gpt-5-image', 'openai/o3-deep-research', 'openai/o4-mini-deep-research', 'nvidia/llama-3.3-nemotron-super-49b-v1.5', 'baidu/ernie-4.5-21b-a3b-thinking', 'google/gemini-2.5-flash-image', 'qwen/qwen3-vl-30b-a3b-thinking', 'qwen/qwen3-vl-30b-a3b-instruct', 'openai/gpt-5-pro', 'z-ai/glm-4.6', 'z-ai/glm-4.6:exacto', 'anthropic/claude-sonnet-4.5', 'deepseek/deepseek-v3.2-exp', 'thedrummer/cydonia-24b-v4.1', 'relace/relace-apply-3', 'google/gemini-2.5-flash-preview-09-2025', 'google/gemini-2.5-flash-lite-preview-09-2025', 'qwen/qwen3-vl-235b-a22b-thinking', 'qwen/qwen3-vl-235b-a22b-instruct', 'qwen/qwen3-max', 'qwen/qwen3-coder-plus', 'openai/gpt-5-codex', 'deepseek/deepseek-v3.1-terminus:exacto', 'deepseek/deepseek-v3.1-terminus', 'x-ai/grok-4-fast', 'alibaba/tongyi-deepresearch-30b-a3b', 'qwen/qwen3-coder-flash', 'opengvlab/internvl3-78b', 'qwen/qwen3-next-80b-a3b-thinking', 'qwen/qwen3-next-80b-a3b-instruct:free', 'qwen/qwen3-next-80b-a3b-instruct', 'meituan/longcat-flash-chat', 'qwen/qwen-plus-2025-07-28', 'qwen/qwen-plus-2025-07-28:thinking', 'nvidia/nemotron-nano-9b-v2:free', 'nvidia/nemotron-nano-9b-v2', 'moonshotai/kimi-k2-0905', 'moonshotai/kimi-k2-0905:exacto', 'qwen/qwen3-30b-a3b-thinking-2507', 'x-ai/grok-code-fast-1', 'nousresearch/hermes-4-70b', 'nousresearch/hermes-4-405b', 'deepseek/deepseek-chat-v3.1', 'openai/gpt-4o-audio-preview', 'mistralai/mistral-medium-3.1', 'baidu/ernie-4.5-21b-a3b', 'baidu/ernie-4.5-vl-28b-a3b', 'z-ai/glm-4.5v', 'ai21/jamba-large-1.7', 'openai/gpt-5-chat', 'openai/gpt-5', 'openai/gpt-5-mini', 'openai/gpt-5-nano', 'openai/gpt-oss-120b:free', 'openai/gpt-oss-120b', 'openai/gpt-oss-120b:exacto', 'openai/gpt-oss-20b:free', 'openai/gpt-oss-20b', 'anthropic/claude-opus-4.1', 'mistralai/codestral-2508', 'qwen/qwen3-coder-30b-a3b-instruct', 'qwen/qwen3-30b-a3b-instruct-2507', 'z-ai/glm-4.5', 'z-ai/glm-4.5-air:free', 'z-ai/glm-4.5-air', 'qwen/qwen3-235b-a22b-thinking-2507', 'z-ai/glm-4-32b', 'qwen/qwen3-coder:free', 'qwen/qwen3-coder', 'qwen/qwen3-coder:exacto', 'bytedance/ui-tars-1.5-7b', 'google/gemini-2.5-flash-lite', 'qwen/qwen3-235b-a22b-2507', 'switchpoint/router', 'moonshotai/kimi-k2', 'mistralai/devstral-medium', 'mistralai/devstral-small', 'cognitivecomputations/dolphin-mistral-24b-venice-edition:free', 'x-ai/grok-4', 'google/gemma-3n-e2b-it:free', 'tencent/hunyuan-a13b-instruct', 'tngtech/deepseek-r1t2-chimera:free', 'tngtech/deepseek-r1t2-chimera', 'morph/morph-v3-large', 'morph/morph-v3-fast', 'baidu/ernie-4.5-vl-424b-a47b', 'baidu/ernie-4.5-300b-a47b', 'inception/mercury', 'mistralai/mistral-small-3.2-24b-instruct', 'minimax/minimax-m1', 'google/gemini-2.5-flash', 'google/gemini-2.5-pro', 'openai/o3-pro', 'x-ai/grok-3-mini', 'x-ai/grok-3', 'google/gemini-2.5-pro-preview', 'deepseek/deepseek-r1-0528:free', 'deepseek/deepseek-r1-0528', 'anthropic/claude-opus-4', 'anthropic/claude-sonnet-4', 'google/gemma-3n-e4b-it:free', 'google/gemma-3n-e4b-it', 'nousresearch/deephermes-3-mistral-24b-preview', 'mistralai/mistral-medium-3', 'google/gemini-2.5-pro-preview-05-06', 'arcee-ai/spotlight', 'arcee-ai/maestro-reasoning', 'arcee-ai/virtuoso-large', 'arcee-ai/coder-large', 'inception/mercury-coder', 'qwen/qwen3-4b:free', 'meta-llama/llama-guard-4-12b', 'qwen/qwen3-30b-a3b', 'qwen/qwen3-8b', 'qwen/qwen3-14b', 'qwen/qwen3-32b', 'qwen/qwen3-235b-a22b', 'tngtech/deepseek-r1t-chimera:free', 'tngtech/deepseek-r1t-chimera', 'openai/o4-mini-high', 'openai/o3', 'openai/o4-mini', 'qwen/qwen2.5-coder-7b-instruct', 'openai/gpt-4.1', 'openai/gpt-4.1-mini', 'openai/gpt-4.1-nano', 'eleutherai/llemma_7b', 'alfredpros/codellama-7b-instruct-solidity', 'x-ai/grok-3-mini-beta', 'x-ai/grok-3-beta', 'nvidia/llama-3.1-nemotron-ultra-253b-v1', 'meta-llama/llama-4-maverick', 'meta-llama/llama-4-scout', 'qwen/qwen2.5-vl-32b-instruct', 'deepseek/deepseek-chat-v3-0324', 'openai/o1-pro', 'mistralai/mistral-small-3.1-24b-instruct:free', 'mistralai/mistral-small-3.1-24b-instruct', 'allenai/olmo-2-0325-32b-instruct', 'google/gemma-3-4b-it:free', 'google/gemma-3-4b-it', 'google/gemma-3-12b-it:free', 'google/gemma-3-12b-it', 'cohere/command-a', 'openai/gpt-4o-mini-search-preview', 'openai/gpt-4o-search-preview', 'google/gemma-3-27b-it:free', 'google/gemma-3-27b-it', 'thedrummer/skyfall-36b-v2', 'perplexity/sonar-reasoning-pro', 'perplexity/sonar-pro', 'perplexity/sonar-deep-research', 'qwen/qwq-32b', 'google/gemini-2.0-flash-lite-001', 'anthropic/claude-3.7-sonnet:thinking', 'anthropic/claude-3.7-sonnet', 'mistralai/mistral-saba', 'meta-llama/llama-guard-3-8b', 'openai/o3-mini-high', 'google/gemini-2.0-flash-001', 'qwen/qwen-vl-plus', 'aion-labs/aion-1.0', 'aion-labs/aion-1.0-mini', 'aion-labs/aion-rp-llama-3.1-8b', 'qwen/qwen-vl-max', 'qwen/qwen-turbo', 'qwen/qwen2.5-vl-72b-instruct', 'qwen/qwen-plus', 'qwen/qwen-max', 'openai/o3-mini', 'mistralai/mistral-small-24b-instruct-2501', 'deepseek/deepseek-r1-distill-qwen-32b', 'perplexity/sonar', 'deepseek/deepseek-r1-distill-llama-70b', 'deepseek/deepseek-r1', 'minimax/minimax-01', 'microsoft/phi-4', 'sao10k/l3.1-70b-hanami-x1', 'deepseek/deepseek-chat', 'sao10k/l3.3-euryale-70b', 'openai/o1', 'cohere/command-r7b-12-2024', 'meta-llama/llama-3.3-70b-instruct:free', 'meta-llama/llama-3.3-70b-instruct', 'amazon/nova-lite-v1', 'amazon/nova-micro-v1', 'amazon/nova-pro-v1', 'openai/gpt-4o-2024-11-20', 'mistralai/mistral-large-2411', 'mistralai/mistral-large-2407', 'mistralai/pixtral-large-2411', 'qwen/qwen-2.5-coder-32b-instruct', 'raifle/sorcererlm-8x22b', 'thedrummer/unslopnemo-12b', 'anthropic/claude-3.5-haiku', 'anthracite-org/magnum-v4-72b', 'anthropic/claude-3.5-sonnet', 'mistralai/ministral-8b', 'mistralai/ministral-3b', 'qwen/qwen-2.5-7b-instruct', 'nvidia/llama-3.1-nemotron-70b-instruct', 'inflection/inflection-3-pi', 'inflection/inflection-3-productivity', 'thedrummer/rocinante-12b', 'meta-llama/llama-3.2-3b-instruct:free', 'meta-llama/llama-3.2-3b-instruct', 'meta-llama/llama-3.2-1b-instruct', 'meta-llama/llama-3.2-11b-vision-instruct', 'qwen/qwen-2.5-72b-instruct', 'neversleep/llama-3.1-lumimaid-8b', 'mistralai/pixtral-12b', 'cohere/command-r-08-2024', 'cohere/command-r-plus-08-2024', 'sao10k/l3.1-euryale-70b', 'qwen/qwen-2.5-vl-7b-instruct', 'nousresearch/hermes-3-llama-3.1-70b', 'nousresearch/hermes-3-llama-3.1-405b:free', 'nousresearch/hermes-3-llama-3.1-405b', 'openai/chatgpt-4o-latest', 'sao10k/l3-lunaris-8b', 'openai/gpt-4o-2024-08-06', 'meta-llama/llama-3.1-405b', 'meta-llama/llama-3.1-8b-instruct', 'meta-llama/llama-3.1-405b-instruct', 'meta-llama/llama-3.1-70b-instruct', 'mistralai/mistral-nemo', 'openai/gpt-4o-mini-2024-07-18', 'openai/gpt-4o-mini', 'google/gemma-2-27b-it', 'google/gemma-2-9b-it', 'sao10k/l3-euryale-70b', 'nousresearch/hermes-2-pro-llama-3-8b', 'mistralai/mistral-7b-instruct', 'mistralai/mistral-7b-instruct-v0.3', 'meta-llama/llama-guard-2-8b', 'openai/gpt-4o-2024-05-13', 'openai/gpt-4o', 'openai/gpt-4o:extended', 'meta-llama/llama-3-70b-instruct', 'meta-llama/llama-3-8b-instruct', 'mistralai/mixtral-8x22b-instruct', 'microsoft/wizardlm-2-8x22b', 'openai/gpt-4-turbo', 'anthropic/claude-3-haiku', 'mistralai/mistral-large', 'openai/gpt-3.5-turbo-0613', 'openai/gpt-4-turbo-preview', 'mistralai/mistral-tiny', 'mistralai/mistral-7b-instruct-v0.2', 'mistralai/mixtral-8x7b-instruct', 'neversleep/noromaid-20b', 'alpindale/goliath-120b', 'openrouter/auto', 'openai/gpt-4-1106-preview', 'openai/gpt-3.5-turbo-instruct', 'mistralai/mistral-7b-instruct-v0.1', 'openai/gpt-3.5-turbo-16k', 'mancer/weaver', 'undi95/remm-slerp-l2-13b', 'gryphe/mythomax-l2-13b', 'openai/gpt-4-0314', 'openai/gpt-4', 'openai/gpt-3.5-turbo']


#Open router text to text models
# TEXT_TO_TEXT_MODELS = [
#     # Anthropic
#     "anthropic/claude-opus-4.6",
#     "anthropic/claude-opus-4.5",
#     "anthropic/claude-opus-4.1",
#     "anthropic/claude-opus-4",
#     "anthropic/claude-sonnet-4.5",
#     "anthropic/claude-sonnet-4",
#     "anthropic/claude-3.7-sonnet",
#     "anthropic/claude-3.7-sonnet:thinking",
#     "anthropic/claude-3.5-sonnet",
#     "anthropic/claude-3.5-haiku",
#     "anthropic/claude-3-haiku",

#     # OpenAI (text-only)
#     "openai/gpt-5",
#     "openai/gpt-5-chat",
#     "openai/gpt-5-mini",
#     "openai/gpt-5-nano",
#     "openai/gpt-5-pro",
#     "openai/gpt-5.2",
#     "openai/gpt-5.2-chat",
#     "openai/gpt-5.2-pro",
#     "openai/gpt-5.2-codex",
#     "openai/gpt-5.1",
#     "openai/gpt-5.1-chat",
#     "openai/gpt-5.1-codex",
#     "openai/gpt-5.1-codex-mini",
#     "openai/gpt-5.1-codex-max",
#     "openai/gpt-4",
#     "openai/gpt-4-turbo",
#     "openai/gpt-4-turbo-preview",
#     "openai/gpt-4-1106-preview",
#     "openai/gpt-4-0314",
#     "openai/gpt-4o",
#     "openai/gpt-4o:extended",
#     "openai/gpt-4o-2024-05-13",
#     "openai/gpt-4o-2024-11-20",
#     "openai/chatgpt-4o-latest",
#     "openai/gpt-4.1",
#     "openai/gpt-4.1-mini",
#     "openai/gpt-4.1-nano",
#     "openai/gpt-3.5-turbo",
#     "openai/gpt-3.5-turbo-0613",
#     "openai/gpt-3.5-turbo-16k",
#     "openai/gpt-3.5-turbo-instruct",
#     "openai/o1",
#     "openai/o1-pro",
#     "openai/o3",
#     "openai/o3-mini",
#     "openai/o3-mini-high",
#     "openai/o3-pro",
#     "openai/o4-mini",
#     "openai/o4-mini-high",

#     # Meta / LLaMA
#     "meta-llama/llama-4-maverick",
#     "meta-llama/llama-4-scout",
#     "meta-llama/llama-3.3-70b-instruct",
#     "meta-llama/llama-3.2-3b-instruct",
#     "meta-llama/llama-3.2-1b-instruct",
#     "meta-llama/llama-3.1-8b-instruct",
#     "meta-llama/llama-3.1-70b-instruct",
#     "meta-llama/llama-3.1-405b-instruct",
#     "meta-llama/llama-3-70b-instruct",
#     "meta-llama/llama-3-8b-instruct",

#     # Qwen (text-only)
#     "qwen/qwen3-max",
#     "qwen/qwen3-max-thinking",
#     "qwen/qwen3-4b",
#     "qwen/qwen3-8b",
#     "qwen/qwen3-14b",
#     "qwen/qwen3-30b-a3b",
#     "qwen/qwen3-32b",
#     "qwen/qwen3-235b-a22b",
#     "qwen/qwen3-235b-a22b-thinking-2507",
#     "qwen/qwen3-next-80b-a3b-instruct",
#     "qwen/qwen3-next-80b-a3b-thinking",
#     "qwen/qwen-plus",
#     "qwen/qwen-plus-2025-07-28",
#     "qwen/qwen-plus-2025-07-28:thinking",
#     "qwen/qwen-max",
#     "qwen/qwen-turbo",

#     # Qwen Coders (still text-to-text)
#     "qwen/qwen3-coder",
#     "qwen/qwen3-coder-plus",
#     "qwen/qwen3-coder-flash",
#     "qwen/qwen3-coder-next",
#     "qwen/qwen3-coder-30b-a3b-instruct",
#     "qwen/qwen2.5-coder-7b-instruct",
#     "qwen/qwen-2.5-coder-32b-instruct",

#     # Mistral / Mixtral
#     "mistralai/mistral-large",
#     "mistralai/mistral-large-2407",
#     "mistralai/mistral-large-2411",
#     "mistralai/mistral-medium-3",
#     "mistralai/mistral-medium-3.1",
#     "mistralai/mistral-small-creative",
#     "mistralai/mistral-small-3.1-24b-instruct",
#     "mistralai/mistral-small-3.2-24b-instruct",
#     "mistralai/mistral-7b-instruct",
#     "mistralai/mistral-7b-instruct-v0.3",
#     "mistralai/mixtral-8x7b-instruct",
#     "mistralai/mixtral-8x22b-instruct",
#     "mistralai/ministral-3b",
#     "mistralai/ministral-8b",
#     "mistralai/ministral-14b-2512",
#     "mistralai/devstral-small",
#     "mistralai/devstral-medium",
#     "mistralai/devstral-2512",
#     "mistralai/codestral-2508",

#     # DeepSeek
#     "deepseek/deepseek-chat",
#     "deepseek/deepseek-chat-v3-0324",
#     "deepseek/deepseek-chat-v3.1",
#     "deepseek/deepseek-v3.2",
#     "deepseek/deepseek-v3.2-exp",
#     "deepseek/deepseek-v3.2-speciale",
#     "deepseek/deepseek-r1",
#     "deepseek/deepseek-r1-0528",
#     "deepseek/deepseek-r1-distill-qwen-32b",
#     "deepseek/deepseek-r1-distill-llama-70b",

#     # Gemini (text-only)
#     "google/gemini-2.5-flash",
#     "google/gemini-2.5-pro",
#     "google/gemini-2.5-pro-preview",
#     "google/gemini-2.0-flash-001",
#     "google/gemini-2.0-flash-lite-001",

#     # Others (text LLMs)
#     "ai21/jamba-large-1.7",
#     "cohere/command-a",
#     "cohere/command-r-08-2024",
#     "cohere/command-r-plus-08-2024",
#     "cohere/command-r7b-12-2024",
#     "microsoft/phi-4",
#     "inflection/inflection-3-pi",
#     "inflection/inflection-3-productivity",
#     "prime-intellect/intellect-3",
#     "nousresearch/hermes-4-70b",
#     "nousresearch/hermes-4-405b",
#     "nousresearch/hermes-3-llama-3.1-70b",
#     "nousresearch/hermes-3-llama-3.1-405b",
#     "allenai/olmo-3.1-32b-instruct",
#     "allenai/olmo-3.1-32b-think",
#     "allenai/olmo-3-7b-instruct",
#     "allenai/olmo-2-0325-32b-instruct",
#     "baidu/ernie-4.5-21b-a3b",
#     "baidu/ernie-4.5-300b-a47b",
#     "z-ai/glm-4.5",
#     "z-ai/glm-4.6",
#     "z-ai/glm-4.7",
#     "x-ai/grok-3",
#     "x-ai/grok-3-mini",
#     "x-ai/grok-4",
#     "x-ai/grok-4-fast",
# ]
