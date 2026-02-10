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
├─ package.json
├─ package-lock.json
├─ postcss.config.cjs
├─ pyproject.toml
├─ requirements.txt
├─ requirements-dev.txt
├─ tailwind.config.cjs
├─ app/
│  ├─ main.py                  # FastAPI factory entrypoint
│  ├─ config.py                # settings/config loader
│  ├─ controller/
│  │  ├─ api/routes.py          # JSON API router (/api)
│  │  ├─ web/routes.py          # Jinja2/HTMX page handlers
│  │  ├─ web/fragments.py       # HTMX fragment helpers
│  │  └─ schemas.py             # Pydantic response/request models
│  ├─ service/
│  │  ├─ admin_service.py       # business logic
│  │  ├─ authorization_service.py
│  │  └─ user_service.py
│  ├─ repository/
│  │  ├─ iv_admin_client.py     # IBM Verify admin client + lifecycle
│  │  ├─ iv_user_client.py      # IBM Verify user client + lifecycle
│  │  ├─ session_store.py       # Redis session store
│  │  └─ yaml_role_policy_repository.py
│  ├─ assets/
│  │  └─ tailwind.css            # Tailwind input (source)
│  ├─ auth/oidc.py             # OIDC helpers
│  ├─ auth/role_mapper.py      # map OIDC claims to roles
│  ├─ core/roles.py            # role definitions
│  ├─ core/permissions.py      # permission constants
│  ├─ core/models/user.py      # user domain model
│  ├─ dependencies/
│  │  ├─ auth.py
│  │  ├─ policies.py
│  │  └─ services.py
│  ├─ middleware/
│  │  ├─ access_log.py
│  │  ├─ auth_mw.py
│  │  ├─ authorization_mw.py
│  │  ├─ error_handlers.py
│  │  ├─ locale_mw.py
│  │  └─ token_refresh_mw.py
│  ├─ policies/roles.yaml      # role→permission mapping
│  ├─ static/main.css          # Tailwind output (built)
│  ├─ templates/
│  │  ├─ base.html
│  │  ├─ home.html
│  │  ├─ auth/login.html
│  │  └─ fragments/requests.html
│  └─ utils/
│     ├─ acl.py                # permission helpers
│     └─ i18n.py                # i18n helpers
└─ tests/
   └─ unit/core/test_permissions.py
```

## Architecture

- `controller`: HTTP routes (API + web + HTMX fragments) and Pydantic schemas.
- `service`: business logic and orchestration.
- `repository`: external adapters (IBM Verify, Redis session store, YAML policy loader).
- `core`: domain models (`user`), roles, and permissions.
- `auth`: OIDC helpers and role mapping.
- `dependencies`: FastAPI dependency providers (service/repository wiring).
- `middleware`: logging, auth, authorization, error handling, session wiring.
- `policies`: declarative role→permission mapping.

## Templating and HTMX

- Base layout in `templates/base.html`; page templates like `templates/home.html` extend it.
- HTMX partials live under `templates/fragments/` and are served via `web` routes or helpers for fine-grained updates.
- Keep HTMX responses light: return fragment HTML and proper `HX-Trigger` headers where needed.

## Styling pipeline

- Tailwind entrypoint: `app/assets/tailwind.css`.
- Build CSS once: `npm run build:css` → outputs `app/static/main.css`.
- Watch during development: `npm run watch:css`.

## Running locally

1. Create `.env` from `.env.sample` and fill values.
2. Install Python deps: `pip install -r requirements-dev.txt`.
3. Install Node deps (for Tailwind): `npm install`.
4. Build or watch CSS (see commands above).`npm run watch:css` for development. `npm run build:css` for production
5. Start the app: `uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload`.

## Core environment variables

- `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_ISSUER`, `OIDC_REDIRECT_URI`
- `SESSION_COOKIE_NAME`, `REDIS_URL`
- `IBM_SV_CLIENT_ID`, `IBM_SV_CLIENT_SECRET`, `IBM_SV_BASE_URL`

## Roles and permissions

- Canonical roles and permissions live in `core/roles.py` and `core/permissions.py`.
- Policy mapping is in `policies/roles.yaml`; authorization middleware and `utils/acl.py` use this for enforcement.

## Testing

- Unit tests cover permission logic and service behavior in [tests/unit/core/test_permissions.py](tests/unit/core/test_permissions.py) and [tests/unit/application/services/test_admin_service.py](tests/unit/application/services/test_admin_service.py).
- Add integration tests for OIDC flows, HTMX fragments, and IBM Verify adapters as features evolve.
