from __future__ import annotations

from typing import Any

from core.services.pipeline_builders.base import BuildContext, TTSBuilder, build_input_params


HTTP_TTS_PROVIDERS = {"asyncai_http", "deepgram", "minimax", "neuphonic", "rime", "sarvam", "speechmatics"}


class CartesiaTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.cartesia.tts import CartesiaTTSService
        voice_kwargs = {}
        voice_kwargs["voice_id"] = ctx.voice_id or "e07c00bc-4134-4eae-9ea4-1a55fb45746b"
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language or "en"
        return CartesiaTTSService(api_key=ctx.api_key, model=ctx.model or "sonic-3", params=build_input_params(CartesiaTTSService, ctx.metadata), **voice_kwargs)


class OpenAITTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.openai.tts import OpenAITTSService
        voice_kwargs = {}
        if ctx.voice_id is not None:
            voice_kwargs["voice"] = ctx.voice_id
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        else:
            voice_kwargs["language"] = None
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return OpenAITTSService(api_key=ctx.api_key, model=ctx.model or "gpt-4o-mini-tts", params=build_input_params(OpenAITTSService, ctx.metadata), **voice_kwargs)


class ElevenLabsTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
        voice_kwargs = {}
        voice_kwargs["voice_id"] = ctx.voice_id or "CwhRBWXzGAHq8TQ4Fs17"
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return ElevenLabsTTSService(api_key=ctx.api_key, model=ctx.model or "eleven_v3", params=build_input_params(ElevenLabsTTSService, ctx.metadata), **voice_kwargs)


class PlayHTTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.playht.tts import PlayHTTTSService
        user_id = ctx.model_meta.get("user_id") or ctx.metadata.get("user_id") or ""
        voice_kwargs = {}
        if ctx.voice_id is not None:
            voice_kwargs["voice_url"] = ctx.voice_id
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return PlayHTTTSService(api_key=ctx.api_key, user_id=user_id, params=build_input_params(PlayHTTTSService, ctx.metadata), **voice_kwargs)


class AsyncAIHttpTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.asyncai.tts import AsyncAIHttpTTSService
        voice_kwargs = {}
        voice_kwargs["voice_id"] = ctx.voice_id or "13616e5f-6fda-4247-b548-8821cb71fb54"
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        else:
            voice_kwargs["language"] = None
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return AsyncAIHttpTTSService(api_key=ctx.api_key, aiohttp_session=ctx.session, params=build_input_params(AsyncAIHttpTTSService, ctx.metadata), **voice_kwargs)


class AWSPollyTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.aws.tts import AWSPollyTTSService
        aws_access_key_id = ctx.model_meta.get("aws_access_key_id") or ctx.metadata.get("aws_access_key_id") or ""
        region = ctx.model_meta.get("region") or ctx.metadata.get("region") or "us-east-1"
        voice_kwargs = {}
        if ctx.voice_id is not None:
            voice_kwargs["voice_id"] = ctx.voice_id
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return AWSPollyTTSService(api_key=ctx.api_key, aws_access_key_id=aws_access_key_id, region=region, params=build_input_params(AWSPollyTTSService, ctx.metadata), **voice_kwargs)


class CambTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.camb.tts import CambTTSService
        voice_kwargs = {}
        if ctx.voice_id is not None:
            voice_kwargs["voice_id"] = ctx.voice_id
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        camb_metadata = {k: v for k, v in ctx.metadata.items() if k != "language"}
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return CambTTSService(api_key=ctx.api_key, params=build_input_params(CambTTSService, camb_metadata), **voice_kwargs)


class DeepgramTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.deepgram.tts import DeepgramHttpTTSService
        dg_voice = ctx.voice_id or "aura-2-helena-en"
        dg_model = ctx.model or "aura-2"
        dg_kwargs = {}
        if ctx.metadata.get("sample_rate") is not None:
            dg_kwargs["sample_rate"] = ctx.metadata["sample_rate"]
        print(f"[TTS {ctx.provider_name}] model: {dg_model}, voice: {dg_voice}")
        return DeepgramHttpTTSService(api_key=ctx.api_key, model=dg_model, voice=dg_voice, aiohttp_session=ctx.session, **dg_kwargs)


class GoogleTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.google.tts import GoogleTTSService
        voice_kwargs = {}
        if ctx.voice_id is not None:
            voice_kwargs["voice_id"] = ctx.voice_id
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}, location: global")
        return GoogleTTSService(credentials=ctx.api_key, params=build_input_params(GoogleTTSService, ctx.metadata), **voice_kwargs)


class GroqTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.groq.tts import GroqTTSService
        voice_kwargs = {}
        if ctx.voice_id is not None:
            voice_kwargs["voice_id"] = ctx.voice_id
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        model = ctx.model
        if not model:
            model = "canopylabs/orpheus-arabic-saudi" if ctx.language == "ar" else "canopylabs/orpheus-v1-english"
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return GroqTTSService(api_key=ctx.api_key, model_name=model, params=build_input_params(GroqTTSService, ctx.metadata), **voice_kwargs)


class HathoraTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.hathora.tts import HathoraTTSService
        voice_kwargs = {}
        if ctx.voice_id is not None:
            voice_kwargs["voice_id"] = ctx.voice_id
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        else:
            voice_kwargs["language"] = None
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return HathoraTTSService(api_key=ctx.api_key, model=ctx.model or "hexgrad-kokoro-82m", params=build_input_params(HathoraTTSService, ctx.metadata), **voice_kwargs)


class MiniMaxTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.minimax.tts import MiniMaxHttpTTSService
        group_id = ctx.model_meta.get("group_id") or ctx.metadata.get("group_id") or ""
        voice_kwargs = {}
        if ctx.voice_id is not None:
            voice_kwargs["voice_id"] = ctx.voice_id
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return MiniMaxHttpTTSService(api_key=ctx.api_key, group_id=group_id, model=ctx.model or "speech-2.8-turbo", aiohttp_session=ctx.session, params=build_input_params(MiniMaxHttpTTSService, ctx.metadata), **voice_kwargs)


class NeuphonicTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.neuphonic.tts import NeuphonicHttpTTSService
        voice_kwargs = {}
        voice_kwargs["voice_id"] = ctx.voice_id or "6654e5a9-143e-46f4-a44a-4fcb9e1fe2a6"
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return NeuphonicHttpTTSService(api_key=ctx.api_key, model=ctx.model or "neu_hq", aiohttp_session=ctx.session, params=build_input_params(NeuphonicHttpTTSService, ctx.metadata), **voice_kwargs)


class NvidiaTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.nvidia.tts import NvidiaTTSService
        server = ctx.model_meta.get("server") or ctx.metadata.get("server") or "grpc.nvcf.nvidia.com:443"
        voice_kwargs = {}
        if ctx.voice_id is not None:
            voice_kwargs["voice_id"] = ctx.voice_id
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return NvidiaTTSService(api_key=ctx.api_key, server=server, params=build_input_params(NvidiaTTSService, ctx.metadata), **voice_kwargs)


class RimeTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.rime.tts import RimeHttpTTSService
        from pipecat.transcriptions.language import Language
        voice_kwargs = {}
        voice_kwargs["voice_id"] = ctx.voice_id or "albion"
        _RIME_LANG_MAP = {
            "english": Language.EN,
            "german": Language.DE,
            "french": Language.FR,
            "spanish": Language.ES,
            "hindi": Language.HI,
        }
        rime_language = None
        if ctx.language:
            rime_language = _RIME_LANG_MAP.get(ctx.language.strip().lower())
        params = build_input_params(RimeHttpTTSService, ctx.metadata)
        if rime_language and params:
            params.language = rime_language
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return RimeHttpTTSService(api_key=ctx.api_key, model=ctx.model or "mistv2", aiohttp_session=ctx.session, params=params, **voice_kwargs)


class SarvamTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.sarvam.tts import SarvamHttpTTSService
        voice_kwargs = {}
        if ctx.voice_id is not None:
            sarvam_voice = ctx.voice_id
            if sarvam_voice.startswith("sarvam-"):
                parts = sarvam_voice.split("-")
                if len(parts) >= 3:
                    sarvam_voice = parts[1]
            voice_kwargs["voice_id"] = sarvam_voice
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return SarvamHttpTTSService(api_key=ctx.api_key, model=ctx.model or "bulbul:v3", aiohttp_session=ctx.session, params=build_input_params(SarvamHttpTTSService, ctx.metadata), **voice_kwargs)


class SpeechmaticsTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.speechmatics.tts import SpeechmaticsTTSService
        voice_kwargs = {}
        if ctx.voice_id is not None:
            voice_kwargs["voice_id"] = ctx.voice_id
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        else:
            voice_kwargs["language"] = None
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return SpeechmaticsTTSService(api_key=ctx.api_key, aiohttp_session=ctx.session, sample_rate=ctx.metadata.get("sample_rate") or SpeechmaticsTTSService.SPEECHMATICS_SAMPLE_RATE, params=build_input_params(SpeechmaticsTTSService, ctx.metadata), **voice_kwargs)


class AzureTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.azure.tts import AzureTTSService
        region = ctx.model_meta.get("region") or ctx.metadata.get("region") or "eastus"
        voice_kwargs = {}
        if ctx.voice_id is not None:
            voice_kwargs["voice"] = ctx.voice_id
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return AzureTTSService(api_key=ctx.api_key, region=region, params=build_input_params(AzureTTSService, ctx.metadata), **voice_kwargs)


class FishTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.fish.tts import FishAudioTTSService
        voice_kwargs = {}
        voice_kwargs["reference_id"] = ctx.voice_id or "0eb2bd3576714dbcad7cd4c6b2b6e12f"
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return FishAudioTTSService(api_key=ctx.api_key, model_id=ctx.model or "s1", params=build_input_params(FishAudioTTSService, ctx.metadata), **voice_kwargs)


class HumeTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.hume.tts import HumeTTSService
        voice_kwargs = {}
        voice_kwargs["voice_id"] = ctx.voice_id or "d8ab67c6-953d-4bd8-9370-8fa53a0f1453"
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        else:
            voice_kwargs["language"] = None
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return HumeTTSService(api_key=ctx.api_key, version=ctx.model or "2", params=build_input_params(HumeTTSService, ctx.metadata), **voice_kwargs)


class InworldTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.inworld.tts import InworldTTSService
        voice_kwargs = {}
        if ctx.voice_id is not None:
            voice_kwargs["voice_id"] = ctx.voice_id
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        else:
            voice_kwargs["language"] = None
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return InworldTTSService(api_key=ctx.api_key, model=ctx.model or "inworld-tts-1.5-max", params=build_input_params(InworldTTSService, ctx.metadata), **voice_kwargs)


class LmntTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.lmnt.tts import LmntTTSService
        voice_kwargs = {}
        voice_kwargs["voice_id"] = ctx.voice_id or "ava"
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        return LmntTTSService(api_key=ctx.api_key, **voice_kwargs)


class ResembleTTSBuilder(TTSBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.resembleai.tts import ResembleAITTSService
        voice_kwargs = {}
        voice_kwargs["voice_id"] = ctx.voice_id
        if ctx.language is not None:
            voice_kwargs["language"] = ctx.language
        else:
            voice_kwargs["language"] = None
        if ctx.metadata.get("sample_rate") is not None:
            voice_kwargs["sample_rate"] = ctx.metadata["sample_rate"]
        print(f"[TTS {ctx.provider_name}] voice_kwargs: {voice_kwargs}")
        return ResembleAITTSService(api_key=ctx.api_key, **voice_kwargs)


TTS_BUILDERS = {
    "cartesia": CartesiaTTSBuilder(),
    "openai": OpenAITTSBuilder(),
    "elevenlabs": ElevenLabsTTSBuilder(),
    "playht": PlayHTTTSBuilder(),
    "asyncai_http": AsyncAIHttpTTSBuilder(),
    "aws_polly": AWSPollyTTSBuilder(),
    "camb": CambTTSBuilder(),
    "deepgram": DeepgramTTSBuilder(),
    "google": GoogleTTSBuilder(),
    "groq": GroqTTSBuilder(),
    "hathora": HathoraTTSBuilder(),
    "minimax": MiniMaxTTSBuilder(),
    "neuphonic": NeuphonicTTSBuilder(),
    "nvidia": NvidiaTTSBuilder(),
    "rime": RimeTTSBuilder(),
    "sarvam": SarvamTTSBuilder(),
    "speechmatics": SpeechmaticsTTSBuilder(),
    "azure": AzureTTSBuilder(),
    "fish": FishTTSBuilder(),
    "hume": HumeTTSBuilder(),
    "inworld": InworldTTSBuilder(),
    "lmnt": LmntTTSBuilder(),
    "resemble": ResembleTTSBuilder(),
}
