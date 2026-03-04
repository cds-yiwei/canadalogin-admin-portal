"""Pytest configuration for controller tests."""

from fastapi.testclient import TestClient
from app.core.roles import Role
from app.main import create_app
import os
import pytest

# Set SKIP_SESSION_STORE before creating app
os.environ["SKIP_SESSION_STORE"] = "1"


def get_mock_user(role=Role.SUPER_ADMIN):
    """Create a mock user dict."""
    return {
        "id": "test-user-1",
        "email": "test@example.gc.ca",
        "display_name": "Test User",
        "roles": [role.value] if isinstance(role, Role) else [role],
        "permissions": ["*"],
    }


@pytest.fixture
def client_as_admin(monkeypatch):
    """Create a test client with SUPER_ADMIN user."""
    from app.dependencies import auth

    # Monkey patch _get_session_user to return admin user
    monkeypatch.setattr(auth, "_get_session_user", lambda request: get_mock_user(Role.SUPER_ADMIN))

    app = create_app()
    return TestClient(app)


@pytest.fixture
def client_as_readonly(monkeypatch):
    """Create a test client with READ_ONLY user."""
    from app.dependencies import auth

    # Monkey patch _get_session_user to return readonly user
    monkeypatch.setattr(auth, "_get_session_user", lambda request: get_mock_user(Role.READ_ONLY))

    app = create_app()
    return TestClient(app)


@pytest.fixture
def client_unauthenticated(monkeypatch):
    """Create a test client with no authenticated user."""
    from app.dependencies import auth

    # Monkey patch _get_session_user to return None
    monkeypatch.setattr(auth, "_get_session_user", lambda request: None)

    app = create_app()
    return TestClient(app)
