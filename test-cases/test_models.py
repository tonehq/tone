"""Tests for Model API endpoints.

Source: core/api/v1/models.py
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


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

    @patch("core.api.v1.models.ModelService")
    def test_get_models_by_provider_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_models_by_provider.return_value = [
            {"id": 1, "name": "gpt-4"}
        ]
        response = client_as_member.get("/api/v1/model/get_models_by_provider?service_provider_id=1")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch("core.api.v1.models.ModelService")
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

    @patch("core.api.v1.models.ModelService")
    def test_upsert_model_create_success(self, mock_service_cls, client_as_member, sample_model_data):
        mock_service_cls.return_value.upsert_model.return_value = {"id": 1, **sample_model_data}
        response = client_as_member.post("/api/v1/model/upsert_model", json=sample_model_data)
        assert response.status_code == 200

    @patch("core.api.v1.models.ModelService")
    def test_upsert_model_update_success(self, mock_service_cls, client_as_member):
        data = {"id": 1, "name": "gpt-4-turbo"}
        mock_service_cls.return_value.upsert_model.return_value = data
        response = client_as_member.post("/api/v1/model/upsert_model", json=data)
        assert response.status_code == 200

    @patch("core.api.v1.models.ModelService")
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

    @patch("core.api.v1.models.ModelService")
    def test_delete_model_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_model.return_value = {"message": "deleted"}
        response = client_as_member.delete("/api/v1/model/delete_model?model_id=1")
        assert response.status_code == 200

    def test_delete_model_missing_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/model/delete_model")
        assert response.status_code == 422

    def test_delete_model_invalid_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/model/delete_model?model_id=abc")
        assert response.status_code == 422

    @patch("core.api.v1.models.ModelService")
    def test_delete_model_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_model.side_effect = HTTPException(
            status_code=404, detail="Model not found"
        )
        response = client_as_member.delete("/api/v1/model/delete_model?model_id=999")
        assert response.status_code == 404

    def test_delete_model_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/model/delete_model?model_id=1")
        assert response.status_code in (401, 403)
