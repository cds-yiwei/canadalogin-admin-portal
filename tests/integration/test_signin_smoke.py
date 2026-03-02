import pathlib
TEMPLATES_DIR = pathlib.Path(__file__).resolve().parents[2] / "app" / "templates" / "auth"
LOGIN_TEMPLATE = TEMPLATES_DIR / "login.html"
FRAGMENT = TEMPLATES_DIR / "_signin_fragment.html"
ADAPTER = TEMPLATES_DIR / "_signin_adapter.html"


def test_login_template_exists_and_contains_fragment():
    assert LOGIN_TEMPLATE.exists(), f"Missing login template: {LOGIN_TEMPLATE}"
    text = LOGIN_TEMPLATE.read_text(encoding="utf-8")
    # login page should include the centralized signin fragment or directly reference gcds-button
    assert "_signin_fragment.html" in text or "gcds-button" in text
    # fragment file should exist
    assert FRAGMENT.exists(), f"Missing fragment: {FRAGMENT}"
    assert ADAPTER.exists(), f"Missing adapter: {ADAPTER}"
    adapter_text = ADAPTER.read_text(encoding="utf-8")
    assert "gcds-button" in adapter_text or "gcds-form" in adapter_text
