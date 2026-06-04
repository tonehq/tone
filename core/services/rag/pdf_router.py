from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from core.services.rag.pdf_analyze import AnalyzeResult, analyze_pdf

PDF_CONTENT_TYPE = "application/pdf"
HTML_CONTENT_TYPE = "text/html"

PIPELINE_HTML_DOCLING = "html_docling"
PIPELINE_OCR = "ocr"

OCR_ENABLED = True


@dataclass
class BuildResult:
    pipeline: str
    recommended_pipeline: str
    content_type: str
    html_path: str
    analysis: AnalyzeResult

    def metrics(self) -> dict:
        insp = self.analysis.inspection
        data = {
            "pipeline": self.pipeline,
            "recommended_pipeline": self.recommended_pipeline,
            "ocr_enabled": OCR_ENABLED,
            "html_conversion_seconds": round(self.analysis.conversion_seconds, 3),
            "html_length": self.analysis.html_length,
            "text_length": self.analysis.text_length,
        }
        data.update(insp.to_dict())
        return data


class IngestionPipelineBuilder:
    pipeline = "base"
    content_type = HTML_CONTENT_TYPE

    def __init__(self, analysis: AnalyzeResult):
        self.analysis = analysis

    def recommended(self) -> str:
        return PIPELINE_OCR if self.analysis.inspection.has_blockers else PIPELINE_HTML_DOCLING

    def build(self) -> BuildResult:
        return BuildResult(
            pipeline=self.pipeline,
            recommended_pipeline=self.recommended(),
            content_type=self.content_type,
            html_path=self.analysis.html_path,
            analysis=self.analysis,
        )


class HtmlDoclingPipelineBuilder(IngestionPipelineBuilder):
    pipeline = PIPELINE_HTML_DOCLING
    content_type = HTML_CONTENT_TYPE


class PdfRoutingService:
    def build(self, pdf_path: str, html_path: str) -> BuildResult:
        analysis = analyze_pdf(pdf_path, html_path)
        result = HtmlDoclingPipelineBuilder(analysis).build()
        logger.info("\n" + _format_banner(result))
        return result


def _format_banner(result: BuildResult) -> str:
    insp = result.analysis.inspection
    bar = "=" * 70
    lines = [
        "",
        bar,
        "  PDF ROUTER",
        bar,
        f"  pipeline             : {result.pipeline}",
        f"  recommended_pipeline : {result.recommended_pipeline}",
        f"  ocr_enabled          : {OCR_ENABLED}",
        f"  pdf -> html          : {result.analysis.conversion_seconds:.2f}s",
        f"  html_path            : {result.html_path}",
        f"  html_length          : {result.analysis.html_length} chars",
        f"  text_length          : {result.analysis.text_length} chars",
        "  " + "-" * 68,
        f"  total_pages          : {insp.total_pages}",
        f"  image_count          : {insp.image_count}  (skipped)",
        f"  table_count          : {insp.table_count}  (skipped)",
        f"  pages_with_images    : {insp.pages_with_images}",
        f"  pages_with_tables    : {insp.pages_with_tables}",
        f"  sections_with_images : {insp.sections_with_images}",
        f"  sections_with_tables : {insp.sections_with_tables}",
        bar,
        "",
    ]
    return "\n".join(lines)
