# Requirements Document

## Introduction

**vue-nuxt-ui-frontend** adds optional Vue SPA scaffolding to django-octave projects: a `frontend/` app using **Vue 3 + Vite + Vue Router + Nuxt UI** (`@nuxt/ui` Vite/Vue plugin — **not** the Nuxt meta-framework), wired to the existing SimpleJWT API.

Users opt in via **`django-octave new --frontend`** (or interactive prompt) and/or **`django-octave add-frontend`** on an existing project. v1 delivers a **shell app**: theme shell, router, JWT login/logout, token storage, authenticated home — not a CRUD UI generator. **Registration is optional**: interactive runs ask; non-interactive uses an explicit flag. When Docker was chosen for the project, Compose gains frontend **dev and production** services.

**Out of scope:** Full Nuxt (Nitro / file-based Nuxt host); React or other SPA frameworks; GraphQL clients; schema-driven CRUD page generators; SSR as a v1 requirement; cloud deploy targets; admin UI themes.

## Alignment with Product Vision

Matches product principle “API-first, optional Vue client” and the Future Vision frontend bullet. Dual UX (flags + prompts) and production-minded Docker when Docker was already opted in. Keeps the REST/JWT backend as the source of truth; the SPA is a thin authenticated client.

## Requirements

### Requirement 1 — Opt-in at `new` and via `add-frontend`

**User Story:** As a solo Django developer, I want to enable a Vue + Nuxt UI frontend when creating a project or later on an existing octave project, so that I get a consistent SPA shell without hand-wiring Vite and CORS.

#### Acceptance Criteria

1. WHEN the user runs `django-octave --help` THEN `add-frontend` SHALL be listed, and `new --help` SHALL document `--frontend` / `--no-frontend` (and register-related flags per Requirement 3).
2. WHEN `django-octave new` runs interactively and frontend is unset THEN the system SHALL prompt whether to scaffold the frontend (default off / opinionated default documented in design).
3. WHEN `new` is non-interactive (no TTY) and `--frontend` / `--no-frontend` is missing THEN the system SHALL fail with a clear message listing required flags (same pattern as Docker/Celery).
4. WHEN `--frontend` is chosen at `new` THEN the same frontend scaffolding path SHALL run as `add-frontend` after the Django project is rendered.
5. WHEN `add-frontend` runs on a valid octave project THEN the system SHALL create `frontend/` (exact layout in design) with Vue 3 + Vite + Vue Router + Nuxt UI per official Vue install path for `@nuxt/ui`.
6. WHEN `frontend/` already exists and `--force` is absent THEN refuse; with `--force`, refresh generated frontend files carefully without inventing unrelated app code.
7. IF the target is not a detectable octave project THEN `add-frontend` SHALL fail with a clear error.

### Requirement 2 — SPA shell (router, Nuxt UI, API client, home)

**User Story:** As a solo Django developer, I want a runnable SPA shell with Nuxt UI theming and an authenticated home page, so that I can extend UI on a solid base.

#### Acceptance Criteria

1. WHEN frontend is scaffolded THEN `frontend/` SHALL include: package manifest, Vite config with `@nuxt/ui` plugin, Tailwind/CSS wiring as required by Nuxt UI Vue docs, Vue entry + `UApp`, Vue Router with at least public login and authenticated home routes, and a minimal layout using Nuxt UI components.
2. WHEN the SPA talks to Django THEN it SHALL use a shared API client configured from env (e.g. Vite `VITE_API_BASE_URL` or equivalent) targeting the generated JWT endpoints (`/api/auth/token/`, `/api/auth/token/refresh/`).
3. WHEN the user logs in successfully THEN access (and refresh) tokens SHALL be stored client-side in a documented approach (design picks storage); subsequent authenticated requests SHALL send the Bearer access token.
4. WHEN the access token is missing/expired and refresh fails THEN the SPA SHALL route the user to login.
5. WHEN logged in THEN a home/dashboard route SHALL render a simple authenticated landing (not CRUD tables).
6. Success output / README SHALL document `install` + `dev` commands for the chosen package manager (design picks **one** primary: npm or pnpm).

### Requirement 3 — Login always; register optional (ask / flag)

**User Story:** As a solo Django developer, I want login included by default and registration only when I opt in, so that public signup is a conscious choice.

#### Acceptance Criteria

