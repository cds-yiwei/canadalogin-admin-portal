"""Shared utility functions for web and API controllers."""

from typing import Any, Dict, List
from ipaddress import ip_address

from pydantic import TypeAdapter, ValidationError
from loguru import logger

from app.controller.schemas import (
    ApplicationListData,
    ApplicationCreation,
    ApplicationAuditTrailResponse,
)


application_list_adapter = TypeAdapter(list[ApplicationListData])


def _extract_application_id(raw_app: dict) -> str | None:
    """Extract application ID from raw API response.

    Tries multiple field names and patterns to extract the ID.
    """
    href = (((raw_app or {}).get("_links") or {}).get("self") or {}).get("href")
    if href:
        candidate = href.rstrip("/").split("/")[-1]
        if candidate and candidate.isdigit():
            return candidate

    for key in ("applicationId", "applicationUuid", "uuid", "id"):
        value = (raw_app or {}).get(key)
        if value:
            value_str = str(value).strip()
            if value_str:
                return value_str
    return None


def _parse_application_list(raw_items: Any) -> list[ApplicationListData]:
    """Parse and validate a list of raw applications from API response."""
    if not isinstance(raw_items, list):
        return []

    normalized: list[dict[str, Any]] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue

        href = str(((raw.get("_links") or {}).get("self") or {}).get("href") or "").strip()
        app_id = _extract_application_id(raw)
        app_name = str(raw.get("name") or "").strip()
        app_type = str(raw.get("type") or "").strip()

        if not app_id or not app_name or not app_type:
            continue

        normalized.append(
            {
                "app_id": app_id,
                "app_name": app_name,
                "app_type": app_type,
                "verify_href": href or None,
            }
        )

    if not normalized:
        return []

    try:
        return application_list_adapter.validate_python(normalized)
    except ValidationError as exc:  # noqa: BLE001
        logger.warning("Failed to validate application list payload: {}", exc)
        return []


def _normalize_epoch_seconds(raw_value: int | None) -> int | None:
    """Normalize epoch timestamp to seconds (handles milliseconds)."""
    if raw_value is None:
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    if value > 10**11:
        return value // 1000
    return value


def _mask_email(value: str) -> str:
    """Mask email address for privacy (keep first 2 chars of local part)."""
    value = str(value or "").strip()
    if not value or "@" not in value:
        return value

    local, domain = value.split("@", 1)
    local = local.strip()
    domain = domain.strip()
    if not local or not domain:
        return value

    prefix = local[:2]
    return f"{prefix}***@{domain}"


def _mask_ip(value: str) -> str:
    """Mask IP address for privacy (IPv4: xxx.xxx, IPv6: first 2 parts)."""
    value = str(value or "").strip()
    if not value:
        return value

    try:
        parsed_ip = ip_address(value)
    except ValueError:
        return value

    if parsed_ip.version == 4:
        octets = value.split(".")
        if len(octets) == 4:
            return f"{octets[0]}.{octets[1]}.xxx.xxx"
        return value

    hextets = parsed_ip.exploded.split(":")
    if len(hextets) == 8:
        masked_tail = ["xxxx"] * 6
        return ":".join(hextets[:2] + masked_tail)
    return value


def _normalize_redirect_uris(raw_value: str | None) -> list[str]:
    """Normalize redirect URIs from form input (newline-delimited)."""
    if not raw_value:
        return []
    return [line.strip() for line in str(raw_value).splitlines() if line.strip()]


def _normalize_checkbox(raw_value: str | None) -> str:
    """Normalize checkbox value to 'true' or 'false' string."""
    if raw_value is None:
        return "false"
    return "true" if str(raw_value).strip().lower() in {"true", "1", "yes", "on"} else "false"


