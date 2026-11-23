# Requirements Document

## Introduction

The remaining security findings from the code audit all concern **the projects the generator emits**. Each one is a default that is unsafe, or a production path that fails at runtime:

| Audit | Finding |
|-------|---------|
| S5 | Prod image cannot serve `/admin/`: `CompressedManifestStaticFilesStorage` needs `collectstatic`, which nothing runs, so admin pages raise `ValueError` (HTTP 500). |
| S3 | `GET /api/users/` (generated with `--frontend`) lists every user's email to any authenticated user, across tenants in multitenancy projects. |
| S4 | Token obtain/refresh and registration only share the global `anon` throttle (60/min), which is generous for credential guessing and signup abuse. Registration also confirms whether an email exists. |
| S6 | OpenAPI schema, Swagger UI and ReDoc are public in production (`drf-spectacular` default is `AllowAny`). |
| S7 | Prod settings do not require `DJANGO_ALLOWED_HOSTS`; they silently fall back to `localhost`, or accept `*`. |
| S9 | The Docker image ships `curl` and `build-essential`, installs dev dependencies, starts via `uv run` (which can re-resolve at boot), and has no lock file for reproducible builds. |
| S2 | `TenantAwareModel.tenant` uses `related_name="%(class)ss"`, which collides for same-named models in different apps. |
| S8 | The SPA's nginx sends no security headers, and token storage in `localStorage` is undocumented. |

Decisions already made with the user: the user list is **tenant-scoped in multitenancy projects and unchanged otherwise**; the API docs are **admin-only in production**.

Out of scope:
- Making the generated SPA send `X-Tenant-ID` or choose a tenant. Since the multitenancy fix, tenant endpoints require the header, and the SPA does not send it, so `--multitenancy --frontend` projects get 403 from tenant endpoints. This is a **separate feature** (tenant selection) and is documented as a known gap here.
- A strict Content-Security-Policy for the SPA (cannot be verified without building and exercising the SPA; recorded as a follow-up).
- Removing the account-existence message from registration (accepted residual risk, bounded by throttling; see R3).
- Postgres row-level security, third-party tenancy libraries.

## Alignment with Product Vision

The product promises a *production-ready* starter. A prod image whose admin returns 500, a public API schema, and a settings file that boots with the wrong host list contradict that promise. Fixes must be defaults (no extra steps for the user) and verified against a real build.

## Requirements

### Requirement 1 — production image serves static files (S5)

**User Story:** As a developer deploying the generated Docker image, I want `/admin/` to work out of the box, so that I do not discover a 500 in production.

#### Acceptance Criteria

1. WHEN the production image is built THEN the build SHALL run `collectstatic` with production settings, using throw-away build-time values that are not stored in the image's environment or layers' `ENV`.
2. WHEN a container starts from that image THEN a request to `/admin/login/` SHALL return 200 with its static assets resolving via the manifest.
3. WHEN `collectstatic` fails THEN the image build SHALL fail.
4. WHEN Docker is not enabled for the project THEN nothing SHALL change.

### Requirement 2 — slimmer, reproducible image (S9)

**User Story:** As an operator, I want a runtime image without build tools and dev dependencies that starts the server directly, so that the attack surface and cold-start behaviour are predictable.

#### Acceptance Criteria

1. WHEN the image is built THEN dependencies SHALL be installed without dev dependencies (`--no-dev`).
2. WHEN a `uv.lock` exists in the project THEN the build SHALL install exactly from it (`--locked`/frozen); WHEN it does not exist THEN the build SHALL still succeed.
3. WHEN the container starts THEN the server SHALL be launched from the project's virtualenv (not via `uv run`), so no dependency resolution happens at boot.
4. WHEN the final image is inspected THEN it SHALL NOT contain `curl` or compilers (`build-essential`), AND SHALL still run as the non-root `app` user. For MariaDB the runtime client library SHALL be present.
5. WHEN Postgres, MariaDB or SQLite is chosen THEN the image SHALL build and start for each.
6. IF the generated project has no `uv.lock` THEN the generated README/next steps SHALL tell the user to run `uv lock` and commit it.

### Requirement 3 — auth endpoints are rate limited (S4)

**User Story:** As an operator, I want login, token refresh and signup throttled more strictly than ordinary API traffic, so that credential guessing and mass signup are impractical.

#### Acceptance Criteria

1. WHEN a client calls the token obtain or token refresh endpoint THEN the system SHALL apply a dedicated `auth` throttle scope, default **10 requests per minute** per client, configurable through `DEFAULT_THROTTLE_RATES["auth"]`.
2. WHEN the project has registration enabled (`--register`) THEN the register endpoint SHALL use the same scope.
3. WHEN the limit is exceeded THEN the system SHALL answer `429` with a `Retry-After` header.
4. WHEN other endpoints are called THEN their throttling SHALL be unchanged.
5. WHEN `add-frontend` patches an existing project's URLs THEN the throttled views SHALL stay wired (patching must keep working on both fresh and previously patched projects).
6. The registration response that says an email already exists SHALL remain (needed by the SPA), documented as accepted residual risk bounded by AC 2.

### Requirement 4 — user list is tenant-scoped in multitenancy projects (S3)

**User Story:** As a tenant member, I want the user list used by FK dropdowns to show only people in my tenant, so that other tenants' users and emails are not exposed.

#### Acceptance Criteria

