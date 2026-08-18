from __future__ import annotations

import random
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import ClassVar, List, Optional

import openai
from loguru import logger

# Import each Google submodule independently — a partial install (e.g. missing
# google-api-core but working google-genai) shouldn't silently zero every
# reference and hide the real cause. Each import stays None if unavailable,
# and GoogleEmbedder raises a clear RuntimeError when the pieces it needs are
# missing.
try:
    from google import genai as google_genai
except ImportError:  # pragma: no cover — SDK is in requirements.txt
    google_genai = None

try:
    from google.genai import types as google_genai_types
except ImportError:  # pragma: no cover
    google_genai_types = None

try:
    from google.api_core import exceptions as google_api_exceptions
except ImportError:  # pragma: no cover
    google_api_exceptions = None

try:
    import tiktoken

    _ENCODING = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENCODING = None


def _count_tokens(texts: List[str]) -> int:
    if _ENCODING is None:
        return sum(len(t) // 4 + 1 for t in texts)
    return sum(len(_ENCODING.encode(t)) for t in texts)


class _TokenRateLimiter:
    def __init__(self, tokens_per_minute: int):
        self.limit = tokens_per_minute
        self.window = 60.0
        self._events: deque = deque()
        self._used = 0
        self._lock = threading.Lock()

    def acquire(self, tokens: int) -> None:
        with self._lock:
            while True:
                now = time.monotonic()
                while self._events and now - self._events[0][0] >= self.window:
                    self._used -= self._events.popleft()[1]
                if self._used + tokens <= self.limit or not self._events:
                    self._events.append((time.monotonic(), tokens))
                    self._used += tokens
                    return
                time.sleep(max(0.0, self.window - (now - self._events[0][0])))


_LIMITERS: dict = {}
_LIMITERS_LOCK = threading.Lock()


def _get_limiter(tokens_per_minute: int) -> _TokenRateLimiter:
    with _LIMITERS_LOCK:
        limiter = _LIMITERS.get(tokens_per_minute)
        if limiter is None:
            limiter = _TokenRateLimiter(tokens_per_minute)
            _LIMITERS[tokens_per_minute] = limiter
        return limiter


@dataclass(frozen=True)
class EmbeddingMetadata:
    """Identity of the model that produced an embedding — stamped into every
    stored record so retrieval can verify the query embedder matches."""

    provider: str
    model: str
    dimensions: int
    version: Optional[str] = None


class Embedder(ABC):
    provider: ClassVar[str] = ""
    dimensions: int = 0
    model: str = ""
    version: Optional[str] = None

    @property
    def metadata(self) -> EmbeddingMetadata:
        return EmbeddingMetadata(
            provider=self.provider,
            model=self.model,
            dimensions=self.dimensions,
            version=self.version,
        )

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        ...

    def embed_query(self, query: str) -> List[float]:
        return self.embed_texts([query])[0]


class OpenAIEmbedder(Embedder):
    provider: ClassVar[str] = "openai"
    MODEL = "text-embedding-3-small"
    dimensions = 1536

    def __init__(self, api_key: str, model: str = None, batch_size: int = 100,
                 max_retries: int = 6, tokens_per_minute: int = 900_000,
                 dimensions: Optional[int] = None):
        self.api_key = api_key
        self.model = model or self.MODEL
        self.batch_size = batch_size
        self.max_retries = max_retries
        self._limiter = _get_limiter(tokens_per_minute)
        if dimensions is not None:
            self.dimensions = dimensions

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        n = len(texts)
        logger.info(
            "[embed:openai] calling texts={} model={} batch_size={}",
            n, self.model, self.batch_size,
        )
        t_start = time.monotonic()
        client = openai.OpenAI(api_key=self.api_key, max_retries=self.max_retries)
        out: List[List[float]] = []
        try:
            for i in range(0, n, self.batch_size):
                batch = texts[i : i + self.batch_size]
                self._limiter.acquire(_count_tokens(batch))
                response = client.embeddings.create(model=self.model, input=batch)
                out.extend(item.embedding for item in response.data)
        except Exception:
            logger.exception(
                "[embed:openai] failed model={} texts={} completed_batches={}",
                self.model, n, len(out),
            )
            raise
        logger.info(
            "[embed:openai] generated {} embeddings (model={}, dimensions={}, elapsed_s={:.1f})",
            len(out), self.model, len(out[0]) if out else 0,
            time.monotonic() - t_start,
        )
        return out


class GoogleEmbedder(Embedder):
    """Google Gemini embedding provider.

    ``dimensions`` is required for every call site that cares about vector
    shape: the run row snapshots it and ``build_embedder_from_run`` passes it
    through. If a caller omits it we fall back to
    ``_MODEL_NATIVE_DIMENSIONS.get(model)`` (only ``gemini-embedding-001`` is
    catalogued today); an unknown model with no explicit dimensions is a
    hard error rather than a silently-wrong 3072.
    """

    provider: ClassVar[str] = "google"
    MODEL = "gemini-embedding-001"

    # Per-model native output size, used only when a caller doesn't pass an
    # explicit ``dimensions``. Extend this map as new Gemini models are
    # exposed in the UI; the run row is still the source of truth.
    _MODEL_NATIVE_DIMENSIONS = {
        "gemini-embedding-001": 3072,
        "gemini-embedding-2": 3072,
    }

    _TASK_TYPE_DOCUMENT = "RETRIEVAL_DOCUMENT"
    _TASK_TYPE_QUERY = "RETRIEVAL_QUERY"

    # Google-API-core exception classes we consider transient and worth
    # retrying. Built once at instantiation from whichever exceptions the
    # installed SDK version exposes — silently omits any that the SDK
    # doesn't ship rather than crashing on AttributeError.
    _RETRYABLE_EXC_NAMES = (
        "ResourceExhausted",
        "ServiceUnavailable",
        "InternalServerError",
        "DeadlineExceeded",
        "Aborted",
        "GatewayTimeout",
        "TooManyRequests",
    )

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        batch_size: int = 100,
        max_retries: int = 6,
        task_type: str = _TASK_TYPE_DOCUMENT,
    ):
        if google_genai is None or google_genai_types is None:
            raise RuntimeError(
                "google-genai SDK is not installed or partially available. "
                "Add `google-genai` to requirements.txt to use the Google "
                "embedding provider."
            )
        self.api_key = api_key
        self.model = model or self.MODEL
        resolved_dims = (
            dimensions
            if dimensions is not None
            else self._MODEL_NATIVE_DIMENSIONS.get(self.model)
        )
        if resolved_dims is None:
            raise ValueError(
                f"GoogleEmbedder: dimensions must be provided for model "
                f"{self.model!r} (no native default is catalogued)."
            )
        self.dimensions = resolved_dims
        self.batch_size = max(1, batch_size)
        self.max_retries = max(0, max_retries)
        self.task_type = task_type
        self._client = google_genai.Client(api_key=api_key)
        self._retryable_excs = self._resolve_retryable_excs()

    @classmethod
    def _resolve_retryable_excs(cls) -> tuple:
        if google_api_exceptions is None:
            return tuple()
        return tuple(
            exc for exc in (
                getattr(google_api_exceptions, name, None)
                for name in cls._RETRYABLE_EXC_NAMES
            )
            if exc is not None and isinstance(exc, type)
        )

    def _sleep_backoff(self, attempt: int) -> None:
        """Exponential backoff with full jitter — spreads retries across
        workers so a coordinated 429 storm doesn't reconverge in lockstep."""
        base = min(30.0, 2 ** attempt)
        time.sleep(random.uniform(0.0, base))

    def _embed_once(self, texts: List[str], task_type: str) -> List[List[float]]:
        """Single API call with retry. Assumes ``texts`` fits within the
        provider's per-request budget — callers are responsible for splitting
        on batch-level failures (see ``_embed_with_split``)."""
        config = google_genai_types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=self.dimensions,
        )
        attempt = 0
        while True:
            try:
                response = self._client.models.embed_content(
                    model=self.model,
                    contents=texts,
                    config=config,
                )
                break
            except Exception as exc:
                retryable = bool(self._retryable_excs) and isinstance(exc, self._retryable_excs)
                if not retryable or attempt >= self.max_retries:
                    raise
                logger.debug(
                    "[embed:google] retryable error attempt={} exc={} model={}",
                    attempt + 1, type(exc).__name__, self.model,
                )
                self._sleep_backoff(attempt)
                attempt += 1

        embeddings = response.embeddings or []
        vectors = [list(item.values or []) for item in embeddings]

        # Hard invariants — pipeline zips vectors with chunks and pgvector
        # columns are fixed-width. A silent length/dim mismatch would either
        # drop chunks or corrupt search, so fail loudly instead.
        if len(vectors) != len(texts):
            raise RuntimeError(
                f"[embed:google] response returned {len(vectors)} embeddings "
                f"for {len(texts)} inputs (model={self.model})"
            )
        for i, v in enumerate(vectors):
            if len(v) != self.dimensions:
                raise RuntimeError(
                    f"[embed:google] embedding at index {i} has {len(v)} "
                    f"dims, expected {self.dimensions} (model={self.model})"
                )
        return vectors

    def _embed_with_split(self, texts: List[str], task_type: str) -> List[List[float]]:
        """Call ``_embed_once``; on a non-retryable client-side failure
        (typically ``InvalidArgument`` when the batch's combined tokens
        exceed the provider's per-request budget) split the batch in half
        and retry each half. Isolates one oversized chunk from wrecking the
        whole batch. Falls back to raising if the batch is already a single
        item — that's a genuine oversize error the user has to see."""
        try:
            return self._embed_once(texts, task_type)
        except Exception as exc:
            if len(texts) <= 1:
                raise
            # Only split on likely-batch-size failures. Bare RuntimeErrors
            # from our own invariant checks aren't split-recoverable.
            is_client_err = google_api_exceptions is not None and isinstance(
                exc,
                (
                    getattr(google_api_exceptions, "InvalidArgument", ()),
                    getattr(google_api_exceptions, "BadRequest", ()),
                ),
            )
            if not is_client_err:
                raise
            mid = len(texts) // 2
            logger.warning(
                "[embed:google] batch of {} rejected ({}); splitting into "
                "{}+{} and retrying",
                len(texts), type(exc).__name__, mid, len(texts) - mid,
            )
            left = self._embed_with_split(texts[:mid], task_type)
            right = self._embed_with_split(texts[mid:], task_type)
            return left + right

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        n = len(texts)
        logger.info(
            "[embed:google] calling texts={} model={} batch_size={} dims={}",
            n, self.model, self.batch_size, self.dimensions,
        )
        t_start = time.monotonic()
        out: List[List[float]] = []
        try:
            for i in range(0, n, self.batch_size):
                batch = texts[i : i + self.batch_size]
                logger.debug(
                    "[embed:google] batch n={} model={} dims={}",
                    len(batch), self.model, self.dimensions,
                )
                out.extend(self._embed_with_split(batch, self.task_type))
        except Exception:
            logger.exception(
                "[embed:google] failed model={} texts={} completed={}",
                self.model, n, len(out),
            )
            raise
        # Same invariant as inside _embed_once but at the aggregate level —
        # RAGPipeline uses zip(chunks, embeddings); a mismatch here would
        # silently drop chunks.
        if len(out) != n:
            raise RuntimeError(
                f"[embed:google] produced {len(out)} embeddings for {n} inputs "
                f"(model={self.model})"
            )
        logger.info(
            "[embed:google] generated {} embeddings (model={}, dimensions={}, elapsed_s={:.1f})",
            len(out), self.model, len(out[0]) if out else 0,
            time.monotonic() - t_start,
        )
        return out

    def embed_query(self, query: str) -> List[float]:
        vectors = self._embed_with_split([query], self._TASK_TYPE_QUERY)
        # _embed_once already asserts len==1 and correct dims, but keep this
        # explicit so a future refactor of _embed_with_split can't silently
        # return an empty vector to pgvector (which would raise a confusing
        # dim-mismatch error at retrieval time).
        if not vectors or len(vectors[0]) != self.dimensions:
            raise RuntimeError(
                f"[embed:google] embed_query returned no usable vector "
                f"(model={self.model}, dimensions={self.dimensions})"
            )
        return vectors[0]
