"""End-to-end RAG evaluation runner.

For each question in `rag-testing/documents/<slug>/questions.json`:

1. Retrieve top-K chunks via `RAGPipeline.retrieve(..., filters={"upload_id": ...})`
   — same call shape as the production `read_document` tool.
2. Ask the answering LLM to answer using ONLY those chunks (prompt in
   `prompts/answer_from_context.md`).
3. Score with the LLM-as-judge (`judge.py`).
4. Compute `retrieval_hit`: does the expected_source_snippet appear (fuzzy) in
   the retrieved chunk text? Separates retrieval-side vs synthesis-side failures.

Writes `documents/<slug>/results/run-<ISO>.json` and prints a pass/fail table.

Usage:
    python rag-testing/scripts/run_eval.py --doc <slug>
    python rag-testing/scripts/run_eval.py --all
    python rag-testing/scripts/run_eval.py --doc <slug> --top-k 8 --answer-model gpt-4o --judge-model gpt-4o
"""
from __future__ import annotations

import argparse
import re
import sys
import time

from common import (
    DocMetadata,
    build_retrieval_pipeline,
    db_session,
    list_all_docs,
    load_questions,
    now_iso,
    openai_client,
    read_prompt,
    render_prompt,
    write_run_result,
)
from judge import judge_answer

_WORD_RE = re.compile(r"[a-z0-9]+")


def _normalize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _retrieval_hit(expected_snippet: str, retrieved_texts: list[str]) -> bool:
    """Fuzzy check: is a meaningful chunk of expected_snippet inside any retrieved text?

    Strategy: tokenize expected + each retrieved chunk, sliding window of the
    expected tokens (min 4) — pass if ≥70% of expected tokens appear in order
    inside any retrieved chunk's token stream.
    """
    if not expected_snippet or not expected_snippet.strip():
        return True  # negative/out-of-scope cases: no source expected

    exp = _normalize(expected_snippet)
    if not exp:
        return True

    if len(exp) < 4:
        joined = " ".join(_normalize(" ".join(retrieved_texts)))
        return " ".join(exp) in joined

    for text in retrieved_texts:
        toks = _normalize(text)
        if not toks:
            continue
        # count how many expected tokens appear (order-preserving greedy match)
        j = 0
        matched = 0
        for tok in toks:
            if j < len(exp) and tok == exp[j]:
                j += 1
                matched += 1
        if matched / len(exp) >= 0.7:
            return True
    return False


def _build_context(chunks: list[dict]) -> str:
    if not chunks:
        return "(no chunks retrieved)"
    parts = []
    for i, ch in enumerate(chunks, 1):
        parts.append(f"[chunk {i}] {ch['text']}")
    return "\n\n".join(parts)


def _generate_answer(*, client, model: str, question: str, chunks: list[dict]) -> str:
    template = read_prompt("answer_from_context.md")
    prompt = render_prompt(template, QUESTION=question, CONTEXT=_build_context(chunks))
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    return (resp.choices[0].message.content or "").strip()


def _run_one_doc(
    *,
    doc_slug: str,
    top_k: int,
    answer_model: str,
    judge_model: str,
) -> dict:
    meta = DocMetadata.load(doc_slug)
    qfile = load_questions(doc_slug)
    questions = qfile.get("questions", [])
    if not questions:
        raise RuntimeError(f"No questions in {doc_slug}/questions.json")

    print(f"\n[eval] doc={doc_slug} upload_id={meta.upload_id} questions={len(questions)}")
    client = openai_client()
    rows: list[dict] = []

    with db_session() as db:
        pipeline = build_retrieval_pipeline(db)

        for q in questions:
            qid = q.get("id", "?")
            question = q["question"]
            expected = q.get("expected_answer", "")
            expected_snippet = q.get("expected_source_snippet", "")
            category = q.get("category", "unknown")

            t0 = time.monotonic()
            try:
                results = pipeline.retrieve(
                    question, top_k=top_k, filters={"upload_id": meta.upload_id}
                )
                retrieved = [
                    {
                        "text": r.text,
                        "score": r.score,
                        "chunk_index": r.metadata.get("chunk_index"),
                        "upload_id": str(r.metadata.get("upload_id", "")),
                    }
                    for r in results
                ]
            except Exception as e:
                retrieved = []
                retrieval_error = f"{type(e).__name__}: {e}"
            else:
                retrieval_error = None

            hit = _retrieval_hit(expected_snippet, [c["text"] for c in retrieved])

            try:
                answer = _generate_answer(
                    client=client, model=answer_model, question=question, chunks=retrieved
                )
                answer_error = None
            except Exception as e:
                answer = ""
                answer_error = f"{type(e).__name__}: {e}"

            verdict = judge_answer(
                question=question,
                expected_answer=expected,
                actual_answer=answer,
                retrieved_chunks=retrieved,
                model=judge_model,
                client=client,
            )
            latency_ms = int((time.monotonic() - t0) * 1000)

            row = {
                "id": qid,
                "category": category,
                "question": question,
                "expected_answer": expected,
                "expected_source_snippet": expected_snippet,
                "retrieval_hit": hit,
                "retrieved_chunks": retrieved,
                "actual_answer": answer,
                "judge": verdict,
                "latency_ms": latency_ms,
                "retrieval_error": retrieval_error,
                "answer_error": answer_error,
            }
            rows.append(row)
            print(
                f"  [{qid} {category:12s}] {verdict['verdict']:7s}"
                f" hit={'Y' if hit else 'N'}"
                f" corr={verdict['correctness']:.2f}"
                f" gnd={verdict['groundedness']:.2f}"
                f" rel={verdict['relevance']:.2f}"
                f" ({latency_ms} ms)"
            )

    summary = _summarize(rows)
    payload = {
        "doc_slug": doc_slug,
        "run_at": now_iso(),
        "upload_id": meta.upload_id,
        "top_k": top_k,
        "answer_model": answer_model,
        "judge_model": judge_model,
        "questions_file_generated_at": qfile.get("generated_at"),
        "summary": summary,
        "results": rows,
    }
    out_path = write_run_result(doc_slug, payload)
    print(f"[eval] wrote {out_path}")
    _print_summary(doc_slug, summary)
    return payload


