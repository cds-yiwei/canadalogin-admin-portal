import pytest

from app.controller.web._utils import _build_application_creation_payload


def test_build_application_creation_payload_minimal():
    form = {
        "name": "My App",
        "description": "A test app",
        "company_name": "MyCo",
        "application_url": "https://example.gc.ca",
        "redirect_uris": "https://example.gc.ca/callback",
        "pkce_enabled": "true",
        "client_type": "confidential",
        "client_auth_method": "client_secret_basic",
        "post_logout_redirect_uris": "https://example.gc.ca/logout-callback",
        "logout_uri": "https://example.gc.ca/logout",
        "logout_method": "back_channel",
    }
    owners = ["1000"]
    payload = _build_application_creation_payload(form, owners)

    assert payload["name"] == "My App"
    # client auth method placed in additionalConfig
    assert payload["providers"]["oidc"]["properties"]["additionalConfig"]["clientAuthMethod"] == "client_secret_basic"
    # logout fields
    assert payload["providers"]["oidc"]["properties"]["additionalConfig"]["logoutURI"] == "https://example.gc.ca/logout"
    assert payload["providers"]["oidc"]["properties"]["additionalConfig"]["logoutRedirectURIs"] == ["https://example.gc.ca/logout-callback"]
    assert payload["providers"]["oidc"]["properties"]["additionalConfig"]["logoutOption"] == "back_channel"
