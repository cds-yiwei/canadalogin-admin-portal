import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.mark.parametrize("path", ["/auth/login"])
def test_login_page_renders(path):
    app = create_app()
    client = TestClient(app)
    resp = client.get(path)
    assert resp.status_code == 200
    # page should contain the sign-in heading or form
    assert "<form" in resp.text
    assert "gcds-button" in resp.text or "Sign in" in resp.text
