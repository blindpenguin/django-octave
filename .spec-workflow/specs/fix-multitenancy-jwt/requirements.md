# Requirements Document

## Introduction

Projects generated with `--multitenancy` do not work for their intended client: a JWT-authenticated API consumer. Reproduced on a fresh project (`new demo --multitenancy`, `add notes`): a user with a valid `Membership` sends `Authorization: Bearer …` and `X-Tenant-ID: <uuid>`, then `POST /api/notes/` fails with `RuntimeError: Cannot save tenant-scoped model without a current tenant` (HTTP 500).

Root causes:

1. **Tenant is bound too early.** `TenantMiddleware` reads `request.user` from Django's `AuthenticationMiddleware` (session auth). JWT is authenticated later, inside the DRF view, so the middleware always sees `AnonymousUser` and binds nothing.
2. **Generated viewsets freeze an empty queryset.** `queryset = Model.objects.all()` runs at import time, when no tenant exists. `TenantManager` returns `.none()`, and DRF clones that empty queryset on every request, so reads stay empty even when a tenant is bound.
3. **`tenant_member` permission** reads `request.tenant`, which is never set for JWT requests, so it always denies.
4. **No test catches this.** Generated API tests are skipped for tenant-aware models (`skip_tenant`), and no generator test exercises a JWT request against a tenant model.

Scope: the multitenancy templates and generators only. Out of scope: switching to a third-party tenancy library (decided: keep the first-party implementation), Postgres RLS, tenant management endpoints, and the unrelated `new --force` fix.

## Alignment with Product Vision

The product promises an opinionated, production-ready starter. `--multitenancy` is an advertised flag; shipping it in a state where the first authenticated write returns a 500 breaks that promise. Tenant isolation must also fail closed, so a request without a valid tenant never reads or writes another tenant's rows.

## Requirements

### Requirement 1

**User Story:** As an API consumer using JWT, I want my `X-Tenant-ID` header honoured, so that I can read and write my tenant's data.

#### Acceptance Criteria

1. WHEN an authenticated JWT user who is a member of tenant T sends `X-Tenant-ID: T` THEN the system SHALL bind T as the current tenant for that request's view logic, and `GET`/`POST`/`PATCH`/`DELETE` on tenant-aware viewsets SHALL operate on T's rows.
2. WHEN a created object has no explicit tenant THEN the system SHALL assign the current tenant.
3. WHEN the request is authenticated by session (e.g. Django admin or browsable API) THEN tenant binding SHALL behave the same as for JWT.
4. WHEN the request finishes (response returned or exception raised) THEN the system SHALL clear the current tenant so it cannot leak into another request on the same thread or task.

### Requirement 2

**User Story:** As a tenant, I want requests without a valid tenant to see nothing and change nothing, so that my data is never exposed to other tenants.

#### Acceptance Criteria

1. IF the `X-Tenant-ID` header is missing THEN tenant-aware endpoints SHALL fail closed with a client error (4xx), not an empty 200 and not a 500.
2. IF the header is not a valid UUID, names a tenant that does not exist, or names a tenant the user is not a member of THEN the system SHALL respond with the same 4xx for all three cases, so tenant existence is not revealed.
3. WHEN a user is a member of tenants A and B and sends `X-Tenant-ID: A` THEN no row belonging to B SHALL be returned or modifiable.
4. WHEN a client supplies a `tenant` (or `tenant_id`) value in a write payload or when calling `save()` with a tenant different from the current one THEN the system SHALL reject the write or ignore the value; it SHALL NOT write into another tenant.
5. WHEN a view is not tenant-aware (token obtain/refresh, schema, admin) THEN it SHALL NOT require the header.

### Requirement 3

**User Story:** As a developer running `add`, `add-viewset` or `add-model`, I want generated viewsets to be tenant-correct without manual edits, so that new endpoints are isolated by default.

#### Acceptance Criteria

1. WHEN a viewset is generated (via `add`, `add-viewset`, or the app template) in a multitenancy project THEN its queryset SHALL be evaluated per request, not at import time.
2. WHEN a viewset is generated in a non-multitenancy project THEN the output SHALL remain unchanged (`queryset = Model.objects.all()`).
3. WHEN `add-viewset --force` refreshes an existing viewset THEN the tenant wiring SHALL be applied consistently.
4. WHEN frontend CRUD or any other generator reads or writes viewset source THEN it SHALL still recognise the generated viewset shape.

### Requirement 4

**User Story:** As a developer, I want the `tenant_member` permission preset to work, so that I can restrict endpoints to members of the current tenant.

#### Acceptance Criteria

1. WHEN `tenant_member` is used and a valid tenant is bound for the request THEN permission SHALL be granted to an authenticated member.
2. WHEN no tenant is bound THEN permission SHALL be denied.
3. WHEN a project was generated before this change THEN `add-permission` SHALL NOT silently break it (see Requirement 6).

### Requirement 5

**User Story:** As a generator maintainer, I want the behaviour proven by tests, so that this class of bug cannot return unnoticed.

#### Acceptance Criteria

1. WHEN generator tests run THEN they SHALL include a test that generates a multitenancy project and exercises the real request path with JWT and `X-Tenant-ID`: list, create, cross-tenant isolation, missing header, non-member header.
2. WHEN `add-test` generates API tests for a tenant-aware model THEN the system SHALL NOT skip them; they SHALL create a tenant and membership, authenticate, send the header, and assert isolation.
3. WHEN the new end-to-end test needs dependencies not available offline THEN it SHALL be marked/skippable so the default unit run stays fast, but it SHALL run in CI (once CI exists) and be documented.

### Requirement 6

**User Story:** As a user of an already generated multitenancy project, I want to know how to adopt the fix, so that my existing project is not left broken.

#### Acceptance Criteria

1. WHEN the fix ships THEN the docs and release notes (`fix(multitenancy)` commit) SHALL describe the problem and the manual migration steps for existing projects.
2. IF an existing project's middleware or viewsets are of the old shape THEN generators SHALL either still work against them or fail with an actionable message; they SHALL NOT generate code that mixes old and new patterns silently.

## Non-Functional Requirements

### Code Architecture and Modularity
- **Single Responsibility Principle**: tenant resolution lives in one place in the generated project (`apps/core`), not repeated per viewset.
- **Modular Design**: generated viewsets opt in through one small shared building block; generators only need to know the name of that block.
- **Dependency Management**: no new third-party dependencies in the generator or in generated projects.
- **Clear Interfaces**: the "current tenant" API (`get_current_tenant` / `set_current_tenant`) keeps its signature; existing generated code that uses it keeps working.

### Performance
- At most one extra indexed query per tenant-scoped request (membership lookup); none for non-tenant routes.

### Security
- Fail closed: no tenant bound means no rows and no writes.
- Isolation errors must not distinguish "tenant does not exist" from "not a member".
- The unscoped manager (`all_objects`) remains available for admin/maintenance code but must be documented as unscoped.

### Reliability
- The current tenant is always cleared at the end of the request, including on exceptions.
- Correct under both sync (WSGI/Gunicorn) and async (ASGI) execution; no state shared between concurrent requests.

### Usability
- Error responses for tenant problems return a clear JSON message in DRF's standard error shape.
- Developer docs explain how to send the header and how to scope a hand-written viewset.
