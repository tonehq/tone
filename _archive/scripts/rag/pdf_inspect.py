from __future__ import annotations

import io
import json
import sys
from dataclasses import dataclass, field
from typing import List

import pdfplumber


@dataclass
class PageInspection:
    page: int
    images: int
    tables: int
    chars: int

    @property
    def has_blocker(self) -> bool:
        return self.images > 0 or self.tables > 0

    def to_dict(self) -> dict:
        return {"page": self.page, "images": self.images, "tables": self.tables, "chars": self.chars}


@dataclass
class PdfInspection:
    total_pages: int
    pages: List[PageInspection] = field(default_factory=list)

    @property
    def total_images(self) -> int:
        return sum(p.images for p in self.pages)

    @property
    def total_tables(self) -> int:
        return sum(p.tables for p in self.pages)

    @property
    def total_chars(self) -> int:
        return sum(p.chars for p in self.pages)

    @property
    def pages_with_images(self) -> List[int]:
        return [p.page for p in self.pages if p.images > 0]

    @property
    def pages_with_tables(self) -> List[int]:
        return [p.page for p in self.pages if p.tables > 0]

    @property
    def blocker_pages(self) -> List[int]:
        return [p.page for p in self.pages if p.has_blocker]

    @property
    def clean_pages(self) -> List[int]:
        return [p.page for p in self.pages if not p.has_blocker]

    def to_dict(self) -> dict:
        return {
            "total_pages": self.total_pages,
            "total_images": self.total_images,
            "total_tables": self.total_tables,
            "total_chars": self.total_chars,
            "pages_with_images": self.pages_with_images,
            "pages_with_tables": self.pages_with_tables,
            "blocker_pages": self.blocker_pages,
            "clean_pages": self.clean_pages,
            "pages": [p.to_dict() for p in self.pages],
        }


def inspect_pdf(file_bytes: bytes) -> PdfInspection:
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        inspection = PdfInspection(total_pages=len(pdf.pages))
        for i, page in enumerate(pdf.pages):
            try:
                tables = len(page.find_tables())
            except Exception:
                tables = 0
            images = len(page.images or [])
            try:
                chars = len(page.extract_text() or "")
            except Exception:
                chars = 0
            inspection.pages.append(PageInspection(page=i + 1, images=images, tables=tables, chars=chars))
    return inspection


def inspect_path(path: str) -> PdfInspection:
    with open(path, "rb") as f:
        return inspect_pdf(f.read())


def _summary_text(insp: PdfInspection) -> str:
    lines = [
        f"pages={insp.total_pages} images={insp.total_images} tables={insp.total_tables} chars={insp.total_chars}",
        f"pages_with_images={len(insp.pages_with_images)} pages_with_tables={len(insp.pages_with_tables)} "
        f"blocker_pages={len(insp.blocker_pages)} clean_pages={len(insp.clean_pages)}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/rag/pdf_inspect.py <file.pdf> [--json]")
        raise SystemExit(2)
    insp = inspect_path(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps(insp.to_dict(), indent=2))
    else:
        print(_summary_text(insp))
