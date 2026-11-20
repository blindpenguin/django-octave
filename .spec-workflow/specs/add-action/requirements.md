# Requirements Document

## Introduction

**add-action** adds `django-octave add-action` to inject a DRF `@action`-decorated method onto an existing ModelViewSet in `apps/<app>/views.py`. Solo developers get a routable custom endpoint (detail or collection) with Spectacular tagging and a safe stub body, without hand-writing decorator boilerplate.

**Out of scope:** Generating full business logic; `@action.mapping` multi-method dispatch; writable nested serializers for action payloads; changing the DefaultRouter registration (router already picks up `@action` methods); Celery/async side effects; GraphQL mutations.

## Alignment with Product Vision

Extends the composable `add-*` family so APIs grow beyond CRUD while staying opinionated (detail vs list, methods allowlist, stub Response). Supports API-first + OpenAPI docs that a later Vue client can call.

## Requirements

### Requirement 1 — Command and dual UX

**User Story:** As a solo Django developer, I want `add-action` with flags or prompts, so that I can script or explore safely.

#### Acceptance Criteria

1. WHEN the user runs `django-octave --help` THEN `add-action` SHALL be listed.
2. WHEN the command runs THEN it SHALL detect an octave project (`--path`, default cwd) like other add-* commands.
3. Required inputs SHALL be: app name, target viewset (Model name or `ModelViewSet`), and action method name (valid Python identifier, **snake_case**). Missing values prompt on TTY or exit non-zero non-interactively.
4. The command SHALL support `--force` to replace an existing method of the same name on that viewset; without `--force`, refuse duplicates.
5. Success output SHALL name the views file and the action URL shape (detail vs list) for the user.

### Requirement 2 — Action method generation

**User Story:** As a solo Django developer, I want an `@action` stub on my viewset, so that the router exposes a custom route immediately.

#### Acceptance Criteria

1. WHEN `add-action` succeeds THEN `apps/<app>/views.py` SHALL contain a method on the target viewset decorated with `rest_framework.decorators.action`.
2. WHEN `--detail` / `--list` (or equivalent) is provided THEN:
   - **detail** (default): `@action(detail=True, …)`; stub body SHALL call `self.get_object()` and return a `Response` (fail-closed style stub, e.g. status payload — no silent bypass of object permissions).
   - **list** (collection): `@action(detail=False, …)`; stub body SHALL return a `Response` (e.g. empty list or simple status); MAY optionally demonstrate `self.filter_queryset(self.get_queryset())` in a comment or minimal lines — design picks one clear stub.
3. WHEN `--methods` is provided THEN it SHALL be a comma-separated allowlist of HTTP methods (lowercase); default SHALL be `post` for detail and `get` for list.
4. WHEN `--url-path` / `--url-name` are omitted THEN DRF defaults (method name / hyphenated name) SHALL apply; when provided, they SHALL be passed to `@action`.
5. Generated code SHALL ensure imports for `action`, `Response`, and (if used) `status` / Spectacular helpers.
6. WHEN the target viewset class is missing THEN the command SHALL fail with a hint to run `add-viewset`.

### Requirement 3 — OpenAPI / Spectacular

**User Story:** As a solo Django developer, I want the new action documented in OpenAPI, so that Swagger/ReDoc stay useful.

#### Acceptance Criteria

1. WHEN an action is added THEN the method SHALL be annotated for Spectacular (e.g. `@extend_schema` on the method, or documented equivalent) with a tag consistent with the viewset’s existing tag when detectable, else the snake_case model/viewset basename.
2. Schema annotation SHALL not break existing `@extend_schema_view` on the class.

### Requirement 4 — Optional permission / serializer overrides on the action

**User Story:** As a solo Django developer, I want optional per-action permission (and light serializer hint), so that custom routes can differ from the viewset defaults.

#### Acceptance Criteria

1. WHEN `--permission CLASS` is provided THEN `@action(..., permission_classes=[CLASS])` SHALL be set; CLASS resolution SHALL reuse the same stock-or-local rules as `add-viewset` / `add-permission` (stock allowlist or `apps.<app>.permissions`).
2. WHEN `--permission` is omitted THEN the action SHALL inherit viewset permissions (no override on the decorator).
3. WHEN `--serializer Name` is provided THEN `@action(..., serializer_class=Name)` SHALL be set and the import ensured if the serializer exists in `apps.<app>.serializers`; IF missing THEN fail with a hint to `add-serializer` (or create is **out of scope** — fail clear).
4. Without `--serializer`, no `serializer_class` override on the decorator.

### Requirement 5 — Docs and tests

**User Story:** As a maintainer, I want README docs and tests for add-action.

#### Acceptance Criteria

1. README SHALL document `add-action` flags (detail/list, methods, url-path, permission, serializer, force) with an example.
2. Tests SHALL cover: help listing; create detail action; create list action; refuse duplicate without force; force replace; missing viewset; bad method name; permission resolve; optional serializer; Spectacular import/annotation smoke.

## Non-Functional Requirements

### Code Architecture and Modularity
- New module under `src/django_octave/api_parts/action_gen.py`; thin Typer command + prompts.
- Reuse `detect_project`, naming validators, `class_exists`, `add_to_import`, `resolve_permission`, viewset name resolution from `permission_gen` / `viewset_gen`.
- Prefer libcst (or a small, well-tested text insert) to inject a method into an existing class without rewriting the whole viewset.

### Performance
- Generator remains filesystem/static-analysis only (no Django setup of the target project required for codegen).

### Security
- Detail stubs MUST use `self.get_object()` so queryset + object permissions apply.
- Do not generate `Model.objects.get(pk=…)` bypasses.

### Reliability
- Refuse unparseable `views.py` with a clear error; never silently corrupt the file.
- Idempotent refuse-without-force for duplicate method names.

### Usability
- Dual UX (flags + TTY prompts); Rich success summary with next-step hint (runserver / OpenAPI).
- MDX-safe README (backticks for CLI tokens).