1. WHEN frontend is scaffolded THEN a login page SHALL always be generated (username/email + password → JWT obtain).
2. WHEN `new` or `add-frontend` runs **interactively** and register is unset THEN the system SHALL **ask** whether to include registration (clear yes/no prompt).
3. WHEN non-interactive THEN `--register` / `--no-register` (names finalized in design) SHALL be required if frontend is enabled; missing flag SHALL fail with a clear message.
4. WHEN register is **declined** THEN no register route/page SHALL be generated; login SHALL remain the only auth form.
5. WHEN register is **accepted** THEN the SPA SHALL include a register page/route, and the Django project SHALL expose a registration API endpoint compatible with the custom user model (create if missing; wire in urls; OpenAPI-friendly). IF registration already exists, reuse it.
6. Logout SHALL clear stored tokens and return the user to login.

### Requirement 4 — Django CORS and env wiring

**User Story:** As a solo Django developer, I want CORS and env examples updated for the Vite origin, so that the SPA can call the API in local and Docker dev without manual CORS debugging.

#### Acceptance Criteria

1. WHEN frontend is added THEN `.env.example` (and local env guidance) SHALL include the Vite dev origin(s) in `CORS_ALLOWED_ORIGINS` (correct default port for the Vite template — not an arbitrary wrong port).
2. WHEN frontend is added THEN Django CORS settings already present SHALL remain the mechanism; the generator SHALL ensure documented origins cover local Vite and Docker-published frontend URLs as applicable.
3. Frontend env example SHALL document the API base URL used by the Vite app for both host-run and Compose-run backends.

### Requirement 5 — Docker Compose when Docker was chosen

**User Story:** As a solo Django developer who opted into Docker, I want Compose services for the frontend in development and production, so that the SPA runs alongside the API without a separate undocumented setup.

#### Acceptance Criteria

1. WHEN the project has Docker/Compose (created with Docker or Compose files present) AND frontend is added THEN Compose SHALL gain:
   - A **development** frontend service running the Vite dev server (hot reload), networked to the API.
   - A **production** path: build the SPA static assets and serve them (dedicated frontend image/service and/or documented integration with the existing production stack — design picks one coherent approach).
2. WHEN the project has **no** Docker THEN success output SHALL document host-only frontend commands only; no Compose files invented solely for frontend unless the user later adds Docker (out of scope to retrofit full Docker from `add-frontend` alone).
3. Documented `docker compose` commands SHALL cover bringing up API + frontend for the common local path.
4. IF frontend Docker services already exist and `--force` is absent THEN refuse duplicate service injection; with `--force`, update carefully.

### Requirement 6 — Docs and generator tests

**User Story:** As a maintainer, I want docs and tests for frontend scaffolding so regressions are caught and users know the flags.

#### Acceptance Criteria

1. User docs (MkDocs command/getting-started pages as appropriate) and generated project README snippets SHALL document: `--frontend`, `add-frontend`, register ask/flags, install/dev commands, JWT auth flow, and Docker services when applicable.
2. Generator tests SHALL cover: help listing; `add-frontend` creates `frontend/` + CORS/env touchpoints; refuse without `--force` when present; `--register` vs `--no-register` file/route differences; Docker Compose services added when Compose fixture exists; missing-project gate.
3. Roadmap “Planned” frontend section SHALL move to shipped (or note in-progress) when implementation completes; non-goals remain: full Nuxt, React, CRUD UI generator.

## Non-Functional Requirements

### Code Architecture and Modularity
- Follow existing generator patterns: Typer command(s), Jinja templates under `src/django_octave/templates/`, shared detect/patch helpers (project root, Docker presence, settings/env/compose edits).
- Prefer one shared “scaffold frontend” implementation called from both `new` and `add-frontend`.
- Keep Vue templates maintainable; avoid shipping a full Nuxt app tree.

### Performance
- Vite defaults are sufficient for v1; no SSR performance goals.

### Security
- No secrets in committed frontend env examples; tokens only in client storage chosen in design (document XSS implications briefly).
- Registration endpoint SHALL validate input and use Django’s password validators; no open admin creation shortcuts.
- CORS SHALL use explicit allowed origins (not “allow all” in production defaults).

### Reliability
- Idempotent refuse/`--force` behavior consistent with `add-celery` / other add commands.
- Parse-safe edits to Compose, `.env.example`, and Django urls/settings.

### Usability
- Dual UX (flags + prompts); Rich next-step output with exact commands.
- Opinionated package manager and ports documented once — no multi-manager matrix in v1.
