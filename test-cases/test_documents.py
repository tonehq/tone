"""Tests for Documents API endpoints.

Source: core/api/v1/documents.py / ee/api/v1/documents.py
Patches target the active edition's module (ee when EE is enabled, core otherwise).
"""

import io
import time
import pytest
from uuid import UUID
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials

from main import app, api_v1
from core.middleware.auth import (
    JWTClaims, get_jwt_claims, require_org_member,
    require_admin_or_owner, require_owner, security,
)
from core.database.session import get_db

# EE auth deps
try:
    from ee.middleware.auth import (
        get_ee_jwt_claims, get_ee_current_user,
        require_ee_org_member, require_ee_admin_or_owner, require_ee_owner,
    )
    _HAS_EE = True
except ImportError:
    _HAS_EE = False

# Detect which edition is active to patch the correct module
try:
    from core.internal.capabilities import is_ee_enabled as _is_ee_enabled
    _EE = _is_ee_enabled()
except Exception:
    _EE = False

_PATCH_MODULE = "ee.api.v1.documents" if _EE else "core.api.v1.documents"
EXPECTED_ORG_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


# ---------------------------------------------------------------------------
# Auth helpers & client fixtures (self-contained for this test file)
# ---------------------------------------------------------------------------

def _fake_security():
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")


def _make_claims(role="member"):
    now = int(time.time())
    return JWTClaims(
        user_id=1,
        org_id="550e8400-e29b-41d4-a716-446655440000",
        role=role,
        email="test@example.com",
        iat=now,
        exp=now + 3600,
    )


def _override_auth(claims):
    def _override():
        return claims
    return _override


def _apply_overrides(claims, mock_db):
    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides[get_jwt_claims] = _override_auth(claims)
    api_v1.dependency_overrides[require_org_member] = _override_auth(claims)
    api_v1.dependency_overrides[require_admin_or_owner] = _override_auth(claims)
    api_v1.dependency_overrides[require_owner] = _override_auth(claims)
    if _HAS_EE:
        api_v1.dependency_overrides[get_ee_jwt_claims] = _override_auth(claims)
        api_v1.dependency_overrides[get_ee_current_user] = _override_auth(claims)
        api_v1.dependency_overrides[require_ee_org_member] = _override_auth(claims)
        api_v1.dependency_overrides[require_ee_admin_or_owner] = _override_auth(claims)
        api_v1.dependency_overrides[require_ee_owner] = _override_auth(claims)


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value = db
    db.filter.return_value = db
    db.first.return_value = None
    db.all.return_value = []
    db.commit.return_value = None
    db.refresh.return_value = None
    db.add.return_value = None
    db.delete.return_value = None
    db.count.return_value = 0
    return db


@pytest.fixture
def client_as_member(mock_db):
    _apply_overrides(_make_claims("member"), mock_db)
    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_unauthenticated(mock_db):
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_document():
    return {
        "id": 1,
        "uuid": "aabbccdd-1234-5678-9999-000000000001",
        "upload_id": 10,
        "agent_id": 5,
        "file_name": "test_doc.pdf",
        "content_type": "application/pdf",
        "file_size_bytes": 1024,
        "url": "https://r2.example.com/presigned-url",
        "status": "ready",
        "meta_data": None,
        "created_at": 1700000000,
        "updated_at": 1700000000,
    }


@pytest.fixture
def sample_documents_response(sample_document):
    return {
        "data": [sample_document],
        "pagination": {
            "page": 1,
            "page_size": 10,
            "total": 1,
            "total_pages": 1,
        },
    }


# ---------------------------------------------------------------------------
# POST /api/v1/document/get_documents
# ---------------------------------------------------------------------------

