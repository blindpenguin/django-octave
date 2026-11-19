# Requirements Document

## Introduction

**project-kickstart** delivers `django-octave new`: the full opinionated generator that creates a production-ready Django REST API project in one step. Solo developers choose project name, database (SQLite / PostgreSQL / MariaDB), whether to include Docker (dev + prod), and whether to enable first-party row-level multitenancy. The generator writes a complete tree (`config/`, `apps/core`, env settings, DRF + Spectacular + JWT, pytest/Ruff/uv, optional Docker and tenancy) so the user can run and extend the API immediately.

**Out of scope for this spec:** `django-octave add` (further app scaffolding), GraphQL, admin UI themes, cloud deploy generators, retrofitting multitenancy onto an existing project, Celery/workers.

## Alignment with Product Vision

Matches product steering: opinionated kickstart for solo Django API work; production-ready defaults; essential choices only (DB, Docker, multitenancy); batteries for REST + OpenAPI; first-party `core` and row-level tenancy; GPL-3.0 package under `src/django_octave/` with in-package Jinja2 templates.

## Requirements

### Requirement 1 — CLI entry and dual UX

**User Story:** As a solo Django developer, I want to create a project via interactive prompts or CLI flags, so that I can explore easily or script generation in CI.

#### Acceptance Criteria

1. WHEN the user runs `django-octave` or `django-octave --help` THEN the system SHALL show available commands including `new`.
2. WHEN the user runs `django-octave new` without required options THEN the system SHALL prompt interactively for project name, database, Docker (yes/no), and multitenancy (yes/no).
3. WHEN the user runs `django-octave new` with flags for all required options THEN the system SHALL generate without interactive prompts.
4. IF a required value is missing in non-interactive/flag mode THEN the system SHALL fail with a clear error (no hanging prompts).
5. WHEN generation succeeds THEN the system SHALL print next-step commands (e.g. `uv sync`, migrate, runserver or compose).

### Requirement 2 — Project skeleton and layout

**User Story:** As a solo Django developer, I want a consistent Django layout with `config/` and `apps/`, so that every project starts the same way.

#### Acceptance Criteria

1. WHEN a project is generated THEN the system SHALL create a classic Django layout with `manage.py`, `config/` (settings, urls, wsgi/asgi), and `apps/` as a Python package.
2. WHEN a project is generated THEN the system SHALL always create `apps.core` with shared primitives including at least a `TimeStampedModel` (or equivalent abstract base).
3. WHEN a project is generated THEN domain apps SHALL live under `apps/` and be referenced in `INSTALLED_APPS` with full paths (e.g. `apps.core`).
4. WHEN a project is generated THEN `config/` SHALL contain only project wiring (settings/urls/ASGI/WSGI), not domain models or views.
5. IF the target directory already exists and is non-empty THEN the system SHALL refuse to overwrite unless an explicit force flag is provided (document the flag in help).

### Requirement 3 — Opinionated REST / production stack

**User Story:** As a solo Django developer, I want DRF, OpenAPI, JWT, and production essentials wired in by default, so that I do not assemble the stack myself.

#### Acceptance Criteria

1. WHEN a project is generated THEN dependencies SHALL include Django (latest stable at generator release), djangorestframework, drf-spectacular (with sidecar), djangorestframework-simplejwt, django-filter, django-cors-headers, django-environ, WhiteNoise, and Gunicorn.
2. WHEN a project is generated THEN settings SHALL be env-driven via django-environ, with a checked-in `.env.example` and no secrets committed.
3. WHEN a project is generated THEN a custom user model SHALL be configured from day one.
4. WHEN a project is generated THEN API auth SHALL default to JWT (SimpleJWT) with URL routes for obtain/refresh (and documented usage).
5. WHEN a project is generated THEN OpenAPI schema and Swagger/ReDoc UI SHALL be available via drf-spectacular.
6. WHEN a project is generated THEN WhiteNoise SHALL be configured for static files and Gunicorn SHALL be the documented production server entry.
7. WHEN a project is generated THEN tooling SHALL include uv (`pyproject.toml`), Ruff, and pytest + pytest-django + factory-boy (+ coverage as agreed in design).
8. WHEN production settings are selected (`DEBUG=False` / prod env) THEN security-related Django settings SHALL be enabled appropriately (e.g. secure cookies/SSL redirect headers as documented in design).

### Requirement 4 — Database selection

**User Story:** As a solo Django developer, I want to choose SQLite, PostgreSQL, or MariaDB at create time, so that local and production SQL needs are covered without a large driver matrix.

#### Acceptance Criteria

