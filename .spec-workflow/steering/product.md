# Product Overview

## Product Purpose

**django-octave** is an opinionated generator package that kickstarts production-ready Django REST API projects. It scaffolds everything a solo developer needs to start building — Django, DRF, OpenAPI (drf-spectacular), auth, settings, tooling, and optional Docker / row-level multitenancy — so they spend time on domain logic, not boilerplate.

## Target Users

- **Primary**: Solo Django developers who want a fast, consistent path from zero to a deployable REST API.
- **Needs**: Sensible defaults, minimal decision fatigue, modern Python packaging (`uv`), clear project layout, and docs/OpenAPI that work out of the box.
- **Pain points**: Assembling DRF + Spectacular + JWT + Docker + env settings by hand; inconsistent project structure across personal projects; forgetting production essentials (WhiteNoise, Gunicorn, security settings).

## Key Features

1. **Project kickstart (`django-octave new`)**: Interactive prompts and/or CLI flags to create a full Django project ready for local and production use.
2. **Opinionated REST stack**: Django + DRF + drf-spectacular (schema + Swagger/ReDoc UI), filtering, CORS, env-based settings, custom user model, JWT auth — decided for the user.
3. **Database choice at create time**: SQLite, PostgreSQL, or MariaDB, with matching dependencies and settings wired in.
4. **Optional Docker**: Dev and production Docker setups (Dockerfile + Compose), using `uv`, when the user opts in.
5. **Optional row-level multitenancy**: Opt-in at project creation; first-party implementation (not a third-party tenancy package) for full control.
6. **`core` app**: Always generated; shared foundations (e.g. timestamped models) used by later apps.
7. **App scaffolding**: Generated Django apps live under `apps/`; CLI supports adding apps after initial create (interactive + flags).
8. **Production readiness by default**: Gunicorn, WhiteNoise, split/env settings, security defaults, pytest stack, Ruff — without cloud-specific deployment wizards.

## Business Objectives

- Be the default “start here” tool for solo Django API work.
- Encode strong opinions so generated projects look and behave the same way.
- Keep the generator maintainable as a GPL-3.0 Python package under `src/django_octave/`.

## Success Metrics

- **Time-to-first-endpoint**: New project runs and serves an authenticated/OpenAPI-documented API with minimal manual steps.
- **Opinion coverage**: A new project needs few extra packages for a typical production REST API.
- **Adoption clarity**: Users understand flags vs prompts; `django-octave --help` documents the full create/add surface.
- **Consistency**: Generated layout (`apps/`, `core`, settings, Docker) matches steering across versions.

## Product Principles

1. **Opinionated over configurable**: Make the good default the only default unless a choice is essential (DB, Docker, multitenancy).
2. **Production-ready from day one**: Local convenience must not omit prod essentials.
3. **Solo-dev ergonomics**: Interactive when exploring; flags when scripting/CI.
4. **Batteries for the API, not the frontend**: REST + OpenAPI focus; no GraphQL, no admin UI themes, no cloud deploy targets.
5. **Own the critical path**: Multitenancy and `core` primitives are first-party so we control behavior and upgrades.

## Non-Goals (v1)

- Cloud deployment generators (AWS/GCP/Azure/Fly/etc.)
- GraphQL
- Admin UI themes / custom admin skins
- Schema-based or third-party multitenancy packages (e.g. django-tenants)
- Adding multitenancy to an already-generated project (create-time option only)
- Frontend SPA scaffolding (React/Vue/etc.)
- Celery / async worker stacks as required defaults (may be considered later)

## Monitoring & Visibility

- **Interface**: CLI (Typer) with clear success/next-step output after generation.
- **Generated visibility**: OpenAPI UI via drf-spectacular; Django admin available as standard Django, unthemed.
- **No product dashboard**: Progress/monitoring is the user’s own ops stack, not part of django-octave.

## Future Vision

- Richer `django-octave add` generators (serializers, viewsets, spectacular extensions) on top of the kickstart.
- Optional hardening packs (rate limiting, audit logging) as explicit later features.
- Keep multitenancy and `core` as the extension points for “generic stuff required later.”

### Potential Enhancements

- **Generators**: Model/API scaffolding beyond empty apps
- **Observability hooks**: Optional Sentry wiring (still no cloud deploy)
- **Docs site**: Published examples of generated projects