def _summarize(rows: list[dict]) -> dict:
    total = len(rows)
    counts = {"PASS": 0, "PARTIAL": 0, "FAIL": 0}
    hit_count = 0
    corr_sum = 0.0
    gnd_sum = 0.0
    rel_sum = 0.0
    by_category: dict[str, dict] = {}

    for r in rows:
        v = r["judge"]["verdict"]
        counts[v] = counts.get(v, 0) + 1
        if r["retrieval_hit"]:
            hit_count += 1
        corr_sum += r["judge"]["correctness"]
        gnd_sum += r["judge"]["groundedness"]
        rel_sum += r["judge"]["relevance"]
        cat = r.get("category", "unknown")
        c = by_category.setdefault(cat, {"total": 0, "PASS": 0, "PARTIAL": 0, "FAIL": 0, "hits": 0})
        c["total"] += 1
        c[v] = c.get(v, 0) + 1
        if r["retrieval_hit"]:
            c["hits"] += 1

    return {
        "total": total,
        "pass": counts["PASS"],
        "partial": counts["PARTIAL"],
        "fail": counts["FAIL"],
        "pass_rate": (counts["PASS"] / total) if total else 0.0,
        "retrieval_hit_rate": (hit_count / total) if total else 0.0,
        "avg_correctness": (corr_sum / total) if total else 0.0,
        "avg_groundedness": (gnd_sum / total) if total else 0.0,
        "avg_relevance": (rel_sum / total) if total else 0.0,
        "by_category": by_category,
    }


def _print_summary(doc_slug: str, s: dict) -> None:
    print(f"\n=== {doc_slug} summary ===")
    print(f"  total={s['total']}  PASS={s['pass']}  PARTIAL={s['partial']}  FAIL={s['fail']}")
    print(
        f"  pass_rate={s['pass_rate']:.2%}  retrieval_hit={s['retrieval_hit_rate']:.2%}"
        f"  avg_corr={s['avg_correctness']:.2f}  avg_gnd={s['avg_groundedness']:.2f}"
        f"  avg_rel={s['avg_relevance']:.2f}"
    )
    for cat, c in sorted(s["by_category"].items()):
        print(
            f"    {cat:14s} n={c['total']:>3}  PASS={c['PASS']:>3}  PART={c['PARTIAL']:>3}"
            f"  FAIL={c['FAIL']:>3}  hits={c['hits']:>3}/{c['total']}"
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="Run RAG evaluation for one or all indexed docs.")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--doc", help="Slug of a single doc under rag-testing/documents/")
    group.add_argument("--all", action="store_true", help="Run all docs with a questions.json")
    ap.add_argument("--top-k", type=int, default=8, help="Chunks to retrieve per question")
    ap.add_argument("--answer-model", default="gpt-4o", help="LLM for grounded answer generation")
    ap.add_argument("--judge-model", default="gpt-4o", help="LLM-as-judge model")
    args = ap.parse_args()

    if args.all:
        slugs = list_all_docs()
        if not slugs:
            print("No docs with metadata.json found under rag-testing/documents/", file=sys.stderr)
            return 2
    else:
        slugs = [args.doc]

    failed_docs: list[str] = []
    for slug in slugs:
        try:
            _run_one_doc(
                doc_slug=slug,
                top_k=args.top_k,
                answer_model=args.answer_model,
                judge_model=args.judge_model,
            )
        except Exception as e:
            print(f"[eval] {slug} ERROR: {type(e).__name__}: {e}", file=sys.stderr)
            failed_docs.append(slug)

    return 1 if failed_docs else 0


if __name__ == "__main__":
    raise SystemExit(main())
