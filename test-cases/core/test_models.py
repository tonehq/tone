"""Tests for Models API endpoints (Core edition).

Source: core/api/v1/models.py
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/model/get_models_by_provider
# ---------------------------------------------------------------------------
class TestGetModelsByProvider:
    @patch("core.api.v1.models.ModelService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_models_by_provider.return_value = [
            {"id": 1, "name": "gpt-4"},
            {"id": 2, "name": "gpt-3.5-turbo"},
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model/get_models_by_provider",
            json={"service_provider_id": 10},
        )

        assert resp.status_code == 200
        assert len(resp.json()) == 2
        mock_service_cls.assert_called_once_with(ANY)
        mock_instance.get_models_by_provider.assert_called_once_with(
            service_provider_id=10,
            name=None,
            status_filter=None,
            service_type=None,
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=10,
        )

    @patch("core.api.v1.models.ModelService")
    def test_empty_list(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_models_by_provider.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model/get_models_by_provider",
            json={"service_provider_id": 999},
        )

        assert resp.status_code == 200
        assert resp.json() == []

    def test_missing_service_provider_id(self, client_as_member):
        resp = client_as_member.post("/api/v1/model/get_models_by_provider", json={})
        assert resp.status_code == 400

    @patch("core.api.v1.models.ModelService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_models_by_provider.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model/get_models_by_provider",
            json={"service_provider_id": 10},
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/v1/model/upsert_model
# ---------------------------------------------------------------------------
class TestUpsertModel:
    @patch("core.api.v1.models.ModelService")
    def test_success_create(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.upsert_model.return_value = {
            "id": 1,
            "name": "gpt-4",
            "service_provider_id": 10,
        }
        mock_service_cls.return_value = mock_instance

        payload = {"service_provider_id": 10, "name": "gpt-4"}
        resp = client_as_member.post("/api/v1/model/upsert_model", json=payload)

        assert resp.status_code == 200
        assert resp.json()["name"] == "gpt-4"
        mock_service_cls.assert_called_once_with(ANY)
        mock_instance.upsert_model.assert_called_once_with(payload)

    @patch("core.api.v1.models.ModelService")
    def test_success_update(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.upsert_model.return_value = {
            "id": 5,
            "name": "gpt-4-updated",
        }
        mock_service_cls.return_value = mock_instance

        payload = {"id": 5, "name": "gpt-4-updated"}
        resp = client_as_member.post("/api/v1/model/upsert_model", json=payload)

        assert resp.status_code == 200
        mock_instance.upsert_model.assert_called_once_with(payload)

    @patch("core.api.v1.models.ModelService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.upsert_model.side_effect = HTTPException(
            status_code=400, detail="Invalid data"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model/upsert_model",
            json={"service_provider_id": 10, "name": "bad-model"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/v1/model/delete_model
# ---------------------------------------------------------------------------
class TestDeleteModel:
    @patch("core.api.v1.models.ModelService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.delete_model.return_value = {"message": "Deleted"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete(
            "/api/v1/model/delete_model", params={"model_id": 3}
        )

        assert resp.status_code == 200
        mock_instance.delete_model.assert_called_once_with(3)

    @patch("core.api.v1.models.ModelService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.delete_model.side_effect = HTTPException(
            status_code=404, detail="Model not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete(
            "/api/v1/model/delete_model", params={"model_id": 999}
        )
        assert resp.status_code == 404

    def test_missing_model_id(self, client_as_member):
        resp = client_as_member.delete("/api/v1/model/delete_model")
        assert resp.status_code == 422
