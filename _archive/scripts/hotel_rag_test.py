#!/usr/bin/env python
"""Standalone RAG diagnostic for the Tone Hotel Assistant Agent — NO STT / NO TTS.

Text question in -> retrieved chunks + grounded LLM answer out. It exercises the
REAL Tone RAG pipeline exactly as the voice agent does at call time
(``document_tool_service`` -> OpenAI query embedding -> pgvector cosine search on
the live DB -> LLM answer grounded in the retrieved context) but with the
microphone and speaker removed. STT (Deepgram/Parakeet) and TTS (Cartesia) are
NOT imported or exercised here — they are tested separately via the tone-test
voice suites.

It is READ-ONLY: it only SELECTs from the existing ``knowledge_base_chunks`` — it
never ingests, writes, or deletes anything in the shared DB.

What it reports, per canonical hotel question:
  * agent-scoped retrieval@k  — what the LIVE agent actually retrieves (all KBs
    attached to the agent's published config), then a grounded answer + hit/miss.
  * (--per-kb) the same, broken down per attached knowledge base, so you can see
    which KB answers and which dilutes retrieval.

Usage:
  cd ~/Desktop/tone
  PYTHONPATH=. ./venv/bin/python scripts/hotel_rag_test.py
  PYTHONPATH=. ./venv/bin/python scripts/hotel_rag_test.py --per-kb
  PYTHONPATH=. ./venv/bin/python scripts/hotel_rag_test.py --agent-id <uuid> --top-k 8
  PYTHONPATH=. ./venv/bin/python scripts/hotel_rag_test.py --no-llm   # retrieval only (no OpenAI chat cost)
"""
from __future__ import annotations

import argparse
import os
import sys

# Load .env WITHOUT python-dotenv's find_dotenv (which asserts on some shells);
# read the repo-root .env directly and only fill missing keys.
_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_ENV_PATH):
    for _line in open(_ENV_PATH):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

from sqlalchemy import text

from core.database.session import get_db_context
from core.services.rag.embedders import OpenAIEmbedder
from core.services.rag.vector_stores.pgvector_store import PgVectorStore

# Production feeds the LLM the top-8 chunks (DEFAULT_TOP_K in
# core/services/document_tool_service.py). Diagnose at the same K.
DEFAULT_TOP_K = 8

# The Hotel Assistant Agent in org "Sunny" (parandhama.reddy@trytone.ai).
DEFAULT_AGENT_ID = "f8e20d72-4799-4094-b7dc-4d49f45c8f98"

# Canonical facts from Coral_Breeze_Resort_Knowledge_Base.pdf (the clean KB).
# (question, [answer substrings, ANY of which counts as correct — case-insensitive])
QUESTIONS = [
    ("What time is check-in?", ["3:00 pm", "3 pm"]),
    ("What time is check-out?", ["11:00 am", "11 am"]),
    ("How much is the Presidential Villa per night?", ["2,200", "3,000"]),
    ("What is the cheapest room and its price?", ["garden view", "350"]),
    ("What is the phone number for reservations?", ["555-0199"]),
    ("Where is the resort located?", ["maui", "hawaii", "ocean drive"]),
    ("Tell me about the fine dining restaurant.", ["coral table", "pacific rim"]),
    ("Does the Presidential Villa have a pool?", ["infinity pool"]),
]

GROUNDING_SYSTEM = (
    "You are the front-desk assistant for Coral Breeze Resort. Answer the guest's "
    "question using ONLY the information in the provided knowledge-base context. "
    "If the answer is not in the context, say you don't have that information. "
    "Be concise (one or two sentences)."
)


def get_agent_uploads(agent_id: str):
    """Return [(knowledge_base_name, upload_id, chunk_count), ...] for an agent."""
    sql = text(
        """
        SELECT kb.name, kb.upload_id, count(c.id) AS chunks
        FROM agent_knowledge_bases akb
        JOIN knowledge_bases kb ON kb.id = akb.knowledge_base_id
        JOIN uploads u ON u.id = kb.upload_id
        LEFT JOIN knowledge_base_chunks c ON c.upload_id = kb.upload_id
        WHERE akb.agent_id = :aid
        GROUP BY kb.name, kb.upload_id
        ORDER BY chunks DESC
        """
    )
    with get_db_context() as db:
        return [(r[0], str(r[1]), r[2]) for r in db.execute(sql, {"aid": agent_id}).all()]


def answer_with_llm(question: str, chunks) -> str:
    import openai

    context = "\n\n---\n\n".join(c.text for c in chunks) or "(no context retrieved)"
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": GROUNDING_SYSTEM},
            {"role": "user", "content": f"Knowledge base context:\n{context}\n\nGuest question: {question}"},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


def evaluate(label, embedder, store, filters, top_k, use_llm):
    print(f"\n{'=' * 70}\n{label}\n{'=' * 70}")
    retrieval_hits = 0
    answer_hits = 0
    for question, expected in QUESTIONS:
        results = store.query(embedder.embed_query(question), top_k=top_k, filters=filters)
        blob = "\n".join(r.text for r in results).lower()
        r_hit = any(e in blob for e in expected)
        retrieval_hits += r_hit
        top = f"{results[0].score:.3f}" if results else "n/a"

        line = f"[retrieval {'HIT ' if r_hit else 'MISS'}] {question!r}  (top_dist={top}, n={len(results)})"
        if use_llm:
            answer = answer_with_llm(question, results)
            a_hit = any(e in answer.lower() for e in expected)
            answer_hits += a_hit
            line = f"[answer {'PASS' if a_hit else 'FAIL'} | retrieval {'HIT ' if r_hit else 'MISS'}] {question!r}"
            print(line)
            print(f"        expected one of {expected}")
            print(f"        answer: {answer!r}")
        else:
            print(line)

    n = len(QUESTIONS)
    print(f"\n  retrieval recall@{top_k}: {retrieval_hits}/{n}")
    if use_llm:
        print(f"  grounded-answer accuracy: {answer_hits}/{n}")
    return retrieval_hits, (answer_hits if use_llm else None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent-id", default=DEFAULT_AGENT_ID)
    ap.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    ap.add_argument("--per-kb", action="store_true", help="also break results down per attached knowledge base")
    ap.add_argument("--no-llm", action="store_true", help="retrieval only; skip the grounded-answer generation")
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("ERROR: OPENAI_API_KEY not set (checked env and repo .env)")

    use_llm = not args.no_llm
    embedder = OpenAIEmbedder(os.environ["OPENAI_API_KEY"])
    store = PgVectorStore()

    uploads = get_agent_uploads(args.agent_id)
    print(f"Agent {args.agent_id} has {len(uploads)} knowledge base(s):")
    for name, uid, n in uploads:
        print(f"  - {name}  (upload={uid}, {n} chunks)")
    if not uploads:
        sys.exit("Agent has no knowledge bases attached — nothing to test.")

    # 1) What the LIVE agent actually retrieves (all KBs, via published config).
    evaluate(
        "AGENT-SCOPED  (live retrieval — every KB attached to the agent)",
        embedder, store, {"agent_id": args.agent_id}, args.top_k, use_llm,
    )

    # 2) Per-KB breakdown to expose which KB answers vs dilutes.
    if args.per_kb:
        for name, uid, n in uploads:
            evaluate(
                f"KB: {name}  ({n} chunks, upload={uid})",
                embedder, store, {"upload_id": uid}, args.top_k, use_llm,
            )

    print("\nDone. (No STT/TTS involved; read-only against the live KB.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
