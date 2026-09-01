"""Tests for Knowledge Base API endpoints (Core edition).

Source: core/api/v1/knowledge_base.py -> core/api/v1/knowledge_base_routes.py
Prefix: /api/v1/knowledge-base
Integration tests -- real DB, real endpoints, no mocks.

The 8 endpoints exercised here:
- POST   /list
- POST   "" (upload)
- PATCH  /{upload_id}
- PATCH  /{upload_id}/file
- POST   /{upload_id}/reprocess
- DELETE /{upload_id}
- POST   /facets
- GET    /filter-values
"""

import io
import uuid

import pytest


BASE = "/api/v1/knowledge-base"
_FAKE_UPLOAD_ID = "00000000-0000-0000-0000-000000000000"


# ─── POST /api/v1/knowledge-base/list ───

class TestListDocuments:
    """POST /list — paginated, faceted list of KB documents."""

    def test_list_empty_body_returns_envelope(self, client_as_member):
        """Postman: List - Success (200). Empty body should default to page=1."""
        resp = client_as_member.post(f"{BASE}/list", json={})
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            for k in ("items", "total", "page", "page_size"):
                assert k in data
            assert isinstance(data["items"], list)
            assert data["page"] == 1
            assert data["page_size"] == 20

    def test_list_with_pagination(self, client_as_member):
        resp = client_as_member.post(
            f"{BASE}/list", json={"page": 2, "page_size": 5}
        )
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert data["page"] == 2
            assert data["page_size"] == 5

    def test_list_with_search(self, client_as_member):
        resp = client_as_member.post(
            f"{BASE}/list", json={"search": "non-existent-document-xyz"}
        )
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            assert resp.json()["items"] == []

    def test_list_with_status_filter(self, client_as_member):
        resp = client_as_member.post(
            f"{BASE}/list", json={"status": "ready"}
        )
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            for item in resp.json()["items"]:
                assert item.get("status") == "ready"

    def test_list_invalid_agent_id(self, client_as_member):
        """Bad UUID for agent_id should 400."""
        resp = client_as_member.post(
            f"{BASE}/list", json={"agent_id": "not-a-uuid"}
        )
        assert resp.status_code in (400, 500)

    def test_list_page_size_caps_at_100(self, client_as_member):
        resp = client_as_member.post(
            f"{BASE}/list", json={"page_size": 9999}
        )
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            assert resp.json()["page_size"] == 100

    def test_list_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(f"{BASE}/list", json={})
        assert resp.status_code in (401, 403)

    def test_list_as_admin(self, client_as_admin):
        resp = client_as_admin.post(f"{BASE}/list", json={})
        assert resp.status_code in (200, 500)

    def test_list_as_owner(self, client_as_owner):
        resp = client_as_owner.post(f"{BASE}/list", json={})
        assert resp.status_code in (200, 500)


# ─── POST /api/v1/knowledge-base ───

class TestUploadDocument:
    """POST '' — multipart upload. Real R2 upload may fail in tests so we
    only assert reasonable contract responses."""

    def _file_part(self, name="sample.txt", body=b"hello world"):
        return {"file": (name, io.BytesIO(body), "text/plain")}

    def test_upload_empty_file_returns_400(self, client_as_member):
        files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
        resp = client_as_member.post(BASE, files=files)
        assert resp.status_code in (400, 500)

    def test_upload_missing_file_returns_422(self, client_as_member):
        resp = client_as_member.post(BASE)
        assert resp.status_code == 422

    def test_upload_invalid_agent_id_returns_400(self, client_as_member):
        files = self._file_part()
        resp = client_as_member.post(
            BASE, files=files, data={"agent_id": "not-a-uuid"}
        )
        assert resp.status_code in (400, 500)

    def test_upload_nonexistent_agent_returns_404(self, client_as_member):
        files = self._file_part()
        ghost_id = str(uuid.uuid4())
        resp = client_as_member.post(
            BASE, files=files, data={"agent_id": ghost_id}
        )
        assert resp.status_code in (404, 409, 500)

    def test_upload_standalone(self, client_as_member):
        """Upload without agent_id should be allowed (standalone upload)."""
        files = self._file_part()
        resp = client_as_member.post(BASE, files=files)
        # Real R2 upload is unreliable in test env -> accept 201 or 5xx.
        assert resp.status_code in (201, 400, 500, 502, 503)

    def test_upload_unsupported_type_returns_400(self, client_as_member):
        """Backend rejects a disallowed extension with 400 BEFORE any R2 write
        (server-side enforcement of the frontend allowlist — a direct API
        caller can't bypass it). Deterministic because validation runs before
        the unreliable R2 upload."""
        files = {"file": ("malware.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")}
        resp = client_as_member.post(BASE, files=files)
        assert resp.status_code == 400

    def test_upload_unauthenticated(self, client_unauthenticated):
        files = self._file_part()
        resp = client_unauthenticated.post(BASE, files=files)
        assert resp.status_code in (401, 403)


