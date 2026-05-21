"""Tests for Model Menu API endpoints (Core edition).

Source: core/api/v1/model_menu.py
Postman: postman_collection/model_menu.postman_collection.json
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/model-menu/get_models_by_provider
# ---------------------------------------------------------------------------
class TestGetModelsByProvider:
    @patch("core.api.v1.model_menu.ModelMenuService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get Models - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.get_models_by_provider.return_value = {
            "data": [
                {
                    "id": 1,
                    "name": "gpt-4o",
                    "service_type": "llm",
                    "status": "active",
                    "model_provider_menu_id": 1,
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
            "/api/v1/model-menu/get_models_by_provider",
            json={
                "model_provider_menu_id": 1,
                "name": "gpt",
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
            model_provider_menu_id=1,
            name="gpt",
            status_filter=None,
            service_type="llm",
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=10,
        )

    def test_missing_model_provider_menu_id(self, client_as_member):
        """Postman: Get Models - Missing ID (400)."""
        resp = client_as_member.post(
            "/api/v1/model-menu/get_models_by_provider", json={}
        )
        assert resp.status_code == 400
        assert "model_provider_menu_id is required" in resp.json()["detail"]

    def test_invalid_model_provider_menu_id(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/model-menu/get_models_by_provider",
            json={"model_provider_menu_id": "abc"},
        )
        assert resp.status_code == 400
        assert "integer" in resp.json()["detail"]

    @patch("core.api.v1.model_menu.ModelMenuService")
    def test_with_filters(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_models_by_provider.return_value = {
            "data": [],
            "pagination": {"page": 2, "page_size": 5, "total": 0, "total_pages": 0},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model-menu/get_models_by_provider",
            json={
                "model_provider_menu_id": 1,
                "name": "gpt",
                "status": "active",
                "service_type": "llm",
                "sort": "name",
                "page": 2,
                "page_size": 5,
            },
        )

        assert resp.status_code == 200
        mock_instance.get_models_by_provider.assert_called_once_with(
            model_provider_menu_id=1,
            name="gpt",
            status_filter="active",
            service_type="llm",
            sort_by="name",
            sort_order="asc",
            page=2,
            page_size=5,
        )

    @patch("core.api.v1.model_menu.ModelMenuService")
    def test_minimal_request(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_models_by_provider.return_value = {
            "data": [],
            "pagination": {"page": 1, "page_size": 10, "total": 0, "total_pages": 0},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model-menu/get_models_by_provider",
            json={"model_provider_menu_id": 1},
        )

        assert resp.status_code == 200
        mock_instance.get_models_by_provider.assert_called_once_with(
            model_provider_menu_id=1,
            name=None,
            status_filter=None,
            service_type=None,
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=10,
        )


# ---------------------------------------------------------------------------
# POST /api/v1/model-menu/upsert_model
# ---------------------------------------------------------------------------
class TestUpsertModel:
    @patch("core.api.v1.model_menu.ModelMenuService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Upsert Model - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.upsert_model.return_value = {
            "id": 1,
            "name": "gpt-4o",
            "service_type": "llm",
            "status": "active",
        }
        mock_service_cls.return_value = mock_instance

        data = {
            "model_provider_menu_id": 1,
            "name": "gpt-4o",
            "service_type": "llm",
            "status": "active",
        }
        resp = client_as_member.post(
            "/api/v1/model-menu/upsert_model",
            json=data,
        )

        assert resp.status_code == 200
        assert resp.json()["name"] == "gpt-4o"
        mock_instance.upsert_model.assert_called_once_with(data)

    @patch("core.api.v1.model_menu.ModelMenuService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.upsert_model.side_effect = HTTPException(
            status_code=400, detail="Invalid data"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model-menu/upsert_model",
            json={"name": "bad-model"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/v1/model-menu/delete_model
# ---------------------------------------------------------------------------
class TestDeleteModel:
    @patch("core.api.v1.model_menu.ModelMenuService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Delete Model - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.delete_model.return_value = {
            "message": "Model deleted successfully"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete(
            "/api/v1/model-menu/delete_model", params={"model_id": 1}
        )

        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()
        mock_instance.delete_model.assert_called_once_with(1)

    @patch("core.api.v1.model_menu.ModelMenuService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.delete_model.side_effect = HTTPException(
            status_code=404, detail="Model not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete(
            "/api/v1/model-menu/delete_model", params={"model_id": 999}
        )
        assert resp.status_code == 404

    def test_missing_model_id(self, client_as_member):
        resp = client_as_member.delete("/api/v1/model-menu/delete_model")
        assert resp.status_code == 422
