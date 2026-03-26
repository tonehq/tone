"""Tests for Model API endpoints.

Source: core/api/v1/models.py
"""

import pytest
from uuid import UUID
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException

EXPECTED_ORG_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


# ─── Fixtures ───

@pytest.fixture
def sample_model_data():
    return {
        "service_provider_id": 1,
        "name": "gpt-4",
        "display_name": "GPT-4",
    }


# ─── GET /api/v1/model/get_models_by_provider — Get Models By Provider ───

class TestGetModelsByProvider:
    """Tests for GET /api/v1/model/get_models_by_provider"""

    @patch("ee.api.v1.models.ModelService")
    def test_get_models_by_provider_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_models_by_provider.return_value = [
            {"id": 1, "name": "gpt-4"}
        ]
        response = client_as_member.get("/api/v1/model/get_models_by_provider?service_provider_id=1")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.models.ModelService")
    def test_get_models_by_provider_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_models_by_provider.return_value = []
        response = client_as_member.get("/api/v1/model/get_models_by_provider?service_provider_id=1")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_models_missing_provider_id(self, client_as_member):
        response = client_as_member.get("/api/v1/model/get_models_by_provider")
        assert response.status_code == 422

    def test_get_models_invalid_provider_id(self, client_as_member):
        response = client_as_member.get("/api/v1/model/get_models_by_provider?service_provider_id=abc")
        assert response.status_code == 422

    def test_get_models_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/model/get_models_by_provider?service_provider_id=1")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/model/upsert_model — Upsert Model ───

class TestUpsertModel:
    """Tests for POST /api/v1/model/upsert_model"""

    @patch("ee.api.v1.models.ModelService")
    def test_upsert_model_create_success(self, mock_service_cls, client_as_member, sample_model_data):
        mock_service_cls.return_value.upsert_model.return_value = {"id": 1, **sample_model_data}
        response = client_as_member.post("/api/v1/model/upsert_model", json=sample_model_data)
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.models.ModelService")
    def test_upsert_model_update_success(self, mock_service_cls, client_as_member):
        data = {"id": 1, "name": "gpt-4-turbo"}
        mock_service_cls.return_value.upsert_model.return_value = data
        response = client_as_member.post("/api/v1/model/upsert_model", json=data)
        assert response.status_code == 200

    @patch("ee.api.v1.models.ModelService")
    def test_upsert_model_missing_service_provider_id(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_model.side_effect = HTTPException(
            status_code=400, detail="service_provider_id is required"
        )
        response = client_as_member.post("/api/v1/model/upsert_model", json={"name": "gpt-4"})
        assert response.status_code == 400

    @patch("ee.api.v1.models.ModelService")
    def test_upsert_model_missing_name(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_model.side_effect = HTTPException(
            status_code=400, detail="name is required"
        )
        response = client_as_member.post("/api/v1/model/upsert_model", json={"service_provider_id": 1})
        assert response.status_code == 400

    @patch("ee.api.v1.models.ModelService")
    def test_upsert_model_empty_body(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_model.side_effect = HTTPException(
            status_code=400, detail="service_provider_id is required"
        )
        response = client_as_member.post("/api/v1/model/upsert_model", json={})
        assert response.status_code == 400

    @patch("ee.api.v1.models.ModelService")
    def test_upsert_model_provider_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_model.side_effect = HTTPException(
            status_code=404, detail="Service provider not found"
        )
        response = client_as_member.post("/api/v1/model/upsert_model", json={
            "service_provider_id": 999, "name": "gpt-4"
        })
        assert response.status_code == 404

    @patch("ee.api.v1.models.ModelService")
    def test_upsert_model_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_model.side_effect = HTTPException(
            status_code=400, detail="Invalid model data"
        )
        response = client_as_member.post("/api/v1/model/upsert_model", json={"name": ""})
        assert response.status_code == 400

    def test_upsert_model_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/model/upsert_model", json={"name": "gpt-4"})
        assert response.status_code in (401, 403)


# ─── DELETE /api/v1/model/delete_model — Delete Model ───

class TestDeleteModel:
    """Tests for DELETE /api/v1/model/delete_model"""

    @patch("ee.api.v1.models.ModelService")
    def test_delete_model_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_model.return_value = {"message": "deleted"}
        response = client_as_member.delete("/api/v1/model/delete_model?model_id=1")
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    def test_delete_model_missing_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/model/delete_model")
        assert response.status_code == 422

    def test_delete_model_invalid_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/model/delete_model?model_id=abc")
        assert response.status_code == 422

    @patch("ee.api.v1.models.ModelService")
    def test_delete_model_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_model.side_effect = HTTPException(
            status_code=404, detail="Model not found"
        )
        response = client_as_member.delete("/api/v1/model/delete_model?model_id=999")
        assert response.status_code == 404

    def test_delete_model_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/model/delete_model?model_id=1")
        assert response.status_code in (401, 403)
