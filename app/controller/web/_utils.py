"""Web controller utilities - re-exports shared utilities with web-specific setup."""
from pathlib import Path

from fastapi.templating import Jinja2Templates
from app.utils.i18n import register_i18n, get_request_locale, match_supported_locale, sanitize_next_url, translate
from app.config import get_settings

# Import all shared utilities
from app.controller._utils import (
    _extract_application_id,
    _parse_application_list,
    _normalize_epoch_seconds,
    _mask_email,
    _mask_ip,
    _normalize_redirect_uris,
    _normalize_checkbox,
    _build_application_creation_payload,
    _parse_audit_trail,
)

# Web-specific setup
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
register_i18n(templates)
settings = get_settings()

__all__ = [
    "templates",
    "settings",
    "get_request_locale",
    "match_supported_locale",
    "sanitize_next_url",
    "translate",
    "_extract_application_id",
    "_parse_application_list",
    "_normalize_epoch_seconds",
    "_mask_email",
    "_mask_ip",
    "_normalize_redirect_uris",
    "_normalize_checkbox",
    "_build_application_creation_payload",
    "_parse_audit_trail",
]
