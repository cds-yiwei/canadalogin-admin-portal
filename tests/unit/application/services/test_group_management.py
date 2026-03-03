import pytest

from app.service.admin_service import AdminService


class FakeGroupAdminClient:
    """Fake ISV client for testing group operations."""

    def __init__(self):
        self.list_groups_called = False
        self.search_groups_called = False
        self.get_group_called = False
        self.add_user_called = False
        self.remove_user_called = False
        self.is_user_in_group_called = False

        # Payloads
        self.list_groups_payload = {
            "Resources": [
                {"id": "group-1", "displayName": "admin"},
                {"id": "group-2", "displayName": "developers"},
            ]
        }
        self.search_groups_payload = {
            "Resources": [{"id": "app-owners-group", "displayName": "application owners"}]
        }
        self.get_group_payload = {
            "id": "group-1",
            "displayName": "admin",
            "members": [{"value": "user-1"}, {"value": "user-2"}],
        }

    async def fetch_users(self):
        return []

    async def list_groups(self, count: int = 100, start_index: int = 1):
        self.list_groups_called = True
        return self.list_groups_payload.get("Resources", [])

    async def search_groups_by_name(self, group_name: str):
        self.search_groups_called = True
        return self.search_groups_payload.get("Resources", [])

    async def get_group_by_id(self, group_id: str):
        self.get_group_called = True
        # Return different data based on group_id
        if group_id == "app-owners-group":
            return {
                "id": "app-owners-group",
                "displayName": "application owners",
                "members": [{"value": "user-2"}, {"value": "user-3"}],
            }
        return self.get_group_payload

    async def add_user_to_group(self, group_id: str, user_id: str):
        self.add_user_called = True

    async def remove_user_from_group(self, group_id: str, user_id: str):
        self.remove_user_called = True

    async def is_user_in_group(self, group_id: str, user_id: str) -> bool:
        self.is_user_in_group_called = True
        # Get group members based on group_id
        if group_id == "app-owners-group":
            members = [{"value": "user-2"}, {"value": "user-3"}]
        else:
            members = self.get_group_payload.get("members", [])
        return user_id in [m.get("value") for m in members]


# ============================================================================
# List Groups Tests
# ============================================================================


@pytest.mark.asyncio
async def test_list_groups_returns_groups():
    client = FakeGroupAdminClient()
    service = AdminService(client)

    result = await service.list_groups(count=100, start_index=1)

    assert result == [
        {"id": "group-1", "displayName": "admin"},
        {"id": "group-2", "displayName": "developers"},
    ]
    assert client.list_groups_called


@pytest.mark.asyncio
async def test_list_groups_with_custom_pagination():
    client = FakeGroupAdminClient()
    service = AdminService(client)

    result = await service.list_groups(count=50, start_index=2)

    assert result == [
        {"id": "group-1", "displayName": "admin"},
        {"id": "group-2", "displayName": "developers"},
    ]
    assert client.list_groups_called


# ============================================================================
# Search Groups Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_groups_by_name_returns_matching_groups():
    client = FakeGroupAdminClient()
    service = AdminService(client)

    result = await service.search_groups_by_name("application owners")

    assert result == [{"id": "app-owners-group", "displayName": "application owners"}]
    assert client.search_groups_called


@pytest.mark.asyncio
async def test_search_groups_by_name_returns_empty_for_no_match():
    client = FakeGroupAdminClient()
    client.search_groups_payload = {"Resources": []}
    service = AdminService(client)

    result = await service.search_groups_by_name("nonexistent")

    assert result == []
    assert client.search_groups_called


# ============================================================================
# Get Group by ID Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_group_by_id_returns_group_data():
    client = FakeGroupAdminClient()
    service = AdminService(client)

    result = await service.get_group_by_id("group-1")

    assert result == {
        "id": "group-1",
        "displayName": "admin",
        "members": [{"value": "user-1"}, {"value": "user-2"}],
    }
    assert client.get_group_called


# ============================================================================
# Add User to Group Tests
# ============================================================================


@pytest.mark.asyncio
async def test_add_user_to_group_calls_client():
    client = FakeGroupAdminClient()
    service = AdminService(client)

    await service.add_user_to_group("group-1", "user-3")

    assert client.add_user_called


