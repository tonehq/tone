from __future__ import annotations

import base64
import io
import time
from dataclasses import dataclass
from html import escape
from statistics import median
from typing import List, Tuple

import pdfplumber
from loguru import logger

KEEP_BLOCKERS = True


def _table_html(table) -> str:
    try:
        rows = table.extract()
    except Exception:
        return ""
    parts = ["<table>"]
    for row in rows:
        parts.append("<tr>")
        for cell in row:
            parts.append(f"<td>{escape(cell or '')}</td>")
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)


def _image_data_uri(page, img) -> str:
    try:
        bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
        pil = page.crop(bbox).to_image(resolution=72).original
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


@dataclass
class PdfInspection:
    total_pages: int
    image_count: int
    table_count: int
    pages_with_images: List[int]
    pages_with_tables: List[int]
    sections_with_images: List[dict]
    sections_with_tables: List[dict]

    @property
    def has_blockers(self) -> bool:
        return self.image_count > 0 or self.table_count > 0

    def to_dict(self) -> dict:
        return {
            "total_pages": self.total_pages,
            "image_count": self.image_count,
            "table_count": self.table_count,
            "pages_with_images": self.pages_with_images,
            "pages_with_tables": self.pages_with_tables,
            "sections_with_images": self.sections_with_images,
            "sections_with_tables": self.sections_with_tables,
        }


@dataclass
class AnalyzeResult:
    inspection: PdfInspection
    html_path: str
    html_length: int
    text_length: int
    conversion_seconds: float


def _word_in_bbox(word, bbox) -> bool:
    x0, top, x1, bottom = bbox
    cx = (word["x0"] + word["x1"]) / 2
    cy = (word["top"] + word["bottom"]) / 2
    return x0 <= cx <= x1 and top <= cy <= bottom


def _reconstruct_lines(words) -> List[str]:
    buckets: List[Tuple[float, list]] = []
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


def _headings_from_words(words) -> List[Tuple[float, str]]:
    if not words:
        return []

    sizes = []
    for w in words:
        try:
            sizes.append(float(w.get("size") or 0))
        except Exception:
            sizes.append(0.0)
    page_median = median(sizes) if sizes else 0.0

    lines = {}
    for w in words:
        try:
            top = float(w.get("top") or 0)
        except Exception:
            top = 0.0
        try:
            size = float(w.get("size") or 0)
        except Exception:
            size = 0.0
        bucket = round(top / 3.0) * 3
        entry = lines.setdefault(bucket, {"top": top, "size": 0.0, "words": []})
        if top < entry["top"]:
            entry["top"] = top
        if size > entry["size"]:
            entry["size"] = size
        entry["words"].append(w.get("text") or "")

    ordered = sorted(lines.values(), key=lambda e: e["top"])
    headings: List[Tuple[float, str]] = []
    for idx, entry in enumerate(ordered):
        title = " ".join(t for t in entry["words"] if t).strip()
        if not title:
            continue
        is_heading = entry["size"] > page_median or idx == 0
        if is_heading:
            headings.append((entry["top"], title[:80]))
    headings.sort(key=lambda h: h[0])
    return headings


def _section_for(top: float, headings: List[Tuple[float, str]], page_number: int) -> str:
    if not headings:
        return f"Page {page_number}"
    best = None
    for h_top, h_title in headings:
        if h_top <= top:
            if best is None or h_top > best[0]:
                best = (h_top, h_title)
    if best is not None:
        return best[1]
    return headings[0][1]


def analyze_pdf(pdf_path: str, html_path: str) -> AnalyzeResult:
    start = time.monotonic()
    image_counts = []
    table_counts = []
    sections_with_images = []
    sections_with_tables = []
    seen_images = set()
    seen_tables = set()
    html_length = 0
    text_length = 0

    with pdfplumber.open(pdf_path) as pdf, open(html_path, "w", encoding="utf-8") as out:
        total = len(pdf.pages)
        logger.info("[pdf-analyze] {} page(s) ...", total)

        def write(chunk: str) -> None:
            nonlocal html_length
            out.write(chunk)
            html_length += len(chunk)

        write("<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>")
        for i, page in enumerate(pdf.pages):
            page_number = i + 1
            lines = []
            image_tops = []
            table_tops = []
            headings = []
            tables = []
            page_images = []
            try:
                words = page.extract_words(extra_attrs=["size"])
                headings = _headings_from_words(words)
                tables = page.find_tables()
                table_bboxes = [t.bbox for t in tables]
                table_tops = [float(b[1]) for b in table_bboxes]
                page_images = list(page.images or [])
                image_tops = [float(im.get("top") or 0) for im in page_images]
                kept = [
                    w
                    for w in words
                    if not any(_word_in_bbox(w, bbox) for bbox in table_bboxes)
                ]
                lines = _reconstruct_lines(kept)
            except Exception:
                lines = []
                image_tops = []
                table_tops = []
                headings = []
                tables = []
                page_images = []

            image_counts.append(len(image_tops))
            table_counts.append(len(table_tops))

            for top in image_tops:
                section = _section_for(top, headings, page_number)
                key = (page_number, section)
                if key not in seen_images:
                    seen_images.add(key)
                    sections_with_images.append({"page": page_number, "section": section})

            for top in table_tops:
                section = _section_for(top, headings, page_number)
                key = (page_number, section)
                if key not in seen_tables:
                    seen_tables.add(key)
                    sections_with_tables.append({"page": page_number, "section": section})

            write(f"<section><h2>Page {page_number}</h2>")
            for line in lines:
                write(f"<p>{escape(line)}</p>")
                text_length += len(line) + 1
            if KEEP_BLOCKERS:
                for table in tables:
                    block = _table_html(table)
                    write(block)
                    text_length += len(block)
                for img in page_images:
                    uri = _image_data_uri(page, img)
                    write(f'<img src="{uri}" />' if uri else '<img alt="image" />')
            write("</section>")

            try:
                page.flush_cache()
            except Exception:
                pass

            if page_number % 25 == 0 or page_number == total:
                logger.info(
                    "[pdf-analyze] {}/{} pages ({} images, {} tables, keep_blockers={}, {:.1f}s)",
                    page_number, total, sum(image_counts), sum(table_counts), KEEP_BLOCKERS,
                    time.monotonic() - start,
                )

        write("</body></html>")

    elapsed = time.monotonic() - start
    logger.info("[pdf-analyze] done: {} pages in {:.1f}s -> {}", total, elapsed, html_path)

    inspection = PdfInspection(
        total_pages=total,
        image_count=sum(image_counts),
        table_count=sum(table_counts),
        pages_with_images=[i + 1 for i, c in enumerate(image_counts) if c > 0],
        pages_with_tables=[i + 1 for i, c in enumerate(table_counts) if c > 0],
        sections_with_images=sections_with_images,
        sections_with_tables=sections_with_tables,
    )
    return AnalyzeResult(
        inspection=inspection,
        html_path=html_path,
        html_length=html_length,
        text_length=text_length,
        conversion_seconds=elapsed,
    )
