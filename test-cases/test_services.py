"""Tests for Services API endpoints.

Source: core/api/v1/services.py
"""

import pytest
from uuid import UUID
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException

EXPECTED_ORG_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
EXPECTED_USER_ID = 1


# ─── Fixtures ───

@pytest.fixture
def sample_service_data():
    return {
        "service_provider_id": 1,
        "name": "GPT-4 Service",
        "service_type": "llm",
        "config": {"model": "gpt-4", "temperature": 0.7},
    }


# ─── POST /api/v1/services/upsert — Upsert Service ───

class TestUpsertService:
    """Tests for POST /api/v1/services/upsert"""

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_upsert_service_create_success(self, mock_service_cls, client_as_admin, sample_service_data):
        mock_service_cls.return_value.upsert_service.return_value = {"id": 1, **sample_service_data}
        response = client_as_admin.post("/api/v1/services/upsert", json=sample_service_data)
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID, user_id=EXPECTED_USER_ID)

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_upsert_service_with_optional_fields(self, mock_service_cls, client_as_admin, sample_service_data):
        data = {**sample_service_data, "description": "Test", "is_default": True, "tags": ["prod"]}
        mock_service_cls.return_value.upsert_service.return_value = {"id": 1}
        response = client_as_admin.post("/api/v1/services/upsert", json=data)
        assert response.status_code == 200

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_upsert_service_missing_service_provider_id(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/services/upsert", json={
            "name": "Test", "service_type": "llm", "config": {}
        })
        assert response.status_code == 400
        assert "service_provider_id, name, service_type, and config are required" in response.json()["detail"]

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_upsert_service_missing_name(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/services/upsert", json={
            "service_provider_id": 1, "service_type": "llm", "config": {}
        })
        assert response.status_code == 400

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_upsert_service_missing_service_type(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/services/upsert", json={
            "service_provider_id": 1, "name": "Test", "config": {}
        })
        assert response.status_code == 400

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_upsert_service_missing_config(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/services/upsert", json={
            "service_provider_id": 1, "name": "Test", "service_type": "llm"
        })
        assert response.status_code == 400

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_upsert_service_empty_body(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/services/upsert", json={})
        assert response.status_code == 400

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_upsert_service_provider_not_found(self, mock_service_cls, client_as_admin, sample_service_data):
        mock_service_cls.return_value.upsert_service.side_effect = HTTPException(
            status_code=404, detail="Service provider not found"
        )
        response = client_as_admin.post("/api/v1/services/upsert", json=sample_service_data)
        assert response.status_code == 404

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_upsert_service_with_default_flag(self, mock_service_cls, client_as_admin, sample_service_data):
        data = {**sample_service_data, "is_default": True}
        mock_service_cls.return_value.upsert_service.return_value = {"id": 1, **data}
        response = client_as_admin.post("/api/v1/services/upsert", json=data)
        assert response.status_code == 200

    def test_upsert_service_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/services/upsert", json={
            "service_provider_id": 1, "name": "T", "service_type": "llm", "config": {}
        })
        assert response.status_code in (401, 403)


# ─── GET /api/v1/services/list — Get All Services ───

class TestGetAllServices:
    """Tests for GET /api/v1/services/list"""

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_get_all_services_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_services.return_value = [{"id": 1, "name": "Svc"}]
        response = client_as_member.get("/api/v1/services/list")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID, user_id=EXPECTED_USER_ID)

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_get_all_services_filter_by_type(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_services.return_value = []
        response = client_as_member.get("/api/v1/services/list?service_type=llm")
        assert response.status_code == 200

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_get_all_services_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_services.return_value = []
        response = client_as_member.get("/api/v1/services/list")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_services_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/services/list")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/services/get — Get Service ───

class TestGetService:
    """Tests for GET /api/v1/services/get"""

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_get_service_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_service.return_value = {"id": 1, "name": "Svc"}
        response = client_as_member.get("/api/v1/services/get?service_id=1")
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID, user_id=EXPECTED_USER_ID)

    def test_get_service_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/services/get")
        assert response.status_code == 422

    def test_get_service_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/services/get?service_id=abc")
        assert response.status_code == 422

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_get_service_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_service.side_effect = HTTPException(
            status_code=404, detail="Service not found"
        )
        response = client_as_member.get("/api/v1/services/get?service_id=999")
        assert response.status_code == 404

    def test_get_service_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/services/get?service_id=1")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/services/default — Get Default Service ───

class TestGetDefaultService:
    """Tests for GET /api/v1/services/default"""

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_get_default_service_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_default_service.return_value = {"id": 1, "is_default": True}
        response = client_as_member.get("/api/v1/services/default?service_type=llm")
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID, user_id=EXPECTED_USER_ID)

    def test_get_default_service_missing_type(self, client_as_member):
        response = client_as_member.get("/api/v1/services/default")
        assert response.status_code == 422

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_get_default_service_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_default_service.side_effect = HTTPException(
            status_code=404, detail="No default service"
        )
        response = client_as_member.get("/api/v1/services/default?service_type=llm")
        assert response.status_code == 404

    def test_get_default_service_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/services/default?service_type=llm")
        assert response.status_code in (401, 403)


# ─── DELETE /api/v1/services/delete — Delete Service ───

class TestDeleteService:
    """Tests for DELETE /api/v1/services/delete"""

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_delete_service_success(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_service.return_value = {"message": "deleted"}
        response = client_as_admin.delete("/api/v1/services/delete?service_id=1")
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID, user_id=EXPECTED_USER_ID)

    def test_delete_service_missing_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/services/delete")
        assert response.status_code == 422

    def test_delete_service_invalid_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/services/delete?service_id=abc")
        assert response.status_code == 422

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_delete_service_not_found(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_service.side_effect = HTTPException(
            status_code=404, detail="Service not found"
        )
        response = client_as_admin.delete("/api/v1/services/delete?service_id=999")
        assert response.status_code == 404

    def test_delete_service_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/services/delete?service_id=1")
        assert response.status_code in (401, 403)