def _build_application_creation_payload(form_data: dict, owners: List[str]) -> dict:
    """Build IBM Verify application creation payload from form data.

    Handles OIDC configuration, client types, and various authentication methods.
    """
    name = str(form_data.get("name") or "").strip()
    description = str(form_data.get("description") or "").strip()
    company_name = str(form_data.get("company_name") or "").strip()
    application_url = str(form_data.get("application_url") or "").strip()
    redirect_uris = _normalize_redirect_uris(form_data.get("redirect_uris"))
    # prefer explicit pkce value, fall back to forced value when client_type enforces it
    pkce_enabled = _normalize_checkbox(
        form_data.get("pkce_enabled") or form_data.get("pkce_enabled_force")
    )

    # New minimal OIDC fields (normalized)
    client_type = str(form_data.get("client_type") or "").strip() or None
    client_auth_method = str(form_data.get("client_auth_method") or "").strip() or None
    post_logout_redirect_uris = _normalize_redirect_uris(form_data.get("post_logout_redirect_uris"))
    logout_uri = str(form_data.get("logout_uri") or "").strip()
    logout_method = str(form_data.get("logout_method") or "").strip()
    # defaulting: if confidential and no auth method provided, default to client_secret_basic
    if client_type == "confidential" and not client_auth_method:
        client_auth_method = "client_secret_basic"
    # If client_type is public, PKCE must be required
    if client_type == "public":
        pkce_enabled = "true"
    # handle jwks for private_key_jwt or jwks_uri selection
    jwks_uri_value = str(form_data.get("jwks_uri") or "").strip()
    if client_auth_method == "private_key_jwt" and not jwks_uri_value:
        raise ValueError("jwks_uri is required for private_key_jwt")
    payload: Dict[str, Any] = {
        "visibleOnLaunchpad": True,
        "customization": {"themeId": "default"},
        "name": name,
        "applicationState": True,
        "description": description,
        "templateId": "998",
        "owners": owners,
        "provisioning": {
            "policies": {
                "provPolicy": "disabled",
                "deProvPolicy": "disabled",
                "deProvAction": "delete",
                "adoptionPolicy": {
                    "matchingAttributes": [],
                    "remediationPolicy": {"policy": "NONE"},
                },
                "gracePeriod": 30,
            },
            "attributeMappings": [],
            "reverseAttributeMappings": [],
        },
        "attributeMappings": [],
        "providers": {
            "sso": {"userOptions": "oidc"},
            "oidc": {
                "properties": {
                    "doNotGenerateClientSecret": "false",
                    "additionalConfig": {
                        "oidcv3": True,
                        "requestObjectParametersOnly": "false",
                        "requestObjectSigningAlg": "RS256",
                        "requestObjectRequireExp": "true",
                        "certificateBoundAccessTokens": "false",
                        "dpopBoundAccessTokens": "false",
                        "validateDPoPProofJti": "false",
                        "dpopProofSigningAlg": "RS256",
                        "authorizeRspSigningAlg": "RS256",
                        "authorizeRspEncryptionAlg": "none",
                        "authorizeRspEncryptionEnc": "none",
                        "responseTypes": ["none", "code"],
                        "responseModes": [
                            "query",
                            "fragment",
                            "form_post",
                            "query.jwt",
                            "fragment.jwt",
                            "form_post.jwt",
                        ],
                        "clientAuthMethod": "default",
                        "requirePushAuthorize": "false",
                        "requestObjectMaxExpFromNbf": 1800,
                        "exchangeForSSOSessionOption": "default",
                        "subjectTokenTypes": ["urn:ietf:params:oauth:token-type:access_token"],
                        "actorTokenTypes": ["urn:ietf:params:oauth:token-type:access_token"],
                        "requestedTokenTypes": ["urn:ietf:params:oauth:token-type:access_token"],
                        "actorTokenRequired": False,
                        "logoutOption": "none",
                        "sessionRequired": False,
                        "requestUris": [],
                        "allowedClientAssertionVerificationKeys": [],
                    },
                    "generateRefreshToken": "true",
                    "renewRefreshToken": "true",
                    "idTokenEncryptAlg": "none",
                    "idTokenEncryptEnc": "none",
                    "grantTypes": {
                        "authorizationCode": "true",
                        "implicit": "false",
                        "clientCredentials": "false",
                        "ropc": "false",
                        "tokenExchange": "false",
                        "deviceFlow": "false",
                        "jwtBearer": "false",
                        "policyAuth": "false",
                    },
                    "accessTokenExpiry": 3600,
                    "refreshTokenExpiry": 86400,
                    "idTokenSigningAlg": "RS256",
                    "renewRefreshTokenExpiry": 86400,
                    "redirectUris": redirect_uris,
                },
                "token": {"accessTokenType": "default", "audiences": []},
                "grantProperties": {"generateDeviceFlowQRCode": "false"},
                "requirePkceVerification": pkce_enabled,
                "consentAction": "always_prompt",
                "applicationUrl": application_url,
                "scopes": [],
                "restrictEntitlements": True,
                "entitlements": [],
            },
            "saml": {"properties": {"companyName": company_name or None, "uniqueID": ""}},
        },
        "apiAccessClients": [],
    }

    # inject minimal extra fields if provided
    if client_type == "public":
        payload["providers"]["oidc"]["properties"]["doNotGenerateClientSecret"] = "true"
        payload["providers"]["oidc"]["properties"]["additionalConfig"][
            "clientAuthMethod"
        ] = "default"
        payload["providers"]["oidc"]["requirePkceVerification"] = "true"
    elif client_type == "confidential":
        if client_auth_method and client_auth_method != "default":
            payload["providers"]["oidc"]["properties"]["additionalConfig"][
                "clientAuthMethod"
            ] = client_auth_method
        if client_auth_method and client_auth_method == "private_key_jwt" and jwks_uri_value:
            payload["providers"]["oidc"]["properties"]["jwksUri"] = jwks_uri_value
    # single logout options
    if logout_method:
        payload["providers"]["oidc"]["properties"]["additionalConfig"][
            "logoutOption"
        ] = logout_method
        payload["providers"]["oidc"]["properties"]["additionalConfig"]["sessionRequired"] = (
            True if logout_method != "none" else False
        )
    if logout_method != "none" and logout_uri:
        payload["providers"]["oidc"]["properties"]["additionalConfig"]["logoutURI"] = logout_uri
    if logout_method != "none" and post_logout_redirect_uris:
        payload["providers"]["oidc"]["properties"]["additionalConfig"][
            "logoutRedirectURIs"
        ] = post_logout_redirect_uris

    return ApplicationCreation.model_validate(payload).model_dump(exclude_none=True)