1. WHEN creating a project THEN the user SHALL be able to select exactly one of: SQLite, PostgreSQL, MariaDB.
2. WHEN SQLite is selected THEN settings and deps SHALL use Django’s built-in SQLite backend with a sensible default DB path.
3. WHEN PostgreSQL is selected THEN the project SHALL include `psycopg` (v3) and settings/`DATABASES` suitable for env-configured Postgres.
4. WHEN MariaDB is selected THEN the project SHALL include a MariaDB-capable driver and settings/`DATABASES` suitable for env-configured MariaDB.
5. WHEN Docker is enabled AND the database is PostgreSQL or MariaDB THEN Compose SHALL include a matching database service; WHEN SQLite is selected THEN Compose SHALL NOT require a DB container.

### Requirement 5 — Optional Docker (dev + prod)

**User Story:** As a solo Django developer, I want optional Docker for both development and production, so that I can run the same stack locally in containers and ship a production baseline.

#### Acceptance Criteria

1. WHEN the user opts into Docker THEN the generator SHALL emit a Dockerfile and both a development-oriented and production-oriented Compose file (or equivalent documented split), using `uv` in images.
2. WHEN Docker is enabled THEN documentation in the generated README SHALL describe how to run dev and prod Compose flows.
3. WHEN the user declines Docker THEN the generator SHALL omit Docker artifacts and the non-Docker local workflow (`uv sync`, `manage.py`, etc.) SHALL still be complete.
4. WHEN Docker prod is used THEN the app process SHALL run under Gunicorn (not Django’s runserver).

### Requirement 6 — Optional row-level multitenancy

**User Story:** As a solo Django developer, I want an optional first-party row-level multitenancy setup at create time, so that multi-tenant APIs start with isolation built in under our control.

#### Acceptance Criteria

1. WHEN the user opts into multitenancy at create time THEN the generator SHALL add first-party tenant models, middleware/request context, and queryset/manager scoping under `apps.core` (and wire settings/urls as needed)—not a third-party tenancy package.
2. WHEN multitenancy is enabled THEN tenant isolation SHALL be enforced at the row/queryset layer for tenant-scoped models (design SHALL specify the base classes and how domain models opt in).
3. WHEN the user declines multitenancy THEN no tenancy middleware/models SHALL be installed beyond what a normal single-tenant project needs.
4. The CLI SHALL NOT offer adding multitenancy to an already-generated project in this spec.

### Requirement 7 — Generated project documentation and package metadata

**User Story:** As a solo Django developer, I want a generated README and env example that tell me how to run the project, so that I can get to a first successful API request quickly.

#### Acceptance Criteria

1. WHEN a project is generated THEN a README SHALL document: install/`uv sync`, env vars, migrate, createsuperuser, runserver (and Compose if present), and OpenAPI UI URLs.
2. WHEN a project is generated THEN `.env.example` SHALL list required variables for the chosen DB and auth/secret settings.
3. WHEN the generator package is installed THEN the console script `django-octave` SHALL invoke the Typer CLI.

### Requirement 8 — Generator package implementation

**User Story:** As a maintainer, I want the generator implemented as an in-package Jinja2/Typer/Rich tool with tests, so that releases stay reliable and opinionated.

#### Acceptance Criteria

1. The generator SHALL live under `src/django_octave/` with Jinja2 templates inside the package (`templates/project/…`).
2. Rendering SHALL be driven by a typed context (project name, database, docker, multitenancy, etc.) with Jinja conditionals—not duplicate full trees per option matrix when avoidable.
3. Unit tests SHALL cover context building and key template outputs (at least: layout presence, DB driver wiring, Docker on/off, multitenancy on/off).
4. The django-octave package license SHALL remain GPL-3.0; generated project license is left to the user unless design specifies otherwise.

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility**: CLI commands, prompts, rendering, and templates are separate modules.
- **Modular Design**: Option flags map to a single context object consumed by Jinja2.
- **Clear Interfaces**: Public surface is the `django-octave` CLI; generated apps have no runtime dependency on django-octave.
- Align with existing Cursor rules (Python typing, Ruff, pytest, Django layout conventions for *generated* code).

### Performance

- Full project generation SHALL complete in seconds on a typical developer machine (no network required at generate time beyond prior package install).

### Security

- Never write real secrets into the repo; use placeholders and `.env.example`.
- Prod settings path SHALL default to secure Django settings when `DEBUG` is false.
- Multitenancy (when on) SHALL fail closed: unscoped access to tenant data must not be the default for tenant-scoped models.

### Reliability

- Invalid combinations or missing paths SHALL produce non-zero exit codes and actionable messages.
- Generation SHALL be atomic enough that a failed mid-write does not silently leave a “looks complete” project (design: write to temp / clean up or document failure behavior).

### Usability

- Help text SHALL document all `new` flags and defaults.
- Interactive prompts SHALL use clear labels and sensible defaults (recommend **SQLite** as default DB for fastest start; Docker and multitenancy default **off**).