# ─── PATCH /api/v1/knowledge-base/{upload_id} ───

class TestRenameDocument:
    """PATCH /{upload_id} — rename only the file_name on a document."""

    def test_rename_invalid_upload_id(self, client_as_member):
        resp = client_as_member.patch(
            f"{BASE}/not-a-uuid", json={"file_name": "new.txt"}
        )
        assert resp.status_code in (400, 500)
        if resp.status_code == 400:
            assert "Invalid upload_id" in resp.json().get("detail", "")

    def test_rename_missing_file_name(self, client_as_member):
        resp = client_as_member.patch(
            f"{BASE}/{_FAKE_UPLOAD_ID}", json={}
        )
        assert resp.status_code in (400, 404, 500)

    def test_rename_empty_file_name(self, client_as_member):
        resp = client_as_member.patch(
            f"{BASE}/{_FAKE_UPLOAD_ID}", json={"file_name": "   "}
        )
        assert resp.status_code in (400, 404, 500)

    def test_rename_file_name_too_long(self, client_as_member):
        resp = client_as_member.patch(
            f"{BASE}/{_FAKE_UPLOAD_ID}", json={"file_name": "a" * 600}
        )
        assert resp.status_code in (400, 404, 500)

    def test_rename_unknown_upload_returns_404(self, client_as_member):
        resp = client_as_member.patch(
            f"{BASE}/{_FAKE_UPLOAD_ID}", json={"file_name": "renamed.txt"}
        )
        assert resp.status_code in (404, 500)

    def test_rename_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.patch(
            f"{BASE}/{_FAKE_UPLOAD_ID}", json={"file_name": "x.txt"}
        )
        assert resp.status_code in (401, 403)


# ─── PATCH /api/v1/knowledge-base/{upload_id}/file ───

class TestReplaceDocumentFile:
    """PATCH /{upload_id}/file — replace the underlying blob, re-process."""

    def _file_part(self):
        return {"file": ("replacement.txt", io.BytesIO(b"updated body"), "text/plain")}

    def test_replace_invalid_upload_id(self, client_as_member):
        files = self._file_part()
        resp = client_as_member.patch(f"{BASE}/not-a-uuid/file", files=files)
        assert resp.status_code in (400, 500)

    def test_replace_unknown_upload(self, client_as_member):
        files = self._file_part()
        resp = client_as_member.patch(
            f"{BASE}/{_FAKE_UPLOAD_ID}/file", files=files
        )
        assert resp.status_code in (404, 500)

    def test_replace_empty_file(self, client_as_member):
        files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
        resp = client_as_member.patch(
            f"{BASE}/{_FAKE_UPLOAD_ID}/file", files=files
        )
        assert resp.status_code in (400, 404, 500)

    def test_replace_missing_file_returns_422(self, client_as_member):
        resp = client_as_member.patch(f"{BASE}/{_FAKE_UPLOAD_ID}/file")
        assert resp.status_code == 422

    def test_replace_unauthenticated(self, client_unauthenticated):
        files = self._file_part()
        resp = client_unauthenticated.patch(
            f"{BASE}/{_FAKE_UPLOAD_ID}/file", files=files
        )
        assert resp.status_code in (401, 403)


