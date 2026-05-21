"""Tests for Generated API Keys endpoints (Core edition).

Source: core/api/v1/generated_api_keys.py
Postman: postman_collection/generated_api_keys.postman_collection.json
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/generated-api-keys/upsert
# ---------------------------------------------------------------------------
class TestUpsertBasicKey:
    @patch("core.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_create_success(self, mock_service_cls, client_as_admin):
        """Postman: Upsert Basic Key - Create (200)."""
        mock_instance = MagicMock()
        mock_instance.upsert_basic_key.return_value = {
            "id": 1,
            "name": "Production Key",
            "key_value": "tone_pk_abc123def456",
            "status": "active",
            "created_at": "2026-01-15T10:00:00",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert",
            json={"name": "Production Key", "key_value": "tone_pk_abc123def456"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Production Key"
        assert data["status"] == "active"
        mock_instance.upsert_basic_key.assert_called_once_with(
            name="Production Key",
            key_value="tone_pk_abc123def456",
            key_id=None,
        )

    @patch("core.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_update_existing(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_basic_key.return_value = {"id": 5, "name": "Updated Key"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert",
            params={"id": 5},
            json={"name": "Updated Key", "key_value": "pk_live_xyz789"},
        )

        assert resp.status_code == 200
        mock_instance.upsert_basic_key.assert_called_once_with(
            name="Updated Key",
            key_value="pk_live_xyz789",
            key_id=5,
        )

    def test_missing_name(self, client_as_admin):
        """Postman: Upsert Basic Key - Missing Fields (400) -- missing name."""
        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert",
            json={"key_value": "pk_live_abc123"},
        )
        assert resp.status_code == 400
        assert "name and key_value are required" in resp.json()["detail"]

    def test_missing_key_value(self, client_as_admin):
        """Postman: Upsert Basic Key - Missing Fields (400) -- missing key_value."""
        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert",
            json={"name": "My Key"},
        )
        assert resp.status_code == 400
        assert "name and key_value are required" in resp.json()["detail"]

    @patch("core.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_service_error(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_basic_key.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert",
            json={"name": "Key", "key_value": "val"},
        )
        assert resp.status_code in (500, 422, 400)

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/generated-api-keys/upsert",
            json={"name": "Key", "key_value": "val"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/generated-api-keys/upsert-full
# ---------------------------------------------------------------------------
class TestUpsertFullKey:
    @patch("core.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_create_success(self, mock_service_cls, client_as_admin):
        """Postman: Upsert Full Key - Create (200)."""
        mock_instance = MagicMock()
        mock_instance.upsert_full_key.return_value = {
            "id": 1,
            "name": "Production Key",
            "key_value": "tone_pk_abc123def456",
            "domains": ["example.com"],
            "abuse_prevention": {"is_toggled": True},
            "fraud_protection": True,
            "status": "active",
        }
        mock_service_cls.return_value = mock_instance

        abuse_config = {
            "is_toggled": True,
            "recaptcha_secret_key": "6Lc...",
            "threshold": 0.5,
        }

        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert-full",
            json={
                "name": "Production Key",
                "key_value": "tone_pk_abc123def456",
                "domains": ["example.com", "api.example.com"],
                "abuse_prevention": abuse_config,
                "fraud_protection": True,
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Production Key"
        assert data["fraud_protection"] is True
        mock_instance.upsert_full_key.assert_called_once_with(
            name="Production Key",
            key_value="tone_pk_abc123def456",
            key_id=None,
            domains=["example.com", "api.example.com"],
            abuse_prevention=abuse_config,
            fraud_protection=True,
        )

    @patch("core.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_minimal_fields(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_full_key.return_value = {"id": 1, "name": "Full Key"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert-full",
            json={"name": "Full Key", "key_value": "pk_live_full"},
        )

        assert resp.status_code == 200
        mock_instance.upsert_full_key.assert_called_once_with(
            name="Full Key",
            key_value="pk_live_full",
            key_id=None,
            domains=None,
            abuse_prevention=None,
            fraud_protection=None,
        )

    @patch("core.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_update_with_id(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_full_key.return_value = {"id": 10}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert-full",
            params={"id": 10},
            json={
                "name": "Full Key",
                "key_value": "pk_live_full",
                "domains": ["example.com"],
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_full_key.assert_called_once_with(
            name="Full Key",
            key_value="pk_live_full",
            key_id=10,
            domains=["example.com"],
            abuse_prevention=None,
            fraud_protection=None,
        )

    def test_missing_name(self, client_as_admin):
        """Postman: Upsert Full Key - Missing Fields (400)."""
        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert-full",
            json={"key_value": "pk_live_full"},
        )
        assert resp.status_code == 400

    def test_missing_key_value(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert-full",
            json={"name": "Full Key"},
        )
        assert resp.status_code == 400

    @patch("core.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_service_error(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_full_key.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert-full",
            json={"name": "Key", "key_value": "val"},
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/generated-api-keys/list
# ---------------------------------------------------------------------------
class TestListGeneratedApiKeys:
    @patch("core.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get All Keys - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.get_all_keys.return_value = [
            {
                "id": 1,
                "name": "Production Key",
                "key_value": "tone_pk_abc***",
                "status": "active",
                "created_at": "2026-01-15T10:00:00",
            }
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/generated-api-keys/list")

        assert resp.status_code == 200
        assert len(resp.json()) == 1
        mock_instance.get_all_keys.assert_called_once()

    @patch("core.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_empty_list(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_keys.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/generated-api-keys/list")

        assert resp.status_code == 200
        assert resp.json() == []

    @patch("core.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_keys.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/generated-api-keys/list")
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/generated-api-keys/get
# ---------------------------------------------------------------------------
class TestGetGeneratedApiKey:
    @patch("core.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get Key - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.get_key_by_id.return_value = {
            "id": 1,
            "name": "Production Key",
            "key_value": "tone_pk_abc123def456",
            "status": "active",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/generated-api-keys/get", params={"key_id": 1}
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == 1
        mock_instance.get_key_by_id.assert_called_once_with(1)

    @patch("core.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_not_found(self, mock_service_cls, client_as_member):
        """Postman: Get Key - Not Found (404)."""
        mock_instance = MagicMock()
        mock_instance.get_key_by_id.side_effect = HTTPException(
            status_code=404, detail="API key not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/generated-api-keys/get", params={"key_id": 999}
        )
        assert resp.status_code == 404

    def test_missing_key_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/generated-api-keys/get")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/v1/generated-api-keys/delete
# ---------------------------------------------------------------------------
class TestDeleteGeneratedApiKey:
    @patch("core.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_success(self, mock_service_cls, client_as_admin):
        """Postman: Delete Key - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.delete_key.return_value = {
            "message": "API key deleted successfully"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/generated-api-keys/delete", params={"key_id": 1}
        )

        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()
        mock_instance.delete_key.assert_called_once_with(1)

    @patch("core.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_not_found(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_key.side_effect = HTTPException(
            status_code=404, detail="Not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/generated-api-keys/delete", params={"key_id": 999}
        )
        assert resp.status_code == 404

    def test_missing_key_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/generated-api-keys/delete")
        assert resp.status_code == 422
