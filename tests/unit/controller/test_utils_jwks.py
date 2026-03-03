import pytest

from app.controller.web._utils import _build_application_creation_payload


def test_jwks_injection_when_private_key_jwt():
    form = {
        "name": "PK Test",
        "client_type": "confidential",
        "client_auth_method": "private_key_jwt",
        "jwks_uri": "https://example.gc.ca/.well-known/jwks.json",
    }
    owners = ["1000"]
    payload = _build_application_creation_payload(form, owners)
    assert payload["providers"]["oidc"]["properties"]["additionalConfig"]["jwksUri"] == "https://example.gc.ca/.well-known/jwks.json"


def test_private_key_jwt_without_jwks_raises():
    form = {"name": "PK Test", "client_type": "confidential", "client_auth_method": "private_key_jwt"}
    owners = ["1000"]
    with pytest.raises(ValueError):
        _build_application_creation_payload(form, owners)
