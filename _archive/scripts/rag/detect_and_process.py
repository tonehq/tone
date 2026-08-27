from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from pdf_inspect import PdfInspection, inspect_pdf

from core.services.rag.chunkers import DoclingHybridChunker
from core.services.rag.readers import DoclingReader


def _format_pages(pages: list[int]) -> str:
    return ", ".join(str(p) for p in pages) if pages else "none"


def _print_report(insp: PdfInspection, parse_time_s: float, chunk_time_s: float, num_chunks: int, total_time_s: float) -> None:
    print("=== PDF DETECTION REPORT ===")
    print("Note: PDFs have no explicit sections; each page is treated as a page/section N.")
    print(f"Total pages/sections: {insp.total_pages}")
    print(f"Total images: {insp.total_images}")
    print(f"Total tables: {insp.total_tables}")
    print(f"Total chars: {insp.total_chars}")
    print(f"Pages/sections with images: {_format_pages(insp.pages_with_images)}")
    print(f"Pages/sections with tables: {_format_pages(insp.pages_with_tables)}")
    print(f"Blocker pages/sections (images OR tables): {_format_pages(insp.blocker_pages)}")
    print(f"Clean (text-only) pages/sections: {_format_pages(insp.clean_pages)}")
    print("--- per page/section ---")
    for page in insp.pages:
        kind = "blocker" if page.has_blocker else "clean"
        print(
            f"page/section {page.page}: images={page.images} tables={page.tables} "
            f"chars={page.chars} [{kind}]"
        )
    print("=== FAST PROCESSING (text-only, no OCR, no table structure) ===")
    print(f"parse_time_s: {parse_time_s:.3f}")
    print(f"chunk_time_s: {chunk_time_s:.3f}")
    print(f"num_chunks: {num_chunks}")
    print(f"total_time_s: {total_time_s:.3f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect images/tables in a PDF and process it the fast way.")
    parser.add_argument("file", help="Path to the PDF file")
    parser.add_argument("--json", action="store_true", help="Print result as indented JSON")
    args = parser.parse_args()

    with open(args.file, "rb") as f:
        file_bytes = f.read()

    insp = inspect_pdf(file_bytes)

    reader = DoclingReader(ocr=False, tables=False)
    parse_start = time.monotonic()
    document = reader.read(file_bytes, content_type="application/pdf")
    parse_time_s = time.monotonic() - parse_start

    chunker = DoclingHybridChunker()
    chunk_start = time.monotonic()
    chunks = chunker.chunk(document)
    chunk_time_s = time.monotonic() - chunk_start

    num_chunks = len(chunks)
    total_time_s = parse_time_s + chunk_time_s

    if args.json:
        result = insp.to_dict()
        result.update(
            {
                "parse_time_s": parse_time_s,
                "chunk_time_s": chunk_time_s,
                "num_chunks": num_chunks,
                "total_time_s": total_time_s,
            }
        )
        print(json.dumps(result, indent=2))
    else:
        _print_report(insp, parse_time_s, chunk_time_s, num_chunks, total_time_s)


if __name__ == "__main__":
    main()
