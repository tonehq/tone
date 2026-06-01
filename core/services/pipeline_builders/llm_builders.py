from __future__ import annotations

from typing import Any

from core.services.pipeline_builders.base import BuildContext, LLMBuilder, build_input_params


class OpenAILLMBuilder(LLMBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.openai.llm import OpenAILLMService
        return OpenAILLMService(api_key=ctx.api_key, model=ctx.model or "gpt-4.1", params=build_input_params(OpenAILLMService, ctx.metadata))


class AnthropicLLMBuilder(LLMBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.anthropic.llm import AnthropicLLMService
        if "enable_prompt_caching" not in ctx.metadata:
            ctx.metadata["enable_prompt_caching"] = True
        params = build_input_params(AnthropicLLMService, ctx.metadata)
        return AnthropicLLMService(api_key=ctx.api_key, model=ctx.model or "claude-haiku-4-5-20251001", params=params)


class GroqLLMBuilder(LLMBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.groq.llm import GroqLLMService
        return GroqLLMService(api_key=ctx.api_key, model=ctx.model or "llama-3.3-70b-versatile", params=build_input_params(GroqLLMService, ctx.metadata))


class OpenRouterLLMBuilder(LLMBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.openrouter.llm import OpenRouterLLMService
        return OpenRouterLLMService(api_key=ctx.api_key, model=ctx.model or "openai/gpt-4o-2024-11-20", params=build_input_params(OpenRouterLLMService, ctx.metadata))


class AWSBedrockLLMBuilder(LLMBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.aws.llm import AWSBedrockLLMService
        return AWSBedrockLLMService(api_key=ctx.api_key, model=ctx.model or "amazon.nova-pro-v1:0", params=build_input_params(AWSBedrockLLMService, ctx.metadata))


class GoogleLLMBuilder(LLMBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.google.llm import GoogleLLMService
        params = build_input_params(GoogleLLMService, ctx.metadata)
        return GoogleLLMService(api_key=ctx.api_key, model=ctx.model or "gemini-2.5-flash", params=params)


class OllamaLLMBuilder(LLMBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.ollama.llm import OLLamaLLMService
        base_url = ctx.api_key if ctx.api_key else "http://localhost:11434/v1"
        return OLLamaLLMService(model=ctx.model or "llama2", base_url=base_url, params=build_input_params(OLLamaLLMService, ctx.metadata))


class OpenAICompatibleLLMBuilder(LLMBuilder):
    DEFAULT_MODELS = {
        "azure": "gpt-4o",
        "cerebras": "llama-4-scout-17b-16e-instruct",
        "nvidia_nim": "meta/llama-3.1-8b-instruct",
        "fireworks": "accounts/fireworks/models/deepseek-v3p1",
        "together": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "perplexity": "sonar",
        "qwen": "qwen-turbo",
        "deepseek": "deepseek-chat",
        "mistral": "mistral-small-latest",
        "sambanova": "Meta-Llama-3.1-8B-Instruct",
        "grok": "grok-3",
    }
    DEFAULT_BASE_URLS = {
        "cerebras": "https://api.cerebras.ai/v1",
        "nvidia_nim": "https://integrate.api.nvidia.com/v1",
        "fireworks": "https://api.fireworks.ai/inference/v1",
        "together": "https://api.together.xyz/v1",
        "perplexity": "https://api.perplexity.ai",
        "qwen": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "deepseek": "https://api.deepseek.com/v1",
        "mistral": "https://api.mistral.ai/v1",
        "sambanova": "https://api.sambanova.ai/v1",
        "grok": "https://api.x.ai/v1",
    }

    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.openai.llm import BaseOpenAILLMService
        base_url = ctx.model_meta.get("base_url") or ctx.metadata.get("base_url")
        if not base_url:
            base_url = self.DEFAULT_BASE_URLS.get(ctx.provider_name)
        default_model = self.DEFAULT_MODELS.get(ctx.provider_name, "gpt-4o")
        return BaseOpenAILLMService(api_key=ctx.api_key, model=ctx.model or default_model, base_url=base_url, params=build_input_params(BaseOpenAILLMService, ctx.metadata))


class OpenAIRealtimeLLMBuilder(LLMBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.openai.realtime.events import (
            AudioConfiguration, AudioInput, AudioOutput,
            InputAudioTranscription, SemanticTurnDetection,
            SessionProperties)
        from pipecat.services.openai.realtime.llm import OpenAIRealtimeLLMService
        voice_id = ctx.metadata.get("voice_id")
        system_prompt = ctx.metadata.get("system_prompt")
        session_props = SessionProperties(
            audio=AudioConfiguration(
                input=AudioInput(
                    transcription=InputAudioTranscription(),
                    turn_detection=SemanticTurnDetection(),
                ),
                output=AudioOutput(voice=voice_id) if voice_id else None,
            ),
            instructions=system_prompt,
        )
        return OpenAIRealtimeLLMService(
            api_key=ctx.api_key,
            model=ctx.model or "gpt-4o-realtime-preview",
            session_properties=session_props,
        )


class GeminiLiveLLMBuilder(LLMBuilder):
    def build(self, ctx: BuildContext) -> Any:
        from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
        voice_id = ctx.metadata.get("voice_id") or "Puck"
        return GeminiLiveLLMService(
            api_key=ctx.api_key,
            model=ctx.model or "models/gemini-2.5-flash-native-audio-preview-12-2025",
            voice_id=voice_id,
            system_instruction=ctx.metadata.get("system_instruction"),
        )


LLM_BUILDERS = {
    "openai": OpenAILLMBuilder(),
    "anthropic": AnthropicLLMBuilder(),
    "groq": GroqLLMBuilder(),
    "openrouter": OpenRouterLLMBuilder(),
    "aws_bedrock": AWSBedrockLLMBuilder(),
    "google": GoogleLLMBuilder(),
    "ollama": OllamaLLMBuilder(),
    "openai_realtime": OpenAIRealtimeLLMBuilder(),
    "gemini_live": GeminiLiveLLMBuilder(),
}

_OPENAI_COMPATIBLE = OpenAICompatibleLLMBuilder()
for _name in ("azure", "cerebras", "nvidia_nim", "fireworks", "together", "perplexity", "qwen", "deepseek", "mistral", "sambanova", "grok"):
    LLM_BUILDERS[_name] = _OPENAI_COMPATIBLE
