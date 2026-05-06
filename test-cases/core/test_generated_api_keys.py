"""Tests for Generated API Keys endpoints (Core edition).

Source: core/api/v1/generated_api_keys.py
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/generated-api-keys/upsert
# ---------------------------------------------------------------------------
class TestUpsertBasicKey:
    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_success_create(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_basic_key.return_value = {
            "id": 1,
            "name": "Production Key",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert",
            json={"name": "Production Key", "key_value": "pk_live_abc123"},
        )

        assert resp.status_code == 200
        assert resp.json()["name"] == "Production Key"
        mock_instance.upsert_basic_key.assert_called_once_with(
            name="Production Key",
            key_value="pk_live_abc123",
            key_id=None,
        )

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_success_update(self, mock_service_cls, client_as_admin):
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

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_missing_name(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert",
            json={"key_value": "pk_live_abc123"},
        )
        assert resp.status_code == 400
        assert "name" in resp.json()["detail"]

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_missing_key_value(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert",
            json={"name": "My Key"},
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
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


# ---------------------------------------------------------------------------
# POST /api/v1/generated-api-keys/upsert-full
# ---------------------------------------------------------------------------
class TestUpsertFullKey:
    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_success_create(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_full_key.return_value = {
            "id": 1,
            "name": "Full Key",
        }
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

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_with_all_optional_fields(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_full_key.return_value = {"id": 1}
        mock_service_cls.return_value = mock_instance

        abuse_config = {
            "is_toggled": True,
            "recaptcha_secret_key": "secret",
            "threshold": 0.5,
        }

        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert-full",
            params={"id": 10},
            json={
                "name": "Full Key",
                "key_value": "pk_live_full",
                "domains": ["example.com", "api.example.com"],
                "abuse_prevention": abuse_config,
                "fraud_protection": True,
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_full_key.assert_called_once_with(
            name="Full Key",
            key_value="pk_live_full",
            key_id=10,
            domains=["example.com", "api.example.com"],
            abuse_prevention=abuse_config,
            fraud_protection=True,
        )

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_missing_name(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert-full",
            json={"key_value": "pk_live_full"},
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_missing_key_value(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/generated-api-keys/upsert-full",
            json={"name": "Full Key"},
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
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
    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_keys.return_value = [
            {"id": 1, "name": "Key A"},
            {"id": 2, "name": "Key B"},
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/generated-api-keys/list")

        assert resp.status_code == 200
        assert len(resp.json()) == 2
        mock_instance.get_all_keys.assert_called_once()

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_empty_list(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_keys.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/generated-api-keys/list")

        assert resp.status_code == 200
        assert resp.json() == []

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
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
    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_key_by_id.return_value = {"id": 3, "name": "Key X"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/generated-api-keys/get", params={"key_id": 3}
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == 3
        mock_instance.get_key_by_id.assert_called_once_with(3)

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_key_by_id.side_effect = HTTPException(
            status_code=404, detail="Not found"
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
    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_key.return_value = {"message": "Deleted"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/generated-api-keys/delete", params={"key_id": 2}
        )

        assert resp.status_code == 200
        mock_instance.delete_key.assert_called_once_with(2)

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
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