class TestGetDocuments:
    """Tests for POST /api/v1/document/get_documents"""

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_success_defaults(self, mock_svc_cls, client_as_member, sample_documents_response):
        mock_svc_cls.return_value.get_documents_by_agent.return_value = sample_documents_response
        resp = client_as_member.post("/api/v1/document/get_documents", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "pagination" in data
        mock_svc_cls.return_value.get_documents_by_agent.assert_called_once_with(
            agent_id=None,
            name=None,
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=10,
        )

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_success_with_agent_filter(self, mock_svc_cls, client_as_member, sample_documents_response):
        mock_svc_cls.return_value.get_documents_by_agent.return_value = sample_documents_response
        resp = client_as_member.post("/api/v1/document/get_documents", json={
            "agent_id": 5,
            "name": "test",
            "sort": "name",
            "page": 2,
            "page_size": 25,
        })
        assert resp.status_code == 200
        mock_svc_cls.return_value.get_documents_by_agent.assert_called_once_with(
            agent_id=5,
            name="test",
            sort_by="name",
            sort_order="asc",
            page=2,
            page_size=25,
        )

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_sort_descending(self, mock_svc_cls, client_as_member, sample_documents_response):
        mock_svc_cls.return_value.get_documents_by_agent.return_value = sample_documents_response
        resp = client_as_member.post("/api/v1/document/get_documents", json={
            "sort": "-updated_at",
        })
        assert resp.status_code == 200
        mock_svc_cls.return_value.get_documents_by_agent.assert_called_once_with(
            agent_id=None,
            name=None,
            sort_by="updated_at",
            sort_order="desc",
            page=1,
            page_size=10,
        )

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_sort_ascending_created_at(self, mock_svc_cls, client_as_member, sample_documents_response):
        mock_svc_cls.return_value.get_documents_by_agent.return_value = sample_documents_response
        resp = client_as_member.post("/api/v1/document/get_documents", json={
            "sort": "created_at",
        })
        assert resp.status_code == 200
        mock_svc_cls.return_value.get_documents_by_agent.assert_called_once_with(
            agent_id=None,
            name=None,
            sort_by="created_at",
            sort_order="asc",
            page=1,
            page_size=10,
        )

    def test_invalid_sort_field(self, client_as_member):
        resp = client_as_member.post("/api/v1/document/get_documents", json={
            "sort": "invalid_field",
        })
        assert resp.status_code == 400
        assert "Invalid sort field" in resp.json()["detail"]

    def test_invalid_sort_field_with_desc_prefix(self, client_as_member):
        resp = client_as_member.post("/api/v1/document/get_documents", json={
            "sort": "-invalid_field",
        })
        assert resp.status_code == 400
        assert "Invalid sort field" in resp.json()["detail"]

    def test_page_zero_rejected(self, client_as_member):
        resp = client_as_member.post("/api/v1/document/get_documents", json={"page": 0})
        assert resp.status_code == 422

    def test_page_size_exceeds_max(self, client_as_member):
        resp = client_as_member.post("/api/v1/document/get_documents", json={"page_size": 101})
        assert resp.status_code == 422

    def test_page_size_zero_rejected(self, client_as_member):
        resp = client_as_member.post("/api/v1/document/get_documents", json={"page_size": 0})
        assert resp.status_code == 422

    def test_negative_page_rejected(self, client_as_member):
        resp = client_as_member.post("/api/v1/document/get_documents", json={"page": -1})
        assert resp.status_code == 422

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_empty_results(self, mock_svc_cls, client_as_member):
        mock_svc_cls.return_value.get_documents_by_agent.return_value = {
            "data": [],
            "pagination": {"page": 1, "page_size": 10, "total": 0, "total_pages": 0},
        }
        resp = client_as_member.post("/api/v1/document/get_documents", json={})
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] == 0
        assert resp.json()["data"] == []

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_with_name_filter_only(self, mock_svc_cls, client_as_member, sample_documents_response):
        mock_svc_cls.return_value.get_documents_by_agent.return_value = sample_documents_response
        resp = client_as_member.post("/api/v1/document/get_documents", json={"name": "report"})
        assert resp.status_code == 200
        mock_svc_cls.return_value.get_documents_by_agent.assert_called_once_with(
            agent_id=None,
            name="report",
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=10,
        )

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/document/get_documents", json={})
        assert resp.status_code in (401, 403)

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_service_error(self, mock_svc_cls, client_as_member):
        mock_svc_cls.return_value.get_documents_by_agent.side_effect = Exception("DB error")
        with pytest.raises(Exception, match="DB error"):
            client_as_member.post("/api/v1/document/get_documents", json={})


# ---------------------------------------------------------------------------
# POST /api/v1/document/upload_document
# ---------------------------------------------------------------------------

