from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.repository.exceptions import IBMVerifyAPIError

def add_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(IBMVerifyAPIError)
    async def ibm_verify_api_error_handler(request: Request, exc: IBMVerifyAPIError):
        """Handle IBM Verify API errors with detailed error information."""
        error_detail = exc.get_error_detail()
        status_code = exc.status_code or 500

        return JSONResponse(
            {"detail": error_detail},
            status_code=status_code,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse({"detail": "Internal Server Error"}, status_code=500)
