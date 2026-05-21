"""Tests for Models API endpoints (Core edition).

Source: core/api/v1/models.py
Postman: postman_collection/models.postman_collection.json
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
        """Postman: Get Models By Provider - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.get_models_by_provider.return_value = {
            "data": [
                {
                    "id": 1,
                    "name": "gpt-4o",
                    "service_type": "llm",
                    "status": "active",
                    "service_provider_id": 1,
                }
            ],
            "pagination": {
                "page": 1,
                "page_size": 10,
                "total": 1,
                "total_pages": 1,
            },
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model/get_models_by_provider",
            json={
                "service_provider_id": 1,
                "name": "gpt",
                "status": "active",
                "service_type": "llm",
                "sort": "-created_at",
                "page": 1,
                "page_size": 10,
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "pagination" in data
        mock_instance.get_models_by_provider.assert_called_once_with(
            service_provider_id=1,
            name="gpt",
            status_filter="active",
            service_type="llm",
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=10,
        )

    @patch("core.api.v1.models.ModelService")
    def test_minimal_request(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_models_by_provider.return_value = {
            "data": [],
            "pagination": {"page": 1, "page_size": 10, "total": 0, "total_pages": 0},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model/get_models_by_provider",
            json={"service_provider_id": 10},
        )

        assert resp.status_code == 200
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

    def test_missing_service_provider_id(self, client_as_member):
        """Postman: Get Models By Provider - Missing ID (400)."""
        resp = client_as_member.post("/api/v1/model/get_models_by_provider", json={})
        assert resp.status_code == 400
        assert "service_provider_id is required" in resp.json()["detail"]

    def test_invalid_service_provider_id(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/model/get_models_by_provider",
            json={"service_provider_id": "abc"},
        )
        assert resp.status_code == 400
        assert "integer" in resp.json()["detail"]

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
        assert resp.status_code in (500, 422, 400)

    @patch("core.api.v1.models.ModelService")
    def test_with_sort_asc(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_models_by_provider.return_value = {
            "data": [],
            "pagination": {"page": 1, "page_size": 10, "total": 0, "total_pages": 0},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model/get_models_by_provider",
            json={"service_provider_id": 1, "sort": "name"},
        )

        assert resp.status_code == 200
        mock_instance.get_models_by_provider.assert_called_once_with(
            service_provider_id=1,
            name=None,
            status_filter=None,
            service_type=None,
            sort_by="name",
            sort_order="asc",
            page=1,
            page_size=10,
        )


# ---------------------------------------------------------------------------
# POST /api/v1/model/upsert_model
# ---------------------------------------------------------------------------
class TestUpsertModel:
    @patch("core.api.v1.models.ModelService")
    def test_create_success(self, mock_service_cls, client_as_member):
        """Postman: Upsert Model - Create (200)."""
        mock_instance = MagicMock()
        mock_instance.upsert_model.return_value = {
            "id": 1,
            "name": "gpt-4o",
            "service_type": "llm",
            "status": "active",
            "service_provider_id": 1,
        }
        mock_service_cls.return_value = mock_instance

        payload = {
            "service_provider_id": 1,
            "name": "gpt-4o",
            "service_type": "llm",
            "meta_data": {},
            "status": "active",
        }
        resp = client_as_member.post("/api/v1/model/upsert_model", json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "gpt-4o"
        mock_instance.upsert_model.assert_called_once_with(payload)

    @patch("core.api.v1.models.ModelService")
    def test_update(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.upsert_model.return_value = {
            "id": 5,
            "name": "gpt-4o-updated",
        }
        mock_service_cls.return_value = mock_instance

        payload = {"id": 5, "name": "gpt-4o-updated"}
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
        """Postman: Delete Model - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.delete_model.return_value = {
            "message": "Model deleted successfully"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete(
            "/api/v1/model/delete_model", params={"model_id": 1}
        )

        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()
        mock_instance.delete_model.assert_called_once_with(1)

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
