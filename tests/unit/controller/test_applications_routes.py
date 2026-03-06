import pytest
from starlette.datastructures import Headers
from app.controller.web import applications_routes

class DummyService:
    async def get_application_audit_trail_search_after(self, application_id, from_date=None, to_date=None, size=25, search_after=None, search_dir=None):
        return ([{"id":"1","timestamp":1554479231870,"username":"u1"}], {'next':'1554479231870, "uuid"', 'prev':'1554479230000, "uuid2"'})

@pytest.mark.asyncio
async def test_usage_route_reads_search_after(monkeypatch):
    # Verify the router exposes the usage path
    router = applications_routes.router
    assert any(r.path == "/applications/{application_id}/usage" for r in router.routes)