class TestUploadDocument:
    """Tests for POST /api/v1/document/upload_document"""

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_upload_single_pdf(self, mock_svc_cls, client_as_member, sample_document):
        mock_doc = MagicMock()
        mock_svc_cls.return_value.upload_and_create_document.return_value = mock_doc
        mock_svc_cls.return_value._document_response.return_value = sample_document

        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "5"},
            files=[("files", ("test.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf"))],
        )
        assert resp.status_code == 201
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 1
        mock_svc_cls.return_value.upload_and_create_document.assert_called_once_with(
            agent_id=5,
            file_bytes=b"%PDF-1.4 fake",
            file_name="test.pdf",
            content_type="application/pdf",
        )

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_upload_multiple_files(self, mock_svc_cls, client_as_member, sample_document):
        mock_doc = MagicMock()
        mock_svc_cls.return_value.upload_and_create_document.return_value = mock_doc
        mock_svc_cls.return_value._document_response.return_value = sample_document

        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "5"},
            files=[
                ("files", ("doc1.pdf", io.BytesIO(b"%PDF content 1"), "application/pdf")),
                ("files", ("doc2.txt", io.BytesIO(b"text content"), "text/plain")),
            ],
        )
        assert resp.status_code == 201
        assert len(resp.json()) == 2

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_upload_docx(self, mock_svc_cls, client_as_member, sample_document):
        mock_doc = MagicMock()
        mock_svc_cls.return_value.upload_and_create_document.return_value = mock_doc
        mock_svc_cls.return_value._document_response.return_value = sample_document

        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "5"},
            files=[("files", ("doc.docx", io.BytesIO(b"PK\x03\x04 fake docx"),
                              "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
        )
        assert resp.status_code == 201

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_upload_csv(self, mock_svc_cls, client_as_member, sample_document):
        mock_doc = MagicMock()
        mock_svc_cls.return_value.upload_and_create_document.return_value = mock_doc
        mock_svc_cls.return_value._document_response.return_value = sample_document

        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "5"},
            files=[("files", ("data.csv", io.BytesIO(b"a,b,c\n1,2,3"), "text/csv"))],
        )
        assert resp.status_code == 201

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_upload_txt(self, mock_svc_cls, client_as_member, sample_document):
        mock_doc = MagicMock()
        mock_svc_cls.return_value.upload_and_create_document.return_value = mock_doc
        mock_svc_cls.return_value._document_response.return_value = sample_document

        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "5"},
            files=[("files", ("notes.txt", io.BytesIO(b"Hello world"), "text/plain"))],
        )
        assert resp.status_code == 201

    def test_unsupported_file_type_png(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "5"},
            files=[("files", ("image.png", io.BytesIO(b"\x89PNG fake"), "image/png"))],
        )
        assert resp.status_code == 400
        assert "Unsupported file type" in resp.json()["detail"]

    def test_unsupported_file_type_json(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "5"},
            files=[("files", ("data.json", io.BytesIO(b'{"a":1}'), "application/json"))],
        )
        assert resp.status_code == 400
        assert "Unsupported file type" in resp.json()["detail"]

    def test_empty_file_rejected(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "5"},
            files=[("files", ("empty.pdf", io.BytesIO(b""), "application/pdf"))],
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_missing_agent_id(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            files=[("files", ("test.pdf", io.BytesIO(b"%PDF content"), "application/pdf"))],
        )
        assert resp.status_code == 422

    def test_missing_files(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "5"},
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "5"},
            files=[("files", ("test.pdf", io.BytesIO(b"%PDF content"), "application/pdf"))],
        )
        assert resp.status_code in (401, 403)

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_service_error(self, mock_svc_cls, client_as_member):
        mock_svc_cls.return_value.upload_and_create_document.side_effect = Exception("R2 error")
        with pytest.raises(Exception, match="R2 error"):
            client_as_member.post(
                "/api/v1/document/upload_document",
                data={"agent_id": "5"},
                files=[("files", ("test.pdf", io.BytesIO(b"%PDF content"), "application/pdf"))],
            )

    def test_unsupported_type_in_multi_upload_fails_fast(self, client_as_member):
        """If any file in a batch has unsupported type, the whole request fails."""
        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "5"},
            files=[
                ("files", ("doc.pdf", io.BytesIO(b"%PDF content"), "application/pdf")),
                ("files", ("img.png", io.BytesIO(b"\x89PNG fake"), "image/png")),
            ],
        )
        assert resp.status_code == 400
        assert "Unsupported file type" in resp.json()["detail"]

    def test_empty_file_in_multi_upload(self, client_as_member):
        """If any file in a batch is empty, the request fails."""
        resp = client_as_member.post(
            "/api/v1/document/upload_document",
            data={"agent_id": "5"},
            files=[
                ("files", ("doc.pdf", io.BytesIO(b"%PDF content"), "application/pdf")),
                ("files", ("empty.txt", io.BytesIO(b""), "text/plain")),
            ],
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# DELETE /api/v1/document/delete_document
# ---------------------------------------------------------------------------

class TestDeleteDocument:
    """Tests for DELETE /api/v1/document/delete_document"""

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_delete_single_document(self, mock_svc_cls, client_as_member):
        mock_svc_cls.return_value.delete_document.return_value = {"message": "Document deleted successfully"}
        resp = client_as_member.delete(
            "/api/v1/document/delete_document", params={"document_ids": 1}
        )
        assert resp.status_code == 200
        assert "deleted successfully" in resp.json()["message"]
        mock_svc_cls.return_value.delete_document.assert_called_once_with(1)

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_delete_multiple_documents(self, mock_svc_cls, client_as_member):
        mock_svc_cls.return_value.delete_document.return_value = {"message": "Document deleted successfully"}
        resp = client_as_member.delete(
            "/api/v1/document/delete_document", params={"document_ids": [1, 2, 3]}
        )
        assert resp.status_code == 200
        assert "3 document(s) deleted" in resp.json()["message"]
        assert mock_svc_cls.return_value.delete_document.call_count == 3

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_delete_not_found(self, mock_svc_cls, client_as_member):
        mock_svc_cls.return_value.delete_document.side_effect = HTTPException(
            status_code=404, detail="Document not found"
        )
        resp = client_as_member.delete(
            "/api/v1/document/delete_document", params={"document_ids": 999}
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_missing_document_ids(self, client_as_member):
        resp = client_as_member.delete("/api/v1/document/delete_document")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            "/api/v1/document/delete_document", params={"document_ids": 1}
        )
        assert resp.status_code in (401, 403)

    @patch(f"{_PATCH_MODULE}.DocumentService")
    def test_service_error(self, mock_svc_cls, client_as_member):
        mock_svc_cls.return_value.delete_document.side_effect = Exception("DB error")
        with pytest.raises(Exception, match="DB error"):
            client_as_member.delete(
                "/api/v1/document/delete_document", params={"document_ids": 1}
            )
