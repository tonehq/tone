"""Tests for Model Menu API endpoints (Core edition).

Source: core/api/v1/model_menu.py
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# POST /api/v1/model-menu/get_models_by_provider
# ---------------------------------------------------------------------------
class TestGetModelsByProvider:
    @patch("ee.api.v1.model_menu.ModelMenuService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_models_by_provider.return_value = {
            "data": [{"id": 1, "name": "gpt-4"}],
            "pagination": {"page": 1, "page_size": 10, "total": 1},
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

    def test_missing_model_provider_menu_id(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/model-menu/get_models_by_provider", json={}
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.model_menu.ModelMenuService")
    def test_with_filters(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_models_by_provider.return_value = {
            "data": [],
            "pagination": {"page": 1, "page_size": 5, "total": 0},
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


# ---------------------------------------------------------------------------
# POST /api/v1/model-menu/upsert_model
# ---------------------------------------------------------------------------
class TestUpsertModel:
    @patch("ee.api.v1.model_menu.ModelMenuService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_model.return_value = {
            "id": 1,
            "name": "gpt-4",
        }
        mock_service_cls.return_value = mock_instance

        data = {"name": "gpt-4", "model_provider_menu_id": 1, "service_type": "llm"}
        resp = client_as_admin.post(
            "/api/v1/model-menu/upsert_model",
            json=data,
        )

        assert resp.status_code == 200
        mock_instance.upsert_model.assert_called_once_with(data)


# ---------------------------------------------------------------------------
# DELETE /api/v1/model-menu/delete_model
# ---------------------------------------------------------------------------
class TestDeleteModel:
    @patch("ee.api.v1.model_menu.ModelMenuService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_model.return_value = {"message": "Deleted"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/model-menu/delete_model", params={"model_id": 1}
        )

        assert resp.status_code == 200
        mock_instance.delete_model.assert_called_once_with(1)

    def test_missing_model_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/model-menu/delete_model")
        assert resp.status_code == 422
