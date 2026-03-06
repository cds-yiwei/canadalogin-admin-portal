from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import FastAPI, Request
from loguru import logger

from app.config import Settings, get_settings
from app.repository.exceptions import (
    IBMVerifyBadRequest,
    IBMVerifyUnauthorized,
    IBMVerifyForbidden,
    IBMVerifyNotFound,
    IBMVerifyServerError,
)


class IBMVerifyAdminClient:
    def __init__(self, base_url: str, client: AsyncOAuth2Client):
        self._base_url = base_url.rstrip("/")
        self._client = client

    def _handle_response(self, response) -> None:
        """Handle HTTP response and raise appropriate IBM Verify exception on error.

        Args:
            response: httpx.Response object

        Raises:
            IBMVerifyAPIError: Appropriate subclass based on status code
        """
        if response.status_code < 400:
            return

        try:
            response_body = response.json()
        except Exception:  # noqa: BLE001
            response_body = {"raw_text": response.text}

        error_map = {
            400: IBMVerifyBadRequest,
            401: IBMVerifyUnauthorized,
            403: IBMVerifyForbidden,
            404: IBMVerifyNotFound,
        }

        exception_class = error_map.get(response.status_code, IBMVerifyServerError)

        raise exception_class(
            message="IBM Verify API request failed",
            status_code=response.status_code,
            response_body=response_body,
        )

    async def fetch_users(self) -> List[Dict[str, Any]]:
        response = await self._client.get(f"{self._base_url}/v2.0/Users")
        self._handle_response(response)
        payload = response.json()
        if isinstance(payload, list):
            return payload
        return payload.get("Resources", [])

    async def search_users_by_name(self, username: str) -> List[Dict[str, Any]]:
        """Search for users by username using the IBM Verify API.

        Args:
            username: The username to search for

        Returns:
            List of user dictionaries matching the search criteria
        """
        query_params = {
            "count": 100,
            "fullText": username,
            "sortBy": "name.formatted",
            "startIndex": 1,
        }
        response = await self._client.get(
            f"{self._base_url}/v2.0/Users",
            params=query_params,
        )
        self._handle_response(response)
        payload = response.json()
        if isinstance(payload, list):
            return payload
        return payload.get("Resources", [])

    async def list_applications(self) -> List[Dict[str, Any]]:
        response = await self._client.get(f"{self._base_url}/v1.0/applications")
        self._handle_response(response)
        payload = response.json()
        if isinstance(payload, list):
            return payload
        return payload.get("resources", payload.get("Resources", []))

    async def get_application_detail(self, application_id: str) -> Dict[str, Any]:
        response = await self._client.get(f"{self._base_url}/v1.0/applications/{application_id}")
        self._handle_response(response)
        return response.json()

    async def create_application(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._client.post(
            f"{self._base_url}/v1.0/applications",
            json=payload,
        )
        self._handle_response(response)
        return response.json()

    async def delete_application(self, application_id: str) -> None:
        response = await self._client.delete(f"{self._base_url}/v1.0/applications/{application_id}")
        self._handle_response(response)

    async def get_application_total_logins(
        self,
        application_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now()
        past_7_days = now - timedelta(days=7)
        to_timestamp = to_date or str(int(now.timestamp() * 1000))
        from_timestamp = from_date or str(int(past_7_days.timestamp() * 1000))
        payload = {"APPID": application_id, "FROM": from_timestamp, "TO": to_timestamp}
        response = await self._client.post(
            f"{self._base_url}/v1.0/reports/app_total_logins",
            json=payload,
        )
        self._handle_response(response)
        return response.json()

    async def get_application_audit_trail(
        self,
        application_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        size: int = 50,
        sort_by: str = "time",
        sort_order: str = "DESC",
    ) -> Dict[str, Any]:
        now = datetime.now()
        past_7_days = now - timedelta(days=7)
        to_timestamp = to_date or str(int(now.timestamp() * 1000))
        from_timestamp = from_date or str(int(past_7_days.timestamp() * 1000))
        normalized_sort_order = (sort_order or "DESC").upper()
        if normalized_sort_order not in {"ASC", "DESC"}:
            normalized_sort_order = "DESC"
        payload = {
            "APPID": application_id,
            "FROM": from_timestamp,
            "TO": to_timestamp,
            "SIZE": size if size > 0 else 50,
            "SORT_BY": sort_by or "time",
            "SORT_ORDER": normalized_sort_order,
        }
        response = await self._client.post(
            f"{self._base_url}/v1.0/reports/app_audit_trail",
            json=payload,
        )
        try:
            _ = response.status_code
        except Exception:
            pass
        self._handle_response(response)
        payload = response.json()
        # Normalize payload (support upstream response.report.hits)
        events = []
        next_token = None
        prev_token = None
        total = None
        try:
            report = payload.get("response", {}).get("report", {})
            hits = report.get("hits", []) if isinstance(report, dict) else []
            # Extract total if present (could be int or dict with value)
            raw_total = report.get("total") if isinstance(report, dict) else None
            if isinstance(raw_total, dict):
                total = raw_total.get("value")
            elif isinstance(raw_total, int):
                total = raw_total
            for hit in hits:
                _id = hit.get("_id")
                sort = hit.get("sort") or []
                if sort and isinstance(sort, list) and len(sort) >= 1:
                    timestamp = sort[0]
                else:
                    timestamp = hit.get("_source", {}).get("time")
                src = hit.get("_source", {})
                data = src.get("data", {}) if isinstance(src, dict) else {}
                geo = src.get("geoip", {}) if isinstance(src, dict) else {}
                events.append(
                    {
                        "id": _id,
                        "timestamp": timestamp,
                        "username": data.get("username") or data.get("userid"),
                        "origin": data.get("origin"),
                        "result": data.get("result"),
                        "country": geo.get("country_name") or geo.get("country_iso_code"),
                    }
                )
            if hits:
                first = hits[0]
                first_sort = first.get("sort") or []
                # For prev token, use first item's sort
                if first_sort and len(first_sort) >= 2:
                    first_ts = first_sort[0]
                    first_id = first_sort[1]
                else:
                    first_ts = first.get("_source", {}).get("time")
                    first_id = first.get("_id")
                if first_ts and first_id:
                    prev_token = f'{first_ts}, "{first_id}"'
                last = hits[-1]
                last_sort = last.get("sort") or []
                if last_sort and len(last_sort) >= 2:
                    last_ts = last_sort[0]
                    last_id = last_sort[1]
                else:
                    last_ts = last.get("_source", {}).get("time")
                    last_id = last.get("_id")
                if last_ts and last_id:
                    next_token = f'{last_ts}, "{last_id}"'
        except Exception:
            pass
        normalized = {"events": events, "next": next_token, "total": total}
        return normalized

    async def app_audit_trail_search_after(self, application_id: str, from_date: Optional[str] = None, to_date: Optional[str] = None, size: int = 25, search_after: Optional[str] = None, search_dir: Optional[str] = None) -> Dict[str, Any]:
        """Call the app_audit_trail_search_after endpoint and return parsed JSON.

        Args:
            application_id: Application ID to query
            from_date: From timestamp (ms)
            to_date: To timestamp (ms)
            size: Page size
            search_after: Optional opaque cursor
            search_dir: Optional direction ("before" or "after")
        Returns:
            Parsed JSON response as dict
        """
        now = datetime.now()
        past_7_days = now - timedelta(days=7)
        to_timestamp = to_date or str(int(now.timestamp() * 1000))
        from_timestamp = from_date or str(int(past_7_days.timestamp() * 1000))
        payload = {
            "APPID": application_id,
            "FROM": from_timestamp,
            "TO": to_timestamp,
            "SIZE": size if size > 0 else 25,
            "SORT_BY": "time",
            "SORT_ORDER": "DESC",
        }
        # Include SEARCH_AFTER/SEARCH_DIR in payload (preferred) for upstream
        if search_after:
            payload["SEARCH_AFTER"] = search_after
        if search_dir:
            payload["SEARCH_DIR"] = search_dir
        # Log outgoing payload and (later) response for debugging
        response = await self._client.post(
            f"{self._base_url}/v1.0/reports/app_audit_trail_search_after",
            json=payload,
        )

        # If upstream reports this report config doesn't exist, fallback gracefully
        if response.status_code == 400:
            try:
                body = response.json()
                msg = str(body.get("messageDescription") or body.get("messageId") or body)
            except Exception:
                msg = getattr(response, "text", "")
            if "app_audit_trail_search_after" in msg:
                logger.warning("app_audit_trail_search_after not supported by tenant, falling back to initial report endpoint")
                # Fall back: call initial report endpoint and return normalized result
                return await self.get_application_audit_trail(application_id, from_date, to_date, size, "time", "DESC")
        self._handle_response(response)
        payload = response.json()
        # Normalize payload similar to get_application_audit_trail
        events = []
        next_token = None
        prev_token = None
        total = None
        try:
            report = payload.get("response", {}).get("report", {})
            hits = report.get("hits", []) if isinstance(report, dict) else []
            # robustly extract total (int, dict.value, or numeric string)
            raw_total = None
            if isinstance(report, dict):
                raw_total = report.get("total")
            if raw_total is None:
                raw_total = payload.get("response", {}).get("report", {}).get("total")
            if isinstance(raw_total, dict):
                total = raw_total.get("value")
            elif isinstance(raw_total, int):
                total = raw_total
            elif isinstance(raw_total, str):
                try:
                    total = int(raw_total)
                except Exception:
                    total = None
            for hit in hits:
                _id = hit.get("_id")
                sort = hit.get("sort") or []
                if sort and isinstance(sort, list) and len(sort) >= 1:
                    timestamp = sort[0]
                else:
                    timestamp = hit.get("_source", {}).get("time")
                src = hit.get("_source", {})
                data = src.get("data", {}) if isinstance(src, dict) else {}
                geo = src.get("geoip", {}) if isinstance(src, dict) else {}
                events.append(
                    {
                        "id": _id,
                        "timestamp": timestamp,
                        "username": data.get("username") or data.get("userid"),
                        "origin": data.get("origin"),
                        "result": data.get("result"),
                        "country": geo.get("country_name") or geo.get("country_iso_code"),
                    }
                )
            if hits:
                first = hits[0]
                first_sort = first.get("sort") or []
                # For prev token, use first item's sort
                if first_sort and len(first_sort) >= 2:
                    first_ts = first_sort[0]
                    first_id = first_sort[1]
                else:
                    first_ts = first.get("_source", {}).get("time")
                    first_id = first.get("_id")
                if first_ts and first_id:
                    prev_token = f'{first_ts}, "{first_id}"'
                last = hits[-1]
                last_sort = last.get("sort") or []
                if last_sort and len(last_sort) >= 2:
                    last_ts = last_sort[0]
                    last_id = last_sort[1]
                else:
                    last_ts = last.get("_source", {}).get("time")
                    last_id = last.get("_id")
                if last_ts and last_id:
                    next_token = f'{last_ts}, "{last_id}"'
        except Exception:
            pass
        normalized = {"events": events, "next": next_token, "total": total}
        return normalized

    async def get_client_secret(self, client_id: str) -> Dict[str, Any]:

        response = await self._client.get(
            f"{self._base_url}/oidc-mgmt/v2.0/clients/{client_id}/secrets"
        )
        self._handle_response(response)
        return response.json()

    async def update_client_secret(self, client_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._client.post(
            f"{self._base_url}/oidc-mgmt/v2.0/clients/{client_id}/secrets",
            json=payload,
        )
        self._handle_response(response)
        return response.json()

    async def delete_rotated_client_secrets(self, client_id: str, path: List[str]) -> bool:
        payload = [{"path": p, "op": "remove"} for p in path]
        response = await self._client.patch(
            f"{self._base_url}/oidc-mgmt/v2.0/clients/{client_id}/secrets",
            json=payload,
        )
        self._handle_response(response)
        return True

    async def get_application_entitlements(self, application_id: str) -> Dict[str, Any]:
        response = await self._client.get(
            f"{self._base_url}/v1.0/owner/applications/{application_id}/entitlements"
        )
        self._handle_response(response)
        return response.json()

    async def list_groups(self, count: int = 100, start_index: int = 1) -> List[Dict[str, Any]]:
        """List all groups from IBM Verify.

        Args:
            count: Number of results to return (default 100)
            start_index: Starting index for pagination (default 1)

        Returns:
            List of group dictionaries
        """
        query_params = {
            "count": count,
            "startIndex": start_index,
        }
        response = await self._client.get(
            f"{self._base_url}/v2.0/Groups",
            params=query_params,
        )
        self._handle_response(response)
        payload = response.json()
        if isinstance(payload, list):
            return payload
        return payload.get("Resources", [])

    async def search_groups_by_name(self, group_name: str) -> List[Dict[str, Any]]:
        """Search for groups by name using the IBM Verify API.

        Args:
            group_name: The group name to search for

        Returns:
            List of group dictionaries matching the search criteria
        """
        query_params = {
            "count": 100,
            "fullText": group_name,
            "sortBy": "displayName",
            "startIndex": 1,
        }
        response = await self._client.get(
            f"{self._base_url}/v2.0/Groups",
            params=query_params,
        )
        self._handle_response(response)
        payload = response.json()
        if isinstance(payload, list):
            return payload
        return payload.get("Resources", [])

    async def get_group_by_id(self, group_id: str) -> Dict[str, Any]:
        """Get a specific group by ID.

        Args:
            group_id: The group ID

        Returns:
            Group dictionary with details
        """
        response = await self._client.get(f"{self._base_url}/v2.0/Groups/{group_id}")
        self._handle_response(response)
        return response.json()

    async def add_user_to_group(self, group_id: str, user_id: str) -> None:
        """Add a user to a group.

        Args:
            group_id: The group ID
            user_id: The user ID to add

        Raises:
            IBMVerifyAPIError: If the operation fails
        """
        payload = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": "add",
                    "path": "members",
                    "value": [{"type": "user", "value": user_id}],
                },
                {
                    "op": "add",
                    "path": "urn:ietf:params:scim:schemas:extension:ibm:2.0:Notification:notifyType",
                    "value": "NONE",
                },
            ],
        }
        response = await self._client.patch(
            f"{self._base_url}/v2.0/Groups/{group_id}",
            json=payload,
            headers={"Content-Type": "application/scim+json"},
        )
        self._handle_response(response)

    async def remove_user_from_group(self, group_id: str, user_id: str) -> None:
        """Remove a user from a group.

        Args:
            group_id: The group ID
            user_id: The user ID to remove

        Raises:
            IBMVerifyAPIError: If the operation fails
        """
        payload = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": "remove",
                    "path": f'members[value eq "{user_id}"]',
                }
            ],
        }
        response = await self._client.patch(
            f"{self._base_url}/v2.0/Groups/{group_id}",
            json=payload,
            headers={"Content-Type": "application/scim+json"},
        )
        self._handle_response(response)

    async def is_user_in_group(self, group_id: str, user_id: str) -> bool:
        """Check if a user is a member of a group.

        Args:
            group_id: The group ID
            user_id: The user ID to check

        Returns:
            bool: True if user is in group, False otherwise

        Raises:
            IBMVerifyAPIError: If the operation fails
        """
        try:
            group = await self.get_group_by_id(group_id)
            members = group.get("members", [])
            for member in members:
                if member.get("value") == user_id:
                    return True
            return False
        except Exception:
            # If group not found or other error, user not in group
            return False

    async def aclose(self) -> None:
        await self._client.aclose()


