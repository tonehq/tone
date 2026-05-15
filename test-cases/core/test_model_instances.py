"""Tests for Model Instances API endpoints (Core edition).

Source: core/api/v1/model_instances.py
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# POST /api/v1/model-instances/upsert
# ---------------------------------------------------------------------------
class TestUpsertModelInstance:
    @patch("ee.api.v1.model_instances.ModelInstanceService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_model_instance.return_value = {
            "id": 1,
            "model_menu_id": 10,
            "account_id": 20,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/model-instances/upsert",
            json={
                "model_menu_id": 10,
                "account_id": 20,
            },
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == 1
        mock_instance.upsert_model_instance.assert_called_once_with(
            model_menu_id=10,
            account_id=20,
            host_region=None,
            instance_status=None,
            instance_id=None,
        )

    @patch("ee.api.v1.model_instances.ModelInstanceService")
    def test_missing_all_fields(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/model-instances/upsert",
            json={},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/v1/model-instances/list
# ---------------------------------------------------------------------------
class TestListModelInstances:
    @patch("ee.api.v1.model_instances.ModelInstanceService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_model_instances.return_value = {
            "data": [{"id": 1, "model_menu_id": 10}],
            "pagination": {"page": 1, "page_size": 10, "total": 1},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/model-instances/list", json={})

        assert resp.status_code == 200
        mock_instance.get_all_model_instances.assert_called_once_with(
            model_menu_id=None,
            account_id=None,
            status_filter=None,
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=None,
        )

    @patch("ee.api.v1.model_instances.ModelInstanceService")
    def test_with_filters(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_model_instances.return_value = {
            "data": [],
            "pagination": {"page": 1, "page_size": 5, "total": 0},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model-instances/list",
            json={
                "model_menu_id": 10,
                "account_id": 20,
                "status": "active",
                "sort": "-updated_at",
                "page": 2,
                "page_size": 5,
            },
        )

        assert resp.status_code == 200
        mock_instance.get_all_model_instances.assert_called_once_with(
            model_menu_id=10,
            account_id=20,
            status_filter="active",
            sort_by="updated_at",
            sort_order="desc",
            page=2,
            page_size=5,
        )


# ---------------------------------------------------------------------------
# POST /api/v1/model-instances/get
# ---------------------------------------------------------------------------
class TestGetModelInstance:
    @patch("ee.api.v1.model_instances.ModelInstanceService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_model_instance.return_value = {
            "id": 1,
            "model_menu_id": 10,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model-instances/get", json={"instance_id": 1}
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == 1
        mock_instance.get_model_instance.assert_called_once_with(1)

    def test_missing_instance_id(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-instances/get", json={})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/v1/model-instances/delete
# ---------------------------------------------------------------------------
class TestDeleteModelInstance:
    @patch("ee.api.v1.model_instances.ModelInstanceService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_model_instance.return_value = {"message": "Deleted"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/model-instances/delete", params={"instance_id": 1}
        )

        assert resp.status_code == 200
        mock_instance.delete_model_instance.assert_called_once_with(1)

    def test_missing_instance_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/model-instances/delete")
        assert resp.status_code == 422