async def _build_application_update_payload(application_id: str, adminService: Any) -> dict:
    """Build IBM Verify application update payload from form data.

    Only includes fields that are present in the form data for partial updates.
    """
    payload: Dict[str, Any] = {
        "name": "demo",
        "templateId": "998",
        "applicationRefId": "",
        "providers": {
            "saml": {
                "properties": {
                    "companyName": "demo comp",
                    "generateUniqueID": "false"
                },
                "justInTimeProvisioning": "false"
            },
            "sso": {
                "userOptions": "oidc"
            },
            "oidc": {
                "applicationUrl": "https://asdf.com",
                "properties": {
                    "grantTypes": {
                        "authorizationCode": "true",
                        "implicit": "false",
                        "deviceFlow": "false",
                        "ropc": "false",
                        "jwtBearer": "false",
                        "policyAuth": "false",
                        "clientCredentials": "false",
                        "tokenExchange": "false"
                    },
                    "redirectUris": [
                        "https://asdf.com/callback"
                    ],
                    "idTokenSigningAlg": "RS256",
                    "accessTokenExpiry": 3600,
                    "refreshTokenExpiry": 86400,
                    "doNotGenerateClientSecret": "false",
                    "generateRefreshToken": "true",
                    "renewRefreshTokenExpiry": 86400,
                    "clientId": "c24c9d1e-4f2a-432f-bf67-9f5bb7b8b7ab",
                    "clientSecret": "jbnGR4evBT",
                    "consentType": "dpcm",
                    "renewRefreshToken": "true",
                    "additionalConfig": {
                        "requestObjectMaxExpFromNbf": 1800,
                        "authorizeRspSigningAlg": "RS256",
                        "allowedClientAssertionVerificationKeys": [],
                        "clientAuthMethod": "default",
                        "validateDPoPProofJti": "false",
                        "subjectTokenTypes": [
                            "urn:ietf:params:oauth:token-type:access_token"
                        ],
                        "certificateBoundAccessTokens": "false",
                        "logoutRedirectURIs": [
                            "https://asdf.com/after-logout"
                        ],
                        "requestObjectSigningAlg": "RS256",
                        "requestedTokenTypes": [
                            "urn:ietf:params:oauth:token-type:access_token"
                        ],
                        "actorTokenRequired": "false",
                        "responseModes": [
                            "query",
                            "fragment",
                            "form_post",
                            "query.jwt",
                            "fragment.jwt",
                            "form_post.jwt"
                        ],
                        "requestObjectParametersOnly": "false",
                        "responseTypes": [
                            "none",
                            "code"
                        ],
                        "logoutOption": "back_channel",
                        "sessionRequired": "true",
                        "exchangeForSSOSessionOption": "default",
                        "logoutURI": "https://asdf.com/logout",
                        "useUserDefaultEntitlements": "true",
                        "dpopBoundAccessTokens": "false",
                        "oidcv3": "true",
                        "requestObjectRequireExp": "true",
                        "authorizeRspEncryptionEnc": "none",
                        "dpopProofSigningAlg": "RS256",
                        "authorizeRspEncryptionAlg": "none",
                        "requirePushAuthorize": "false",
                        "actorTokenTypes": [
                            "urn:ietf:params:oauth:token-type:access_token"
                        ],
                        "requestUris": []
                    },
                    "idTokenEncryptAlg": "none",
                    "idTokenEncryptEnc": "none"
                },
                "scopes": [],
                "entitlements": [],
                "restrictEntitlements": "true",
                "grantProperties": {
                    "generateDeviceFlowQRCode": "false"
                },
                "token": {
                    "accessTokenType": "default",
                    "audiences": []
                },
                "consentAction": "always_prompt",
                "requirePkceVerification": "true"
            }
        },
        "applicationState": "true",
        "approvalRequired": "false",
        "description": "demo desc",
        "signonState": "true",
        "provisioningMode": "",
        "identitySources": [],
        "visibleOnLaunchpad": "true",
        "provisioning": {
            "authentication": {},
            "attributeMappings": [],
            "reverseAttributeMappings": [],
            "policies": {
                "provPolicy": "disabled",
                "deProvPolicy": "disabled",
                "deProvAction": "delete",
                "passwordSync": "disabled",
                "adoptionPolicy": {
                    "matchingAttributes": [],
                    "remediationPolicy": {
                        "policy": "NONE",
                        "autoRemediateOnUpdate": "false"
                    }
                },
                "gracePeriod": 30
            },
            "extension": {},
            "provisioningState": "disabled",
            "sendNotifications": "false",
            "generatePassword": "false",
            "generatePasswordOnRestore": "false",
            "generatedPasswordRecipients": []
        },
        "customization": {
            "themeId": "default"
        },
        "apiAccessClients": [],
        "adaptiveAuthentication": {},
        "owners": [
            "772001EFL1"
        ],
        "customIcon": "",
        "attributeMappings": []
    }
    
    current_detail = await adminService.get_application_detail(application_id)
    if not current_detail:
        raise ValueError(f"Application with ID {application_id} not found.")
    payload.update({k: v for k, v in current_detail.items() if k in payload})
    

    return payload

