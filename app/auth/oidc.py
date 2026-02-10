"""
OIDC (OpenID Connect) authentication implementation.
"""

from typing import Any, Dict, Optional

import httpx
from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from authlib.jose import jwt
from authlib.jose.rfc7519.jwt import create_load_key

from app.config import get_settings

settings = get_settings()

oauth = OAuth()
oauth.register(
    name="verify_oidc",
    client_id=settings.oidc_client_id,
    client_secret=settings.oidc_client_secret,
    server_metadata_url=f"{settings.oidc_issuer}/.well-known/openid-configuration",
    client_kwargs={
        "scope": " ".join(settings.oidc_scopes),
    },
)


def get_verify_oidc_client() -> StarletteOAuth2App:
    client = oauth.create_client("verify_oidc")
    if client is None:
        raise ValueError("OIDC client 'verify_oidc' is not registered.")
    return client


async def validate_token(
    token: str, claims_options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    client = get_verify_oidc_client()
    jwk_set_data = await client.fetch_jwk_set()
    load_key = create_load_key(jwk_set_data)
    effective_claims_options = {
        "iss": {"values": [settings.oidc_issuer]},
        "aud": {"values": [settings.oidc_client_id]},
    }
    if claims_options:
        effective_claims_options.update(claims_options)
    try:
        claims = jwt.decode(token, load_key, claims_options=effective_claims_options)
        claims.validate(leeway=120)
        return {"active": True, "claims": dict(claims)}
    except Exception as exc:  # noqa: BLE001
        return {"active": False, "error": str(exc)}


async def refresh_token(
    http_client: httpx.AsyncClient, refresh_token: str, scope: Optional[str] = None
) -> Dict[str, Any]:
    client = get_verify_oidc_client()
    try:
        if not client.server_metadata:
            await client.load_server_metadata()
        token_endpoint = (
            client.server_metadata.get("token_endpoint") if client.server_metadata else None
        )
        if not token_endpoint:
            raise RuntimeError("OIDC token endpoint missing from server metadata")
        form_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.oidc_client_id,
            "client_secret": settings.oidc_client_secret,
        }
        if scope:
            form_data["scope"] = scope
        response = await http_client.post(
            token_endpoint,
            data=form_data,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"refresh token failed: {exc}") from exc
