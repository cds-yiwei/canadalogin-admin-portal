# CanadaLogin Admin Site — FastAPI + Jinja2 + HTMX

## Short description

CanadaLogin Admin Site is an Enterprise FastAPI app that renders HTML with Jinja2 templates, augments interactivity with HTMX, styles with Tailwind CSS, authenticates via OIDC (Authlib), and keeps server-side sessions in Redis using `starsessions`. All business calls go to IBM Security Verify; there is no local database.

## Key points

- Server-rendered HTML (no React/SSR bundle) with Jinja2.
- HTMX for partial page updates; Tailwind for styling compiled to `app/static/main.css`.
- OIDC authentication with Authlib; sessions stored in Redis via `starsessions`.
- IBM Security Verify is the source of business data; no DB layer.
- Simple layered structure: controller, service, repository.

## Repository structure (current)

```
cl-admin-portal/
├─ README.md
├─ Dockerfile
├─ docker-compose.yml
├─ Makefile
├─ .env.sample
├─ .flake8
├─ package.json                  # npm scripts for Tailwind CSS
├─ package-lock.json
├─ postcss.config.cjs
├─ pyproject.toml
├─ requirements.txt
├─ requirements-dev.txt
├─ tailwind.config.cjs
├─ app/
│  ├─ main.py                  # FastAPI factory, middleware stack, lifecycle
│  ├─ config.py                # Settings/config loader (pydantic-settings)
│  ├─ controller/
│  │  ├─ api/                  # JSON API routes (REST endpoints)
│  │  │  ├─ routes.py
│  │  │  ├─ admin_routes.py    # /api/admin/* endpoints
│  │  │  └─ user_routes.py     # /api/user/* endpoints
│  │  ├─ web/                  # HTML + HTMX page handlers
│  │  │  ├─ routes.py          # Web router composition
│  │  │  ├─ auth_routes.py     # Login, logout, sign-in page
│  │  │  ├─ applications_routes.py  # Admin dashboard views
│  │  │  ├─ fragments.py       # HTMX fragment helpers
│  │  │  └─ _utils.py          # Controller utilities
│  │  └─ schemas.py            # Pydantic request/response models
│  ├─ service/
│  │  ├─ admin_service.py      # Admin business logic (applications, users)
│  │  ├─ authorization_service.py  # Permission checks
│  │  └─ user_service.py       # User-facing business logic
│  ├─ repository/
│  │  ├─ iv_admin_client.py    # IBM Verify admin API client + lifecycle
│  │  ├─ iv_user_client.py     # IBM Verify user API client + lifecycle
│  │  ├─ session_store.py      # Redis-backed session store (starsessions)
│  │  └─ yaml_role_policy_repository.py  # YAML policy loader
│  ├─ auth/
│  │  ├─ oidc.py              # OIDC flow helpers (Authlib wrapper)
│  │  └─ role_mapper.py        # Map OIDC claims to roles
│  ├─ core/
│  │  ├─ roles.py             # Role definitions (ADMIN, READ_ONLY, etc.)
│  │  ├─ permissions.py       # Permission constants
│  │  └─ models/user.py       # User domain model
│  ├─ middleware/
│  │  ├─ access_log.py        # HTTP request/response logging
│  │  ├─ auth_mw.py           # Session-based auth for web and API
│  │  ├─ authorization_mw.py  # Route-level authz via policies
│  │  ├─ error_handlers.py    # Global error handling (404, 500, etc.)
│  │  ├─ locale_mw.py         # i18n locale selection and session storage
│  │  └─ token_refresh_mw.py  # OIDC token refresh
│  ├─ dependencies/
│  │  ├─ auth.py              # FastAPI dependency: current user
│  │  ├─ policies.py          # FastAPI dependency: policies object
│  │  └─ services.py          # FastAPI dependency: service wiring
│  ├─ policies/
│  │  └─ roles.yaml           # Declarative role→permission mapping
│  ├─ assets/
│  │  └─ tailwind.css         # Tailwind input (npm run build:css)
│  ├─ static/
│  │  └─ main.css             # Tailwind output (built, minified)
│  ├─ templates/
│  │  ├─ base.html            # Base Jinja2 layout
│  │  ├─ home.html            # Home page
│  │  ├─ auth/login.html      # Sign-in page
│  │  └─ fragments/           # HTMX fragment templates
│  ├─ locales/                # i18n translation files
│  └─ utils/
│     ├─ acl.py               # Permission/ACL helpers
│     └─ i18n.py              # i18n utilities (locale matching, selection)
└─ tests/
   ├─ unit/
   │  ├─ core/test_permissions.py
   │  ├─ application/services/test_admin_service.py
   │  └─ controller/
   │     ├─ test_utils.py
   │     └─ test_utils_jwks.py
   └─ integration/
      └─ test_signin_smoke.py
```

