# Design Document

## Overview

Move tenant resolution from Django middleware (runs before JWT auth) into DRF, immediately after authentication, using one small mixin in the generated project. Tenant-aware viewsets opt in with `TenantScopedMixin`. The mixin:

1. authenticates (existing DRF behaviour),
2. resolves `X-Tenant-ID` against the user's memberships,
3. binds the tenant (request attribute + existing contextvar) **before** permission checks run,
4. rebuilds the queryset per request,
5. clears the contextvar in a `finally`.

`TenantMiddleware` is no longer generated. The `get_current_tenant` / `set_current_tenant` API and the `TenantManager` fail-closed behaviour are unchanged.

## Steering Document Alignment

### Technical Standards (tech.md)
Generated projects stay on DRF + simplejwt with no new dependencies. Generator code stays typed, Ruff-clean, and templated through Jinja where the output is more than a few lines.

### Project Structure (structure.md)
Generated-project code goes in `src/django_octave/templates/project/apps/core/`, rendered only when `use_multitenancy`. Generator logic stays in `api_parts/` and `models_gen/`.

## Code Reuse Analysis

### Existing Components to Leverage
- **`apps/core/models.py.j2`** (`TenantManager`, `get_current_tenant`, `set_current_tenant`): kept; the mixin only changes who binds the tenant.
- **`project/detect.py`** (`OctaveProject.use_multitenancy`): already tells generators whether a project is multitenant.
- **`inspect/model_fields.py`** (`info.has_tenant_aware`): decides whether a model gets the mixin.
- **`rendering/writer.py::_should_skip`**: existing mechanism for multitenancy-only files.

### Integration Points
- **Three viewset emitters** must agree: `templates/app/views.py.j2`, `api_parts/viewset_gen.py::build_viewset_class`, `models_gen/api_sync.py` (stub at line ~58).
- **`frontend_gen/crud_discover.py`** discovers models via the regex `queryset\s*=\s*(?P<model>\w+)\.objects`. The generated `queryset = Model.objects.all()` line stays, so discovery keeps working.
- **`api_parts/permission_gen.py`** `tenant_member` preset reads `request.tenant`; the mixin sets it.
- **`api_parts/test_gen.py`** currently skips API tests for tenant models; that skip is replaced.

## Architecture

```mermaid
sequenceDiagram
    participant C as Client
    participant V as Tenant viewset (TenantScopedMixin)
    participant A as JWT auth
    participant DB as Membership/Tenant
    C->>V: GET /api/notes/ (Bearer, X-Tenant-ID)
    V->>A: perform_authentication → request.user
    V->>DB: tenant where id=header AND member=user
    alt found
        V->>V: request.tenant = t; set_current_tenant(t)
        V->>V: check_permissions (tenant_member can now see request.tenant)
        V->>V: get_queryset → Model.objects.all() (scoped now)
    else missing / invalid / unknown / not member
        V-->>C: 403 {"detail": "A valid X-Tenant-ID header is required."}
    end
    V->>V: finally: set_current_tenant(None)
```

### Modular Design Principles
- **Single responsibility**: `apps/core/tenancy.py` holds only tenant resolution for DRF. `models.py` holds only data primitives.
- **One place**: viewsets never resolve tenants themselves; they inherit the mixin.
- **Fail closed by default**: if the mixin is forgotten, `Model.objects` still returns `.none()` (no tenant bound), never other tenants' rows.

## Components and Interfaces

### 1. `apps/core/tenancy.py` (new generated file, multitenancy only)
- **Purpose:** DRF-level tenant binding.
- **Interface:**
  ```python
  class TenantRequired(PermissionDenied):          # DRF 403
      default_detail = "A valid X-Tenant-ID header is required."

  class TenantScopedMixin:
      tenant_header = "X-Tenant-ID"
      def perform_authentication(self, request) -> None: ...
      def get_queryset(self): ...                   # self.queryset.model.objects.all()
      def dispatch(self, request, *args, **kwargs): ...  # try/finally reset
  ```
- **Behaviour details:**
  - `perform_authentication`: call `super()`; if `request.user` is authenticated, read the header; parse as UUID; look up `Tenant` filtered by `memberships__user`; on any failure (missing, malformed, unknown, non-member) raise the **same** `TenantRequired`. If found: `request.tenant = tenant`, `set_current_tenant(tenant)`. Unauthenticated requests are left to the permission classes (401).
  - `get_queryset`: `self.queryset.model.objects.all()`. Re-evaluated per request, so the scoped `TenantManager` sees the bound tenant. Custom filtering/`select_related` is added by overriding `get_queryset` and calling `super()`.
  - `dispatch`: `try: return super().dispatch(...) finally: set_current_tenant(None)`. Covers exceptions that never reach `finalize_response`.
- **Dependencies:** DRF, `apps.core.models` (`Tenant`, `set_current_tenant`).
- **Reuses:** existing contextvar helpers and `TenantManager`.

### 2. `apps/core/models.py.j2` (modified)
- `TenantAwareModel.save()`: if `tenant_id` is set and a current tenant is bound and they differ, raise `django.core.exceptions.PermissionDenied` (DRF maps it to 403). Keeps `all_objects` for admin/maintenance, documented as unscoped.

### 3. Removed: `apps/core/middleware.py.j2` and its `MIDDLEWARE` entry
- `rendering/writer.py::_should_skip` loses the middleware special case; `settings/base.py.j2` loses the conditional line.
- `project/detect.py::_has_tenant_middleware` is replaced by a check for `apps/core/tenancy.py` (models check stays), so old projects (middleware) and new projects (tenancy) are both detected as multitenant.