1. WHEN the project uses multitenancy THEN `GET /api/users/` SHALL inherit `TenantScopedMixin` and list only users with a membership in the current tenant; a missing/invalid tenant header SHALL return the standard 403.
2. WHEN the project does not use multitenancy THEN the endpoint SHALL behave as today.
3. WHEN the endpoint is called unauthenticated THEN it SHALL return 401 as today.
4. WHEN the list is returned THEN it SHALL contain only `id`, `email` and `label` (unchanged).

### Requirement 5 — API docs are admin-only in production (S6)

**User Story:** As an operator, I want the OpenAPI schema and Swagger/ReDoc hidden from the public in production, so that the API surface is not advertised.

#### Acceptance Criteria

1. WHEN running with local settings THEN schema, Swagger UI and ReDoc SHALL remain open as today.
2. WHEN running with prod settings THEN these three views SHALL require an authenticated admin (`IsAdminUser`) using session authentication, so an admin who is logged in to `/admin/` can open them in a browser.
3. WHEN an anonymous or non-admin user requests them in prod THEN the response SHALL be 401/403 and no schema content SHALL be returned.
4. The docs SHALL explain how an admin opens the API docs in production.

### Requirement 6 — prod settings fail fast on host configuration (S7)

**User Story:** As an operator, I want the app to refuse to start with an unset or wildcard host list, so that I find the mistake at deploy time.

#### Acceptance Criteria

1. WHEN prod settings load AND `DJANGO_ALLOWED_HOSTS` is unset or empty THEN the system SHALL raise `ImproperlyConfigured` with a message naming the variable.
2. WHEN `DJANGO_ALLOWED_HOSTS` contains `*` THEN the system SHALL raise `ImproperlyConfigured`.
3. WHEN it is set to explicit hosts THEN startup SHALL succeed and `ALLOWED_HOSTS` SHALL equal them.
4. WHEN local settings load THEN behaviour SHALL be unchanged.
5. WHEN a user copies `.env.example` to production THEN the README/`.env.example` comments SHALL make clear that the host list must be changed (the example value is `localhost,127.0.0.1`).

### Requirement 7 — tenant related names cannot collide (S2)

**User Story:** As a developer with several apps, I want two tenant-aware models with the same class name to coexist, so that startup is not broken by a reverse-accessor clash.

#### Acceptance Criteria

1. WHEN `TenantAwareModel` is generated THEN its `tenant` foreign key SHALL use a related name that includes the app label (`%(app_label)s_%(class)s_set`).
2. WHEN two apps define a tenant-aware model with the same class name THEN `manage.py check` SHALL pass.
3. WHEN an existing project is upgraded THEN the docs SHALL note that Django will generate a harmless `AlterField` migration per tenant-aware model.

### Requirement 8 — SPA container security headers and token-storage note (S8)

**User Story:** As an operator of the generated SPA, I want baseline security headers and an honest note on token storage, so that I can judge the trade-off.

#### Acceptance Criteria

1. WHEN the SPA's nginx config is generated THEN it SHALL send `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and `Referrer-Policy: same-origin` on all responses, including proxied `/api/` and error pages (`always`).
2. WHEN the docs describe the frontend THEN they SHALL state that tokens are stored in `localStorage`, what that means for XSS, and that a CSP is recommended (not generated).
3. The generated nginx config SHALL remain valid (`nginx -t`) and SHALL NOT change proxy behaviour.

### Requirement 9 — proof and docs

**User Story:** As a maintainer, I want every change above proven against a real project and documented, so that the audit findings stay closed.

#### Acceptance Criteria

1. WHEN generator tests run THEN they SHALL cover each requirement's rendered output.
2. WHEN the opt-in e2e suite runs (`OCTAVE_E2E=1`) THEN it SHALL, on a generated project with prod settings: pass `manage.py check --deploy` (with the documented environment), run `collectstatic`, load `/admin/login/` successfully, return 401/403 for the schema to anonymous users, refuse to boot without `DJANGO_ALLOWED_HOSTS`, return 429 after the auth limit, and check two same-named tenant-aware models in different apps.
3. WHEN Docker is available AND `OCTAVE_E2E_DOCKER=1` THEN an additional opt-in test SHALL build the production image for SQLite and Postgres/MariaDB variants and confirm: runs as non-root, no `curl`/compiler present, `/admin/login/` returns 200. WHEN Docker is not available THEN the test SHALL skip with a clear reason.
4. WHEN the work is done THEN `docs/code-audit-2026-11-23.md` statuses SHALL be updated and the multitenancy docs SHALL list the SPA tenant-header gap.

## Non-Functional Requirements

### Code Architecture and Modularity
- **Single Responsibility Principle**: throttling classes live in one small generated module; prod-only behaviour stays in `prod.py`; Docker concerns stay in `Dockerfile.j2` and compose files.
- **Modular Design**: no duplication of the auth-throttle wiring between the base project and the frontend patch.
- **Dependency Management**: no new dependencies in the generator or in generated projects.
- **Clear Interfaces**: the generated `TenantScopedMixin` and its error type are reused, not re-implemented.

### Performance
- Throttling uses DRF's built-in cache-backed throttles; no extra queries. The user list adds one membership join.

### Security
- Fail closed everywhere: unset hosts, wildcard hosts, missing tenant, non-admin docs access.
- No secret from the build (`collectstatic` placeholders) persists in image `ENV` or the final environment.
- Defaults are secure without user action.

### Reliability
- Image build is deterministic when a lock file exists; failure of `collectstatic` fails the build rather than shipping a broken image.
- Existing generated projects are not modified by this change; documented upgrade notes cover them.

### Usability
- Startup errors name the exact environment variable and say what to set.
- Throttled clients get `429` with `Retry-After`.