## Architecture

- **Controller layer** (`controller/`): HTTP routes split into API routes (`api/`) and web routes (`web/`) for Jinja2 templates + HTMX fragments. Pydantic schemas for type-safe request/response validation.
- **Service layer** (`service/`): Business logic and orchestration. Thin wrappers over repository clients; focused on policy, validation, and composition.
- **Repository layer** (`repository/`): External system adapters (IBM Verify admin/user clients, Redis session store, YAML policy loader).
- **Core** (`core/`): Domain models (User), role and permission definitions.
- **Auth** (`auth/`): OIDC flow helpers (Authlib integration) and role mapper from OIDC claims.
- **Dependencies** (`dependencies/`): FastAPI dependency providers for injecting services, policies, and current user context.
- **Middleware** (`middleware/`): Request/response processing: logging, auth, authz, error handling, token refresh, locale selection.
- **i18n** (`locales/`, `utils/i18n.py`, `middleware/locale_mw.py`): Multilingual support with locale-aware session storage and middleware-based selection.
- **Policies** (`policies/roles.yaml`): Declarative role→permission mapping, loaded and enforced by middleware and ACL utilities.

## Templating and HTMX

- **Base layout** (`templates/base.html`): Root HTML structure.
- **Page templates** (e.g., `templates/home.html`): Extend base layout.
- **HTMX fragments** (`templates/fragments/`): Partials served via web routes or fragment helpers for fine-grained UI updates (no full page reload).
- **Fragment pattern**: Controllers set `HX-Trigger` headers and return lightweight HTML snippets; HTMX swaps them into the DOM.
- **Best practice**: Keep HTMX responses light and focused; avoid business logic in templates.

## Styling and CSS pipeline

- **Tailwind entrypoint**: `app/assets/tailwind.css`.
- **Build once**: `npm run build:css` → outputs `app/static/main.css` (minified).
- **Watch mode** (dev): `npm run watch:css` → auto-rebuild on template/config changes.
- **Included in layout**: `base.html` links `<link rel="stylesheet" href="{{ url_for('static', path='main.css') }}">`.

## Running locally

### Setup
1. **Create `.env` from `.env.sample`** and fill in OIDC + IBM Verify credentials:
   - `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_ISSUER`, `OIDC_REDIRECT_URI`
   - `IBM_SV_CLIENT_ID`, `IBM_SV_CLIENT_SECRET`, `IBM_SV_BASE_URL`
   - `REDIS_URL` (default: `redis://localhost:6379/0`)
   - `SESSION_COOKIE_NAME`, `SESSION_COOKIE_SECURE`, `SESSION_LIFETIME`

2. **Create and activate a Python virtual environment (recommended, Python 3.12)**:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Install Node dependencies** (for Tailwind CSS build):
   ```bash
   npm install
   ```

### Development workflow
4. **Build or watch CSS** (in a separate terminal):
   ```bash
   npm run watch:css  # Auto-rebuild on changes
   # OR
   npm run build:css  # One-time build (production)
   ```

5. **Start the FastAPI dev server**:
   ```bash
   uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload
   ```
   - Server runs at `http://localhost:8000`.
   - `--reload` enables hot-reload on Python file changes.

6. **Run tests**:
   ```bash
   pytest                                        # All tests
   pytest -q tests/unit/core/                    # Unit tests only
   pytest tests/unit/application/services/test_admin_service.py::test_list_users  # Single test
   pytest -q -v                                 # Verbose output
   ```

## Configuration (environment variables)

