"""Regression tests for lazy-loading the heavy RAG parsing/chunking stack.

The API pod imports the parser/tokeniser *factories* (via
``knowledge_base_routes``) purely to expose the registries — it never parses or
chunks a document (the Procrastinate ingestion worker does). Historically the
factory import chain eagerly pulled docling + torch + transformers + chonkie
(and their transitive nltk / scikit-learn), costing ~1 GB of RSS in every API
pod and causing OOM.

These tests lock in the fix: importing the factories must NOT import the heavy
libraries, while the registries must stay fully populated so the actual parse /
chunk work (in the worker) is unaffected. The import-isolation check runs in a
fresh subprocess so it is hermetic regardless of what the outer test session
already imported.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

# Modules that must NOT be pulled in merely by importing the RAG factories.
# These are the packages the memory trace attributed to the eager import chain.
_HEAVY_MODULES = ["docling", "docling_core", "transformers", "torch", "chonkie", "nltk", "sklearn"]


def _import_isolation_check() -> subprocess.CompletedProcess:
    """Import the API-pod entry modules in a clean interpreter and report which
    heavy modules ended up in ``sys.modules``."""
    code = textwrap.dedent(
        f"""
        import sys
        # Exactly what the API pod loads via knowledge_base_routes: the two
        # registries. Nothing here should touch a real parse/chunk path.
        import core.services.rag.parser_factory  # noqa: F401
        import core.services.rag.tokeniser_factory  # noqa: F401
        leaked = [m for m in {_HEAVY_MODULES!r} if m in sys.modules]
        print("LEAKED:" + ",".join(leaked))
        """
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )


def test_importing_factories_does_not_load_heavy_stack():
    """Importing the parser/tokeniser factories (the API-pod path) must not
    drag docling / torch / transformers / chonkie into memory."""
    result = _import_isolation_check()
    if result.returncode != 0:
        # Environment can't import the app (missing base deps) — skip rather
        # than fail; this test is meaningful only where the app imports.
        pytest.skip(f"factory import failed in subprocess:\n{result.stderr}")

    line = next((l for l in result.stdout.splitlines() if l.startswith("LEAKED:")), None)
    assert line is not None, f"probe produced no LEAKED marker; stdout={result.stdout!r}"
    leaked = [m for m in line[len("LEAKED:"):].split(",") if m]
    assert leaked == [], (
        "Importing the RAG factories eagerly loaded heavy modules that belong "
        f"only in the ingestion worker: {leaked}. Keep docling/transformers/"
        "chonkie imports inside the reader/chunker methods that use them."
    )


def test_parser_registry_still_complete():
    """The lazy refactor must not shrink the parser registry — every parser the
    worker relies on must still resolve to a class."""
    from core.services.rag.parser_factory import PARSERS

    for slug in ("docling", "pypdf", "docx", "text", "composite"):
        assert slug in PARSERS, f"parser slug missing after lazy refactor: {slug}"


def test_tokeniser_registry_still_complete():
    """The lazy refactor must not shrink the tokeniser registry."""
    from core.services.rag.tokeniser_factory import TOKENISERS

    for slug in (
        "docling_hybrid",
        "recursive_char",
        "token_aware",
        "chonkie_recursive",
        "chonkie_sentence",
        "chonkie_semantic",
        "chonkie_sdpm",
    ):
        assert slug in TOKENISERS, f"tokeniser slug missing after lazy refactor: {slug}"
