from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from html import escape
from typing import List

import pdfplumber

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from pdf_inspect import PdfInspection, inspect_pdf

from core.services.rag.chunkers import DoclingHybridChunker
from core.services.rag.readers import DoclingReader


def _split_paragraphs(text: str) -> List[str]:
    blocks = [b.strip() for b in (text or "").split("\n\n")]
    return [b for b in blocks if b]


def pdf_to_html(file_bytes: bytes, title: str) -> str:
    parts: List[str] = [
        "<!DOCTYPE html>",
        "<html>",
        "<head><meta charset=\"utf-8\"></head>",
        "<body>",
        f"<h1>{escape(title)}</h1>",
    ]
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            parts.append("<section>")
            parts.append(f"<h2>Page {i + 1}</h2>")
            for para in _split_paragraphs(text):
                parts.append(f"<p>{escape(para)}</p>")
            parts.append("</section>")
    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts)


def _text_report(insp: PdfInspection, html_bytes: int, out_path: str, num_chunks: int, timings: dict) -> str:
    html_mb = html_bytes / 1024 / 1024
    lines: List[str] = []
    lines.append("=== PDF -> HTML (text-only, images & tables skipped) ===")
    lines.append(f"output: {out_path}")
    lines.append(f"html_size: {html_bytes} bytes ({html_mb:.3f} MB)")
    lines.append("")
    lines.append("=== Inspection (each page treated as a section) ===")
    lines.append(
        f"total_pages/sections={insp.total_pages} total_images={insp.total_images} "
        f"total_tables={insp.total_tables} total_chars={insp.total_chars}"
    )
    lines.append(f"pages_with_images (page/section N): {insp.pages_with_images}")
    lines.append(f"pages_with_tables (page/section N): {insp.pages_with_tables}")
    lines.append("")
    lines.append("=== Skipped content per blocker page/section ===")
    if insp.blocker_pages:
        for p in insp.pages:
            if p.has_blocker:
                lines.append(f"page/section {p.page}: images={p.images} tables={p.tables} (skipped)")
    else:
        lines.append("none")
    lines.append("")
    lines.append("=== Pipeline ===")
    lines.append(f"num_chunks={num_chunks}")
    lines.append("")
    lines.append("=== Timings ===")
    lines.append(f"pdf_to_html_time_s={timings['pdf_to_html_time_s']:.4f}")
    lines.append(f"html_parse_time_s={timings['html_parse_time_s']:.4f}")
    lines.append(f"chunk_time_s={timings['chunk_time_s']:.4f}")
    lines.append(f"total_time_s={timings['total_time_s']:.4f}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("--out")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    total_start = time.monotonic()

    with open(args.pdf, "rb") as f:
        file_bytes = f.read()

    insp = inspect_pdf(file_bytes)

    stem = os.path.splitext(os.path.basename(args.pdf))[0]
    out_path = args.out or os.path.join("files", f"{stem}.from_pdf.html")

    convert_start = time.monotonic()
    html = pdf_to_html(file_bytes, os.path.basename(args.pdf))
    pdf_to_html_time_s = time.monotonic() - convert_start

    html_bytes = html.encode("utf-8")
    html_size = len(html_bytes)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    parse_start = time.monotonic()
    document = DoclingReader().read(html_bytes, "text/html")
    html_parse_time_s = time.monotonic() - parse_start

    chunk_start = time.monotonic()
    chunks = DoclingHybridChunker().chunk(document)
    chunk_time_s = time.monotonic() - chunk_start

    num_chunks = len(chunks)
    total_time_s = time.monotonic() - total_start

    timings = {
        "pdf_to_html_time_s": pdf_to_html_time_s,
        "html_parse_time_s": html_parse_time_s,
        "chunk_time_s": chunk_time_s,
        "total_time_s": total_time_s,
    }

    if args.json:
        result = insp.to_dict()
        result.update(timings)
        result["num_chunks"] = num_chunks
        result["html_size_bytes"] = html_size
        result["html_size_mb"] = html_size / 1024 / 1024
        result["out_path"] = out_path
        print(json.dumps(result, indent=2))
    else:
        print(_text_report(insp, html_size, out_path, num_chunks, timings))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
