"""Unit tests for ``UploadService.validate_upload_file`` — the backend upload
guard (size ceiling + type allowlist).

Pure function: no DB, no R2. This is the single source of truth enforced for
HTTP upload, file-replace, and the CLI (see core/services/upload_service.py),
so a direct API / CLI caller cannot bypass the frontend limits.
"""

import pytest

from core.services.ingestion_errors import IngestionValidationError
from core.services.upload_service import (
    ALLOWED_KB_EXTENSIONS,
    DEFAULT_MAX_KB_FILE_SIZE_BYTES,
    MAX_KB_FILE_NAME_LENGTH,
    UploadService,
    _sanitize_kb_file_name,
)


class TestValidateUploadFile:
    def test_accepts_allowed_types_within_limit(self):
        for ext in ALLOWED_KB_EXTENSIONS:
            # Should not raise for any allowed extension.
            UploadService.validate_upload_file(file_name=f"doc.{ext}", size_bytes=1024)

    def test_extension_check_is_case_insensitive(self):
        UploadService.validate_upload_file(file_name="DOC.PDF", size_bytes=10)

    def test_rejects_unsupported_extension(self):
        with pytest.raises(IngestionValidationError, match="Unsupported file type"):
            UploadService.validate_upload_file(file_name="malware.exe", size_bytes=1024)

    def test_rejects_missing_extension(self):
        with pytest.raises(IngestionValidationError, match="Unsupported file type"):
            UploadService.validate_upload_file(file_name="noext", size_bytes=1024)

    def test_rejects_oversize_file(self):
        with pytest.raises(IngestionValidationError, match="too large"):
            UploadService.validate_upload_file(
                file_name="big.pdf",
                size_bytes=DEFAULT_MAX_KB_FILE_SIZE_BYTES + 1,
            )

    def test_accepts_file_at_exactly_the_limit(self):
        # Boundary: exactly the ceiling is allowed (only strictly-greater fails).
        UploadService.validate_upload_file(
            file_name="edge.pdf", size_bytes=DEFAULT_MAX_KB_FILE_SIZE_BYTES
        )

    def test_rejects_name_over_max_length(self):
        # Regression: a name longer than KnowledgeBase.name (255) used to slip
        # past validation and blow up as a DB DataError → HTTP 500. Now it's a
        # clean IngestionValidationError → 400.
        long_name = "x" * (MAX_KB_FILE_NAME_LENGTH + 1 - 4) + ".pdf"  # 256 chars
        assert len(long_name) == MAX_KB_FILE_NAME_LENGTH + 1
        with pytest.raises(IngestionValidationError, match="too long"):
            UploadService.validate_upload_file(file_name=long_name, size_bytes=10)

    def test_accepts_name_at_max_length(self):
        # Boundary: exactly the create-path limit is allowed.
        name = "p" * (MAX_KB_FILE_NAME_LENGTH - 4) + ".pdf"
        assert len(name) == MAX_KB_FILE_NAME_LENGTH
        UploadService.validate_upload_file(file_name=name, size_bytes=10)

    def test_replace_path_allows_wider_name_limit(self):
        # The replace path stores Upload.file_name (512), so it passes a wider
        # limit — a 300-char name is fine there but would fail the default.
        name = "y" * 296 + ".pdf"  # 300 chars
        UploadService.validate_upload_file(
            file_name=name, size_bytes=10, max_name_length=512
        )
        with pytest.raises(IngestionValidationError, match="too long"):
            UploadService.validate_upload_file(
                file_name="z" * 520 + ".pdf", size_bytes=10, max_name_length=512
            )


class TestSanitizeFileName:
    def test_normal_name_unchanged(self):
        assert _sanitize_kb_file_name("report.pdf") == "report.pdf"

    def test_unicode_and_spaces_preserved(self):
        assert _sanitize_kb_file_name("é £ notes.csv") == "é £ notes.csv"

    def test_strips_path_traversal_and_separators(self):
        assert _sanitize_kb_file_name("../../evil.pdf") == "evil.pdf"
        assert _sanitize_kb_file_name("a/b/c/report.docx") == "report.docx"
        assert _sanitize_kb_file_name("dir\\sub\\file.txt") == "file.txt"

    def test_empty_or_whitespace_falls_back(self):
        assert _sanitize_kb_file_name("   ") == "upload.bin"
        assert _sanitize_kb_file_name("/") == "upload.bin"