async def get_admin_api_client_async(request: Request) -> AsyncOAuth2Client:
    admin_api_client_async = getattr(request.app.state, "admin_api_client_async", None)
    if admin_api_client_async is None:
        # Lazily initialize an AsyncOAuth2Client for test/edge cases where startup
        # lifespan wasn't executed. Use runtime settings to configure the client.
        settings = get_settings()
        token_endpoint = f"{settings.ibm_sv_base_url.rstrip('/')}" + "/oauth2/token"
        admin_api_client_async = AsyncOAuth2Client(
            client_id=settings.ibm_sv_client_id,
            client_secret=settings.ibm_sv_client_secret,
            grant_type="client_credentials",
            token_endpoint=token_endpoint,
            leeway=120,
        )
        request.app.state.admin_api_client_async = admin_api_client_async
        logger.info("Lazy-registered Async Admin API Client on app.state")

    if not admin_api_client_async.token or admin_api_client_async.token.is_expired():
        logger.info("Fetching new token for Admin API client")
        await admin_api_client_async.fetch_token()
    return admin_api_client_async


async def init_admin_api_client(app: FastAPI, settings: Settings) -> None:
    """Initialize and register the admin API client during application startup."""
    token_endpoint = f"{settings.ibm_sv_base_url.rstrip('/')}/oauth2/token"
    admin_api_client_async = AsyncOAuth2Client(
        client_id=settings.ibm_sv_client_id,
        client_secret=settings.ibm_sv_client_secret,
        grant_type="client_credentials",
        token_endpoint=token_endpoint,
        leeway=120,
    )

    app.state.admin_api_client_async = admin_api_client_async
    logger.info("Async Admin API Client registered on app.state")


async def close_admin_api_client(app: FastAPI) -> None:
    """Close and unregister the admin API client during application shutdown."""
    admin_api_client_async = getattr(app.state, "admin_api_client_async", None)
    if admin_api_client_async is None:
        logger.info("No admin_api_client_async found on app.state to close")
        return

    await admin_api_client_async.aclose()
    logger.info("Closing Async Admin API Client")
    delattr(app.state, "admin_api_client_async")
