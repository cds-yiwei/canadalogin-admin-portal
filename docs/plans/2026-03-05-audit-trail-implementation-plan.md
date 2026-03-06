# Audit Trail Prev/Next Implementation Plan

> **REQUIRED SUB-SKILL:** Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Implement Prev/Next audit-trail navigation on the existing usage page using search_after cursors from /v1.0/reports/app_audit_trail_search_after; default page size 25, always sorted by time desc.

**Architecture:** Reuse the existing usage route and template. Add a repository client call in iv_admin_client.py, a thin AdminService method to call it and normalize results, and update the controller to accept SEARCH_AFTER and SEARCH_DIR headers and return HTMX fragments when requested. Prev and Next tokens are constructed from the first and last items of the current page respectively.

**Tech Stack:** Python 3.12, FastAPI, Jinja2 templates, HTMX, pytest for tests.

---

### Task 0: Add repository client call for app_audit_trail_search_after

**TDD scenario:** Modifying repository code — add client method; tests should mock HTTP responses.

**Files:**
- Modify: `app/repository/iv_admin_client.py` (add new method)
- Test: `tests/unit/repository/test_iv_admin_client.py`

Step 1: Write failing test
```python
# tests/unit/repository/test_iv_admin_client.py
import pytest
from app.repository.iv_admin_client import IVAdminClient

@pytest.mark.asyncio
async def test_app_audit_trail_search_after_calls_api(httpx_mock):
    client = IVAdminClient(base_url="https://iv.example")
    # Mock response
    httpx_mock.add_response(json={"events": [{"id": "u1", "timestamp": 1}], "next": "155..."})
    res = await client.app_audit_trail_search_after(app_id="app1", per_page=25)
    assert isinstance(res, dict)
    assert "events" in res
```

Step 2: Run test to verify it fails
Run: `pytest tests/unit/repository/test_iv_admin_client.py -q`
Expected: FAIL (method missing)

Step 3: Implement minimal client method
- Add async def app_audit_trail_search_after(self, app_id, per_page=25, search_after=None, search_dir=None): call endpoint and return parsed json.

Step 4: Run test to verify it passes
Run: `pytest tests/unit/repository/test_iv_admin_client.py -q`
Expected: PASS

Step 5: Commit
```bash
git add app/repository/iv_admin_client.py tests/unit/repository/test_iv_admin_client.py
git commit -m "feat(repo): add app_audit_trail_search_after client method"
```

---

### Task 1: Add AdminService.get_application_audit_trail_search_after

**TDD scenario:** New service method — start with tests.

**Files:**
- Modify: `app/service/admin_service.py` (add method near other audit methods)
- Test: `tests/unit/service/test_admin_service.py`

Step 1: Write failing test
```python
# tests/unit/service/test_admin_service.py
import pytest
from app.service.admin_service import AdminService

@pytest.mark.asyncio
async def test_get_application_audit_trail_search_after(mocker):
    mock_client = mocker.AsyncMock()
    mock_client.app_audit_trail_search_after.return_value = {
        "events": [{"id":"1","timestamp":1554479231870,"username":"u","ip":"1.2.3.4","result":"success","country":"US"}],
        "next": '1554479231870, "uuid"'
    }
    service = AdminService(mock_client)
    events, next_token = await service.get_application_audit_trail_search_after("app1")
    assert len(events) == 1
    assert next_token is not None
```

Step 2: Run test to verify it fails
Run: `pytest tests/unit/service/test_admin_service.py::test_get_application_audit_trail_search_after -q`
Expected: FAIL (method missing)

Step 3: Implement minimal service method
- Call client.app_audit_trail_search_after, normalize event dicts into domain objects/dicts, return (events, next_token)

Step 4: Run test and iterate

Step 5: Commit

---

### Task 2: Update usage route handler to accept SEARCH_AFTER/SEARCH_DIR and HTMX fragment responses

**TDD scenario:** Modifying controller — add tests for HTMX fragment responses.

**Files:**
- Modify: `app/controller/web/applications_routes.py` (usage route)
- Test: `tests/unit/controller/test_applications_routes.py`

Step 1: Write failing tests
- Test that GET /applications/{id}/usage with SEARCH_AFTER header returns fragment when HX-Request present
- Test that controller enforces CAN_VIEW_AUDIT_TRAIL

Step 2: Run tests to verify failures

Step 3: Implement changes:
- Read SEARCH_AFTER and SEARCH_DIR from headers
- Call AdminService.get_application_audit_trail_search_after
- If request.headers.get("HX-Request") -> return TemplateResponse("fragments/audit_trail_list.html", context)
- Provide next_search_after and prev_search_after in context

Step 4: Run tests & fix
Step 5: Commit

---

### Task 3: Modify usage template to render fragment and Prev/Next buttons (HTMX)

**TDD scenario:** Template change — verify via template rendering tests.

**Files:**
- Modify: `app/templates/applications/usage.html` (insert fragment container and pagination buttons)
- Create: `app/templates/fragments/audit_trail_list.html`
- Test: `tests/unit/controller/test_templates.py`

Steps:
1. Update usage.html to include a div id="audit-trail-list" and render fragment there.
2. Create fragment template that renders rows and buttons with hx-headers using tokens next_search_after and prev_search_after.
3. Write test to render template with sample context and assert Next/Prev buttons contain correct headers.
4. Run tests and commit.

---

### Task 4: Add unit tests for service and controller, and mocks for iv_admin_client

**TDD scenario:** Tests-first for edge cases and fallback behavior.

**Files:**
- Tests added across `tests/unit/service/` and `tests/unit/controller/` as described earlier.

Key tests:
- Upstream error -> controller returns 503 fragment for HTMX
- Malformed token -> controller returns 400
- Prev/Next tokens present/absent logic
- Fallback emulation when SEARCH_DIR before unsupported

Run: `pytest -q tests/unit/service tests/unit/controller`

Commit tests.

---

### Task 5: Run tests and fix failures

Steps:
1. Run `pytest -q` locally.
2. Fix failing tests.
3. Iterate until green.
4. Commit final changes.

---

Testing & Verification

- Verify manual flows by running dev server and using the UI with HTMX (or curl for header tests):
  - `uvicorn app.main:create_app --factory --reload`
  - Load /applications/{app_id}/usage and click Prev/Next
- Use HTTP client to simulate HX requests and SEARCH_AFTER header.

Deliverables

- Changes in `app/repository/iv_admin_client.py`, `app/service/admin_service.py`, `app/controller/web/applications_routes.py`, `app/templates/*` and tests under `tests/unit/`.
- Design doc already saved at `docs/plans/2026-03-05-audit-trail-design.md`.


