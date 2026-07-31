"""Populate ``rag-benchmarks/<key>/{docs/,qa.jsonl}`` for the 4 standard-dataset
benchmarks Plan 2 defines. Each fetcher:

  1. Fetches the raw source (HF ``datasets`` or a raw HTTP URL).
  2. Takes the FIRST N questions in dataset order — no random sampling, so runs
     are byte-identical across re-runs.
  3. Downloads / synthesizes only the docs those N questions reference.
  4. Emits ``qa.jsonl`` where each line matches the plumbing schema exactly:

     { "id","doc_filename","category","question","expected_answer",
       "expected_source_snippet" }

Usage:
    cd rag-benchmarks/scripts
    pip install -r requirements.txt
    python download_datasets.py                 # all 4 datasets
    python download_datasets.py --dataset tatqa-mini
    python download_datasets.py --force         # overwrite existing outputs

Idempotency: if a dataset's ``qa.jsonl`` already exists, the dataset is skipped
unless ``--force`` is passed. Individual doc downloads also skip files that
already exist on disk.

If any fetcher's upstream URL / HF subset drifts, adjust that fetcher — do NOT
hand-edit the emitted ``qa.jsonl``; re-runs would clobber your edits.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

BENCHMARKS_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_KEYS = {
    "id",
    "doc_filename",
    "category",
    "question",
    "expected_answer",
    "expected_source_snippet",
}

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(s: str, *, max_len: int = 80) -> str:
    """Deterministic filename slug — lower/ASCII/underscore. Truncated to keep
    filesystem paths short; a hash suffix is NOT added because the dataset's
    own id space is what enforces uniqueness at the qa.jsonl level, and doc
    dedupe already handles collisions by content identity."""
    base = _SLUG_RE.sub("_", s.lower()).strip("_")
    return (base or "doc")[:max_len]


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            missing = REQUIRED_KEYS - row.keys()
            if missing:
                raise ValueError(f"qa row missing keys {missing}: {row!r}")
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_text_doc(docs_dir: Path, filename: str, content: str, *, force: bool) -> Path:
    docs_dir.mkdir(parents=True, exist_ok=True)
    path = docs_dir / filename
    if path.exists() and not force:
        return path
    path.write_text(content, encoding="utf-8")
    return path


def _to_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return ", ".join(_to_str(x) for x in v if x is not None)
    return str(v)


# ── HotpotQA (distractor, dev split) ─────────────────────────────────────────

def fetch_hotpotqa_mini(dataset_dir: Path, *, n: int, category: str, force: bool) -> int:
    """First N Qs from HotpotQA distractor validation. doc_filename = slug of
    the FIRST supporting-fact title. Doc text = full sentence list joined by
    space; expected_source_snippet = the specific supporting sentence.

    Uses HF instead of the classical CMU URL because the CMU host is flaky.
    HF loader: ``hotpot_qa`` config ``distractor`` split ``validation``.
    """
    from datasets import load_dataset

    ds = load_dataset("hotpot_qa", "distractor", split="validation")
    docs_dir = dataset_dir / "docs"
    rows: list[dict] = []
    seen_docs: set[str] = set()

    for i, item in enumerate(ds):
        if len(rows) >= n:
            break
        sup = item.get("supporting_facts") or {}
        titles = sup.get("title") or []
        sent_ids = sup.get("sent_id") or []
        if not titles:
            continue
        title = titles[0]
        sent_id = int(sent_ids[0]) if sent_ids else 0

        ctx = item.get("context") or {}
        ctx_titles = ctx.get("title") or []
        ctx_sentences = ctx.get("sentences") or []
        try:
            doc_idx = ctx_titles.index(title)
        except ValueError:
            continue
        sentences = ctx_sentences[doc_idx] or []
        if not sentences:
            continue

        snippet = sentences[sent_id] if 0 <= sent_id < len(sentences) else ""

        doc_slug = slugify(title)
        doc_filename = f"{doc_slug}.txt"

        if doc_slug not in seen_docs:
            write_text_doc(
                docs_dir,
                doc_filename,
                " ".join(str(s) for s in sentences).strip(),
                force=force,
            )
            seen_docs.add(doc_slug)

        rows.append({
            "id": f"hpq-{len(rows):03d}",
            "doc_filename": doc_filename,
            "category": category,
            "question": _to_str(item.get("question")),
            "expected_answer": _to_str(item.get("answer")),
            "expected_source_snippet": _to_str(snippet),
        })

    write_jsonl(dataset_dir / "qa.jsonl", rows)
    return len(rows)


# ── TAT-QA (dev split from GitHub raw) ───────────────────────────────────────

def fetch_tatqa_mini(dataset_dir: Path, *, n: int, category: str, force: bool) -> int:
    """First N QUESTIONS across TAT-QA dev contexts, in file order. Each hybrid
    context becomes ONE doc: paragraphs joined by blank lines, then a
    ``[TABLE]`` marker + a naive markdown table. Contexts are deduped by uid
    so shared contexts produce a single doc."""
    import requests

    url = "https://raw.githubusercontent.com/NExTplusplus/TAT-QA/master/dataset_raw/tatqa_dataset_dev.json"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    payload = resp.json()

    docs_dir = dataset_dir / "docs"
    rows: list[dict] = []
    seen_ctx: set[str] = set()

    for ctx_idx, entry in enumerate(payload):
        if len(rows) >= n:
            break
        table = entry.get("table") or {}
        paragraphs = entry.get("paragraphs") or []
        questions = entry.get("questions") or []
        if not questions:
            continue

        ctx_uid = table.get("uid") or f"ctx_{ctx_idx:04d}"
        doc_filename = f"tatqa_ctx_{ctx_idx:04d}.txt"

        if ctx_uid not in seen_ctx:
            paragraph_text = "\n\n".join(
                _to_str(p.get("text")) for p in paragraphs if p.get("text")
            ).strip()
            table_md = _tatqa_table_to_markdown(table.get("table") or [])
            body_parts = []
            if paragraph_text:
                body_parts.append(paragraph_text)
            if table_md:
                body_parts.append(f"[TABLE]\n{table_md}")
            write_text_doc(
                docs_dir,
                doc_filename,
                "\n\n".join(body_parts) or "(empty context)",
                force=force,
            )
            seen_ctx.add(ctx_uid)

        for q in questions:
            if len(rows) >= n:
                break
            rows.append({
                "id": _to_str(q.get("uid")) or f"tat-{len(rows):04d}",
                "doc_filename": doc_filename,
                "category": category,
                "question": _to_str(q.get("question")),
                "expected_answer": _to_str(q.get("answer")),
                "expected_source_snippet": "",
            })

    write_jsonl(dataset_dir / "qa.jsonl", rows)
    return len(rows)


def _tatqa_table_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    header = [_to_str(c) for c in rows[0]]
    body = [[_to_str(c) for c in r] for r in rows[1:]]
    md = ["| " + " | ".join(header) + " |",
          "| " + " | ".join("---" for _ in header) + " |"]
    for r in body:
        md.append("| " + " | ".join(r) + " |")
    return "\n".join(md)


# ── RAGBench EManual ─────────────────────────────────────────────────────────

def fetch_ragbench_emanual(dataset_dir: Path, *, n: int, category: str, force: bool) -> int:
    """First N Qs from ``rungalileo/ragbench`` subset ``emanual``. Plan asks
    for a Samsung TV manual PDF; there is no canonical download URL for it, so
    we synthesize a single doc from the UNION of ``documents`` chunks across
    the sampled Qs — the KB pipeline treats it the same as any text upload,
    and every Q ends up pointing at that one file. If a manual PDF URL is ever
    added upstream, replace this synthesizer with a plain download."""
    from datasets import load_dataset

    ds = _load_ragbench_split("emanual")
    docs_dir = dataset_dir / "docs"
    doc_filename = "samsung_smart_tv_manual.txt"

    rows: list[dict] = []
    unique_chunks: list[str] = []
    seen: set[str] = set()

    for item in ds:
        if len(rows) >= n:
            break
        docs = item.get("documents") or item.get("passages") or []
        for chunk in docs:
            text = _to_str(chunk).strip()
            if not text or text in seen:
                continue
            unique_chunks.append(text)
            seen.add(text)

        answer = _to_str(item.get("response") or item.get("answer"))
        rows.append({
            "id": _to_str(item.get("id")) or f"emanual-{len(rows):03d}",
            "doc_filename": doc_filename,
            "category": category,
            "question": _to_str(item.get("question")),
            "expected_answer": answer,
            "expected_source_snippet": _first_non_empty(docs) if isinstance(docs, list) else "",
        })

    write_text_doc(
        docs_dir,
        doc_filename,
        "\n\n---\n\n".join(unique_chunks) or "(no chunks)",
        force=force,
    )
    write_jsonl(dataset_dir / "qa.jsonl", rows)
    return len(rows)


def _load_ragbench_split(subset: str):
    """RAGBench splits vary by subset; try the common ones in order and use
    whichever loads first. Kept isolated so a single split-name drift doesn't
    require touching the caller."""
    from datasets import load_dataset

    for split in ("test", "validation", "train"):
        try:
            return load_dataset("rungalileo/ragbench", subset, split=split)
        except Exception:  # noqa: BLE001
            continue
    raise RuntimeError(
        f"Could not load rungalileo/ragbench subset={subset!r} on any of test/validation/train splits"
    )


def _first_non_empty(items: list[Any]) -> str:
    for item in items:
        text = _to_str(item).strip()
        if text:
            return text
    return ""


# ── Open-RAG-Bench arXiv ─────────────────────────────────────────────────────

def fetch_openragbench_arxiv(dataset_dir: Path, *, n: int, category: str, force: bool) -> int:
    """First N arXiv-domain Qs from ``vectara/open_ragbench``. Downloads only
    the PDFs those N Qs reference (via ``hf_hub_download`` on the dataset repo)
    rather than the whole PDF corpus. If PDF download fails for a given
    document, we fall back to writing the passage text to a ``.txt`` file so
    the eval can still run — a lossy but non-blocking degradation.

    The exact HF subset / column names may drift; this fetcher inspects the
    first row and picks the arXiv-shaped rows heuristically."""
    from datasets import load_dataset
    from huggingface_hub import hf_hub_download

    ds = _load_openragbench_arxiv()
    docs_dir = dataset_dir / "docs"
    rows: list[dict] = []
    downloaded: set[str] = set()

    for item in ds:
        if len(rows) >= n:
            break

        doc_id = (
            item.get("document_id")
            or item.get("doc_id")
            or item.get("arxiv_id")
            or item.get("source_id")
        )
        question = _to_str(item.get("question") or item.get("query"))
        answer = _to_str(
            item.get("answer")
            or item.get("response")
            or item.get("ground_truth_answer")
        )
        snippet = _to_str(
            item.get("passage")
            or item.get("context")
            or _first_non_empty(item.get("passages") or [])
        )

        if not question or not doc_id:
            continue

        pdf_name = f"{slugify(str(doc_id), max_len=64)}.pdf"
        pdf_path = docs_dir / pdf_name
        if pdf_name not in downloaded:
            ok = _try_download_openragbench_pdf(
                doc_id, pdf_path, force=force, url=_to_str(item.get("pdf_url"))
            )
            if not ok:
                # Fall back: write passage text under a .txt filename so eval can still run.
                txt_name = f"{slugify(str(doc_id), max_len=64)}.txt"
                write_text_doc(docs_dir, txt_name, snippet or "(no text)", force=force)
                pdf_name = txt_name
            downloaded.add(pdf_name)

        rows.append({
            "id": _to_str(item.get("id")) or f"orb-arxiv-{len(rows):03d}",
            "doc_filename": pdf_name,
            "category": category,
            "question": question,
            "expected_answer": answer,
            "expected_source_snippet": snippet,
        })

    write_jsonl(dataset_dir / "qa.jsonl", rows)
    return len(rows)


def _load_openragbench_arxiv():
    """Load the arXiv slice of vectara/open_ragbench by joining its 4 index
    JSONs (queries, answers, qrels, pdf_urls) into the row shape the caller
    expects. We bypass ``datasets.load_dataset`` because the upstream
    ``answers.json`` has schema drift that trips Arrow inference.
    Returns a list of dicts with keys the caller reads via ``item.get(...)``:
    ``id``, ``document_id``, ``question``, ``answer``, ``passage``,
    ``pdf_url``."""
    import json
    from huggingface_hub import hf_hub_download

    def _load(filename: str):
        path = hf_hub_download(
            repo_id="vectara/open_ragbench",
            filename=filename,
            repo_type="dataset",
        )
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    try:
        queries = _load("pdf/arxiv/queries.json")   # {qid: {query, type, source}}
        answers = _load("pdf/arxiv/answers.json")   # {qid: answer_str}
        qrels = _load("pdf/arxiv/qrels.json")       # {qid: {doc_id, section_id}}
        pdf_urls = _load("pdf/arxiv/pdf_urls.json") # {doc_id: arxiv_pdf_url}
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Could not load vectara/open_ragbench arXiv index files: {exc}"
        ) from exc

    rows: list[dict] = []
    for qid, qmeta in queries.items():
        rel = qrels.get(qid) or {}
        doc_id = rel.get("doc_id")
        if not doc_id:
            continue
        rows.append({
            "id": qid,
            "document_id": doc_id,
            "question": (qmeta or {}).get("query") or "",
            "answer": answers.get(qid) or "",
            "passage": "",  # per-passage text not indexed; we ingest the PDF itself
            "pdf_url": pdf_urls.get(doc_id) or "",
        })
    if not rows:
        raise RuntimeError("open_ragbench arXiv index produced 0 usable rows")
    return rows


def _looks_like_arxiv_row(row: dict) -> bool:
    for key in ("domain", "source", "dataset", "corpus"):
        val = row.get(key)
        if isinstance(val, str) and "arxiv" in val.lower():
            return True
    doc_id = row.get("document_id") or row.get("doc_id") or ""
    return bool(re.match(r"\d{4}\.\d{4,5}", str(doc_id)))


def _try_download_openragbench_pdf(
    doc_id: Any, dest: Path, *, force: bool, url: str = ""
) -> bool:
    """Download the arXiv PDF for a given doc_id. The vectara/open_ragbench
    repo does NOT bundle the PDFs — it ships URLs in ``pdf_urls.json`` pointing
    at ``https://arxiv.org/pdf/{arxiv_id}``. We fetch from arxiv.org directly.
    A pre-resolved ``url`` (from ``_load_openragbench_arxiv``) wins; otherwise
    we synthesize the arXiv URL from the doc_id."""
    import requests

    if dest.exists() and not force:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)

    urls = []
    if url:
        urls.append(url)
    urls.append(f"https://arxiv.org/pdf/{doc_id}")
    urls.append(f"https://arxiv.org/pdf/{doc_id}.pdf")

    for u in urls:
        try:
            resp = requests.get(u, timeout=60, allow_redirects=True)
            if resp.status_code == 200 and resp.content[:4] == b"%PDF":
                dest.write_bytes(resp.content)
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


# ── Registry + CLI ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DatasetSpec:
    key: str
    n_questions: int
    category: str
    fetch: Callable[..., int]


DATASETS: dict[str, DatasetSpec] = {
    "hotpotqa-mini": DatasetSpec(
        key="hotpotqa-mini", n_questions=100, category="multi-hop",
        fetch=fetch_hotpotqa_mini,
    ),
    "ragbench-emanual": DatasetSpec(
        key="ragbench-emanual", n_questions=100, category="manual",
        fetch=fetch_ragbench_emanual,
    ),
    "tatqa-mini": DatasetSpec(
        key="tatqa-mini", n_questions=100, category="finance-table",
        fetch=fetch_tatqa_mini,
    ),
    "openragbench-arxiv-mini": DatasetSpec(
        key="openragbench-arxiv-mini", n_questions=50, category="scientific-pdf",
        fetch=fetch_openragbench_arxiv,
    ),
}


def _run_one(spec: DatasetSpec, *, force: bool) -> tuple[str, int | None, str | None]:
    dataset_dir = BENCHMARKS_ROOT / spec.key
    qa_path = dataset_dir / "qa.jsonl"
    if qa_path.exists() and not force:
        return spec.key, None, "skipped (qa.jsonl exists; --force to overwrite)"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    try:
        count = spec.fetch(
            dataset_dir,
            n=spec.n_questions,
            category=spec.category,
            force=force,
        )
        return spec.key, count, None
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return spec.key, None, f"{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--dataset",
        choices=sorted(DATASETS.keys()),
        default=None,
        help="Run only this dataset (default: all four).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing qa.jsonl and re-download docs even if present.",
    )
    args = parser.parse_args()

    targets = (
        [DATASETS[args.dataset]] if args.dataset else list(DATASETS.values())
    )

    results = [_run_one(spec, force=args.force) for spec in targets]

    print("\n── summary ─────────────────────────────────────────────")
    total_ok = 0
    total_failed = 0
    for key, count, err in results:
        if err and count is None and "skipped" in err:
            print(f"  {key:30s} SKIP  {err}")
        elif err:
            total_failed += 1
            print(f"  {key:30s} FAIL  {err}")
        else:
            total_ok += 1
            print(f"  {key:30s} OK    {count} questions")
    print(f"── {total_ok} ok, {total_failed} failed ────────────────")
    return 1 if total_failed else 0


if __name__ == "__main__":
    sys.exit(main())