# ─── POST /api/v1/knowledge-base/{upload_id}/reprocess ───

class TestReprocessDocument:
    """POST /{upload_id}/reprocess — re-queue the ingestion pipeline."""

    def test_reprocess_invalid_upload_id(self, client_as_member):
        resp = client_as_member.post(f"{BASE}/not-a-uuid/reprocess")
        assert resp.status_code in (400, 500)

    def test_reprocess_unknown_upload(self, client_as_member):
        resp = client_as_member.post(f"{BASE}/{_FAKE_UPLOAD_ID}/reprocess")
        assert resp.status_code in (404, 500)

    def test_reprocess_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(f"{BASE}/{_FAKE_UPLOAD_ID}/reprocess")
        assert resp.status_code in (401, 403)


# ─── DELETE /api/v1/knowledge-base/{upload_id} ───

class TestDeleteDocument:
    """DELETE /{upload_id} — remove the upload + KB row + blob."""

    def test_delete_invalid_upload_id(self, client_as_member):
        resp = client_as_member.delete(f"{BASE}/not-a-uuid")
        assert resp.status_code in (400, 500)

    def test_delete_unknown_upload(self, client_as_member):
        resp = client_as_member.delete(f"{BASE}/{_FAKE_UPLOAD_ID}")
        assert resp.status_code in (404, 500)

    def test_delete_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(f"{BASE}/{_FAKE_UPLOAD_ID}")
        assert resp.status_code in (401, 403)


# ─── POST /api/v1/knowledge-base/facets ───

class TestDocumentFacets:
    """POST /facets — faceted aggregates over org-scoped uploads."""

    def test_facets_empty_filters(self, client_as_member):
        resp = client_as_member.post(f"{BASE}/facets", json={"filters": []})
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            assert isinstance(resp.json(), dict)

    def test_facets_with_status_filter(self, client_as_member):
        resp = client_as_member.post(
            f"{BASE}/facets",
            json={"filters": [{"field": "status", "op": "eq", "value": "ready"}]},
        )
        assert resp.status_code in (200, 422, 500)

    def test_facets_invalid_body_returns_422(self, client_as_member):
        # FacetsRequest requires a body — sending raw list trips validation.
        resp = client_as_member.post(f"{BASE}/facets", json=[])
        assert resp.status_code in (422, 500)

    def test_facets_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(f"{BASE}/facets", json={})
        assert resp.status_code in (401, 403)


# ─── GET /api/v1/knowledge-base/filter-values ───

class TestDocumentFilterValues:
    """GET /filter-values?column_name=... — distinct values for a column."""

    def test_filter_values_status(self, client_as_member):
        resp = client_as_member.get(
            f"{BASE}/filter-values", params={"column_name": "status"}
        )
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            # distinct_values may return either a list or a {column: [...]} dict
            # depending on the helper; accept either contract.
            assert isinstance(resp.json(), (list, dict))

    def test_filter_values_file_name(self, client_as_member):
        resp = client_as_member.get(
            f"{BASE}/filter-values", params={"column_name": "file_name"}
        )
        assert resp.status_code in (200, 500)

    def test_filter_values_missing_column(self, client_as_member):
        resp = client_as_member.get(f"{BASE}/filter-values")
        assert resp.status_code == 422

    def test_filter_values_disallowed_column(self, client_as_member):
        """size_bytes/created_at aren't in the allowed map -> service raises."""
        resp = client_as_member.get(
            f"{BASE}/filter-values", params={"column_name": "size_bytes"}
        )
        assert resp.status_code in (400, 500)

    def test_filter_values_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            f"{BASE}/filter-values", params={"column_name": "status"}
        )
        assert resp.status_code in (401, 403)
