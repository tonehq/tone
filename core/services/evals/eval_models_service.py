"""LLM model catalog for the Evaluation Settings UI.

Powers the generation / answer model dropdowns on the Evaluations settings
page. Intentionally limited to OpenAI and Google (Gemini) providers because
these are the two families the RAG evaluation pipeline has been validated
against.

Transport-agnostic: takes a SQLAlchemy session, returns plain dicts. No HTTP
concepts leak in. Callers (HTTP router, CLI, background job) are expected to
translate any raised exception into their own transport error.
"""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from core.models.model import Model
from core.models.model_provider import ModelProvider

# The two provider ids (``ModelProvider.provider_id``, the natural slug — not
# the DB UUID) exposed in the eval-settings dropdowns. Kept as a module-level
# constant so the router / tests / future callers can import and reuse the
# same allowlist instead of re-defining it.
EVAL_MODEL_PROVIDER_IDS: tuple[str, ...] = ("openai", "google")


class EvalModelsService:
    """Read-only catalog of LLM models offered on the Evaluations settings
    page. There is no write path — model rows are managed by the Services
    admin (``ModelProviderService``); this service only projects the subset
    the eval UI consumes."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_llm_options(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return active LLM models grouped by provider id for the dropdowns.

        Shape:

            {
              "providers": [
                {"provider_id": "openai", "display_name": "OpenAI"},
                {"provider_id": "google", "display_name": "Google"},
              ],
              "models": [
                {"provider_id": "openai", "provider_display_name": "OpenAI",
                 "name": "gpt-4o", "display_name": "GPT-4o"},
                ...
              ],
            }

        Only ``kind == "llm"`` + active provider + active model rows are
        returned so a disabled model can't be picked as a generation / answer
        model. Sorted by provider then model name for stable UI ordering.
        """
        # Case-insensitive provider_id match — the DB column has no lowercase
        # constraint, and admins creating providers via the Services admin
        # can type e.g. "OpenAI". func.lower() lets those rows resolve too.
        rows = (
            self._db.query(
                Model.name,
                Model.display_name,
                ModelProvider.provider_id,
                ModelProvider.display_name.label("provider_display_name"),
            )
            .join(ModelProvider, ModelProvider.id == Model.provider_id)
            .filter(
                Model.kind == "llm",
                Model.is_active.is_(True),
                ModelProvider.is_active.is_(True),
                func.lower(ModelProvider.provider_id).in_(EVAL_MODEL_PROVIDER_IDS),
            )
            .order_by(ModelProvider.provider_id.asc(), Model.name.asc())
            .all()
        )

        providers_seen: Dict[str, str] = {}
        models: List[Dict[str, Any]] = []
        for row in rows:
            providers_seen.setdefault(row.provider_id, row.provider_display_name)
            models.append(
                {
                    "provider_id": row.provider_id,
                    "provider_display_name": row.provider_display_name,
                    "name": row.name,
                    "display_name": row.display_name or row.name,
                }
            )

        providers = [
            {"provider_id": pid, "display_name": pname}
            for pid, pname in providers_seen.items()
        ]
        return {"providers": providers, "models": models}
