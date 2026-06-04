from __future__ import annotations

import io
import time
from dataclasses import dataclass
from html import escape

import pdfplumber


@dataclass
class HtmlConversion:
    html: str
    text: str
    image_count: int
    table_count: int
    conversion_seconds: float


def _word_in_bbox(word, bbox) -> bool:
    x0, top, x1, bottom = bbox
    cx = (word["x0"] + word["x1"]) / 2
    cy = (word["top"] + word["bottom"]) / 2
    return x0 <= cx <= x1 and top <= cy <= bottom


def _reconstruct_lines(words) -> list[str]:
    buckets: list[tuple[float, list]] = []
    for word in words:
        top = word["top"]
        placed = False
        for bucket in buckets:
            if abs(bucket[0] - top) <= 3:
                bucket[1].append(word)
                placed = True
                break
        if not placed:
            buckets.append((top, [word]))
    buckets.sort(key=lambda b: b[0])
    lines = []
    for _, bucket_words in buckets:
        bucket_words.sort(key=lambda w: w["x0"])
        line = " ".join(w["text"] for w in bucket_words).strip()
        if line:
            lines.append(line)
    return lines


def convert_pdf_to_html(file_bytes: bytes) -> HtmlConversion:
    start = time.monotonic()
    html_parts = ["<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>"]
    page_texts: list[str] = []
    image_count = 0
    table_count = 0

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            lines: list[str] = []
            try:
                image_count += len(page.images or [])
                tables = page.find_tables()
                table_count += len(tables)
                table_bboxes = [table.bbox for table in tables]
                words = page.extract_words()
                kept = [
                    word
                    for word in words
                    if not any(_word_in_bbox(word, bbox) for bbox in table_bboxes)
                ]
                lines = _reconstruct_lines(kept)
            except Exception:
                lines = []

            html_parts.append(f"<section><h2>Page {i + 1}</h2>")
            for line in lines:
                html_parts.append(f"<p>{escape(line)}</p>")
            html_parts.append("</section>")

            if lines:
                page_texts.append("\n".join(lines))

    html_parts.append("</body></html>")
    elapsed = time.monotonic() - start

    return HtmlConversion(
        html="".join(html_parts),
        text="\n\n".join(page_texts),
        image_count=image_count,
        table_count=table_count,
        conversion_seconds=elapsed,
    )


def pdf_to_html(file_bytes: bytes) -> str:
    return convert_pdf_to_html(file_bytes).html
