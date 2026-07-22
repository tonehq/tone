You are creating an evaluation dataset for a Retrieval-Augmented Generation (RAG) system.

Given the DOCUMENT below, produce a JSON array of test questions that will be used to grade whether the RAG pipeline can retrieve the right passages and answer accurately.

## Output format (STRICT)

Reply with **only** a JSON object, no prose, no code fences:

```
{
  "questions": [
    {
      "id": "q1",
      "category": "factual",
      "question": "…",
      "expected_answer": "…",
      "expected_source_snippet": "…",
      "notes": ""
    }
  ]
}
```

## Required categories and counts

Produce exactly this mix (minimum 30 questions total, adjust up if the doc is long):

- **factual** (≥ 12) — direct lookup. Answer is a specific fact stated verbatim (or near-verbatim) in the document. `expected_source_snippet` MUST be a substring copied literally from the document (≤ 200 chars) that contains the answer.
- **negative** (≥ 6) — a plausible-sounding question about something the document does NOT contain. `expected_answer` MUST be exactly the string `"not in the provided documents"`. `expected_source_snippet` MUST be an empty string.
- **ambiguous** (≥ 4) — under-specified question that could refer to multiple things in the doc (e.g. "What is the limit?" when several limits are mentioned). `expected_answer` should describe the ambiguity or list the possibilities; `expected_source_snippet` should be one representative snippet.
- **out-of-scope** (≥ 4) — adjacent domain but not covered by this doc (e.g. asking about a competitor product). Same rules as `negative` for expected_answer/snippet.
- **edge** (≥ 4) — requires multi-hop reasoning or synthesis across ≥ 2 separated passages. `expected_source_snippet` should be the most load-bearing of the required snippets.

## Rules

1. `expected_answer` must be self-contained and unambiguous for `factual` and `edge` (a human grader could mark PASS/FAIL from it alone).
2. Do NOT invent facts. Every factual/edge answer must be verifiable against the document below.
3. Vary question phrasing (who/what/when/why/how, direct/indirect).
4. Prefer questions that would matter to a real user of this document.
5. Keep `expected_source_snippet` short — enough to prove the answer's location, not the whole paragraph.
6. IDs are sequential: `q1`, `q2`, …

## DOCUMENT

```
{{DOCUMENT_TEXT}}
```
