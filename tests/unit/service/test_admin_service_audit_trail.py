import pytest

from app.service.admin_service import AdminService


class DummyClient:
    def __init__(self, resp=None, supports_before=True):
        self.resp = resp or {"events": [], "next": None}
        self.calls = []
        self.supports_before = supports_before

    async def app_audit_trail_search_after(
        self,
        application_id,
        from_date=None,
        to_date=None,
        size=25,
        search_after=None,
        search_dir=None,
    ):
        self.calls.append(
            {
                "application_id": application_id,
                "search_after": search_after,
                "search_dir": search_dir,
            }
        )
        # Simulate upstream that doesn't support 'before' by raising when search_dir=='before' and supports_before=False
        if search_dir == "before" and not self.supports_before:
            raise NotImplementedError("before not supported")
        return self.resp


@pytest.mark.asyncio
async def test_service_returns_normalized_events_and_next_token():
    resp = {
        "events": [
            {
                "id": "1",
                "timestamp": 1554479231870,
                "username": "u1",
                "origin": "1.2.3.4",
                "result": "success",
                "country": "US",
            }
        ],
        "next": '1554479231870, "uuid"',
    }
    client = DummyClient(resp=resp)
    svc = AdminService(client)
    res = await svc.get_application_audit_trail_search_after("app1")
    # service may return normalized dict; accept dict shape or tuple
    if isinstance(res, dict):
        events = res.get("events", [])
        tokens = {"next": res.get("next"), "total": res.get("total")}
    else:
        events, tokens = res
    assert isinstance(events, list)
    assert len(events) == 1
    assert tokens.get("next") == '1554479231870, "uuid"'
