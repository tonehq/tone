from __future__ import annotations

import io
from dataclasses import dataclass
from statistics import median
from typing import List, Tuple

import pdfplumber


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


def _detect_headings(page) -> List[Tuple[float, str]]:
    try:
        words = page.extract_words(extra_attrs=["size"])
    except Exception:
        words = []
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


def _page_image_tops(page) -> List[float]:
    tops: List[float] = []
    try:
        images = page.images or []
    except Exception:
        images = []
    for img in images:
        try:
            tops.append(float(img.get("top") or 0))
        except Exception:
            tops.append(0.0)
    return tops


def _page_table_tops(page) -> List[float]:
    tops: List[float] = []
    try:
        tables = page.find_tables()
    except Exception:
        tables = []
    for table in tables:
        try:
            tops.append(float(table.bbox[1]))
        except Exception:
            tops.append(0.0)
    return tops


def inspect_pdf(file_bytes: bytes) -> PdfInspection:
    total_pages = 0
    image_counts: List[int] = []
    table_counts: List[int] = []
    sections_with_images: List[dict] = []
    sections_with_tables: List[dict] = []
    seen_images = set()
    seen_tables = set()

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        total_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            page_number = i + 1
            try:
                headings = _detect_headings(page)
            except Exception:
                headings = []

            image_tops = _page_image_tops(page)
            table_tops = _page_table_tops(page)
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

    return PdfInspection(
        total_pages=total_pages,
        image_count=sum(image_counts),
        table_count=sum(table_counts),
        pages_with_images=[i + 1 for i, c in enumerate(image_counts) if c > 0],
        pages_with_tables=[i + 1 for i, c in enumerate(table_counts) if c > 0],
        sections_with_images=sections_with_images,
        sections_with_tables=sections_with_tables,
    )
