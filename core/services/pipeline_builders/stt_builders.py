from __future__ import annotations

from typing import Any

from core.services.pipeline_builders.base import (
    BuildContext, STTBuilder, build_input_params,
    clean_meta, resolve_language_code,
)


class DeepgramSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from deepgram import LiveOptions
        from pipecat.services.deepgram.stt import DeepgramSTTService
        # Note: sample_rate is NOT user-configurable for Deepgram — it's
        # auto-detected by the transport (Twilio=8kHz, WebRTC=16kHz).
        # Setting it incorrectly breaks transcription.
        live_opts = {}
        if ctx.model:
            live_opts["model"] = ctx.model
        lang = resolve_language_code(ctx.metadata.get("language"))
        if lang:
            live_opts["language"] = lang
        live_options = LiveOptions(**live_opts) if live_opts else None
        return DeepgramSTTService(api_key=ctx.api_key, live_options=live_options)


class OpenAISTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.openai.stt import OpenAISTTService
        return OpenAISTTService(
            api_key=ctx.api_key,
            model=ctx.model or "gpt-4o-transcribe",
            language=resolve_language_code(ctx.metadata.get("language")),
            prompt=clean_meta(ctx.metadata, "prompt"),
            temperature=clean_meta(ctx.metadata, "temperature"),
        )


class GroqSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.groq.stt import GroqSTTService
        return GroqSTTService(
            api_key=ctx.api_key,
            model=ctx.model or "whisper-large-v3-turbo",
            language=resolve_language_code(ctx.metadata.get("language")),
            prompt=clean_meta(ctx.metadata, "prompt"),
            temperature=ctx.metadata.get("temperature"),
        )


class AzureSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.azure.stt import AzureSTTService
        region = clean_meta(ctx.metadata, "region") or ctx.model_meta.get("region") or "eastus"
        azure_kwargs = {}
        lang = resolve_language_code(ctx.metadata.get("language"))
        if lang:
            azure_kwargs["language"] = lang
        sample_rate = clean_meta(ctx.metadata, "sample_rate")
        if sample_rate is not None:
            azure_kwargs["sample_rate"] = int(sample_rate)
        endpoint_id = clean_meta(ctx.metadata, "endpoint_id")
        if endpoint_id:
            azure_kwargs["endpoint_id"] = endpoint_id
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
            model=ctx.model or "saaras:v3",
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
        sample_rate = clean_meta(ctx.metadata, "sample_rate")
        if sample_rate is not None:
            conn_kwargs["sample_rate"] = int(sample_rate)
        wfmwt = clean_meta(ctx.metadata, "word_finalization_max_wait_time")
        if wfmwt is not None:
            conn_kwargs["word_finalization_max_wait_time"] = int(wfmwt)
        eotct = clean_meta(ctx.metadata, "end_of_turn_confidence_threshold")
        if eotct is not None:
            conn_kwargs["end_of_turn_confidence_threshold"] = float(eotct)
        speech_model = clean_meta(ctx.metadata, "speech_model")
        if speech_model:
            conn_kwargs["speech_model"] = speech_model
        asm_kwargs = {}
        lang = resolve_language_code(ctx.metadata.get("language"))
        if lang:
            asm_kwargs["language"] = lang
        if conn_kwargs:
            asm_kwargs["connection_params"] = AssemblyAIConnectionParams(**conn_kwargs)
        return AssemblyAISTTService(api_key=ctx.api_key, **asm_kwargs)


class CartesiaSTTBuilder(STTBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.cartesia.stt import CartesiaLiveOptions, CartesiaSTTService
        sr = clean_meta(ctx.metadata, "sample_rate")
        sample_rate = int(sr) if sr else 16000
        live_opts = {
            "language": resolve_language_code(ctx.metadata.get("language")) or "en",
            "sample_rate": sample_rate,
        }
        if ctx.model:
            live_opts["model"] = ctx.model
        live_options = CartesiaLiveOptions(**live_opts)
        return CartesiaSTTService(
            api_key=ctx.api_key,
            sample_rate=sample_rate,
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
        lang = resolve_language_code(ctx.metadata.get("language"))
        if lang:
            sn_kwargs["language"] = lang
        prompt = clean_meta(ctx.metadata, "prompt")
        if prompt:
            sn_kwargs["prompt"] = prompt
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
