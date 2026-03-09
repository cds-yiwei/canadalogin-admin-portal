# .pi AGENTS.md

This file is a lightweight agent guide for operations inside the cl-admin-portal repository. The repository root contains a full AGENTS.md that should be consulted for detailed policies and workflows. This .pi/AGENTS.md highlights the most important commands and agent-focused rules for quick reference.

Project summary
- Stack: Python 3.x (FastAPI), Jinja2 + HTMX for server-rendered fragments, Tailwind CSS for styling, Node.js for asset tooling.
- External integrations: IBM Security Verify clients (admin & user), Redis session store (optional), Docker for local containerized runs.

Quick commands
- Create python venv & install dev deps:
  python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt

- Run tests (all):
  pytest -q

- Run unit tests only:
  pytest -q tests/unit/

- Static checks (skip Redis session store):
  SKIP_SESSION_STORE=1 pytest -q

- Start dev server with hot-reload:
  uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload

- Node asset commands (Tailwind):
  npm ci
  npm run build:css
  npm run watch:css

- Docker compose (build + run):
  docker-compose up --build

- Lint / format:
  flake8 .
  black . --target-version py311

Files to check first (useful entry points)
- AGENTS.md (repo root) — authoritative agent guidance
- app/main.py — application factory and middleware
- pyproject.toml, requirements*.txt — Python deps and tooling
- package.json, tailwind.config.cjs, postcss.config.cjs — Node/Tailwind setup
- tests/ — unit and integration tests

Agent rules (summary)
- Read before write: inspect callers, tests, and existing patterns before making changes.
- Run tests locally for any behavioral change; capture exact failing output if blocked.
- Never add secrets or credentials to code or test fixtures.
- Keep changes small and well-tested. Prefer focused tests for bug fixes or new behavior.
- Consult the repo AGENTS.md for full workflows, code style, and CI expectations.

Notes
- SKIP_SESSION_STORE=1 is useful for running static checks or tests without Redis.
- When adding/altering routes or permissions, update tests and policy files together.

Auth / OIDC guidance (authlib)
- The project integrates OIDC flows; see app/auth/oidc.py and app/auth/role_mapper.py for implementation details.
- Use the authlib skill when implementing or debugging OAuth/OIDC flows, JWT validation, or token refresh logic.
- Tests and local runs may require mocking OIDC providers; do not commit real client secrets to code or test fixtures.

END
