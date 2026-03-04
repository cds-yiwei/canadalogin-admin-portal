"""Tests for group management web routes."""

import pytest
from unittest.mock import AsyncMock, patch


def test_group_management_page_requires_super_admin_role(client_as_readonly):
    """Test that accessing group management page without SUPER_ADMIN role returns 403."""
    response = client_as_readonly.get("/group-management/application-owners")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_group_management_page_loads_for_super_admin(client_as_admin):
    """Test that SUPER_ADMIN can access the group management page."""
    with patch("app.dependencies.services.get_admin_service") as mock_get_service:
        # Mock the admin service
        mock_service = AsyncMock()
        mock_service.search_groups_by_name.return_value = [
            {"id": "group-app-owners", "displayName": "application owners"}
        ]
        mock_service.get_group_by_id.return_value = {
            "id": "group-app-owners",
            "displayName": "application owners",
            "members": [
                {"id": "user-1", "email": "owner1@example.gc.ca"},
                {"id": "user-2", "email": "owner2@example.gc.ca"},
            ],
        }
        mock_get_service.return_value = mock_service

        response = client_as_admin.get("/group-management/application-owners")
        assert response.status_code == 200
        assert "Application Owners" in response.text or "Group Management" in response.text


@pytest.mark.asyncio
async def test_group_management_page_handles_missing_group(client_as_admin):
    """Test that group management page handles missing group gracefully."""
    with patch("app.dependencies.services.get_admin_service") as mock_get_service:
        # Mock service that returns no groups
        mock_service = AsyncMock()
        mock_service.search_groups_by_name.return_value = []
        mock_get_service.return_value = mock_service

        response = client_as_admin.get("/group-management/application-owners")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_add_user_to_group_requires_super_admin(client_as_readonly):
    """Test that adding a user requires SUPER_ADMIN role."""
    response = client_as_readonly.post(
        "/group-management/application-owners/add-user",
        data={"user_id": "user-1"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_add_user_to_group_succeeds(client_as_admin):
    """Test adding a user to the application owners group."""
    with patch("app.dependencies.services.get_admin_service") as mock_get_service:
        # Mock the service
        mock_service = AsyncMock()
        mock_service.search_groups_by_name.return_value = [
            {"id": "group-app-owners", "displayName": "application owners"}
        ]
        mock_service.get_group_by_id.return_value = {
            "id": "group-app-owners",
            "displayName": "application owners",
            "members": [
                {"id": "user-1", "email": "owner1@example.gc.ca"},
                {"id": "new-user", "email": "newowner@example.gc.ca"},
            ],
        }
        mock_service.add_user_to_group.return_value = None
        mock_get_service.return_value = mock_service

        response = client_as_admin.post(
            "/group-management/application-owners/add-user",
            data={"user_id": "new-user"},
        )

        assert response.status_code == 200
        # Should have HX-Trigger header with toast
        assert "HX-Trigger" in response.headers or "User added successfully" in response.text


@pytest.mark.asyncio
async def test_add_user_handles_missing_group(client_as_admin):
    """Test that adding user when group doesn't exist is handled."""
    with patch("app.dependencies.services.get_admin_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_service.search_groups_by_name.return_value = []
        mock_get_service.return_value = mock_service

        response = client_as_admin.post(
            "/group-management/application-owners/add-user",
            data={"user_id": "user-1"},
        )

        assert response.status_code in [404, 500]


@pytest.mark.asyncio
async def test_remove_user_from_group_requires_super_admin(client_as_readonly):
    """Test that removing a user requires SUPER_ADMIN role."""
    response = client_as_readonly.post(
        "/group-management/application-owners/remove-user-modal",
        data={"user_id": "user-1"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_remove_user_from_group_succeeds(client_as_admin):
    """Test removing a user from the application owners group."""
    with patch("app.dependencies.services.get_admin_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_service.search_groups_by_name.return_value = [
            {"id": "group-app-owners", "displayName": "application owners"}
        ]
        mock_service.get_group_by_id.return_value = {
            "id": "group-app-owners",
            "displayName": "application owners",
            "members": [
                {"id": "user-1", "email": "owner1@example.gc.ca"},
            ],
        }
        mock_service.remove_user_from_group.return_value = None
        mock_get_service.return_value = mock_service

        response = client_as_admin.post(
            "/group-management/application-owners/remove-user-modal",
            data={"user_id": "user-2"},
        )

        assert response.status_code == 200
        # Should have HX-Trigger header with toast
        assert "HX-Trigger" in response.headers or "User removed successfully" in response.text


@pytest.mark.asyncio
async def test_remove_user_handles_missing_group(client_as_admin):
    """Test that removing user when group doesn't exist is handled."""
    with patch("app.dependencies.services.get_admin_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_service.search_groups_by_name.return_value = []
        mock_get_service.return_value = mock_service

        response = client_as_admin.post(
            "/group-management/application-owners/remove-user-modal",
            data={"user_id": "user-1"},
        )

        assert response.status_code in [404, 500]


@pytest.mark.asyncio
async def test_add_user_handles_service_error(client_as_admin):
    """Test that service errors are handled gracefully."""
    with patch("app.dependencies.services.get_admin_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_service.search_groups_by_name.return_value = [
            {"id": "group-app-owners", "displayName": "application owners"}
        ]
        mock_service.add_user_to_group.side_effect = Exception("API error")
        mock_get_service.return_value = mock_service

        response = client_as_admin.post(
            "/group-management/application-owners/add-user",
            data={"user_id": "user-1"},
        )

        # Should handle error gracefully
        assert response.status_code in [400, 500]


@pytest.mark.asyncio
async def test_remove_user_handles_service_error(client_as_admin):
    """Test that service errors are handled gracefully during removal."""
    with patch("app.dependencies.services.get_admin_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_service.search_groups_by_name.return_value = [
            {"id": "group-app-owners", "displayName": "application owners"}
        ]
        mock_service.remove_user_from_group.side_effect = Exception("API error")
        mock_get_service.return_value = mock_service

        response = client_as_admin.post(
            "/group-management/application-owners/remove-user-modal",
            data={"user_id": "user-1"},
        )

        # Should handle error gracefully
        assert response.status_code in [400, 500]
