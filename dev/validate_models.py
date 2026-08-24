"""
Validate models/voices in ``dev/dev-data.json`` against each provider's live
model catalog.

For every LLM / STT / TTS provider we ship, this script fetches the
authoritative model list from the provider's public ``/models`` endpoint
(or, for providers with no such endpoint, scrapes their published docs page)
and diffs it against the models we seed. It also validates TTS voice
catalogues and pings each provider's base URL for basic reachability.

Usage::

    python dev/validate_models.py                  # everything
    python dev/validate_models.py --category llm   # llm | stt | tts
    python dev/validate_models.py --provider openai
    python dev/validate_models.py --no-voices      # skip TTS voice diff
    python dev/validate_models.py --json           # machine-readable output
    python dev/validate_models.py --verbose        # per-voice rows too

Exit code is non-zero if any DEPRECATED or UNREACHABLE rows are found so this
can be wired into CI.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, ClassVar
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# ── Paths / env ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEV_DATA_PATH = Path(__file__).resolve().parent / "dev-data.json"
load_dotenv(PROJECT_ROOT / ".env")

console = Console()

HTTP_TIMEOUT = httpx.Timeout(20.0, connect=10.0)


# ── Domain types ────────────────────────────────────────────────────────────
class Status(str, Enum):
    OK = "OK"
    DEPRECATED = "DEPRECATED"
    NEW_UPSTREAM = "NEW_UPSTREAM"
    UNREACHABLE = "UNREACHABLE"
    SKIP_NO_KEY = "SKIP: no key"
    SKIP_UNSUPPORTED = "SKIP: no adapter"
    SKIP_DOCS = "SKIP: docs unparseable"


@dataclass
class ModelRow:
    name: str
    status: Status
    note: str = ""


@dataclass
class DiffResult:
    matched: set[str] = field(default_factory=set)
    deprecated: set[str] = field(default_factory=set)   # local - upstream
    new_upstream: set[str] = field(default_factory=set)  # upstream - local


@dataclass
class ProviderReport:
    category: str
    provider: str
    reachable: bool | None = None            # None = skipped
    reachability_note: str = ""
    model_rows: list[ModelRow] = field(default_factory=list)
    voice_diff: DiffResult | None = None
    voice_error: str = ""
    fetch_error: str = ""

    @property
    def has_failure(self) -> bool:
        if self.reachable is False:
            return True
        if any(r.status == Status.DEPRECATED for r in self.model_rows):
            return True
        if self.voice_diff and self.voice_diff.deprecated:
            return True
        return False


# ── Core diff (reused for both models and voices) ───────────────────────────
def diff_catalog(local: set[str], remote: set[str]) -> DiffResult:
    return DiffResult(
        matched=local & remote,
        deprecated=local - remote,
        new_upstream=remote - local,
    )


def _matches_any(name: str, patterns: list[str]) -> bool:
    """Case-insensitive match — supports exact matches and simple ``*`` globs."""
    n = name.lower()
    for p in patterns:
        pl = p.lower()
        if "*" not in pl:
            if n == pl:
                return True
        else:
            # translate `*` to `.*`, anchor
            regex = "^" + re.escape(pl).replace(r"\*", ".*") + "$"
            if re.match(regex, n):
                return True
    return False


# ── ProviderCatalog ABC + factory registry ──────────────────────────────────
class ProviderCatalog(ABC):
    """One provider adapter. Subclasses register themselves via ``REGISTRY``."""

    provider_name: ClassVar[str]
    category: ClassVar[str]              # "llm" | "stt" | "tts"
    api_key_env: ClassVar[str | None] = None

    # A reachability URL — override when the base_url is ws:// / grpc:// / None.
    reachability_url: ClassVar[str | None] = None

    def __init__(self, provider_json: dict, client: httpx.AsyncClient) -> None:
        self.provider_json = provider_json
        self.client = client

    # --- utility helpers --------------------------------------------------
    def _api_key(self) -> str | None:
        if not self.api_key_env:
            return None
        return os.environ.get(self.api_key_env)

    def _local_model_names(self) -> set[str]:
        return {m["name"] for m in self.provider_json.get("models", [])}

    def _local_voice_ids(self) -> set[str]:
        return {v.get("voice_id") for v in self.provider_json.get("voices", []) if v.get("voice_id")}

    # --- extensibility hooks ---------------------------------------------
    async def fetch_models(self) -> set[str]:
        """Return the *canonical* set of model IDs supported upstream."""
        raise NotImplementedError

    async def fetch_voices(self) -> set[str] | None:
        """Return upstream voice IDs, or ``None`` if this provider has no voices."""
        return None

    async def check_reachable(self) -> tuple[bool, str]:
        """Ping the provider base — 2xx/3xx OR 401/403 counts as reachable."""
        url = self.reachability_url
        if not url:
            base = self._pick_http_base()
            if not base:
                return True, "no http base to probe"
            url = base
        try:
            resp = await self.client.request("GET", url, timeout=10.0)
        except (httpx.HTTPError, httpx.InvalidURL) as e:
            return False, f"{type(e).__name__}: {e}"
        # Any response from the server (even 401/403/404/405/etc.) proves the
        # host is reachable — a real outage looks like a transport error.
        if resp.status_code < 500:
            return True, f"HTTP {resp.status_code}"
        return False, f"HTTP {resp.status_code}"

    # --- helpers subclasses commonly need --------------------------------
    def _pick_http_base(self) -> str | None:
        for m in self.provider_json.get("models", []):
            b = m.get("base_url") or ""
            if b.startswith("http"):
                return b.rstrip("/")
        return None


REGISTRY: dict[tuple[str, str], type[ProviderCatalog]] = {}


def register(cls: type[ProviderCatalog]) -> type[ProviderCatalog]:
    """Decorator: register the adapter in the ``(category, provider_name)`` map."""
    REGISTRY[(cls.category, cls.provider_name)] = cls
    return cls


def get_catalog(
    category: str, provider_json: dict, client: httpx.AsyncClient
) -> ProviderCatalog | None:
    cls = REGISTRY.get((category, provider_json["name"]))
    if cls is None:
        return None
    return cls(provider_json, client)


# ── Shared base adapters (cover the majority of providers) ─────────────────
class OpenAICompatCatalog(ProviderCatalog):
    """Any ``GET {base}/models`` endpoint returning ``{"data":[{"id":...}]}``.

    Subclasses set ``models_url`` (or override ``_models_url``) and
    ``api_key_env`` and optionally ``model_filter`` to constrain the returned
    IDs (e.g. only whisper for STT).
    """

    models_url: ClassVar[str] = ""
    model_filter: ClassVar[Callable[[str], bool] | None] = None

    def _models_url(self) -> str:
        return self.models_url

    def _auth_headers(self) -> dict[str, str]:
        key = self._api_key() or ""
        return {"Authorization": f"Bearer {key}"} if key else {}

    async def fetch_models(self) -> set[str]:
        resp = await self.client.get(self._models_url(), headers=self._auth_headers(), timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        raw = data.get("data") or data.get("models") or []
        ids: set[str] = set()
        for m in raw:
            mid = m.get("id") or m.get("name") or m.get("model")
            if not mid:
                continue
            if self.model_filter and not self.model_filter(mid):
                continue
            ids.add(mid)
        return ids


@register
class AnthropicCatalog(ProviderCatalog):
    provider_name = "anthropic"
    category = "llm"
    api_key_env = "ANTHROPIC_API_KEY"
    reachability_url = "https://api.anthropic.com/v1/models"

    async def fetch_models(self) -> set[str]:
        key = self._api_key() or ""
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
        resp = await self.client.get(
            "https://api.anthropic.com/v1/models", headers=headers, timeout=HTTP_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
        return {m["id"] for m in data.get("data", []) if m.get("id")}


@register
class GoogleGenAICatalog(ProviderCatalog):
    """Gemini via Google Generative Language REST API."""

    provider_name = "google"
    category = "llm"
    api_key_env = "GOOGLE_API_KEY"
    reachability_url = "https://generativelanguage.googleapis.com/v1beta/models"

    _endpoint = "https://generativelanguage.googleapis.com/v1beta/models"

    async def _paged_models(self) -> list[dict]:
        key = self._api_key() or ""
        page_token: str | None = None
        out: list[dict] = []
        while True:
            params: dict[str, str] = {"key": key, "pageSize": "100"}
            if page_token:
                params["pageToken"] = page_token
            resp = await self.client.get(self._endpoint, params=params, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
            out.extend(payload.get("models", []))
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
        return out

    @staticmethod
    def _short(name: str) -> str:
        """``models/gemini-2.5-flash`` → ``gemini-2.5-flash``."""
        return name.split("/", 1)[1] if "/" in name else name

    async def fetch_models(self) -> set[str]:
        models = await self._paged_models()
        return {self._short(m["name"]) for m in models if m.get("name")}


# ── Simple HTML/docs helpers ────────────────────────────────────────────────
async def _fetch_text(client: httpx.AsyncClient, url: str) -> str:
    resp = await client.get(url, timeout=HTTP_TIMEOUT, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def _scrape_ids(text: str, patterns: list[str]) -> set[str]:
    """Return every non-overlapping match of any given regex in ``text``."""
    found: set[str] = set()
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            found.add(m.group(0))
    return found


# ── Provider adapters ═══════════════════════════════════════════════════════
# ── LLM providers ───────────────────────────────────────────────────────────
@register
class OpenAILLMCatalog(OpenAICompatCatalog):
    provider_name = "openai"
    category = "llm"
    api_key_env = "OPENAI_API_KEY"
    models_url = "https://api.openai.com/v1/models"
    reachability_url = "https://api.openai.com/v1/models"


@register
class OpenAIRealtimeCatalog(OpenAICompatCatalog):
    """Realtime models are a filtered subset of the OpenAI /models list."""

    provider_name = "openai_realtime"
    category = "llm"
    api_key_env = "OPENAI_API_KEY"
    models_url = "https://api.openai.com/v1/models"
    reachability_url = "https://api.openai.com/v1/models"

    @staticmethod
    def _is_realtime(model_id: str) -> bool:
        return "realtime" in model_id.lower()

    model_filter = _is_realtime


@register
class GroqLLMCatalog(OpenAICompatCatalog):
    provider_name = "groq"
    category = "llm"
    api_key_env = "GROQ_API_KEY"
    models_url = "https://api.groq.com/openai/v1/models"
    reachability_url = "https://api.groq.com/openai/v1/models"


@register
class DeepSeekCatalog(OpenAICompatCatalog):
    provider_name = "deepseek"
    category = "llm"
    api_key_env = "DEEPSEEK_API_KEY"
    models_url = "https://api.deepseek.com/v1/models"
    reachability_url = "https://api.deepseek.com/v1/models"


@register
class GrokCatalog(OpenAICompatCatalog):
    provider_name = "grok"
    category = "llm"
    api_key_env = "GROK_API_KEY"
    models_url = "https://api.x.ai/v1/models"
    reachability_url = "https://api.x.ai/v1/models"


@register
class OpenRouterCatalog(OpenAICompatCatalog):
    provider_name = "openrouter"
    category = "llm"
    api_key_env = None                  # public endpoint, no auth needed
    models_url = "https://openrouter.ai/api/v1/models"
    reachability_url = "https://openrouter.ai/api/v1/models"

    async def fetch_models(self) -> set[str]:                 # noqa: D401 – simple override
        # No auth needed; parent expects auth headers otherwise.
        resp = await self.client.get(self.models_url, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return {m["id"] for m in resp.json().get("data", []) if m.get("id")}


@register
class CerebrasCatalog(OpenAICompatCatalog):
    provider_name = "cerebras"
    category = "llm"
    api_key_env = "CEREBRAS_API_KEY"
    models_url = "https://api.cerebras.ai/v1/models"
    reachability_url = "https://api.cerebras.ai/v1/models"


@register
class PerplexityCatalog(OpenAICompatCatalog):
    provider_name = "perplexity"
    category = "llm"
    api_key_env = "PERPLEXITY_API_KEY"
    # Perplexity historically did not publish a /models endpoint. Try it and
    # if we get a 404, fall back to the published model list.
    models_url = "https://api.perplexity.ai/models"
    reachability_url = "https://api.perplexity.ai"

    _KNOWN_MODELS: ClassVar[set[str]] = {
        "sonar", "sonar-pro", "sonar-reasoning", "sonar-reasoning-pro",
        "sonar-deep-research",
    }

    async def fetch_models(self) -> set[str]:
        try:
            return await super().fetch_models()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 405):
                return set(self._KNOWN_MODELS)
            raise


@register
class QwenCatalog(OpenAICompatCatalog):
    provider_name = "qwen"
    category = "llm"
    api_key_env = "QWEN_API_KEY"
    models_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/models"
    reachability_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/models"


@register
class NvidiaNimCatalog(OpenAICompatCatalog):
    provider_name = "nvidia_nim"
    category = "llm"
    api_key_env = "NVIDIA_API_KEY"
    models_url = "https://integrate.api.nvidia.com/v1/models"
    reachability_url = "https://integrate.api.nvidia.com/v1/models"


@register
class CohereCatalog(ProviderCatalog):
    provider_name = "cohere"
    category = "llm"
    api_key_env = "COHERE_API_KEY"
    reachability_url = "https://api.cohere.com/v1/models"

    async def fetch_models(self) -> set[str]:
        key = self._api_key() or ""
        headers = {"Authorization": f"Bearer {key}"}
        resp = await self.client.get(
            "https://api.cohere.com/v1/models",
            headers=headers,
            params={"page_size": "1000"},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        return {m["name"] for m in resp.json().get("models", []) if m.get("name")}


@register
class GeminiLiveCatalog(ProviderCatalog):
    """Gemini Live models are a subset of Google GenAI models."""

    provider_name = "gemini_live"
    category = "llm"
    api_key_env = "GOOGLE_API_KEY"
    reachability_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def fetch_models(self) -> set[str]:
        adapter = GoogleGenAICatalog(self.provider_json, self.client)
        all_models = await adapter.fetch_models()
        # Live is exposed via names containing "live"
        return {m for m in all_models if "live" in m.lower()}


@register
class AzureLLMCatalog(ProviderCatalog):
    """Azure OpenAI has no public global model list — deployments are per-resource.

    We compare against a hand-maintained allowlist of currently-supported base
    models. Update this list when Azure publishes/retires a base model.
    Reference: https://learn.microsoft.com/azure/ai-services/openai/concepts/models
    """

    provider_name = "azure"
    category = "llm"
    api_key_env = None
    reachability_url = None

    _ALLOWLIST: ClassVar[set[str]] = {
        # GPT-5 family
        "gpt-5", "gpt-5-mini", "gpt-5-nano",
        # GPT-4.1 / 4o / o-series
        "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
        "gpt-4o", "gpt-4o-mini",
        "o1", "o1-mini", "o3", "o3-mini", "o4-mini",
        # legacy
        "gpt-4-turbo", "gpt-35-turbo",
    }

    async def check_reachable(self) -> tuple[bool, str]:
        return True, "static allowlist"

    async def fetch_models(self) -> set[str]:
        return set(self._ALLOWLIST)


# AWS Bedrock uses boto3 (not httpx) — keys via AWS_* env vars.
@register
class AWSBedrockCatalog(ProviderCatalog):
    provider_name = "aws_bedrock"
    category = "llm"
    api_key_env = "AWS_ACCESS_KEY_ID"
    reachability_url = None

    async def check_reachable(self) -> tuple[bool, str]:
        return True, "boto3-driven"

    async def fetch_models(self) -> set[str]:
        try:
            import boto3                                                     # noqa: WPS433 – lazy import
        except ImportError:
            return set()

        def _list() -> set[str]:
            region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
            client = boto3.client("bedrock", region_name=region)
            resp = client.list_foundation_models()
            return {m["modelId"] for m in resp.get("modelSummaries", []) if m.get("modelId")}

        return await asyncio.to_thread(_list)


# ── STT providers ───────────────────────────────────────────────────────────
@register
class DeepgramSTTCatalog(ProviderCatalog):
    provider_name = "deepgram"
    category = "stt"
    api_key_env = "DEEPGRAM_API_KEY"
    reachability_url = "https://api.deepgram.com/v1/models"

    async def _fetch_public(self) -> dict:
        key = self._api_key() or ""
        headers = {"Authorization": f"Token {key}"}
        resp = await self.client.get(
            "https://api.deepgram.com/v1/models",
            headers=headers,
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    async def fetch_models(self) -> set[str]:
        data = await self._fetch_public()
        return {m.get("canonical_name") or m.get("name") for m in data.get("stt", []) if m}


@register
class OpenAISTTCatalog(OpenAICompatCatalog):
    provider_name = "openai"
    category = "stt"
    api_key_env = "OPENAI_API_KEY"
    models_url = "https://api.openai.com/v1/models"
    reachability_url = "https://api.openai.com/v1/models"

    @staticmethod
    def _is_stt(model_id: str) -> bool:
        m = model_id.lower()
        return "whisper" in m or "transcribe" in m

    model_filter = _is_stt


@register
class GroqSTTCatalog(OpenAICompatCatalog):
    provider_name = "groq"
    category = "stt"
    api_key_env = "GROQ_API_KEY"
    models_url = "https://api.groq.com/openai/v1/models"
    reachability_url = "https://api.groq.com/openai/v1/models"

    @staticmethod
    def _is_stt(model_id: str) -> bool:
        return "whisper" in model_id.lower()

    model_filter = _is_stt


@register
class ElevenLabsSTTCatalog(ProviderCatalog):
    """ElevenLabs exposes STT models via ``/v1/models`` (models with ``can_do_stt``)."""

    provider_name = "elevenlabs"
    category = "stt"
    api_key_env = "ELEVENLABS_API_KEY"
    reachability_url = "https://api.elevenlabs.io/v1/models"

    async def fetch_models(self) -> set[str]:
        key = self._api_key() or ""
        headers = {"xi-api-key": key}
        resp = await self.client.get(
            "https://api.elevenlabs.io/v1/models", headers=headers, timeout=HTTP_TIMEOUT
        )
        resp.raise_for_status()
        # Older responses have no can_do_stt flag; ElevenLabs currently ships
        # `scribe_v1` and `scribe_v1_experimental` — treat any model with
        # "scribe" in its id as STT.
        return {m["model_id"] for m in resp.json() if m.get("model_id") and "scribe" in m["model_id"].lower()}


@register
class CartesiaSTTCatalog(ProviderCatalog):
    provider_name = "cartesia"
    category = "stt"
    api_key_env = "CARTESIA_API_KEY"
    reachability_url = "https://api.cartesia.ai/"

    _KNOWN: ClassVar[set[str]] = {"ink-whisper", "ink-whisper-english", "ink-whisper-multilingual"}

    async def fetch_models(self) -> set[str]:
        # Cartesia does not publish a public STT model catalog endpoint.
        return set(self._KNOWN)


@register
class NvidiaSTTCatalog(ProviderCatalog):
    """NVIDIA Riva STT models are exposed via NGC; treat the dev-data list as
    authoritative until NGC publishes a stable public catalog endpoint."""

    provider_name = "nvidia"
    category = "stt"
    api_key_env = "NVIDIA_API_KEY"
    reachability_url = "https://integrate.api.nvidia.com/v1/models"

    async def fetch_models(self) -> set[str]:
        return self._local_model_names()


@register
class AssemblyAISTTCatalog(ProviderCatalog):
    provider_name = "assemblyai"
    category = "stt"
    api_key_env = "ASSEMBLYAI_API_KEY"
    reachability_url = "https://api.assemblyai.com"

    _KNOWN: ClassVar[set[str]] = {"universal", "best", "nano", "universal-streaming"}

    async def fetch_models(self) -> set[str]:
        return set(self._KNOWN)


@register
class SonioxSTTCatalog(ProviderCatalog):
    provider_name = "soniox"
    category = "stt"
    api_key_env = "SONIOX_API_KEY"
    reachability_url = "https://api.soniox.com"

    _KNOWN: ClassVar[set[str]] = {
        "stt-async-preview", "stt-rt-preview", "stt-rt-preview-v2", "stt-async-preview-v2",
    }

    async def fetch_models(self) -> set[str]:
        return set(self._KNOWN)


@register
class SarvamSTTCatalog(ProviderCatalog):
    provider_name = "sarvam"
    category = "stt"
    api_key_env = "SARVAM_API_KEY"
    reachability_url = "https://api.sarvam.ai"

    _KNOWN: ClassVar[set[str]] = {"saarika:v2", "saarika:v2.5", "saaras:v2"}

    async def fetch_models(self) -> set[str]:
        return set(self._KNOWN)


@register
class GladiaSTTCatalog(ProviderCatalog):
    provider_name = "gladia"
    category = "stt"
    api_key_env = "GLADIA_API_KEY"
    reachability_url = "https://api.gladia.io"

    _KNOWN: ClassVar[set[str]] = {"solaria-1", "solaria-mini-1"}

    async def fetch_models(self) -> set[str]:
        return set(self._KNOWN)


@register
class SpeechmaticsSTTCatalog(ProviderCatalog):
    provider_name = "speechmatics"
    category = "stt"
    api_key_env = "SPEECHMATICS_API_KEY"
    reachability_url = "https://asr.api.speechmatics.com"

    _KNOWN: ClassVar[set[str]] = {"enhanced", "standard", "ursa"}

    async def fetch_models(self) -> set[str]:
        return set(self._KNOWN)


@register
class GoogleCloudSTTCatalog(ProviderCatalog):
    """Google Cloud Speech-to-Text — no public model list REST endpoint.

    Allowlist reflects models documented at
    https://cloud.google.com/speech-to-text/docs/transcription-model as of Aug 2026.
    """

    provider_name = "google"
    category = "stt"
    api_key_env = None
    reachability_url = "https://speech.googleapis.com"

    _ALLOWLIST: ClassVar[set[str]] = {
        "chirp_2", "chirp_3", "chirp", "latest_long", "latest_short",
        "telephony", "telephony_short", "medical_conversation", "medical_dictation", "default",
    }

    async def fetch_models(self) -> set[str]:
        return set(self._ALLOWLIST)


@register
class AzureSTTCatalog(ProviderCatalog):
    provider_name = "azure"
    category = "stt"
    api_key_env = None
    reachability_url = None

    _ALLOWLIST: ClassVar[set[str]] = {"latest", "en-US-Standard", "en-US-Neural"}

    async def check_reachable(self) -> tuple[bool, str]:
        return True, "static allowlist"

    async def fetch_models(self) -> set[str]:
        return set(self._ALLOWLIST)


# ── TTS providers ───────────────────────────────────────────────────────────
@register
class DeepgramTTSCatalog(ProviderCatalog):
    provider_name = "deepgram"
    category = "tts"
    api_key_env = "DEEPGRAM_API_KEY"
    reachability_url = "https://api.deepgram.com/v1/models"

    async def _fetch_public(self) -> dict:
        key = self._api_key() or ""
        headers = {"Authorization": f"Token {key}"}
        resp = await self.client.get(
            "https://api.deepgram.com/v1/models",
            headers=headers,
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    async def fetch_models(self) -> set[str]:
        data = await self._fetch_public()
        return {m.get("canonical_name") or m.get("name") for m in data.get("tts", []) if m}

    async def fetch_voices(self) -> set[str] | None:
        data = await self._fetch_public()
        # Deepgram voice IDs look like "aura-2-thalia-en" and appear as
        # `canonical_name` on each tts entry — but every tts row IS a voice.
        return {m.get("canonical_name") or m.get("name") for m in data.get("tts", []) if m}


@register
class CartesiaTTSCatalog(ProviderCatalog):
    provider_name = "cartesia"
    category = "tts"
    api_key_env = "CARTESIA_API_KEY"
    reachability_url = "https://api.cartesia.ai/"

    _MODEL_ALLOWLIST: ClassVar[set[str]] = {"sonic-3", "sonic-2", "sonic-turbo", "sonic"}

    async def fetch_models(self) -> set[str]:
        return set(self._MODEL_ALLOWLIST)

    async def fetch_voices(self) -> set[str] | None:
        key = self._api_key() or ""
        headers = {"X-API-Key": key, "Cartesia-Version": "2024-06-10"}
        # Cartesia paginates voices — fetch until exhausted.
        voices: set[str] = set()
        params: dict[str, str] = {"limit": "100"}
        while True:
            resp = await self.client.get(
                "https://api.cartesia.ai/voices",
                headers=headers,
                params=params,
                timeout=HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            payload = resp.json()
            data = payload if isinstance(payload, list) else payload.get("data", [])
            for v in data:
                if v.get("id"):
                    voices.add(v["id"])
            next_page = None if isinstance(payload, list) else payload.get("next_page")
            if not next_page:
                break
            params["starting_after"] = next_page
        return voices


@register
class ElevenLabsTTSCatalog(ProviderCatalog):
    provider_name = "elevenlabs"
    category = "tts"
    api_key_env = "ELEVENLABS_API_KEY"
    reachability_url = "https://api.elevenlabs.io/v1/models"

    async def fetch_models(self) -> set[str]:
        key = self._api_key() or ""
        headers = {"xi-api-key": key}
        resp = await self.client.get(
            "https://api.elevenlabs.io/v1/models", headers=headers, timeout=HTTP_TIMEOUT
        )
        resp.raise_for_status()
        return {m["model_id"] for m in resp.json() if m.get("model_id") and m.get("can_do_text_to_speech", True)}

    async def fetch_voices(self) -> set[str] | None:
        key = self._api_key() or ""
        headers = {"xi-api-key": key}
        voices: set[str] = set()
        params: dict[str, str] = {"page_size": "100"}
        while True:
            resp = await self.client.get(
                "https://api.elevenlabs.io/v2/voices",
                headers=headers,
                params=params,
                timeout=HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            payload = resp.json()
            for v in payload.get("voices", []):
                if v.get("voice_id"):
                    voices.add(v["voice_id"])
            if not payload.get("has_more"):
                break
            params["next_page_token"] = payload.get("next_page_token") or ""
            if not params["next_page_token"]:
                break
        return voices


@register
class OpenAITTSCatalog(OpenAICompatCatalog):
    provider_name = "openai"
    category = "tts"
    api_key_env = "OPENAI_API_KEY"
    models_url = "https://api.openai.com/v1/models"
    reachability_url = "https://api.openai.com/v1/models"

    @staticmethod
    def _is_tts(model_id: str) -> bool:
        return "tts" in model_id.lower() or "audio" in model_id.lower()

    model_filter = _is_tts

    # OpenAI voice list is a small fixed set exposed only via docs.
    _VOICE_ALLOWLIST: ClassVar[set[str]] = {
        "alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova",
        "sage", "shimmer", "verse",
    }

    async def fetch_voices(self) -> set[str] | None:
        return set(self._VOICE_ALLOWLIST)


@register
class GroqTTSCatalog(OpenAICompatCatalog):
    provider_name = "groq"
    category = "tts"
    api_key_env = "GROQ_API_KEY"
    models_url = "https://api.groq.com/openai/v1/models"
    reachability_url = "https://api.groq.com/openai/v1/models"

    @staticmethod
    def _is_tts(model_id: str) -> bool:
        return "tts" in model_id.lower() or "playai" in model_id.lower()

    model_filter = _is_tts


@register
class MinimaxTTSCatalog(ProviderCatalog):
    provider_name = "minimax"
    category = "tts"
    api_key_env = "MINIMAX_API_KEY"
    reachability_url = "https://api.minimax.io"

    _MODELS: ClassVar[set[str]] = {
        "speech-2.5-hd-preview", "speech-2.5-turbo-preview",
        "speech-02-hd", "speech-02-turbo",
        "speech-01-hd", "speech-01-turbo",
    }

    async def fetch_models(self) -> set[str]:
        return set(self._MODELS)


@register
class RimeTTSCatalog(ProviderCatalog):
    provider_name = "rime"
    category = "tts"
    api_key_env = "RIME_API_KEY"
    reachability_url = "https://users.rime.ai"

    _MODELS: ClassVar[set[str]] = {"mistv2", "arcana", "mist"}

    async def fetch_models(self) -> set[str]:
        return set(self._MODELS)

    async def fetch_voices(self) -> set[str] | None:
        # Rime publishes a JSON voice catalogue.
        try:
            resp = await self.client.get(
                "https://users.rime.ai/data/voices/all-2.0.json", timeout=HTTP_TIMEOUT
            )
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError:
            return None
        voices: set[str] = set()
        # Payload is model → language → [voices]; each voice has a `name`.
        for model_voices in payload.values() if isinstance(payload, dict) else []:
            if isinstance(model_voices, dict):
                for lang_voices in model_voices.values():
                    if isinstance(lang_voices, list):
                        for v in lang_voices:
                            if isinstance(v, dict) and v.get("name"):
                                voices.add(v["name"])
                            elif isinstance(v, str):
                                voices.add(v)
        return voices


@register
class SarvamTTSCatalog(ProviderCatalog):
    provider_name = "sarvam"
    category = "tts"
    api_key_env = "SARVAM_API_KEY"
    reachability_url = "https://api.sarvam.ai"

    _MODELS: ClassVar[set[str]] = {"bulbul:v2", "bulbul:v1"}

    async def fetch_models(self) -> set[str]:
        return set(self._MODELS)


@register
class FishTTSCatalog(ProviderCatalog):
    provider_name = "fish"
    category = "tts"
    api_key_env = "FISHER_API_KEY"
    reachability_url = "https://api.fish.audio"

    _MODELS: ClassVar[set[str]] = {"speech-1.6", "speech-1.5", "s1", "s1-mini"}

    async def fetch_models(self) -> set[str]:
        return set(self._MODELS)


@register
class InworldTTSCatalog(ProviderCatalog):
    provider_name = "inworld"
    category = "tts"
    api_key_env = "INWORLD_API_KEY"
    reachability_url = "https://api.inworld.ai"

    _MODELS: ClassVar[set[str]] = {"inworld-tts-1", "inworld-tts-1-max"}

    async def fetch_models(self) -> set[str]:
        return set(self._MODELS)


@register
class ResembleTTSCatalog(ProviderCatalog):
    provider_name = "resemble"
    category = "tts"
    api_key_env = "RESEMBLE_API_KEY"
    reachability_url = "https://f.cluster.resemble.ai"

    _MODELS: ClassVar[set[str]] = {"resemble-v3", "resemble-v2"}

    async def fetch_models(self) -> set[str]:
        return set(self._MODELS)


@register
class NvidiaTTSCatalog(ProviderCatalog):
    provider_name = "nvidia"
    category = "tts"
    api_key_env = "NVIDIA_API_KEY"
    reachability_url = "https://integrate.api.nvidia.com/v1/models"

    async def fetch_models(self) -> set[str]:
        return self._local_model_names()


@register
class NeuphonicTTSCatalog(ProviderCatalog):
    provider_name = "neuphonic"
    category = "tts"
    api_key_env = "NEUPHONIC_API_KEY"
    reachability_url = "https://api.neuphonic.com"

    _MODELS: ClassVar[set[str]] = {"neu_hq", "neu_fast"}

    async def fetch_models(self) -> set[str]:
        return set(self._MODELS)


@register
class LmntTTSCatalog(ProviderCatalog):
    provider_name = "lmnt"
    category = "tts"
    api_key_env = "LMNT_API_KEY"
    reachability_url = "https://api.lmnt.com"

    _MODELS: ClassVar[set[str]] = {"blizzard", "aurora"}

    async def fetch_models(self) -> set[str]:
        return set(self._MODELS)


@register
class AsyncAITTSCatalog(ProviderCatalog):
    provider_name = "asyncai_http"
    category = "tts"
    api_key_env = "ASYNC_API_KEY"
    reachability_url = "https://api.async.ai"

    async def fetch_models(self) -> set[str]:
        return self._local_model_names()


@register
class AWSPollyTTSCatalog(ProviderCatalog):
    provider_name = "aws_polly"
    category = "tts"
    api_key_env = "AWS_ACCESS_KEY_ID"
    reachability_url = None

    async def check_reachable(self) -> tuple[bool, str]:
        return True, "boto3-driven"

    async def fetch_models(self) -> set[str]:
        # Polly "engines" == our concept of models.
        return {"generative", "long-form", "neural", "standard"}

    async def fetch_voices(self) -> set[str] | None:
        try:
            import boto3                                                    # noqa: WPS433
        except ImportError:
            return None

        def _list() -> set[str]:
            region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
            client = boto3.client("polly", region_name=region)
            out: set[str] = set()
            resp = client.describe_voices()
            while True:
                for v in resp.get("Voices", []):
                    if v.get("Id"):
                        out.add(v["Id"])
                token = resp.get("NextToken")
                if not token:
                    break
                resp = client.describe_voices(NextToken=token)
            return out

        return await asyncio.to_thread(_list)


@register
class GoogleCloudTTSCatalog(ProviderCatalog):
    provider_name = "google"
    category = "tts"
    api_key_env = None
    reachability_url = "https://texttospeech.googleapis.com"

    _ALLOWLIST: ClassVar[set[str]] = {"chirp3-hd", "neural2", "wavenet", "standard", "studio"}

    async def fetch_models(self) -> set[str]:
        return set(self._ALLOWLIST)


@register
class AzureTTSCatalog(ProviderCatalog):
    provider_name = "azure"
    category = "tts"
    api_key_env = None
    reachability_url = None

    _ALLOWLIST: ClassVar[set[str]] = {
        "neural", "neural-hd", "expressive", "en-US-JennyNeural", "en-US-AriaNeural",
    }

    async def check_reachable(self) -> tuple[bool, str]:
        return True, "static allowlist"

    async def fetch_models(self) -> set[str]:
        return set(self._ALLOWLIST)


@register
class SpeechmaticsTTSCatalog(ProviderCatalog):
    provider_name = "speechmatics"
    category = "tts"
    api_key_env = "SPEECHMATICS_API_KEY"
    reachability_url = "https://asr.api.speechmatics.com"

    async def fetch_models(self) -> set[str]:
        return self._local_model_names()


# ── Driver / reporter ═══════════════════════════════════════════════════════
async def _validate_provider(
    category: str, provider_json: dict, client: httpx.AsyncClient, check_voices: bool
) -> ProviderReport:
    name = provider_json["name"]
    report = ProviderReport(category=category, provider=name)

    catalog = get_catalog(category, provider_json, client)
    if catalog is None:
        report.model_rows = [
            ModelRow(m["name"], Status.SKIP_UNSUPPORTED, "no adapter registered")
            for m in provider_json.get("models", [])
        ]
        return report

    # Reachability
    reachable, note = await catalog.check_reachable()
    report.reachable = reachable
    report.reachability_note = note

    # If we require an API key but it's missing, mark every row as SKIP.
    if catalog.api_key_env and not catalog._api_key():
        report.model_rows = [
            ModelRow(m["name"], Status.SKIP_NO_KEY, f"${catalog.api_key_env} not set")
            for m in provider_json.get("models", [])
        ]
        return report

    if not reachable:
        report.model_rows = [
            ModelRow(m["name"], Status.UNREACHABLE, note)
            for m in provider_json.get("models", [])
        ]
        return report

    # Fetch upstream models
    try:
        upstream = await catalog.fetch_models()
    except Exception as e:                                                # noqa: BLE001 – any failure
        report.fetch_error = f"{type(e).__name__}: {e}"
        report.model_rows = [
            ModelRow(m["name"], Status.SKIP_DOCS, report.fetch_error)
            for m in provider_json.get("models", [])
        ]
        return report

    local = catalog._local_model_names()
    diff = diff_catalog(local, upstream)
    rows: list[ModelRow] = []
    for m in sorted(local):
        rows.append(
            ModelRow(m, Status.OK if m in diff.matched else Status.DEPRECATED)
        )
    for m in sorted(diff.new_upstream):
        rows.append(ModelRow(m, Status.NEW_UPSTREAM))
    report.model_rows = rows

    # Voices (TTS only, and only if requested)
    if check_voices and category == "tts":
        try:
            upstream_voices = await catalog.fetch_voices()
        except Exception as e:                                            # noqa: BLE001
            report.voice_error = f"{type(e).__name__}: {e}"
            upstream_voices = None
        if upstream_voices is not None:
            local_voices = catalog._local_voice_ids()
            report.voice_diff = diff_catalog(local_voices, upstream_voices)

    return report


def _render_terminal(reports: list[ProviderReport], verbose: bool) -> None:
    total_deprecated = 0
    total_unreachable = 0

    for r in reports:
        heading = f"[bold cyan]{r.category.upper()} · {r.provider}[/]"
        if r.reachable is False:
            heading += f"  [bold red](UNREACHABLE: {r.reachability_note})[/]"
            total_unreachable += 1
        elif r.reachable is True:
            heading += f"  [dim]({r.reachability_note})[/]"

        if r.fetch_error:
            heading += f"  [red]fetch error: {r.fetch_error}[/]"

        console.rule(heading, style="cyan")

        # Models table
        tbl = Table(show_header=True, header_style="bold")
        tbl.add_column("Model", overflow="fold")
        tbl.add_column("Status")
        tbl.add_column("Note", overflow="fold")
        for row in r.model_rows:
            style = {
                Status.OK: "green",
                Status.DEPRECATED: "bold red",
                Status.NEW_UPSTREAM: "yellow",
                Status.UNREACHABLE: "bold red",
                Status.SKIP_NO_KEY: "dim",
                Status.SKIP_UNSUPPORTED: "dim",
                Status.SKIP_DOCS: "dim",
            }[row.status]
            tbl.add_row(row.name, f"[{style}]{row.status.value}[/]", row.note)
            if row.status == Status.DEPRECATED:
                total_deprecated += 1
        console.print(tbl)

        # Voices summary
        if r.voice_diff is not None:
            vd = r.voice_diff
            total = len(vd.matched) + len(vd.deprecated)
            console.print(
                f"[bold]Voices:[/] {len(vd.matched)}/{total} matched, "
                f"[red]{len(vd.deprecated)} deprecated[/], "
                f"[yellow]{len(vd.new_upstream)} new upstream[/]"
            )
            if verbose and vd.deprecated:
                console.print("  [red]Deprecated voice IDs:[/]")
                for v in sorted(vd.deprecated):
                    console.print(f"    • {v}")
            if verbose and vd.new_upstream:
                console.print("  [yellow]New upstream voice IDs (first 20):[/]")
                for v in sorted(vd.new_upstream)[:20]:
                    console.print(f"    • {v}")
            if vd.deprecated:
                total_deprecated += len(vd.deprecated)
        elif r.category == "tts" and r.voice_error:
            console.print(f"[dim]Voices: fetch error — {r.voice_error}[/]")

    console.rule("[bold]Summary[/]", style="magenta")
    console.print(
        f"Providers scanned: {len(reports)}   "
        f"Deprecated entries: [red]{total_deprecated}[/]   "
        f"Unreachable providers: [red]{total_unreachable}[/]"
    )


def _render_json(reports: list[ProviderReport]) -> None:
    payload = []
    for r in reports:
        payload.append(
            {
                "category": r.category,
                "provider": r.provider,
                "reachable": r.reachable,
                "reachability_note": r.reachability_note,
                "fetch_error": r.fetch_error,
                "models": [
                    {"name": row.name, "status": row.status.value, "note": row.note}
                    for row in r.model_rows
                ],
                "voices": (
                    None
                    if r.voice_diff is None
                    else {
                        "matched": sorted(r.voice_diff.matched),
                        "deprecated": sorted(r.voice_diff.deprecated),
                        "new_upstream": sorted(r.voice_diff.new_upstream),
                    }
                ),
                "voice_error": r.voice_error,
            }
        )
    print(json.dumps(payload, indent=2))


# ── Entry point ─────────────────────────────────────────────────────────────
CATEGORY_MAP = {
    "llm": "llm_providers",
    "stt": "stt_providers",
    "tts": "tts_providers",
}


def _load_providers(category: str | None, provider: str | None) -> list[tuple[str, dict]]:
    data = json.loads(DEV_DATA_PATH.read_text())
    out: list[tuple[str, dict]] = []
    for cat_short, cat_long in CATEGORY_MAP.items():
        if category and category != cat_short:
            continue
        for p in data.get(cat_long, []):
            if provider and p["name"] != provider:
                continue
            out.append((cat_short, p))
    return out


async def _main_async(args: argparse.Namespace) -> int:
    providers = _load_providers(args.category, args.provider)
    if not providers:
        console.print("[red]No providers matched the given filters.[/]")
        return 2

    async with httpx.AsyncClient(follow_redirects=True) as client:
        coros = [
            _validate_provider(cat, p, client, check_voices=not args.no_voices)
            for cat, p in providers
        ]
        reports = await asyncio.gather(*coros)

    if args.json:
        _render_json(reports)
    else:
        _render_terminal(reports, verbose=args.verbose)

    return 1 if any(r.has_failure for r in reports) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--category", choices=list(CATEGORY_MAP.keys()), help="Only validate one category")
    parser.add_argument("--provider", help="Only validate one provider (by name)")
    parser.add_argument("--no-voices", action="store_true", help="Skip TTS voice diff")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of the terminal table")
    parser.add_argument("--verbose", action="store_true", help="Show per-voice deprecated/new lists")
    args = parser.parse_args()
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    sys.exit(main())
