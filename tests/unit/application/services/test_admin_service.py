import pytest

from app.service.admin_service import AdminService


class FakeAdminGateway:
    def __init__(self):
        self.application_id = None
        self.client_id = None
        self.audit_trail_params = None
        self.total_logins_params = None
        self.detail_payload = {"id": "app-1"}
        self.total_logins_payload = {"total": 3}
        self.audit_trail_payload = {"events": ["login"]}
        self.client_secret_payload = {"secrets": ["abc"]}
        self.entitlements_payload = {"entitlements": ["read"]}

    async def fetch_users(self):
        return []

    async def get_application_detail(self, application_id: str):
        self.application_id = application_id
        return self.detail_payload

    async def get_application_total_logins(self, application_id: str, from_date=None, to_date=None):
        self.total_logins_params = {
            "application_id": application_id,
            "from_date": from_date,
            "to_date": to_date,
        }
        return self.total_logins_payload

    async def get_application_audit_trail(
        self,
        application_id: str,
        from_date=None,
        to_date=None,
        size: int = 50,
        sort_by: str = "time",
        sort_order: str = "DESC",
    ):
        self.audit_trail_params = {
            "application_id": application_id,
            "from_date": from_date,
            "to_date": to_date,
            "size": size,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }
        return self.audit_trail_payload

    async def get_client_secret(self, client_id: str):
        self.client_id = client_id
        return self.client_secret_payload

    async def get_application_entitlements(self, application_id: str):
        self.application_id = application_id
        return self.entitlements_payload


@pytest.mark.asyncio
async def test_get_application_detail_returns_payload_and_passes_id():
    gateway = FakeAdminGateway()
    service = AdminService(gateway)

    result = await service.get_application_detail("app-123")

    assert result == gateway.detail_payload
    assert gateway.application_id == "app-123"


@pytest.mark.asyncio
async def test_get_application_total_logins_returns_payload():
    gateway = FakeAdminGateway()
    service = AdminService(gateway)

    result = await service.get_application_total_logins("app-777")

    assert result == gateway.total_logins_payload
    assert gateway.total_logins_params == {
        "application_id": "app-777",
        "from_date": None,
        "to_date": None,
    }


@pytest.mark.asyncio
async def test_get_application_audit_trail_returns_payload():
    gateway = FakeAdminGateway()
    service = AdminService(gateway)

    result = await service.get_application_audit_trail("app-999")

    assert result == gateway.audit_trail_payload
    assert gateway.audit_trail_params == {
        "application_id": "app-999",
        "from_date": None,
        "to_date": None,
        "size": 50,
        "sort_by": "time",
        "sort_order": "DESC",
    }


@pytest.mark.asyncio
async def test_get_client_secret_returns_payload_and_passes_id():
    gateway = FakeAdminGateway()
    service = AdminService(gateway)

    result = await service.get_client_secret("client-9")

    assert result == gateway.client_secret_payload
    assert gateway.client_id == "client-9"


@pytest.mark.asyncio
async def test_get_application_entitlements_returns_payload_and_passes_id():
    gateway = FakeAdminGateway()
    service = AdminService(gateway)

    result = await service.get_application_entitlements("app-456")

    assert result == gateway.entitlements_payload
    assert gateway.application_id == "app-456"
