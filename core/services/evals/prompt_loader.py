"""Prompt loader — single source of truth for the eval prompts.

Prompts live on disk under ``rag-testing/prompts/`` so they stay editable as
plain markdown and can be diffed in git without a DB migration. The loader is
resilient to being called from either the backend (``python main.py``) or the
CLI (``python rag-testing/scripts/...``) — both resolve the same directory."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_PROMPTS_DIR = _REPO_ROOT / "rag-testing" / "prompts"


class PromptLoader:
    def __init__(self, prompts_dir: Optional[Path] = None):
        self._dir = prompts_dir or _DEFAULT_PROMPTS_DIR

    def load(self, name: str) -> str:
        path = self._dir / name
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text()

    def hash(self, name: str) -> str:
        """SHA-256 of the prompt text — stamped onto ``evals.generation_prompt_hash``
        so a prompt edit is auditable without storing the prompt body per row."""
        return hashlib.sha256(self.load(name).encode("utf-8")).hexdigest()


def render_prompt(template: str, **values: str) -> str:
    """Simple ``{{VAR}}`` substitution — matches the CLI convention."""
    out = template
    for key, val in values.items():
        out = out.replace("{{" + key + "}}", val)
    return out
