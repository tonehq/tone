"""``DeepEvalBaseLLM`` adapter that routes judge calls through Tone's shared
LLM router (``chat_complete``) so the org's existing encrypted provider keys
work unchanged.

DeepEval metrics call ``model.generate(prompt)`` (sync) or
``model.a_generate(prompt)`` (async). We forward both to ``chat_complete``,
which infers the provider from the model prefix. The async path runs the
sync SDK call in a worker thread — DeepEval's asyncio use is fine with
that and it avoids per-provider async client duplication.
"""

from __future__ import annotations

# Fire the DeepEval telemetry opt-out BEFORE any ``deepeval`` import in this
# module so direct submodule imports don't leak PostHog/Sentry beacons or
# install ``nest_asyncio`` before opt-out. ``opt_out`` is idempotent.
from core.services.evals.deepeval.telemetry import opt_out as _opt_out

_opt_out()

import asyncio  # noqa: E402

from deepeval.models.base_model import DeepEvalBaseLLM  # noqa: E402

from core.services.llm.chat_complete import chat_complete  # noqa: E402


class ToneDeepEvalLLM(DeepEvalBaseLLM):
    """DeepEval judge LLM backed by Tone's router.

    ``temperature=0.0`` is pinned so metric scores are reproducible across
    eval runs — the compare view relies on stable-ish scores to distinguish
    signal from noise.
    """

    def __init__(self, *, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    # DeepEval calls this to construct the underlying client; we don't need
    # one (chat_complete manages its own) so we just return self.
    def load_model(self):
        return self

    def generate(self, prompt: str) -> str:
        return chat_complete(
            model=self._model,
            api_key=self._api_key,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            json_mode=False,
        )

    async def a_generate(self, prompt: str) -> str:
        return await asyncio.to_thread(self.generate, prompt)

    def get_model_name(self) -> str:
        return self._model
