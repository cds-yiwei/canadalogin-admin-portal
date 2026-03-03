from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    oidc_client_id: str
    oidc_client_secret: str
    oidc_issuer: str
    oidc_redirect_uri: str
    oidc_scopes: List[str] = ["openid", "profile", "email"]

    session_cookie_name: str = "enterprise_session"
    session_cookie_domain: Optional[str] = None
    session_cookie_secure: bool = False
    session_lifetime: int = 3600
    redis_url: str = "redis://localhost:6379/0"

    token_refresh_leeway_seconds: int = 600

    ibm_sv_client_id: str
    ibm_sv_client_secret: str
    ibm_sv_base_url: str
    # Optional date used in the site footer; read from environment (e.g. 2026-02-05)
    date_modified: Optional[str] = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
