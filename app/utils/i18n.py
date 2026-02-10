from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import yaml
from jinja2 import pass_context
from starlette.requests import Request
from app.config import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent
LOCALES_DIR = BASE_DIR / "locales"

SUPPORTED_LOCALES = ("en", "en-ca", "fr", "fr-ca")
DEFAULT_LOCALE = "en"
FALLBACK_LOCALES = {
    "en-ca": "en",
    "fr-ca": "fr",
}


def normalize_locale(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def match_supported_locale(value: str | None) -> str | None:
    if not value:
        return None
    normalized = normalize_locale(value)
    if normalized in SUPPORTED_LOCALES:
        return normalized
    base = normalized.split("-")[0]
    if base in SUPPORTED_LOCALES:
        return base
    return None


def parse_accept_language(header_value: str | None) -> list[str]:
    if not header_value:
        return []
    items: list[tuple[str, float]] = []
    for part in header_value.split(","):
        section = part.strip()
        if not section:
            continue
        lang, *params = section.split(";")
        q_value = 1.0
        for param in params:
            param = param.strip()
            if param.startswith("q="):
                try:
                    q_value = float(param.split("=", 1)[1])
                except ValueError:
                    q_value = 0.0
        items.append((lang.strip(), q_value))
    items.sort(key=lambda entry: entry[1], reverse=True)
    return [lang for lang, _ in items]


def select_locale(accept_language: str | None) -> str:
    for candidate in parse_accept_language(accept_language):
        matched = match_supported_locale(candidate)
        if matched:
            return matched
    return DEFAULT_LOCALE


@lru_cache(maxsize=32)
def load_messages(locale: str) -> dict[str, Any]:
    path = LOCALES_DIR / f"{locale}.yml"
    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except FileNotFoundError:
        return {}


def _lookup_message(messages: dict[str, Any], key: str) -> str | None:
    value: Any = messages
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    if value is None:
        return None
    return str(value)


def translate(locale: str, key: str, **kwargs: Any) -> str:
    message = _lookup_message(load_messages(locale), key)
    if message is None:
        fallback_locale = FALLBACK_LOCALES.get(locale)
        if fallback_locale:
            message = _lookup_message(load_messages(fallback_locale), key)
    if message is None and locale != DEFAULT_LOCALE:
        message = _lookup_message(load_messages(DEFAULT_LOCALE), key)
    if message is None:
        return key
    try:
        return message.format(**kwargs)
    except KeyError:
        return message


def get_request_locale(request: Request | None) -> str:
    if request is None:
        return DEFAULT_LOCALE
    return getattr(request.state, "locale", DEFAULT_LOCALE)


def build_language_switch_url(request: Request | None, target_locale: str) -> str:
    locale = match_supported_locale(target_locale) or DEFAULT_LOCALE
    if request is None:
        return f"/locale?{urlencode({'lang': locale})}"

    query_items: list[tuple[str, str]] = []
    for key, value in request.query_params.multi_items():
        if key == "lang":
            continue
        query_items.append((key, value))

    next_path = request.url.path
    if query_items:
        next_path = f"{next_path}?{urlencode(query_items)}"

    return f"/locale?{urlencode({'lang': locale, 'next': next_path})}"


def sanitize_next_url(next_url: str | None) -> str | None:
    if not next_url:
        return None
    parsed = urlparse(next_url)
    if parsed.scheme or parsed.netloc:
        return None
    if not parsed.path.startswith("/"):
        return None
    return next_url


@pass_context
def jinja_translate(context: dict[str, Any], key: str, **kwargs: Any) -> str:
    request = context.get("request")
    locale = get_request_locale(request)
    return translate(locale, key, **kwargs)


@pass_context
def jinja_current_locale(context: dict[str, Any]) -> str:
    request = context.get("request")
    return get_request_locale(request)


@pass_context
def jinja_lang_switch_url(context: dict[str, Any], target_locale: str) -> str:
    request = context.get("request")
    return build_language_switch_url(request, target_locale)


def register_i18n(templates: Any) -> None:
    templates.env.globals["t"] = jinja_translate
    templates.env.globals["current_locale"] = jinja_current_locale
    templates.env.globals["lang_switch_url"] = jinja_lang_switch_url
    # Expose configured site-level values to templates
    settings = get_settings()
    templates.env.globals["date_modified"] = settings.date_modified