### 4. Viewset emitters (3 places)
- When the project is multitenant and the model is tenant-aware (or the chosen permission is `tenant_member`), emit:
  ```python
  from apps.core.tenancy import TenantScopedMixin

  class NoteViewSet(TenantScopedMixin, viewsets.ModelViewSet):
      queryset = Note.objects.all()
  ```
- Otherwise output is byte-identical to today (R3.2).
- If the project is multitenant but `apps/core/tenancy.py` is missing (a project generated before this fix), the command fails with an actionable error pointing at the migration docs, rather than emitting code that cannot import (R6.2).
- A shared helper `viewset_bases(use_mt, tenant_aware, permission) -> str` lives in `viewset_gen.py`; the other emitters call it (DRY).

### 5. Serializer generation (no change; deviation noted during implementation)
- _Update:_ generated serializers never expose `tenant` (the inspector does not list fields inherited from `TenantAwareModel`, and `--fields tenant` is rejected), so no code change is needed. A test asserts the invariant. Original plan follows for reference.
- For tenant-aware models, `tenant` is excluded from writable fields (added to `read_only_fields`), so a client cannot post a foreign `tenant` value. The `save()` guard in (2) is the backstop.

### 6. `tenant_member` permission (deviation noted during implementation)
- _Update:_ `add-viewset` does not add the mixin for non-tenant-aware models (the permission is a custom class resolved by name). Instead `add-permission --viewset` warns when the wired viewset lacks the mixin. Original plan follows.
- Docstring updated; logic unchanged (reads `request.tenant`, now actually set). Using it adds the mixin, since without it nothing sets the tenant.

### 7. Generated API tests (`api_parts/test_gen.py`)
- Remove `skip_tenant`. For tenant-aware models the generated tests use two fixtures added to the generated `conftest.py` (multitenancy only): `tenant` (Tenant + Membership for `user`) and a client that sends `X-Tenant-ID`. Generated assertions: list/retrieve scoped to the tenant, a missing header returns 403, a second tenant's row is not visible.

## Data Models

No schema or migration changes: `Tenant`, `Membership`, `TenantAwareModel` fields are unchanged. Existing generated `core` migrations remain valid.

## Error Handling

### Error Scenarios
1. **Header missing / malformed / unknown tenant / user not a member**
   - **Handling:** one `TenantRequired` (403) for all four; no distinction, so tenant existence is not revealed.
   - **User Impact:** `{"detail": "A valid X-Tenant-ID header is required."}`.
2. **Unauthenticated request to a tenant viewset**
   - **Handling:** mixin skips resolution; the permission class returns 401/403 as it does today.
   - **User Impact:** unchanged standard DRF response.
3. **Client posts a different `tenant` in the body**
   - **Handling:** field is read-only (ignored); a direct `save()` with a foreign tenant raises `PermissionDenied`.
   - **User Impact:** the object is created in the current tenant, or 403 on the direct-save path.
4. **Exception inside a view**
   - **Handling:** `dispatch` `finally` clears the contextvar.
   - **User Impact:** none; no tenant leaks into the next request.
5. **Old project (middleware, no `tenancy.py`) + new generator**
   - **Handling:** `add-viewset`/`add` fail with an explicit message and docs link (R6.2).
   - **User Impact:** told exactly what to add; nothing half-generated.

### Known gap (out of scope, documented)
Django admin for tenant models uses `_default_manager` (`objects`) with session auth and no header, so it shows no rows. That was already true for browser sessions (no way to send the header). Follow-up: admin generator uses `all_objects` for tenant models. Recorded in the docs, not changed here.

## Testing Strategy

### Unit Testing
- `viewset_gen`/template/`api_sync` output for: non-MT (unchanged, golden string), MT + tenant-aware (mixin present, `queryset` line kept), MT + `tenant_member` on a non-tenant model.
- Generator error when MT project lacks `tenancy.py`.
- `detect_project` marks a project multitenant with either old middleware or new `tenancy.py`.
- Serializer output makes `tenant` read-only.
- `build_api_test_source` for tenant models no longer skips and contains the header/isolation tests.
- Writer: no middleware file, no `MIDDLEWARE` entry; `tenancy.py` present only with `--multitenancy`.

### Integration Testing
- Render a multitenancy project, `ast.parse` every generated Python file, assert imports line up (`apps.core.tenancy` resolvable).

### End-to-End Testing
- New `tests/e2e/test_multitenancy_jwt.py`, marker `e2e`, skipped unless `OCTAVE_E2E=1` (needs network for `uv sync`). Generates a project, adds an app, runs migrations, then drives the real stack with `APIClient`: JWT login; create and list with header; two tenants isolated; missing header 403; non-member header 403 with identical body to unknown tenant; foreign `tenant` in payload ignored; contextvar cleared after an exception. This is the scenario reproduced in the audit.
- The generated project's own `pytest` (with the new API tests) runs as part of the same e2e test.

## Alternatives Considered

- **Custom DRF authentication class** that wraps JWT and binds the tenant: runs at the right time but hides tenancy inside auth and still needs the queryset fix. Rejected: more indirection than a mixin.
- **`Model.all_objects` queryset + explicit `.filter(tenant=request.tenant)`**: reads don't depend on the contextvar, but forgetting the mixin would expose all tenants (fail-open). Rejected in favour of fail-closed `objects`.
- **Django middleware that authenticates JWT itself**: duplicates simplejwt and couples to its internals. Rejected.
- **Third-party library** (django-multitenant, django-rls-tenants): decided against; none of them removes the need to bind the tenant in DRF.
