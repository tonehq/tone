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
    UploadService,
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