### OIDC / Authentication
- `OIDC_CLIENT_ID` — OIDC provider client ID
- `OIDC_CLIENT_SECRET` — OIDC provider client secret
- `OIDC_ISSUER` — OIDC provider issuer URL (e.g., `https://issuer.example.com`)
- `OIDC_REDIRECT_URI` — Callback URI after successful sign-in (e.g., `http://localhost:8000/auth/callback`)

### Session & Security
- `SESSION_COOKIE_NAME` — Name of session cookie (default: `enterprise_session`)
- `SESSION_COOKIE_DOMAIN` — Domain for session cookie (optional; `None` = current domain)
- `SESSION_COOKIE_SECURE` — Require HTTPS for session cookie (default: `false` for local dev)
- `SESSION_LIFETIME` — Session TTL in seconds (default: `3600`)
- `TOKEN_REFRESH_LEEWAY_SECONDS` — Buffer before token expiry to trigger refresh (default: `600`)

### IBM Security Verify
- `IBM_SV_CLIENT_ID` — IBM Verify service account client ID
- `IBM_SV_CLIENT_SECRET` — IBM Verify service account client secret
- `IBM_SV_BASE_URL` — IBM Verify tenant base URL (e.g., `https://verify.ibm.com`)

### Data & Logging
- `REDIS_URL` — Redis connection URL (default: `redis://localhost:6379/0`)
- `DATE_MODIFIED` — Optional date string for footer display (e.g., `2026-03-03`)
- `SKIP_SESSION_STORE` — Set to `1` to disable Redis session store (useful for static checks)

## Roles and permissions

- **Roles** (`app/core/roles.py`): Enumerated role types (e.g., `ADMIN`, `READ_ONLY`).
- **Permissions** (`app/core/permissions.py`): Permission constants (e.g., `CAN_VIEW_APPLICATIONS`, `CAN_DELETE_USER`).
- **Policy mapping** (`app/policies/roles.yaml`): YAML-driven declarative mapping of roles to permissions.
- **Enforcement**: Authorization middleware (`middleware/authorization_mw.py`) and ACL utilities (`utils/acl.py`) enforce permissions on routes and operations.
- **Access control**: Endpoints use dependency injection (`dependencies/auth.py`) to enforce current user, and ACL checks to gate operations.
- **OIDC to roles**: `app/auth/role_mapper.py` maps OIDC claims to local roles at login time.

## Testing

### Unit tests
- **Permission logic**: `tests/unit/core/test_permissions.py` — validates role/permission enforcement.
- **Service layer**: `tests/unit/application/services/test_admin_service.py` — tests business logic and IBM Verify adapters.
- **Controller utilities**: `tests/unit/controller/test_utils.py`, `test_utils_jwks.py` — validation and JWT parsing.

### Integration tests
- **Sign-in smoke test**: `tests/integration/test_signin_smoke.py` — validates sign-in template, OIDC adapter presence, and accessibility (pa11y).

### Running tests
```bash
pytest                                          # Run all tests
pytest -q                                       # Quiet mode (summary only)
pytest tests/unit/                              # Unit tests only
pytest tests/unit/core/test_permissions.py -v  # Verbose + single file
pytest -k admin_service                         # Tests matching a keyword
```

### Test coverage
- Use `pytest-cov` for coverage reports (add to `requirements-dev.txt` if needed):
  ```bash
  pytest --cov=app --cov-report=html
  ```

## Internationalization (i18n)

- **Locale support** (`app/utils/i18n.py`): Default locale and supported locale matching.
- **Middleware selection** (`app/middleware/locale_mw.py`): Automatic locale selection from query params (`?lang=fr`), session, or `Accept-Language` header.
- **Session storage**: Selected locale is persisted in the session for consistent experience.
- **Response header**: `Content-Language` header is set on all responses for client-side language negotiation.
- **Template integration**: Jinja2 templates can access the current locale via `request.state.locale` to render localized content.

## Deployment

- **Docker**: `Dockerfile` included for containerized deployment.
- **Environment**: All configuration via `.env` (pydantic-settings).
- **Redis**: Requires a running Redis instance (local or remote).
- **Session store skipping**: Set `SKIP_SESSION_STORE=1` for static checks/CI (avoids hard Redis dependency during CI linting).

---

---
Agent-oriented instructions: see AGENTS.md for automated-agent guidance and workflows.