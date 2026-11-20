# Requirements Document

## Introduction

**add-test** adds `django-octave add-test` to scaffold **factory-boy** factories and **pytest-django** API tests for an existing model (and its viewset when present) under the generated project’s `tests/` tree. Solo developers get a runnable smoke suite for list/retrieve/create (and auth denial) without hand-wiring factories and `APIClient`.

**Out of scope:** Full coverage generators (every permission matrix, nested writes); browser/E2E; mutating kickstart `conftest.py` beyond additive fixtures if needed; replacing pytest with unittest; Celery task tests; snapshot/golden files; generating tests that require a live server.

## Alignment with Product Vision

Kickstart already ships pytest + pytest-django + factory-boy. This command closes the loop so domain models created via `add-model` / `add-viewset` get matching test stubs — production-ready ergonomics without decision fatigue.

## Requirements

### Requirement 1 — Command and dual UX

**User Story:** As a solo Django developer, I want `add-test` with flags or prompts, so that I can script or explore safely.

#### Acceptance Criteria

1. WHEN the user runs `django-octave --help` THEN `add-test` SHALL be listed.
2. WHEN the command runs THEN it SHALL detect an octave project (`--path`, default cwd) like other add-* commands.
3. Required inputs SHALL be app name and model name (PascalCase). Missing values prompt on TTY or exit non-zero non-interactively.
4. IF the model is missing from `apps/<app>/models.py` THEN the command SHALL fail with a hint to run `add-model`.
5. The command SHALL support `--force` to replace existing generated factory/test modules for that model; without `--force`, refuse if those files (or the named factory/test class) already exist.
6. Success output SHALL name the files written and remind how to run `uv run pytest`.

### Requirement 2 — Factory generation

**User Story:** As a solo Django developer, I want a factory-boy factory for my model, so that tests can create instances without boilerplate.

#### Acceptance Criteria

1. WHEN `add-test` succeeds THEN the system SHALL ensure a factory module exists (prefer `tests/factories/<app>_<model_snake>.py` or `tests/factories/<app>.py` with upserted class — **design picks one clear layout**; prefer **per-model file** `tests/factories/test_<app>_<snake>.py` no — prefer `tests/factories/<app>_<snake>.py` exporting `{Model}Factory`).
2. The factory SHALL subclass `factory.django.DjangoModelFactory` with `Meta.model` pointing at `apps.<app>.models.<Model>`.
3. Field defaults SHALL be derived from inspected model fields with sensible factory_boy helpers (e.g. `Sequence`/`Faker` for Char/Text/Email/Slug; bools/defaults for Boolean; `SubFactory` or simple related stubs for FK/O2O when a related factory can be referenced or a minimal related create — design: **SubFactory if related factory exists or is generated in same run for same-app targets; else skip optional null FKs / use `factory.Iterator` / document TODO for cross-app**).
4. M2M and large JSON/binary fields MAY be omitted from the factory with a short comment.
5. Timestamp fields managed by TimeStamped bases SHALL not be forced in the factory (auto).

### Requirement 3 — API / model tests

**User Story:** As a solo Django developer, I want pytest stubs that hit my viewset (or at least the model), so that I have a green starting point.

#### Acceptance Criteria

1. WHEN a `{Model}ViewSet` exists in `apps/<app>/views.py` THEN the system SHALL write `tests/test_<app>_<snake>_api.py` (or equivalent) with `@pytest.mark.django_db` tests using DRF `APIClient`:
   - Unauthenticated list/create denied (401/403 as appropriate for project defaults).
   - Authenticated list returns 200 (pagination-aware: accept list or `results` key).
   - Authenticated retrieve for a factory-created instance returns 200.
   - Authenticated create with minimal valid payload returns 201 when serializer fields allow (best-effort from inspected required-ish fields; skip create test with clear `pytest.skip` or omit if payload cannot be inferred safely).
2. WHEN no viewset exists THEN the system SHALL still write a **model** smoke test file (e.g. factory creates instance and `__str__`/pk works) and SHALL note in success output that API tests were skipped pending `add-viewset`.
3. URL resolution SHALL prefer `reverse` with the router basename from octave conventions (`basename` = snake model from `add-viewset` / `api_sync`) and app API include path (`/api/<app>/…`); IF reverse fails at generation time, fall back to documented path strings matching kickstart URL layout.
4. Auth helper: reuse or add a small fixture (e.g. in `tests/conftest.py` or local module) that provides `api_client` and `auth_client` via `force_authenticate` against the project’s custom User model (`get_user_model()`), creating a user with factory or `create_user`.

### Requirement 4 — Multitenancy awareness (light)

**User Story:** As a solo Django developer on a multitenancy project, I want stubs that do not immediately explode on tenant requirements.

#### Acceptance Criteria

1. WHEN the project has multitenancy AND the model is TenantAware (or has a tenant FK) THEN the factory/tests SHALL set or attach a tenant in a minimal way consistent with existing kickstart tenancy helpers if discoverable; IF not safely discoverable THEN generate TODO comments and a skipped or narrowly scoped model test rather than a broken API create.
2. WHEN the project has no multitenancy THEN no tenant fixtures SHALL be required.

### Requirement 5 — Docs and tests (generator package)

**User Story:** As a maintainer, I want README docs and generator tests for add-test.

#### Acceptance Criteria

1. README SHALL document `add-test`, output paths, and `uv run pytest` usage.
2. Generator package tests SHALL cover: help listing; factory+API files created after add-model+add-viewset; refuse without force; force replace; model-only path without viewset; bad/missing model.

## Non-Functional Requirements

### Code Architecture and Modularity
- New module `src/django_octave/api_parts/test_gen.py` (or `testing_gen.py`); thin Typer command + prompts.
- Reuse `inspect_model_fields`, `detect_project`, naming helpers, `class_exists` for viewset detection.
- Generated tests target the **user’s** project tree (`tests/`), not the generator’s own tests.

### Performance
- Stubs stay small (few tests); no network; no live server.

### Security
- Do not hardcode real secrets; use `set_password` / factory post-generation for users.
- Test credentials are throwaway (`password` in factories only).

### Reliability
- Refuse collisions without `--force`; never overwrite unrelated test modules.
- Generated code must be syntactically valid Python.

### Usability
- Dual UX; Rich success with pytest command; MDX-safe README.
