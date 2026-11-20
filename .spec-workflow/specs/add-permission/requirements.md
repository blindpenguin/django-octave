# Requirements Document

## Introduction

**add-permission** adds `django-octave add-permission` to scaffold project-local DRF permission classes and optionally wire them onto an existing viewset — so solo developers can move beyond the built-in `IsAuthenticated` / `AllowAny` / `IsAdminUser` allowlist before building a Vue UI.

**Out of scope:** Django model `PermissionsMixin` / admin permissions matrix UI; object-level ACLs beyond a simple “owner” pattern; OAuth scopes; changing global `REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]` unless an explicit flag opts in (default: do not).

## Alignment with Product Vision

Extends the composable `add-*` family with authz primitives needed for real APIs, while staying opinionated (template presets, not a free-form policy engine).

## Requirements

### Requirement 1 — Command and dual UX

**User Story:** As a solo Django developer, I want `add-permission` with flags or prompts, so that I can script or explore safely.

#### Acceptance Criteria

1. WHEN the user runs `django-octave --help` THEN `add-permission` SHALL be listed.
2. WHEN the command runs THEN it SHALL detect an octave project (`--path`, default cwd) like other add-* commands.
3. Required inputs SHALL include a permission class name (PascalCase ending in a clear convention, e.g. `IsOwner` / `IsStaffOrReadOnly`); missing values prompt on TTY or exit non-zero non-interactively.
4. The command SHALL support `--force` to replace an existing class of the same name; without `--force`, refuse duplicates.
5. Success output SHALL name the file touched and, if wired, the viewset updated.

### Requirement 2 — Permission class generation

**User Story:** As a solo Django developer, I want a small set of opinionated permission templates, so that I get working DRF `BasePermission` subclasses quickly.

#### Acceptance Criteria

1. WHEN `add-permission` succeeds THEN the system SHALL ensure `apps/<app>/permissions.py` exists (create with module docstring if missing) and contains the named class subclassing `rest_framework.permissions.BasePermission`.
2. WHEN `--preset` (or equivalent) is provided THEN the generated body SHALL match an allowlisted preset:
   - **`owner`** — object-level: allow if `obj.owner` / `obj.user` / configurable attr equals `request.user` (default attr `owner`); safe methods optional via flag.
   - **`staff_or_read`** — SAFE_METHODS for anyone authenticated (or anon read — design picks one clear default: **authenticated read + staff write** or **anon read + staff write**; prefer **SAFE_METHODS allow any, write requires staff**).
   - **`auth_or_read`** — SAFE_METHODS allow any; write requires authentication.
   - **`tenant_member`** — only when project has multitenancy: require authenticated user with membership in request tenant (align with existing tenancy helpers if present); IF project has no multitenancy THEN refuse this preset with a clear error.
3. WHEN `--preset` is omitted THEN default SHALL be `owner` (or prompt among presets on TTY — design picks; prefer **default `owner`** for non-interactive).
4. Target app SHALL default to the domain app passed as argument (or `core` if design places shared permissions there — **prefer app argument** `add-permission APP CLASS` so permissions live next to the domain).
5. Generated classes SHALL include `has_permission` and/or `has_object_permission` as appropriate for the preset, with type hints consistent with project stubs.

### Requirement 3 — Optional viewset wiring

**User Story:** As a solo Django developer, I want to attach the new permission to a viewset in one step, so that I do not hand-edit imports.

#### Acceptance Criteria

1. WHEN `--viewset Model` (or `--viewset ModelViewSet`) is provided THEN the command SHALL set `permission_classes` on that viewset in `apps/<app>/views.py` to include the new permission (replace list or append — **prefer replace with `[NewPermission]`** for clarity, with optional `--append` if cheap).
2. WHEN wiring succeeds THEN imports for the permission class SHALL be ensured.
3. IF the viewset class is missing THEN the system SHALL fail with a hint to run `add-viewset`.
4. Without `--viewset`, only the permission file is written.

### Requirement 4 — Integration with add-viewset allowlist (light touch)

**User Story:** As a solo Django developer, I want `add-viewset --permission` to accept my custom class name when it exists in the app, so that regeneration does not force me back to stock DRF permissions.

#### Acceptance Criteria

1. WHEN `add-viewset --permission IsOwner` runs and `IsOwner` exists in `apps.<app>.permissions` THEN the viewset SHALL use that class (import from `apps.<app>.permissions`).
2. WHEN the name is a stock DRF allowlist entry THEN behavior remains as today.
3. WHEN the name is neither stock nor found in the app’s `permissions.py` THEN the command SHALL fail listing stock allowlist and hinting `add-permission`.

### Requirement 5 — Docs and tests

**User Story:** As a maintainer, I want README docs and tests for presets and wiring.

#### Acceptance Criteria

1. README SHALL document `add-permission` presets, `--viewset`, and the extended `add-viewset --permission` behavior.
2. Tests SHALL cover: create permission file; refuse without force; each preset smoke; tenant preset gated; wire viewset; add-viewset custom permission resolution; bad names/presets.

## Non-Functional Requirements

### Code Architecture and Modularity
- New module under `api_parts/permission_gen.py` (or `permissions_gen.py`); thin Typer command.
- Reuse detect/validate/cst_util patterns from add-serializer/add-viewset.

### Security
- Owner checks must fail closed when the object attribute is missing (deny).
- Do not weaken global default permission classes unless explicitly requested.

### Usability
- Preset names are short kebab/snake tokens on the CLI (`owner`, `staff_or_read`, …); class names remain PascalCase.
