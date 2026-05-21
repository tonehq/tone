"""Tests for Documents API endpoints (Core edition).

Source: core/api/v1/documents.py
Postman: documents.postman_collection.json
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


PATCH_SERVICE = "core.api.v1.documents.DocumentService"


# ---------------------------------------------------------------------------
# POST /api/v1/document/get_documents
# ---------------------------------------------------------------------------

class TestGetDocuments:
    """Tests for POST /api/v1/document/get_documents"""

    @patch(PATCH_SERVICE)
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get Documents - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.get_documents_by_agent.return_value = {
            "data": [
                {
                    "id": 1,
                    "name": "User Guide.pdf",
                    "agent_id": 1,
                    "content_type": "application/pdf",
                    "status": "processed",
                    "created_at": "2026-01-15T10:00:00",
                }
            ],
            "pagination": {
                "page": 1,
                "page_size": 10,
                "total": 1,
                "total_pages": 1,
            },
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/document/get_documents", json={
            "agent_id": 1,
            "name": "user guide",
            "sort": "-created_at",
            "page": 1,
            "page_size": 10,
        })

        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["total"] == 1
        mock_instance.get_documents_by_agent.assert_called_once_with(
            agent_id=1,
            name="user guide",
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=10,
        )

    @patch(PATCH_SERVICE)
    def test_success_defaults(self, mock_service_cls, client_as_member):
        """Empty body uses defaults: sort=-created_at, page=1, page_size=10."""
        mock_instance = MagicMock()
        mock_instance.get_documents_by_agent.return_value = {
            "data": [{"id": 1, "name": "doc.pdf"}],
            "pagination": {"page": 1, "page_size": 10, "total": 1, "total_pages": 1},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/document/get_documents", json={})

        assert resp.status_code == 200
        mock_instance.get_documents_by_agent.assert_called_once_with(
            agent_id=None,
            name=None,
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=10,
        )

    @patch(PATCH_SERVICE)
    def test_with_filters(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_documents_by_agent.return_value = {"data": [], "pagination": {"total": 0}}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/document/get_documents", json={
            "agent_id": 5,
            "name": "report",
            "sort": "name",
            "page": 2,
            "page_size": 5,
        })

        assert resp.status_code == 200
        mock_instance.get_documents_by_agent.assert_called_once_with(
            agent_id=5,
            name="report",
            sort_by="name",
            sort_order="asc",
            page=2,
            page_size=5,
        )

    @patch(PATCH_SERVICE)
    def test_sort_desc(self, mock_service_cls, client_as_member):
        """Prefix '-' on sort field means descending."""
        mock_instance = MagicMock()
        mock_instance.get_documents_by_agent.return_value = {"data": []}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/document/get_documents", json={
            "sort": "-updated_at",
        })

        assert resp.status_code == 200
        mock_instance.get_documents_by_agent.assert_called_once_with(
            agent_id=None,
            name=None,
            sort_by="updated_at",
            sort_order="desc",
            page=1,
            page_size=10,
        )

    def test_invalid_sort_field(self, client_as_member):
        """Postman: Get Documents - Invalid Sort (400)"""
        resp = client_as_member.post("/api/v1/document/get_documents", json={
            "sort": "-invalid_field",
        })
        assert resp.status_code == 400
        assert "Invalid sort field" in resp.json()["detail"]

    def test_invalid_page(self, client_as_member):
        """page must be >= 1."""
        resp = client_as_member.post("/api/v1/document/get_documents", json={
            "page": 0,
        })
        assert resp.status_code == 422

    def test_invalid_page_size(self, client_as_member):
        """page_size must be >= 1."""
        resp = client_as_member.post("/api/v1/document/get_documents", json={
            "page_size": 0,
        })
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/document/get_documents", json={})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/document/upload_document
# ---------------------------------------------------------------------------

class TestUploadDocument:
    """Tests for POST /api/v1/document/upload_document (multipart/form-data)"""

    @patch(PATCH_SERVICE)
    def test_success_pdf(self, mock_service_cls, client_as_member):
        """Postman: Upload Document - Success (201)"""
        mock_instance = MagicMock()
        mock_doc = MagicMock()
        mock_instance.upload_and_create_document.return_value = mock_doc
        mock_instance._document_response.return_value = {
            "id": 1,
            "name": "User Guide.pdf",
            "agent_id": 1,
            "content_type": "application/pdf",
            "status": "processing",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "1"},
            files={"files": ("User Guide.pdf", b"PDF content here", "application/pdf")},
        )

        assert resp.status_code == 201
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["name"] == "User Guide.pdf"
        assert data[0]["status"] == "processing"
        mock_instance.upload_and_create_document.assert_called_once()

    @patch(PATCH_SERVICE)
    def test_unsupported_file_type(self, mock_service_cls, client_as_member):
        """Postman: Upload Document - Unsupported Type (400)"""
        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "1"},
            files={"files": ("photo.png", b"image data", "image/png")},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "Unsupported file type" in detail
        assert "photo.png" in detail

    @patch(PATCH_SERVICE)
    def test_empty_file(self, mock_service_cls, client_as_member):
        """Postman: Upload Document - Empty File (400)"""
        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "1"},
            files={"files": ("empty.pdf", b"", "application/pdf")},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "empty" in detail.lower()
        assert "empty.pdf" in detail

    def test_missing_agent_id(self, client_as_member):
        """agent_id is required form field -- 422 when missing."""
        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            files={"files": ("test.pdf", b"PDF", "application/pdf")},
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "1"},
            files={"files": ("test.pdf", b"PDF", "application/pdf")},
        )
        assert resp.status_code in (401, 403)

    @patch(PATCH_SERVICE)
    def test_success_docx(self, mock_service_cls, client_as_member):
        """Upload DOCX file type."""
        mock_instance = MagicMock()
        mock_instance.upload_and_create_document.return_value = MagicMock()
        mock_instance._document_response.return_value = {"id": 2, "name": "doc.docx"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "1"},
            files={"files": (
                "doc.docx",
                b"DOCX content",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )},
        )
        assert resp.status_code == 201

    @patch(PATCH_SERVICE)
    def test_success_txt(self, mock_service_cls, client_as_member):
        """Upload TXT file type."""
        mock_instance = MagicMock()
        mock_instance.upload_and_create_document.return_value = MagicMock()
        mock_instance._document_response.return_value = {"id": 3, "name": "readme.txt"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "1"},
            files={"files": ("readme.txt", b"text content", "text/plain")},
        )
        assert resp.status_code == 201

    @patch(PATCH_SERVICE)
    def test_success_csv(self, mock_service_cls, client_as_member):
        """Upload CSV file type."""
        mock_instance = MagicMock()
        mock_instance.upload_and_create_document.return_value = MagicMock()
        mock_instance._document_response.return_value = {"id": 4, "name": "data.csv"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "1"},
            files={"files": ("data.csv", b"a,b,c\n1,2,3", "text/csv")},
        )
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# DELETE /api/v1/document/delete_document
# ---------------------------------------------------------------------------

class TestDeleteDocument:
    """Tests for DELETE /api/v1/document/delete_document"""

    @patch(PATCH_SERVICE)
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Delete Document - Success (200) with multiple IDs."""
        mock_instance = MagicMock()
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete(
            "/api/v1/document/delete_document", params={"document_ids": [1, 2]}
        )

        assert resp.status_code == 200
        assert "2 document(s)" in resp.json()["message"]

    @patch(PATCH_SERVICE)
    def test_single_document(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete(
            "/api/v1/document/delete_document", params={"document_ids": 5}
        )

        assert resp.status_code == 200
        assert "1 document(s)" in resp.json()["message"]

    def test_missing_document_ids(self, client_as_member):
        """document_ids is required query param -- 422 when missing."""
        resp = client_as_member.delete("/api/v1/document/delete_document")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            "/api/v1/document/delete_document", params={"document_ids": 1}
        )
        assert resp.status_code in (401, 403)

    @patch(PATCH_SERVICE)
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.delete_document.side_effect = HTTPException(
            status_code=404, detail="Document not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete(
            "/api/v1/document/delete_document", params={"document_ids": 999}
        )
        assert resp.status_code == 404
