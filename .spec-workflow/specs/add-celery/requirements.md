# Requirements Document

## Introduction

**add-celery** adds optional Celery background-task support to django-octave projects: a project-level Celery app + Redis broker wiring, Docker/Compose worker (and Beat) services when Docker is present, an `add-task` generator for `@shared_task` stubs, and clear local run commands. Celery remains **opt-in** (not a kickstart default), matching product non-goals (“not a required default”).

**Note on Beat:** Celery Beat and `django-celery-beat` are actively maintained (Celery 5.7 docs; django-celery-beat 2.9.0 in 2026). This spec uses Beat for periodic schedules. Alternatives (e.g. custom cron calling `delay`, or third-party schedulers) are out of scope for v1.

**Out of scope:** Making Celery mandatory on `new`; Kubernetes/cloud deploy manifests; Flower as required (optional mention only); Kafka/SQS brokers in v1 (Redis only); replacing Redis with in-memory for production; Dramatiq/RQ/Huey; full task monitoring UI.

## Alignment with Product Vision

Solo-dev ergonomics: optional background work without forcing a worker stack on every project. Opinionated Redis + Celery + Compose services when Docker was chosen. Complements the `add-*` family.

## Requirements

### Requirement 1 — Opt-in project Celery setup

**User Story:** As a solo Django developer, I want to enable Celery on an existing octave project (and optionally at `new` time), so that I can run background jobs without hand-wiring the app.

#### Acceptance Criteria

1. WHEN the user runs `django-octave --help` THEN `add-celery` SHALL be listed.
2. WHEN `add-celery` runs on an octave project THEN the system SHALL:
   - Add Celery (+ Redis client deps as needed) to the project’s `pyproject.toml` / dependency groups in an idempotent way.
   - Create a Celery application module (prefer `config/celery.py`) and ensure `config/__init__.py` loads it (`celery_app` / `app` export pattern).
   - Wire settings: broker/result backend from env (default Redis URL), `CELERY_*` / django-celery conventions as designed.
   - Extend `.env.example` with `REDIS_URL` / `CELERY_BROKER_URL` (and result backend if distinct).
3. WHEN the project was created with Docker THEN Compose SHALL gain `redis`, `worker`, and `beat` services (or documented equivalents) that talk to the app; IF no Docker THEN success output SHALL print local `celery -A … worker` / `beat` commands only.
4. WHEN Celery is already configured (detect celery module / setting) and `--force` is absent THEN refuse; with `--force`, refresh generated celery wiring carefully without wiping unrelated settings.
5. Optional: `django-octave new … --celery` (or prompt) MAY call the same setup path after project render — **include if cheap**; otherwise document “run `add-celery` after `new`” as v1.

### Requirement 2 — Worker / Beat runner DX

**User Story:** As a solo Django developer, I want a clear way to run the worker and periodic scheduler locally, so that tasks actually execute.

#### Acceptance Criteria

1. README / success output SHALL document:
   - Worker: `uv run celery -A config worker -l INFO` (exact app path per design).
   - Beat: `uv run celery -A config beat -l INFO` (and DatabaseScheduler if django-celery-beat is chosen).
   - Dev-only combined: `worker --beat` as an optional convenience note (not for production).
2. WHEN Docker Compose is updated THEN `docker compose up worker beat` (names per design) SHALL be documented.
3. Periodic schedules in v1 SHALL use either:
   - **A)** code `beat_schedule` in celery config, and/or  
   - **B)** `django-celery-beat` + admin-editable periodic tasks  
   Design picks **one primary**; prefer **A for simplicity** with optional B as a flag `--database-scheduler` if low cost.

### Requirement 3 — `add-task` generator

**User Story:** As a solo Django developer, I want `add-task` to create a `@shared_task` stub in my app, so that I can enqueue work from views/services quickly.

#### Acceptance Criteria

1. WHEN the user runs `django-octave add-task APP NAME` THEN a snake_case task function SHALL be added under `apps/<app>/tasks.py` (create file with imports if missing), using `@shared_task` (bind optional via `--bind`).
2. Dual UX (flags/prompts); `--force` replaces an existing task of the same name; without force, refuse duplicates.
3. Optional `--schedule CRON` or `--every SECONDS` SHALL register the task in the project’s Beat schedule (code schedule or django-celery-beat row — match Requirement 2 choice); without schedule flags, only the task stub is written.
4. IF Celery is not set up THEN fail with a hint to run `add-celery` first.
5. Success output SHALL show how to call `.delay()` / `.apply_async()` and, if scheduled, how Beat picks it up.

### Requirement 4 — Docs and tests

**User Story:** As a maintainer, I want README docs and generator tests for Celery setup and add-task.

#### Acceptance Criteria

1. README SHALL document `add-celery`, worker/beat run commands, Compose services, and `add-task`.
2. Generator tests SHALL cover: help; add-celery creates celery module + env keys; refuse without force; add-task stub; schedule flag smoke; missing celery gate; Docker path adds services when compose exists (fixture).
3. Roadmap / product notes SHALL clarify Celery is optional (not a required default); Beat is supported.

## Non-Functional Requirements

### Code Architecture and Modularity
- Modules e.g. `src/django_octave/celery_gen/` or `api_parts` + `commands/add_celery.py`, `add_task.py`.
- Idempotent patches to `pyproject.toml`, settings, compose, `.env.example`.
- Reuse `detect_project`, Docker detection from kickstart flags/files.

### Performance
- Default Redis locally; no embedded broker pretending to be production-safe.

### Security
- Broker URL from env only; no committed secrets.
- Tasks must not log sensitive payloads by default in stubs.

### Reliability
- Clear refuse when already configured; parse-safe settings/compose edits.

### Usability
- Dual UX; Rich next-step commands; MDX-safe README.
