"""HTTP exceptions for IBM Verify API client."""

from typing import Any, Dict, Optional


class IBMVerifyAPIError(Exception):
    """Base exception for IBM Verify API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code from response
            response_body: Full response body from API (may contain error details)
        """
        self.message = message
        self.status_code = status_code
        self.response_body = response_body or {}
        super().__init__(self.message)

    def get_error_detail(self) -> str:
        """Extract user-friendly error detail from response body.

        IBM Verify API typically returns error info in these fields:
        - messageCode: Machine-readable error code
        - message: Human-readable message
        - details: Additional context
        """
        if not self.response_body:
            return self.message

        # Try common IBM Verify error fields
        if isinstance(self.response_body, dict):
            msg = self.response_body.get("messageId")
            detail = self.response_body.get("messageDescription")

            if msg or detail:
                return f"{msg}: {detail}" if msg and detail else msg or detail

            # Sometimes errors are nested under 'error'
            error_obj = self.response_body.get("error", {})
            if isinstance(error_obj, dict):
                error_msg = error_obj.get("message")
                if error_msg:
                    return error_msg

        return self.message

    def __str__(self) -> str:
        """Return string representation including details if available."""
        detail = self.get_error_detail()
        if self.status_code:
            return f"{self.status_code}: {detail}"
        return detail


class IBMVerifyBadRequest(IBMVerifyAPIError):
    """400 Bad Request - invalid payload or validation error."""

    pass


class IBMVerifyUnauthorized(IBMVerifyAPIError):
    """401 Unauthorized - authentication failed."""

    pass


class IBMVerifyForbidden(IBMVerifyAPIError):
    """403 Forbidden - insufficient permissions."""

    pass


class IBMVerifyNotFound(IBMVerifyAPIError):
    """404 Not Found - resource does not exist."""

    pass


class IBMVerifyServerError(IBMVerifyAPIError):
    """500+ Server Error - IBM Verify service issue."""

    pass