# ============================================================================
# Remove User from Group Tests
# ============================================================================


@pytest.mark.asyncio
async def test_remove_user_from_group_calls_client():
    client = FakeGroupAdminClient()
    service = AdminService(client)

    await service.remove_user_from_group("group-1", "user-1")

    assert client.remove_user_called


# ============================================================================
# Is User in Group Tests
# ============================================================================


@pytest.mark.asyncio
async def test_is_user_in_group_returns_true_when_member():
    client = FakeGroupAdminClient()
    service = AdminService(client)

    result = await service.is_user_in_group("group-1", "user-1")

    assert result is True
    assert client.is_user_in_group_called


@pytest.mark.asyncio
async def test_is_user_in_group_returns_false_when_not_member():
    client = FakeGroupAdminClient()
    service = AdminService(client)

    result = await service.is_user_in_group("group-1", "user-999")

    assert result is False
    assert client.is_user_in_group_called


@pytest.mark.asyncio
async def test_is_user_in_group_returns_false_for_empty_members():
    client = FakeGroupAdminClient()
    client.get_group_payload = {"id": "group-1", "displayName": "admin", "members": []}
    service = AdminService(client)

    result = await service.is_user_in_group("group-1", "user-1")

    assert result is False


# ============================================================================
# Auto-Assign Workflow Tests
# ============================================================================


@pytest.mark.asyncio
async def test_auto_assign_owners_workflow():
    """Test complete workflow: find group, check membership, add if needed."""
    client = FakeGroupAdminClient()
    service = AdminService(client)

    # Step 1: Search for "application owners" group
    groups = await service.search_groups_by_name("application owners")
    assert len(groups) == 1
    group_id = groups[0].get("id")
    assert group_id == "app-owners-group"

    # Step 2: Check if owner is already in group
    is_member = await service.is_user_in_group(group_id, "user-1")
    assert is_member is False

    # Step 3: Add owner to group
    await service.add_user_to_group(group_id, "user-1")
    assert client.add_user_called


@pytest.mark.asyncio
async def test_auto_assign_idempotent_check():
    """Test that pre-check prevents duplicate additions."""
    client = FakeGroupAdminClient()
    # Simulate owner already in group
    client.get_group_payload = {
        "id": "group-1",
        "displayName": "application owners",
        "members": [{"value": "user-1"}],
    }
    service = AdminService(client)

    # Check membership
    is_member = await service.is_user_in_group("group-1", "user-1")
    assert is_member is True

    # Should NOT call add_user_to_group when already member
    # (this is the responsibility of the caller, but the check is available)
    assert not client.add_user_called


@pytest.mark.asyncio
async def test_group_membership_check_multiple_owners():
    """Test checking multiple owners for group membership."""
    client = FakeGroupAdminClient()
    client.get_group_payload = {
        "id": "group-1",
        "displayName": "application owners",
        "members": [{"value": "user-1"}, {"value": "user-2"}],
    }
    service = AdminService(client)

    # Check each owner
    for owner_id in ["user-1", "user-2", "user-3"]:
        is_member = await service.is_user_in_group("group-1", owner_id)
        if owner_id in ["user-1", "user-2"]:
            assert is_member is True
        else:
            assert is_member is False


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_add_multiple_owners_to_group():
    """Integration test: add multiple owners to application owners group."""
    client = FakeGroupAdminClient()
    service = AdminService(client)

    # Simulate finding the group
    groups = await service.search_groups_by_name("application owners")
    assert len(groups) > 0
    group_id = groups[0].get("id")

    # Add multiple owners
    owners = ["owner-1", "owner-2", "owner-3"]
    for owner_id in owners:
        # Check if already member (would be false in this test)
        is_member = await service.is_user_in_group(group_id, owner_id)
        if not is_member:
            await service.add_user_to_group(group_id, owner_id)

    # All adds should have been called
    assert client.add_user_called


@pytest.mark.asyncio
async def test_remove_user_from_application_owners_group():
    """Test removing a user from the application owners group."""
    client = FakeGroupAdminClient()
    service = AdminService(client)

    # Get the group
    group = await service.get_group_by_id("app-owners-group")
    assert group["id"] == "app-owners-group"

    # Remove a user
    await service.remove_user_from_group("app-owners-group", "user-1")
    assert client.remove_user_called
