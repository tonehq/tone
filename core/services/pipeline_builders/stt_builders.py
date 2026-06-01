from __future__ import annotations

from typing import Any

from core.services.pipeline_builders.base import BuildContext, STTBuilder, build_input_params


class DeepgramSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from deepgram import LiveOptions
        from pipecat.services.deepgram.stt import DeepgramSTTService
        dg_kwargs = {}
        if ctx.metadata.get("sample_rate") is not None:
            dg_kwargs["sample_rate"] = ctx.metadata["sample_rate"]
        live_options = None
        if ctx.metadata.get("language"):
            live_options = LiveOptions(language=ctx.metadata["language"])
        return DeepgramSTTService(api_key=ctx.api_key, live_options=live_options, **dg_kwargs)


class OpenAISTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.openai.stt import OpenAISTTService
        return OpenAISTTService(
            api_key=ctx.api_key,
            model=ctx.model or "gpt-4o-transcribe",
            language=ctx.metadata.get("language"),
            prompt=ctx.metadata.get("prompt"),
            temperature=ctx.metadata.get("temperature"),
        )


class GroqSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.groq.stt import GroqSTTService
        return GroqSTTService(
            api_key=ctx.api_key,
            model=ctx.model or "whisper-large-v3-turbo",
            language=ctx.metadata.get("language"),
            prompt=ctx.metadata.get("prompt"),
            temperature=ctx.metadata.get("temperature"),
        )


class AzureSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.azure.stt import AzureSTTService
        region = ctx.model_meta.get("region") or ctx.metadata.get("region") or "eastus"
        azure_kwargs = {}
        if ctx.metadata.get("language") is not None:
            azure_kwargs["language"] = ctx.metadata["language"]
        if ctx.metadata.get("sample_rate") is not None:
            azure_kwargs["sample_rate"] = ctx.metadata["sample_rate"]
        if ctx.metadata.get("endpoint_id") is not None:
            azure_kwargs["endpoint_id"] = ctx.metadata["endpoint_id"]
        return AzureSTTService(api_key=ctx.api_key, region=region, **azure_kwargs)


class GoogleSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.google.stt import GoogleSTTService
        return GoogleSTTService(credentials=ctx.api_key, params=build_input_params(GoogleSTTService, ctx.metadata))


class NvidiaSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.nvidia.stt import NvidiaSTTService
        return NvidiaSTTService(api_key=ctx.api_key, params=build_input_params(NvidiaSTTService, ctx.metadata))


class SarvamSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.sarvam.stt import SarvamSTTService
        return SarvamSTTService(
            api_key=ctx.api_key,
            model=ctx.model or "saarika:v2.5",
            sample_rate=ctx.metadata.get("sample_rate"),
            params=build_input_params(SarvamSTTService, ctx.metadata),
        )


class SpeechmaticsSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from core.services.speechmatics_stt import ToneSpeechmaticsSTTService
        if "turn_detection_mode" not in ctx.metadata:
            ctx.metadata["turn_detection_mode"] = "adaptive"
        if "operating_point" not in ctx.metadata:
            ctx.metadata["operating_point"] = "enhanced"
        if "max_delay" not in ctx.metadata:
            ctx.metadata["max_delay"] = 0.7
        return ToneSpeechmaticsSTTService(
            api_key=ctx.api_key,
            base_url="wss://us2.rt.speechmatics.com/v2",
            sample_rate=ctx.metadata.get("sample_rate"),
            params=build_input_params(ToneSpeechmaticsSTTService, ctx.metadata),
        )


class AssemblyAISTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.assemblyai.models import AssemblyAIConnectionParams
        from pipecat.services.assemblyai.stt import AssemblyAISTTService
        conn_kwargs = {}
        if ctx.metadata.get("sample_rate") is not None:
            conn_kwargs["sample_rate"] = ctx.metadata["sample_rate"]
        if ctx.metadata.get("word_finalization_max_wait_time") is not None:
            conn_kwargs["word_finalization_max_wait_time"] = ctx.metadata["word_finalization_max_wait_time"]
        if ctx.metadata.get("end_of_turn_confidence_threshold") is not None:
            conn_kwargs["end_of_turn_confidence_threshold"] = ctx.metadata["end_of_turn_confidence_threshold"]
        if ctx.metadata.get("speech_model") is not None:
            conn_kwargs["speech_model"] = ctx.metadata["speech_model"]
        asm_kwargs = {}
        if ctx.metadata.get("language") is not None:
            asm_kwargs["language"] = ctx.metadata["language"]
        if conn_kwargs:
            asm_kwargs["connection_params"] = AssemblyAIConnectionParams(**conn_kwargs)
        return AssemblyAISTTService(api_key=ctx.api_key, **asm_kwargs)


class CartesiaSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.cartesia.stt import CartesiaLiveOptions, CartesiaSTTService
        live_options = CartesiaLiveOptions(
            language=ctx.metadata.get("language") or "en",
            sample_rate=ctx.metadata.get("sample_rate") or 16000,
        )
        return CartesiaSTTService(
            api_key=ctx.api_key,
            sample_rate=ctx.metadata.get("sample_rate") or 16000,
            live_options=live_options,
        )


class ElevenLabsSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService
        return ElevenLabsRealtimeSTTService(api_key=ctx.api_key, model=ctx.model or "scribe_v2_realtime", params=build_input_params(ElevenLabsRealtimeSTTService, ctx.metadata))


class GladiaSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.gladia.stt import GladiaSTTService
        return GladiaSTTService(
            api_key=ctx.api_key,
            model=ctx.model or "solaria-1",
            region=ctx.metadata.get("region"),
            sample_rate=ctx.metadata.get("sample_rate"),
            params=build_input_params(GladiaSTTService, ctx.metadata),
        )


class SonioxSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.soniox.stt import SonioxSTTService
        return SonioxSTTService(api_key=ctx.api_key, params=build_input_params(SonioxSTTService, ctx.metadata))


class HathoraSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.hathora.stt import HathoraSTTService
        return HathoraSTTService(api_key=ctx.api_key, model=ctx.model or "parakeet", params=build_input_params(HathoraSTTService, ctx.metadata))


class SambaNovaSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.sambanova.stt import SambaNovaSTTService
        sn_kwargs = {}
        if ctx.metadata.get("language") is not None:
            sn_kwargs["language"] = ctx.metadata["language"]
        if ctx.metadata.get("prompt") is not None:
            sn_kwargs["prompt"] = ctx.metadata["prompt"]
        if ctx.metadata.get("temperature") is not None:
            sn_kwargs["temperature"] = ctx.metadata["temperature"]
        return SambaNovaSTTService(api_key=ctx.api_key, model=ctx.model or "Whisper-Large-v3", **sn_kwargs)


STT_BUILDERS = {
    "deepgram": DeepgramSTTBuilder(),
    "openai": OpenAISTTBuilder(),
    "groq": GroqSTTBuilder(),
    "azure": AzureSTTBuilder(),
    "google": GoogleSTTBuilder(),
    "nvidia": NvidiaSTTBuilder(),
    "sarvam": SarvamSTTBuilder(),
    "speechmatics": SpeechmaticsSTTBuilder(),
    "assemblyai": AssemblyAISTTBuilder(),
    "cartesia": CartesiaSTTBuilder(),
    "elevenlabs": ElevenLabsSTTBuilder(),
    "gladia": GladiaSTTBuilder(),
    "soniox": SonioxSTTBuilder(),
    "hathora": HathoraSTTBuilder(),
    "sambanova": SambaNovaSTTBuilder(),
}
