"""Standalone smoke test for the tone RAG pipeline.

Ingests a PDF and runs a set of retrieval queries against it, using the real
OpenAIEmbedder together with the InMemoryVectorStore -- so it exercises the true
chunk -> embed -> retrieve path WITHOUT needing Postgres/pgvector.

Two ingestion modes:
  (default) production path : DoclingReader + DoclingHybridChunker  (matches prod)
  --fast                    : PyPDF2 CompositeReader + RecursiveCharacterChunker

Usage:
  ./venv/bin/python scripts/rag_pipeline_smoketest.py
  ./venv/bin/python scripts/rag_pipeline_smoketest.py --fast --top-k 3
  ./venv/bin/python scripts/rag_pipeline_smoketest.py --pdf some_other.pdf
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

import hashlib
import re
from typing import List

from core.services.rag.chunkers import DoclingHybridChunker, RecursiveCharacterChunker
from core.services.rag.embedders import Embedder, OpenAIEmbedder
from core.services.rag.pipeline import RAGPipeline
from core.services.rag.readers import DoclingReader, PdfReader
from core.services.rag.vector_stores.memory_store import InMemoryVectorStore


class LocalHFEmbedder(Embedder):
    """Real semantic embeddings from a local HuggingFace model (no API key).

    Uses sentence-transformers/all-MiniLM-L6-v2 via transformers + mean pooling.
    Downloads ~90MB on first run, then fully offline. A genuine stand-in for
    OpenAI embeddings to test *retrieval quality* while the OpenAI key is down.
    """

    MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    dimensions = 384

    def __init__(self):
        import torch
        from transformers import AutoModel, AutoTokenizer

        self._torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL)
        self.model = AutoModel.from_pretrained(self.MODEL)
        self.model.eval()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        torch = self._torch
        enc = self.tokenizer(texts, padding=True, truncation=True, max_length=256, return_tensors="pt")
        with torch.no_grad():
            out = self.model(**enc)
        mask = enc["attention_mask"].unsqueeze(-1).float()
        summed = (out.last_hidden_state * mask).sum(1)
        counts = mask.sum(1).clamp(min=1e-9)
        emb = torch.nn.functional.normalize(summed / counts, p=2, dim=1)
        return emb.tolist()


class HashingEmbedder(Embedder):
    """Deterministic, offline bag-of-words embedder (no API key needed).

    Hashes each word into a fixed-size vector. Cosine similarity then tracks
    lexical overlap -- good enough to validate pipeline plumbing and keyword
    retrieval without hitting OpenAI. NOT a substitute for real semantic search.
    """

    dimensions = 1536

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]

    def _embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dimensions
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            vec[h % self.dimensions] += 1.0
        return vec

DEFAULT_PDF = "Coral_Breeze_Resort_Knowledge_Base.pdf"
AGENT_ID = "smoke-test-agent"

# (spoken query, list of substrings that MUST appear in the retrieved chunks).
# Matching is case-insensitive; a query passes if ANY expected substring is found
# in the concatenated top-k chunk texts.
QUERIES = [
    ("What time is check-in?", ["3:00 PM", "3 PM"]),
    ("When do I have to check out?", ["11:00 AM", "11 AM"]),
    ("How much does the Presidential Villa cost per night?", ["2,200", "3,000"]),
    ("What is the cheapest room and its price?", ["Garden View", "350"]),
    ("What's the phone number for reservations?", ["555-0199"]),
    ("Where is the resort located?", ["Maui", "Hawaii", "Ocean Drive"]),
    ("Tell me about the fine dining restaurant.", ["Coral Table", "Pacific Rim"]),
    ("Does the Presidential Villa have a pool?", ["infinity pool"]),
    # Negative case: nothing in the doc should answer this well.
    ("Do you allow pet elephants in the rooms?", ["__no_expected_match__"]),
]


def build_pipeline(fast: bool, fake_embeddings: bool, local_embeddings: bool) -> RAGPipeline:
    if local_embeddings:
        embedder = LocalHFEmbedder()
    elif fake_embeddings:
        embedder = HashingEmbedder()
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            sys.exit("ERROR: OPENAI_API_KEY not set (check .env)")
        embedder = OpenAIEmbedder(api_key)
    store = InMemoryVectorStore()
    if fast:
        # PyPDF2 reader directly -- CompositeReader routes PDFs through Docling.
        reader, chunker = PdfReader(), RecursiveCharacterChunker()
    else:
        reader, chunker = DoclingReader(), DoclingHybridChunker()
    return RAGPipeline(embedder=embedder, store=store, reader=reader, chunker=chunker)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default=DEFAULT_PDF)
    parser.add_argument("--fast", action="store_true", help="use PyPDF2 reader (skips heavy Docling)")
    parser.add_argument("--fake-embeddings", action="store_true", help="offline deterministic bag-of-words embedder (no OpenAI key)")
    parser.add_argument("--local-embeddings", action="store_true", help="real local HF semantic embedder MiniLM (no OpenAI key)")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        sys.exit(f"ERROR: PDF not found: {args.pdf}")

    with open(args.pdf, "rb") as f:
        pdf_bytes = f.read()

    mode = "FAST (PyPDF2)" if args.fast else "PRODUCTION (Docling)"
    if args.local_embeddings:
        embed = "Local MiniLM (real semantic, offline)"
    elif args.fake_embeddings:
        embed = "HASHING (offline)"
    else:
        embed = "OpenAI text-embedding-3-small"
    print(f"\n=== RAG pipeline smoke test ===")
    print(f"PDF   : {args.pdf} ({len(pdf_bytes) / 1024:.1f} KB)")
    print(f"Reader: {mode}   Embedder: {embed}   top_k={args.top_k}\n")

    pipeline = build_pipeline(args.fast, args.fake_embeddings, args.local_embeddings)

    # --- Ingest ---
    t0 = time.monotonic()
    n_chunks = pipeline.ingest_file(pdf_bytes, "application/pdf", metadata={"agent_id": AGENT_ID})
    ingest_s = time.monotonic() - t0
    print(f"Ingested {n_chunks} chunks in {ingest_s:.1f}s")
    if n_chunks == 0:
        print("FAIL: no chunks were produced from the PDF")
        return 1
    print()

    # --- Retrieve + score ---
    passed = 0
    total = 0
    for query, expected in QUERIES:
        is_negative = expected == ["__no_expected_match__"]
        results = pipeline.retrieve(query, top_k=args.top_k, filters={"agent_id": AGENT_ID})
        blob = "\n".join(r.text for r in results).lower()
        hit = None if is_negative else next((e for e in expected if e.lower() in blob), None)

        if is_negative:
            # Informational only: we just report the top score/distance.
            top = f"{results[0].score:.3f}" if results else "n/a"
            print(f"[info] {query!r}\n        top distance={top} (negative/no-answer case)")
            continue

        total += 1
        ok = hit is not None
        passed += ok
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {query!r}")
        if ok:
            print(f"        matched {hit!r} (top distance={results[0].score:.3f})")
        else:
            preview = results[0].text[:120].replace(chr(10), " ") if results else "<no results>"
            print(f"        expected one of {expected} -- top chunk: {preview!r}")

    print(f"\n=== {passed}/{total} retrieval assertions passed ===\n")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
