"""Generate an evaluation Q&A dataset for one knowledge-base document.

Reads the source file at `rag-testing/documents/<slug>/source.*`, extracts its
text using the SAME readers as production ingestion (`CompositeReader`), sends
it to the LLM with `prompts/question_generation.md`, and writes
`documents/<slug>/questions.json`.

Usage:
    python rag-testing/scripts/generate_questions.py --doc <slug>
    python rag-testing/scripts/generate_questions.py --doc <slug> --model gpt-4o --max-chars 60000

The reviewer is expected to open the emitted file, prune weak questions, and
add manual edge cases before committing.
"""
from __future__ import annotations

import argparse
import json
import sys

from common import (
    DocMetadata,
    doc_dir,
    extract_document_text,
    now_iso,
    openai_client,
    read_prompt,
    render_prompt,
    resolve_source_file,
    write_questions,
)


def _clip_document(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return f"{text[:half]}\n\n…[TRUNCATED FOR PROMPT SIZE]…\n\n{text[-half:]}"


def _parse_response(raw: str) -> dict:
    import re

    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def generate(doc_slug: str, *, model: str, max_chars: int) -> dict:
    meta = None
    meta_path = doc_dir(doc_slug) / "metadata.json"
    if meta_path.exists():
        try:
            meta = DocMetadata.load(doc_slug)
        except FileNotFoundError:
            meta = None

    source_path = resolve_source_file(doc_slug, meta)
    print(f"[generate] doc={doc_slug} source={source_path.name}")
    text = extract_document_text(source_path)
    print(f"[generate] extracted {len(text):,} chars; clipping to {max_chars:,}")
    document_text = _clip_document(text, max_chars)

    template = read_prompt("question_generation.md")
    prompt = render_prompt(template, DOCUMENT_TEXT=document_text)

    client = openai_client()
    print(f"[generate] calling {model} …")
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    parsed = _parse_response(content)

    questions = parsed.get("questions", [])
    if not isinstance(questions, list) or not questions:
        raise RuntimeError(
            "LLM did not return a non-empty `questions` array. "
            f"Raw response starts with: {content[:200]!r}"
        )

    for i, q in enumerate(questions, 1):
        q.setdefault("id", f"q{i}")
        q.setdefault("notes", "")
        q.setdefault("expected_source_snippet", "")

    payload = {
        "doc_slug": doc_slug,
        "generated_at": now_iso(),
        "generator_model": model,
        "source_file": source_path.name,
        "questions": questions,
    }
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a RAG eval Q&A file for one document.")
    ap.add_argument("--doc", required=True, help="Slug matching rag-testing/documents/<slug>/")
    ap.add_argument("--model", default="gpt-4o", help="OpenAI model for question generation")
    ap.add_argument(
        "--max-chars",
        type=int,
        default=60_000,
        help="Truncate document text to this many chars before sending to the LLM",
    )
    ap.add_argument("--force", action="store_true", help="Overwrite existing questions.json")
    args = ap.parse_args()

    out_path = doc_dir(args.doc) / "questions.json"
    if out_path.exists() and not args.force:
        print(f"[generate] {out_path} already exists. Use --force to overwrite.", file=sys.stderr)
        return 2

    payload = generate(args.doc, model=args.model, max_chars=args.max_chars)
    written = write_questions(args.doc, payload)

    by_cat: dict[str, int] = {}
    for q in payload["questions"]:
        by_cat[q.get("category", "unknown")] = by_cat.get(q.get("category", "unknown"), 0) + 1
    breakdown = ", ".join(f"{k}={v}" for k, v in sorted(by_cat.items()))
    print(f"[generate] wrote {written} — {len(payload['questions'])} questions ({breakdown})")
    print("[generate] REVIEW the file: prune weak questions, add manual edge cases, then commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
