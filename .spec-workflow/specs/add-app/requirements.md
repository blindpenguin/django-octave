# Requirements Document

## Introduction

**add-app** delivers `django-octave add`: scaffold a new domain Django app under `apps/` inside an existing django-octave project. The command creates the app package (models ready for `TimeStampedModel`, admin, migrations), **API stubs** (serializer, viewset, urls with Spectacular annotations), **registers the app in `INSTALLED_APPS`**, and **mounts its API routes** under the project URLConf. Dual UX: interactive prompts and/or CLI flags.

**Out of scope:** generating arbitrary custom fields/models from a schema DSL; GraphQL; admin UI themes; creating a new project (`new`); retrofitting multitenancy; Celery tasks.

## Alignment with Product Vision

Matches product feature “App scaffolding” and the follow-on vision for richer `add` generators (serializers, viewsets, spectacular). Keeps opinionated layout (`apps/`, `core` primitives) and solo-dev dual UX from steering.

## Requirements

### Requirement 1 — CLI entry and dual UX

**User Story:** As a solo Django developer, I want to add an app via prompts or flags, so that I can extend a project quickly in a terminal or script.

#### Acceptance Criteria

1. WHEN the user runs `django-octave --help` THEN the system SHALL list an `add` command.
2. WHEN the user runs `django-octave add` without a required app name AND stdin is a TTY THEN the system SHALL prompt for the app name (and any other required options).
3. WHEN the user runs `django-octave add <name>` with flags THEN the system SHALL not prompt for values already provided.
4. IF required options are missing in non-interactive mode THEN the system SHALL exit non-zero with a clear message (no hanging prompts).
5. WHEN generation succeeds THEN the system SHALL print what was created and any next steps (e.g. makemigrations/migrate).

### Requirement 2 — Project detection and safety

**User Story:** As a solo Django developer, I want `add` to run only in a compatible project and refuse unsafe overwrites, so that I do not corrupt unrelated directories.

#### Acceptance Criteria

1. WHEN `add` runs THEN the system SHALL resolve the target project directory (default: current working directory; optional `--path` to the project root).
2. IF the target is not a django-octave-style project (at minimum: `apps/` package and `config/settings` with `INSTALLED_APPS`) THEN the system SHALL fail with a clear error.
3. IF `apps/<app_name>` already exists THEN the system SHALL refuse to overwrite unless `--force` is passed (behavior of force documented in help).
4. IF the requested app name is reserved or invalid (`core`, `users`, non-`snake_case` / illegal Python module name) THEN the system SHALL reject it with a clear error.
5. The command SHALL NOT modify files outside the target project root.

### Requirement 3 — Domain app skeleton

**User Story:** As a solo Django developer, I want a consistent app under `apps/` ready to use `TimeStampedModel`, so that domain apps match project conventions.

#### Acceptance Criteria

1. WHEN an app is added THEN the system SHALL create `apps/<app_name>/` with `__init__.py`, `apps.py` (`AppConfig` with correct `name`/`label`), `models.py`, `admin.py`, `migrations/__init__.py`.
2. WHEN an app is added THEN `models.py` SHALL include at least one concrete starter model that subclasses `apps.core.models.TimeStampedModel` (name derived from the app or a documented default such as a singular resource), suitable as the basis for the API stubs.
3. IF the project has multitenancy enabled (detectable from project markers agreed in design, e.g. presence of `TenantAwareModel` / middleware) THEN the starter model SHALL subclass `TenantAwareModel` instead of (or in addition to) plain `TimeStampedModel` as specified in design.
4. WHEN an app is added THEN `admin.py` SHALL register the starter model (basic `ModelAdmin`).
5. App module naming SHALL use `snake_case`; `INSTALLED_APPS` entry SHALL be `apps.<app_name>`.

### Requirement 4 — Auto-wire Django settings and URLs

**User Story:** As a solo Django developer, I want the new app registered and routable without hand-editing settings/urls, so that the API is reachable immediately after migrate.

#### Acceptance Criteria

1. WHEN an app is added THEN the system SHALL append `apps.<app_name>` to `INSTALLED_APPS` in the project’s base settings if not already present.
2. WHEN an app is added THEN the system SHALL add a URL include for the app’s API urls under a path derived from the app name (e.g. `api/<app_name>/`), wired into `config/urls.py` without duplicating an existing include for that app.
3. IF settings or urls patching fails (unparseable file) THEN the system SHALL fail clearly and leave a recoverable state (design: prefer not to half-apply; document behavior).

### Requirement 5 — API stubs (DRF + Spectacular)

**User Story:** As a solo Django developer, I want serializer, viewset, and URL stubs with OpenAPI hooks, so that I can implement domain logic on top of a working CRUD skeleton.

#### Acceptance Criteria

1. WHEN an app is added THEN the system SHALL create DRF stubs: at least `serializers.py`, `views.py` (or `viewsets.py`), and `urls.py` using a router for the starter model.
2. WHEN an app is added THEN the viewset SHALL provide standard ModelViewSet (or documented subset) CRUD actions for the starter model.
3. WHEN an app is added THEN stubs SHALL use JWT-friendly defaults consistent with the project (e.g. `IsAuthenticated`) and include drf-spectacular extensions/annotations sufficient for the schema to list the endpoints.
4. WHEN an app is added THEN `django-filter` compatibility SHALL be prepared (e.g. `filterset_fields` or empty filterset hook) matching project conventions.
5. Generated API modules SHALL follow thin-view / service-ready layout guidance: viewset stays thin; optional empty `services.py` MAY be created as a placeholder for write logic (design decides if required).

### Requirement 6 — Tests and docs for the generator

**User Story:** As a maintainer, I want tests and README usage for `add`, so that the command stays reliable.

#### Acceptance Criteria

1. Unit/integration tests SHALL cover: happy-path add into a generated fixture project; reject invalid/reserved names; refuse existing app without `--force`; assert `INSTALLED_APPS` and url include updates; assert API stub files exist.
2. The django-octave README SHALL document `django-octave add` (interactive + flag examples).
3. After add, printed next steps SHALL mention `makemigrations` / `migrate` for the new app.

## Non-Functional Requirements

### Code Architecture and Modularity

- Reuse rendering patterns from `project-kickstart` (Jinja templates under `src/django_octave/templates/app/`, shared context helpers).
- Keep `add` command separate from `new`; share slug/validation utilities where practical.
- Generated code must not depend on django-octave at runtime.

### Performance

- App generation SHALL complete in well under a second for a normal project tree (excluding user migrate).

### Security

- Do not invent or write secrets; only edit structure/settings/urls/app files as specified.
- Respect existing project auth defaults (no weakening permissions in stubs).

### Reliability

- Idempotent registration: re-running with `--force` must not duplicate `INSTALLED_APPS` entries or URL includes.
- Invalid project / name / collision errors use non-zero exit codes.

### Usability

- Help text documents app name rules, `--path`, `--force`, and defaults.
- Starter model/API naming is predictable from the app name (documented in design).
