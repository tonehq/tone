"""Tests for Documents API endpoints (EE edition).

Source: ee/api/v1/documents.py
Integration tests — real DB, real endpoints, no mocks.
"""

import io
import pytest


# ---------------------------------------------------------------------------
# POST /api/v1/document/get_documents
# ---------------------------------------------------------------------------

class TestGetDocuments:
    """Tests for POST /api/v1/document/get_documents"""

    def test_get_documents_returns_200(self, client_as_member):
        response = client_as_member.post("/api/v1/document/get_documents", json={})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    def test_get_documents_with_filters(self, client_as_member):
        response = client_as_member.post("/api/v1/document/get_documents", json={
            "agent_id": 1,
            "name": "test",
            "sort": "-created_at",
            "page": 1,
            "page_size": 10,
        })
        assert response.status_code == 200

    def test_get_documents_sort_ascending(self, client_as_member):
        response = client_as_member.post("/api/v1/document/get_documents", json={
            "sort": "created_at",
        })
        assert response.status_code == 200

    def test_get_documents_sort_by_name(self, client_as_member):
        response = client_as_member.post("/api/v1/document/get_documents", json={
            "sort": "name",
        })
        assert response.status_code == 200

    def test_get_documents_sort_by_updated_at(self, client_as_member):
        response = client_as_member.post("/api/v1/document/get_documents", json={
            "sort": "-updated_at",
        })
        assert response.status_code == 200

    def test_invalid_sort_field(self, client_as_member):
        response = client_as_member.post("/api/v1/document/get_documents", json={
            "sort": "invalid_field",
        })
        assert response.status_code == 400
        assert "Invalid sort field" in response.json()["detail"]

    def test_invalid_sort_field_with_desc_prefix(self, client_as_member):
        response = client_as_member.post("/api/v1/document/get_documents", json={
            "sort": "-invalid_field",
        })
        assert response.status_code == 400

    def test_page_zero_rejected(self, client_as_member):
        response = client_as_member.post("/api/v1/document/get_documents", json={
            "page": 0,
        })
        assert response.status_code == 422

    def test_page_size_exceeds_max(self, client_as_member):
        response = client_as_member.post("/api/v1/document/get_documents", json={
            "page_size": 101,
        })
        assert response.status_code == 422

    def test_page_size_zero_rejected(self, client_as_member):
        response = client_as_member.post("/api/v1/document/get_documents", json={
            "page_size": 0,
        })
        assert response.status_code == 422

    def test_negative_page_rejected(self, client_as_member):
        response = client_as_member.post("/api/v1/document/get_documents", json={
            "page": -1,
        })
        assert response.status_code == 422

    def test_empty_results(self, client_as_member):
        """Querying with a non-existent agent_id returns empty data."""
        response = client_as_member.post("/api/v1/document/get_documents", json={
            "agent_id": 999999,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 0
        assert data["data"] == []

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/document/get_documents", json={})
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/document/upload_document
# ---------------------------------------------------------------------------

class TestUploadDocument:
    """Tests for POST /api/v1/document/upload_document"""

    def test_unsupported_file_type(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "1"},
            files=[("files", ("image.png", io.BytesIO(b"\x89PNG fake"), "image/png"))],
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_empty_file_rejected(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "1"},
            files=[("files", ("empty.pdf", io.BytesIO(b""), "application/pdf"))],
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_missing_agent_id(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/document/upload_document",
            files=[("files", ("test.pdf", io.BytesIO(b"%PDF content"), "application/pdf"))],
        )
        assert response.status_code == 422

    def test_missing_files(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "1"},
        )
        assert response.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "1"},
            files=[("files", ("test.pdf", io.BytesIO(b"%PDF content"), "application/pdf"))],
        )
        assert response.status_code in (401, 403)

    def test_unsupported_type_in_multi_upload(self, client_as_member):
        """If any file has unsupported type, the request fails."""
        response = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "1"},
            files=[
                ("files", ("img.jpg", io.BytesIO(b"\xff\xd8 fake"), "image/jpeg")),
                ("files", ("doc.pdf", io.BytesIO(b"%PDF content"), "application/pdf")),
            ],
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/v1/document/delete_document
# ---------------------------------------------------------------------------

class TestDeleteDocument:
    """Tests for DELETE /api/v1/document/delete_document"""

    def test_delete_not_found(self, client_as_member):
        response = client_as_member.delete(
            "/api/v1/document/delete_document", params={"document_ids": 999999}
        )
        assert response.status_code == 404

    def test_missing_document_ids(self, client_as_member):
        response = client_as_member.delete("/api/v1/document/delete_document")
        assert response.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete(
            "/api/v1/document/delete_document", params={"document_ids": 1}
        )
        assert response.status_code in (401, 403)
