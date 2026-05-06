"""Tests for Documents API endpoints (Core edition).

Source: core/api/v1/documents.py
"""

import pytest
from io import BytesIO
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/document/get_documents
# ---------------------------------------------------------------------------
class TestGetDocuments:
    @patch("ee.api.v1.documents.DocumentService")
    def test_success_defaults(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_documents_by_agent.return_value = {
            "data": [{"id": 1, "name": "doc.pdf"}],
            "total": 1,
            "page": 1,
            "page_size": 10,
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

    @patch("ee.api.v1.documents.DocumentService")
    def test_with_filters(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_documents_by_agent.return_value = {"data": [], "total": 0}
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

    @patch("ee.api.v1.documents.DocumentService")
    def test_sort_desc(self, mock_service_cls, client_as_member):
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
        resp = client_as_member.post("/api/v1/document/get_documents", json={
            "sort": "-invalid_field",
        })
        assert resp.status_code == 400
        assert "Invalid sort field" in resp.json()["detail"]

    def test_invalid_page(self, client_as_member):
        resp = client_as_member.post("/api/v1/document/get_documents", json={
            "page": 0,
        })
        assert resp.status_code == 422

    def test_invalid_page_size(self, client_as_member):
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
    @patch("ee.api.v1.documents.DocumentService")
    def test_success_pdf(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.upload_and_create_document.return_value = MagicMock()
        mock_instance._document_response.return_value = {"id": 1, "name": "test.pdf"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "1"},
            files={"files": ("test.pdf", b"PDF content here", "application/pdf")},
        )

        assert resp.status_code == 201
        mock_instance.upload_and_create_document.assert_called_once()

    @patch("ee.api.v1.documents.DocumentService")
    def test_unsupported_file_type(self, mock_service_cls, client_as_member):
        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "1"},
            files={"files": ("test.exe", b"binary", "application/x-msdownload")},
        )
        assert resp.status_code == 400
        assert "Unsupported file type" in resp.json()["detail"]

    @patch("ee.api.v1.documents.DocumentService")
    def test_empty_file(self, mock_service_cls, client_as_member):
        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "1"},
            files={"files": ("test.pdf", b"", "application/pdf")},
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_missing_agent_id(self, client_as_member):
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


# ---------------------------------------------------------------------------
# DELETE /api/v1/document/delete_document
# ---------------------------------------------------------------------------
class TestDeleteDocument:
    @patch("ee.api.v1.documents.DocumentService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete(
            "/api/v1/document/delete_document", params={"document_ids": [1, 2]}
        )

        assert resp.status_code == 200
        assert "2 document(s)" in resp.json()["message"]

    @patch("ee.api.v1.documents.DocumentService")
    def test_single_document(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete(
            "/api/v1/document/delete_document", params={"document_ids": 5}
        )

        assert resp.status_code == 200
        assert "1 document(s)" in resp.json()["message"]

    def test_missing_document_ids(self, client_as_member):
        resp = client_as_member.delete("/api/v1/document/delete_document")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            "/api/v1/document/delete_document", params={"document_ids": 1}
        )
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.documents.DocumentService")
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
