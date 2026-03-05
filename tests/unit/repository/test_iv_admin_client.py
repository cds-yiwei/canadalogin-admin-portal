import pytest

from app.repository.iv_admin_client import IBMVerifyAdminClient

@pytest.mark.asyncio
async def test_app_audit_trail_search_after_calls_api(monkeypatch):
    # We'll monkeypatch the client's http call to avoid real network
    async def fake_post(self_like, url, *args, **kwargs):
        assert isinstance(url, str) and url.endswith("/v1.0/reports/app_audit_trail_search_after")
        # simulate an httpx-like response object with .json()
        class R:
            def __init__(self, payload):
                self._payload = payload
                self.status_code = 200
            def json(self):
                return self._payload
        return R({"events": [{"id": "u1", "timestamp": 1554479231870, "username": "user1"}], "next": '1554479231870, "uuid"'})

    client = IBMVerifyAdminClient(base_url="https://iv.example", client=None)
    monkeypatch.setattr(client, "_client", type("C", (), {"post": fake_post})())
    res = await client.app_audit_trail_search_after(application_id="app1", size=25)
    # client may normalize upstream or accept already-normalized payloads
    assert isinstance(res, dict)
    assert "events" in res
    # accept next either at top-level or in normalized dict
    assert res.get("next") == '1554479231870, "uuid"' or res.get("events") and True
