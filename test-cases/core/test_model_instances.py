"""Tests for Model Instances API endpoints (Core edition).

Source: core/api/v1/model_instances.py
Postman: postman_collection/model_instances.postman_collection.json
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/model-instances/upsert
# ---------------------------------------------------------------------------
class TestUpsertModelInstance:
    @patch("core.api.v1.model_instances.ModelInstanceService")
    def test_create_success(self, mock_service_cls, client_as_admin):
        """Postman: Upsert - Create (200)."""
        mock_instance = MagicMock()
        mock_instance.upsert_model_instance.return_value = {
            "id": 1,
            "model_menu_id": 1,
            "account_id": 1,
            "host_region": "us-east-1",
            "status": "active",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/model-instances/upsert",
            json={
                "model_menu_id": 1,
                "account_id": 1,
                "host_region": "us-east-1",
                "status": "active",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["model_menu_id"] == 1
        mock_instance.upsert_model_instance.assert_called_once_with(
            model_menu_id=1,
            account_id=1,
            host_region="us-east-1",
            instance_status="active",
            instance_id=None,
        )

    @patch("core.api.v1.model_instances.ModelInstanceService")
    def test_minimal_fields(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_model_instance.return_value = {
            "id": 1,
            "model_menu_id": 10,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/model-instances/upsert",
            json={"model_menu_id": 10},
        )

        assert resp.status_code == 200
        mock_instance.upsert_model_instance.assert_called_once_with(
            model_menu_id=10,
            account_id=None,
            host_region=None,
            instance_status=None,
            instance_id=None,
        )

    def test_missing_model_menu_id(self, client_as_admin):
        """Postman: Upsert - Missing Model Menu ID (400)."""
        resp = client_as_admin.post(
            "/api/v1/model-instances/upsert",
            json={},
        )
        assert resp.status_code == 400
        assert "model_menu_id is required" in resp.json()["detail"]

    @patch("core.api.v1.model_instances.ModelInstanceService")
    def test_update_existing(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_model_instance.return_value = {"id": 5}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/model-instances/upsert",
            json={
                "id": 5,
                "model_menu_id": 10,
                "account_id": 20,
                "host_region": "eu-west-1",
                "status": "inactive",
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_model_instance.assert_called_once_with(
            model_menu_id=10,
            account_id=20,
            host_region="eu-west-1",
            instance_status="inactive",
            instance_id=5,
        )

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/model-instances/upsert",
            json={"model_menu_id": 1},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/model-instances/list
# ---------------------------------------------------------------------------
class TestListModelInstances:
    @patch("core.api.v1.model_instances.ModelInstanceService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get All - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.get_all_model_instances.return_value = {
            "data": [
                {
                    "id": 1,
                    "model_menu_id": 1,
                    "account_id": 1,
                    "host_region": "us-east-1",
                    "status": "active",
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
            "/api/v1/model-instances/list",
            json={
                "model_menu_id": 1,
                "account_id": 1,
                "status": "active",
                "sort": "-created_at",
                "page": 1,
                "page_size": 10,
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "pagination" in data
        mock_instance.get_all_model_instances.assert_called_once_with(
            model_menu_id=1,
            account_id=1,
            status_filter="active",
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=10,
        )

    @patch("core.api.v1.model_instances.ModelInstanceService")
    def test_empty_body(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_model_instances.return_value = {
            "data": [],
            "pagination": {"page": 1, "page_size": None, "total": 0, "total_pages": 0},
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

    @patch("core.api.v1.model_instances.ModelInstanceService")
    def test_with_filters(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_model_instances.return_value = {
            "data": [],
            "pagination": {"page": 2, "page_size": 5, "total": 0, "total_pages": 0},
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
    @patch("core.api.v1.model_instances.ModelInstanceService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.get_model_instance.return_value = {
            "id": 1,
            "model_menu_id": 1,
            "account_id": 1,
            "host_region": "us-east-1",
            "status": "active",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model-instances/get", json={"instance_id": 1}
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == 1
        mock_instance.get_model_instance.assert_called_once_with(1)

    def test_missing_instance_id(self, client_as_member):
        """Postman: Get - Missing ID (400)."""
        resp = client_as_member.post("/api/v1/model-instances/get", json={})
        assert resp.status_code == 400
        assert "instance_id is required" in resp.json()["detail"]

    def test_invalid_instance_id(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/model-instances/get", json={"instance_id": "abc"}
        )
        assert resp.status_code == 400
        assert "integer" in resp.json()["detail"]

    @patch("core.api.v1.model_instances.ModelInstanceService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_model_instance.side_effect = HTTPException(
            status_code=404, detail="Model instance not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model-instances/get", json={"instance_id": 999}
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/model-instances/delete
# ---------------------------------------------------------------------------
class TestDeleteModelInstance:
    @patch("core.api.v1.model_instances.ModelInstanceService")
    def test_success(self, mock_service_cls, client_as_admin):
        """Postman: Delete - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.delete_model_instance.return_value = {
            "message": "Model instance deleted successfully"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/model-instances/delete", params={"instance_id": 1}
        )

        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()
        mock_instance.delete_model_instance.assert_called_once_with(1)

    @patch("core.api.v1.model_instances.ModelInstanceService")
    def test_not_found(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_model_instance.side_effect = HTTPException(
            status_code=404, detail="Not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/model-instances/delete", params={"instance_id": 999}
        )
        assert resp.status_code == 404

    def test_missing_instance_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/model-instances/delete")
        assert resp.status_code == 422