def _parse_audit_trail(raw_payload: Any) -> list[dict[str, Any]]:
    """Parse and transform audit trail response from IBM Verify API.

    Extracts hits, masks sensitive data (emails, IPs), and normalizes timestamps.

    Accepts either the upstream shape (dict with response.report.hits) or a normalized
    dict with key 'events' containing a list of flattened event dicts (id, timestamp, username, origin, result, country).
    """
    # If caller passed a normalized dict (from iv_admin_client), accept it directly
    if isinstance(raw_payload, dict) and "events" in raw_payload:
        events = raw_payload.get("events") or []
        rows: list[dict[str, Any]] = []
        for ev in events:
            username_raw = str(ev.get("username") or ev.get("userid") or "").strip()
            username_known = bool(username_raw) and username_raw.upper() != "UNKNOWN"
            origin_raw = str(ev.get("origin") or "").strip()
            ip_version: int | None = None
            if origin_raw:
                try:
                    ip_version = ip_address(origin_raw).version
                except ValueError:
                    ip_version = None
            result_raw = str(ev.get("result") or "").strip().lower()
            time_seconds = _normalize_epoch_seconds(ev.get("timestamp"))
            country = str(ev.get("country") or "").strip()
            username_display = _mask_email(username_raw) if username_known else ""
            origin_display = _mask_ip(origin_raw)
            rows.append(
                {
                    "username": username_raw,
                    "username_display": username_display,
                    "username_known": username_known,
                    "origin": origin_raw,
                    "origin_display": origin_display,
                    "ip_version": ip_version,
                    "result": result_raw,
                    "time_seconds": time_seconds,
                    "country": country,
                }
            )
        return rows

    parsed_payload: ApplicationAuditTrailResponse | None = None
    try:
        parsed_payload = ApplicationAuditTrailResponse.model_validate(raw_payload)
    except ValidationError as exc:  # noqa: BLE001
        logger.warning("Failed to validate audit trail payload: {}", exc)
        return []
    hits = parsed_payload.response.report.hits
    if not hits:
        return []
    rows: list[dict[str, Any]] = []
    for hit in hits:
        data = hit.source.data
        geoip = hit.source.geoip
        username_raw = str(data.username or "").strip()
        username_known = bool(username_raw) and username_raw.upper() != "UNKNOWN"
        origin_raw = str(data.origin or "").strip()
        ip_version: int | None = None
        if origin_raw:
            try:
                ip_version = ip_address(origin_raw).version
            except ValueError:
                ip_version = None
        result_raw = str(data.result or "").strip().lower()
        time_seconds = _normalize_epoch_seconds(hit.source.time)
        country = str(geoip.country_name or geoip.country_iso_code or "").strip()
        username_display = _mask_email(username_raw) if username_known else ""
        origin_display = _mask_ip(origin_raw)
        rows.append(
            {
                "username": username_raw,
                "username_display": username_display,
                "username_known": username_known,
                "origin": origin_raw,
                "origin_display": origin_display,
                "ip_version": ip_version,
                "result": result_raw,
                "time_seconds": time_seconds,
                "country": country,
            }
        )
    return rows
