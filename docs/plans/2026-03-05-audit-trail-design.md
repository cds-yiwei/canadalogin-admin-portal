Audit Trail Design — 2026-03-05

Overview

Goal: Enhance the existing application "usage" page to provide Prev/Next navigation for the audit trail using search_after cursors returned by the upstream API (/v1.0/reports/app_audit_trail_search_after). There are no numeric pages: both Prev and Next tokens are derived from the current page's items (Prev from first item, Next from last item). Results are always sorted by time (descending), with ID as tiebreaker.

Components

- Controller: reuse the existing usage route (GET /applications/{app_id}/usage). It will accept HX requests and the SEARCH_AFTER header. Controller will call AdminService.get_application_audit_trail(...).
- Service: AdminService.get_application_audit_trail(app_id, start=None, end=None, action=None, per_page=25, search_after=None, direction='after') which returns (events, tokens) where tokens includes next_search_after and prev_search_after (if available).
- Repository / iv_admin_client: add app_audit_trail_search_after(...) that calls /v1.0/reports/app_audit_trail_search_after with provided params. The client should accept a SEARCH_AFTER header and also a SEARCH_DIR header when present (SEARCH_DIR: "before" or "after"). The client returns events + metadata needed to build tokens.
- Templates: modify app/templates/applications/usage.html to render the audit_trail rows in a fragment container and render Prev/Next buttons. HTMX will be used to request the fragment on navigation.

Data flow and token semantics

- Initial load: controller calls service with search_after=None. The repository queries upstream for the most recent per_page items (per_page default 25). The returned events are sorted by time desc.
- Token construction: repository builds token strings directly from event fields and returns them as opaque strings. Token format: "{timestamp_ms}, \"{id}\"" (e.g., 1554479231870, "30f5a726-0e11-4066-a49f-e1e1d03a62b4"). The UI will receive next_search_after (built from last item) and prev_search_after (built from first item) as returned by service; tokens are treated opaque by UI and server.
- Next: user clicks Next; HTMX issues a request to the usage route with header SEARCH_AFTER set to next_search_after and SEARCH_DIR left as default ("after"). The controller passes token to service which calls repository with SEARCH_AFTER and SEARCH_DIR: "after".
- Prev: user clicks Prev; HTMX issues a request with SEARCH_AFTER equal to prev_search_after and SEARCH_DIR: "before". The controller passes both values; if upstream supports SEARCH_DIR the repository passes it through.
- Server-side emulation fallback: If upstream does not support SEARCH_DIR="before", service will emulate Prev by re-running base queries and walking pages until it locates items that precede the current first item. This fallback is documented and covered by tests.

HTMX and UI

- HTMX usage: audit-trail rows live inside a container with id="audit-trail-list". Prev/Next buttons use hx-post (or hx-get for backward-compatible) to the same usage URL and include hx-headers with SEARCH_AFTER and SEARCH_DIR when appropriate. Example (rendered by Jinja2):
  - Next: <button hx-post="/applications/{{app_id}}/usage" hx-headers='{"SEARCH_AFTER":"{{ next_search_after }}"}'>Next</button>
  - Prev: <button hx-post="/applications/{{app_id}}/usage" hx-headers='{"SEARCH_AFTER":"{{ prev_search_after }}", "SEARCH_DIR":"before"}'>Prev</button>
- Escape/encoding: ensure tokens are escaped when inserted into JSON attributes (Jinja2 autoescape + building hx-headers server-side recommended).
- Rendering: controller detects HX-Request header and returns fragment template containing only the table rows + pagination actions.

Controller behavior specifics

- Read inputs in this precedence:
  1. If SEARCH_AFTER header present on request: use its value and read SEARCH_DIR header (default 'after').
  2. Else if query/body contains a token (from hx-vals): use that.
  3. Else: initial load, search_after=None.
- Call AdminService.get_application_audit_trail with provided params.
- Build prev/next tokens to render. Prev token will be provided when the returned data indicates there are items before the current page (or always provided from first item for navigation). Next token present when upstream returns a next cursor.
- Always enforce sort by time desc.

Error handling and UX

- Upstream errors: if the repository call fails, controller returns a fragment with an error row and a toast/alert message. For HTMX requests, return a 503 fragment with a friendly message and a retry button.
- Malformed SEARCH_AFTER: validate length and pattern; reject with 400 and a friendly message.
- Empty results: render an empty state row and disable Prev/Next as appropriate.

Testing plan

- Unit tests for AdminService:
  - initial load returns normalized events + next/prev tokens.
  - Next call with SEARCH_AFTER forwards token to repository and returns subsequent events.
  - Prev with SEARCH_DIR='before' calls repository with direction when upstream supports it.
  - Fallback emulation: simulate upstream lacking 'before' support and verify service emulates Prev correctly.
- Controller tests:
  - HTMX requests return fragment only and include proper prev/next tokens in rendered context.
  - Malformed token causes 400.
- Integration-like tests mocking iv_admin_client responses for common flows (initial, next, prev, empty, error).

Security & validation

- Treat SEARCH_AFTER as opaque; do not parse beyond minimal validation. Limit token length to a reasonable maximum (e.g., 256 chars).
- Escape tokens when embedding in HTML attributes.
- Enforce permission CAN_VIEW_AUDIT_TRAIL via existing ACL utilities.

Open questions / assumptions

- Assume iv_admin_client (existing) will be used to call the /v1.0/report endpoint. If you'd prefer a dedicated audit repository file, we can create app/repository/audit_repository.py and keep iv_admin_client thin.
- Assume upstream supports SEARCH_DIR header; if not, we emulate Prev server-side.

Next steps

- Validate this design. If approved, I'll:
  1) Write this design to docs/plans (done).
  2) Mark brainstorm complete in plan_tracker.
  3) Move to implementation planning (writing-plans) and then implement on feature/audit-trail-fragament branch.

