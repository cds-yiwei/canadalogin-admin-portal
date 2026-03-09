from typing import Any, Dict, List, Optional

from app.core.models.user import User
from app.core.roles import Role
from app.repository.iv_admin_client import IBMVerifyAdminClient


class AdminService:
    def __init__(self, client: IBMVerifyAdminClient):
        self._client = client

    def _normalize_audit_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize audit report payload into standardized dict.

        Returns: {"events": [...], "next": <token>|None, "total": <int>|None}
        """
        # If upstream already returned a normalized payload, return as-is
        if isinstance(payload, dict) and isinstance(payload.get("events"), list):
            return {
                "events": payload.get("events", []),
                "next": payload.get("next"),
                "total": payload.get("total"),
            }
        events: List[Dict[str, Any]] = []
        next_token = None
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
        return {"events": events, "next": next_token, "total": total}

    async def list_users(self) -> List[User]:
        data = await self._client.fetch_users()
        return [
            User(
                id=item.get("id", "unknown"),
                email=item.get("userName", ""),
                roles=[Role.READ_ONLY],
                permissions=item.get("permissions", []),
            )
            for item in data
        ]

    async def search_users_by_name(self, username: str) -> List[User]:
        """Search for users by username."""
        data = await self._client.search_users_by_name(username)
        return [
            User(
                id=item.get("id", "unknown"),
                email=item.get("userName", ""),
                roles=[Role.READ_ONLY],
                permissions=item.get("permissions", []),
            )
            for item in data
        ]

    async def get_application_detail(self, application_id: str) -> Dict[str, Any]:
        return await self._client.get_application_detail(application_id)

    async def create_application(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._client.create_application(payload)

    async def delete_application(self, application_id: str) -> None:
        await self._client.delete_application(application_id)

    async def get_application_total_logins(
        self,
        application_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._client.get_application_total_logins(application_id, from_date, to_date)

    async def get_application_audit_trail(
        self,
        application_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        size: int = 50,
        sort_by: str = "time",
        sort_order: str = "DESC",
    ) -> Dict[str, Any]:

        payload = await self._client.get_application_audit_trail(
            application_id,
            from_date,
            to_date,
            size,
            sort_by,
            sort_order,
        )
        return self._normalize_audit_report(payload)

    async def get_application_audit_trail_search_after(
        self,
        application_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        size: int = 25,
        search_after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Call repository search_after API and normalize results.

        Returns: dict {"events": [...], "next": str|None, "total": int|None}
        """
        payload = await self._client.app_audit_trail_search_after(
            application_id,
            from_date,
            to_date,
            size=size,
            search_after=search_after,
        )
        return self._normalize_audit_report(payload)

    async def get_client_secret(self, client_id: str) -> Dict[str, Any]:
        return await self._client.get_client_secret(client_id)

    async def update_client_secret(self, client_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._client.update_client_secret(client_id, payload)

    async def delete_rotated_client_secrets(self, client_id: str, path: List[str]) -> bool:
        return await self._client.delete_rotated_client_secrets(client_id, path)

    async def get_application_entitlements(self, application_id: str) -> Dict[str, Any]:
        return await self._client.get_application_entitlements(application_id)

    async def list_groups(self, count: int = 100, start_index: int = 1) -> List[Dict[str, Any]]:
        """List all groups."""
        return await self._client.list_groups(count, start_index)

    async def search_groups_by_name(self, group_name: str) -> List[Dict[str, Any]]:
        """Search for groups by name."""
        return await self._client.search_groups_by_name(group_name)

    async def get_group_by_id(self, group_id: str) -> Dict[str, Any]:
        """Get a specific group by ID."""
        return await self._client.get_group_by_id(group_id)

    async def add_user_to_group(self, group_id: str, user_id: str) -> None:
        """Add a user to a group."""
        await self._client.add_user_to_group(group_id, user_id)

    async def remove_user_from_group(self, group_id: str, user_id: str) -> None:
        """Remove a user from a group."""
        await self._client.remove_user_from_group(group_id, user_id)

    async def is_user_in_group(self, group_id: str, user_id: str) -> bool:
        """Check if a user is a member of a group."""
        return await self._client.is_user_in_group(group_id, user_id)

    async def update_application_section(self, application_id: str, section: str, payload: dict) -> Any:
        """Update a single logical section of an application and persist via the repository client.

        This method performs local merges into the current application detail and delegates
        persistence to the IBMVerifyAdminClient. It catches HTTP/client errors and
        raises a RuntimeError with helpful context (status / correlation id) so callers
        can handle user-facing messaging.
        """

        current_detail = await self.get_application_detail(application_id)
        if not current_detail:
            raise ValueError(f"Application with ID {application_id} not found.")

        # Make a shallow copy to avoid mutating cached objects
        updated = dict(current_detail)

        # Update the relevant section with new payload
        if section == "application_info":
            updated["name"] = payload.get("name", updated.get("name"))
            updated["description"] = payload.get("description", updated.get("description"))
            providers = updated.get("providers", {})
            if "saml" in providers and payload.get("providers", {}).get("saml"):
                saml_props = providers["saml"].get("properties", {})
                saml_payload_props = payload["providers"]["saml"].get("properties", {})
                saml_props["companyName"] = saml_payload_props.get("companyName", saml_props.get("companyName"))
                providers["saml"]["properties"] = saml_props
            if "oidc" in providers and payload.get("providers", {}).get("oidc"):
                oidc_props = providers["oidc"].get("properties", {})
                oidc_payload_props = payload["providers"]["oidc"].get("properties", {})
                oidc_props["applicationUrl"] = oidc_payload_props.get(
                    "applicationUrl", oidc_props.get("applicationUrl")
                )
                providers["oidc"]["properties"] = oidc_props
            updated["providers"] = providers

        try:
            result = await self._client.update_application(application_id, updated)
            return result
        except Exception as exc:
            # Attempt to extract correlation id or status from the client exception if available
            corr = None
            status = None
            headers = {}
            resp = None
            try:
                # If the client raised an HTTPError-like exception with response attr
                resp = getattr(exc, "response", None)
                if resp is not None:
                    status = getattr(resp, "status_code", None)
                    # headers may be a dict-like
                    headers = getattr(resp, "headers", {}) or {}
                    corr = headers.get("x-correlation-id") or headers.get("X-Correlation-Id") or headers.get("x-global-transaction-id")
            except Exception:
                pass

            # Log detailed info for debugging (include headers and any response text if available)
            try:
                import logging

                logger = logging.getLogger("app.admin_service")
                logger.error("Failed update_application: status=%s corr=%s exception=%s", status, corr, exc)
                if resp is not None:
                    try:
                        text = getattr(resp, "text", None)
                        if text:
                            logger.error("Upstream response body: %s", text)
                    except Exception:
                        pass
                    try:
                        logger.error("Upstream response headers: %s", dict(headers))
                    except Exception:
                        pass
            except Exception:
                # Best-effort logging; do not mask the original exception
                pass

            msg = f"update_application failed"
            if status:
                msg = f"{msg} (status={status})"
            if corr:
                msg = f"{msg} (corr={corr})"
            # Re-raise as RuntimeError to be handled by controller
            raise RuntimeError(msg) from exc


