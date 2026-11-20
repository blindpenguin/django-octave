# Tasks Document

- [x] 1.0 Frontend package skeleton + SPA templates
  - [x] 1.1 Create `frontend_gen` package + Jinja `templates/frontend/` SPA shell
    - Files: `src/django_octave/frontend_gen/__init__.py`, `setup.py` (scaffold render entry), `src/django_octave/templates/frontend/**`
    - Render Vue 3 + Vite + Vue Router + Nuxt UI tree: package.json (pnpm), vite.config.ts with `ui()`, main.ts, App.vue/`UApp`, CSS imports, index.html `isolate`, login + home pages, auth tokens/client/router guards, `.env.example`, `.gitignore`
    - Context flag `include_register` controls RegisterView + route (templates only; Django register API is task 2.1)
    - Purpose: Opinionated SPA shell on disk
    - _Leverage: `rendering/writer.py` Jinja patterns; design layout; https://ui.nuxt.com/docs/getting-started/installation/vue_
    - _Requirements: 2.1–2.6, 3.1, 3.4–3.6_
    - _Prompt: Implement the task for spec vue-nuxt-ui-frontend, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Vue/Vite template engineer | Task: Add frontend_gen render of templates/frontend SPA shell with Nuxt UI Vite plugin and JWT client stubs; support include_register Jinja flag | Restrictions: Not full Nuxt; no CLI yet; no Compose/Django register API yet; do not run pnpm in generator | Success: Rendering into tmpdir yields expected files; register page absent when flag false | After done: log-implementation then mark [-]/[x] in tasks.md_

  - [x] 1.2 Detect existing frontend + force/refuse in setup entrypoint
    - Files: `src/django_octave/frontend_gen/detect.py`, extend `setup.py`, unit tests under `tests/frontend_gen/`
    - Probe `frontend/package.json` (or `frontend/`); refuse without force; with force re-render carefully
    - Purpose: Idempotent scaffolding
    - _Leverage: `celery_gen/detect.py` patterns_
    - _Requirements: 1.6–1.7_
    - _Prompt: Implement the task for spec vue-nuxt-ui-frontend, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python generator engineer | Task: Implement detect + force/refuse around setup_frontend render | Restrictions: No CLI; do not wipe unrelated sibling dirs | Success: Unit tests cover refuse and force overwrite of marker files | Log + mark complete_

- [x] 2.0 Django wiring (CORS, JWT email obtain, optional register)
  - [x] 2.1 Email token obtain + optional register API + urls/env CORS merge
    - Files: `src/django_octave/frontend_gen/django_patch.py`, Jinja snippets under `templates/frontend_django/` or inline writers; tests
    - Patch `.env.example` CORS for Vite 5173 (+ 8080 when Docker); swap/add email-aware TokenObtainPair serializer/view; if register: `apps/users` register view + `POST /api/auth/register/` in `config/urls.py`; skip register files if already present
    - Purpose: SPA can login (email) and optionally signup
    - _Leverage: existing urls/token paths; User email USERNAME_FIELD; design register contract_
    - _Requirements: 3.2–3.5, 4.1–4.3_
    - _Prompt: Implement the task for spec vue-nuxt-ui-frontend, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DRF engineer | Task: Implement django_patch for CORS env merge, email JWT obtain, optional register endpoint | Restrictions: No allow-all CORS; use password validators; parse-safe url edits | Success: Unit tests on fixture project files for register on/off and CORS lines | Log + mark complete_

- [x] 3.0 Docker Compose + orchestration
  - [x] 3.1 Compose inject (dev Vite + prod nginx) + `frontend/Dockerfile` / nginx.conf
    - Files: `src/django_octave/frontend_gen/compose.py`, templates for Dockerfile/nginx (if not already in task 1.1), tests
    - Marker inject into `docker-compose.yml` and `docker-compose.prod.yml` when present; skip when absent; force replaces markers
    - Purpose: Docker projects run SPA alongside API
    - _Leverage: `celery_gen/compose.py` markers; design service YAML_
    - _Requirements: 5.1–5.4_
    - _Prompt: Implement the task for spec vue-nuxt-ui-frontend, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Compose/DevOps engineer | Task: Marker-based frontend service inject for dev and prod compose | Restrictions: Do not break web/db/celery services; no inventing Compose when Docker was never chosen | Success: Unit tests on sample compose YAML | Log + mark complete_

  - [x] 3.2 Wire `setup_frontend` orchestrator (render + django_patch + compose)
    - Files: `src/django_octave/frontend_gen/setup.py`, `__init__.py` exports, tests
    - Single `setup_frontend(root, *, register: bool, force: bool)` used by CLI and `new`
    - Purpose: One shared path for both entry points
    - _Leverage: `celery_gen/setup.py`_
    - _Requirements: 1.4–1.5, 5.2_
    - _Prompt: Implement the task for spec vue-nuxt-ui-frontend, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Generator architect | Task: Orchestrate detect/render/django_patch/compose in setup_frontend | Restrictions: Keep side effects ordered and testable | Success: Integration-style unit test creates frontend + env touchpoints on fixture | Log + mark complete_

- [x] 4.0 CLI: `add-frontend` + `new --frontend`
  - [x] 4.1 Commands, prompts, cli registration
    - Files: `commands/add_frontend.py`, `prompts/add_frontend.py`, `prompts/new_project.py`, `commands/new.py`, `cli.py`
    - Dual UX: `--frontend/--no-frontend`, `--register/--no-register`; ask register when frontend on and TTY; non-interactive missing flags exit 2; post-render `setup_frontend` like celery
    - Purpose: User-facing surface
    - _Leverage: `add_celery` / `new --celery` patterns_
    - _Requirements: 1.1–1.5, 3.2–3.3_
    - _Prompt: Implement the task for spec vue-nuxt-ui-frontend, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI developer | Task: Wire add-frontend and new frontend/register flags + prompts | Restrictions: Thin commands; register prompt only if frontend enabled | Success: Listed in --help; flag modes work | Log + mark complete_

- [x] 5.0 Docs and generator tests
  - [x] 5.1 User docs + roadmap + generated README snippets
    - Files: `docs/` (add-frontend / getting-started / new), `docs/roadmap.md`, project README template touch if needed
    - Document flags, pnpm commands, JWT flow, Docker services, register ask
    - Purpose: Discoverability; docs match release policy later
    - _Requirements: 6.1, 6.3_
    - _Prompt: Implement the task for spec vue-nuxt-ui-frontend, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Document frontend scaffolding in MkDocs + roadmap shipped note | Restrictions: MDX-safe; no full Nuxt claims | Success: Examples match CLI | Log + mark complete_

  - [x] 5.2 CliRunner integration matrix
    - Files: `tests/commands/test_add_frontend.py`, optional `tests/commands/test_new_frontend.py`
    - Cover: help; add-frontend create; refuse/force; register on/off; compose fixture; not-octave gate; new --frontend smoke if cheap
    - Purpose: End-to-end confidence
    - _Requirements: 6.2_
    - _Prompt: Implement the task for spec vue-nuxt-ui-frontend, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA | Task: Integration tests for add-frontend and new --frontend | Restrictions: Keep reasonably fast; no mandatory full pnpm build in CI unless already trivial | Success: Cases pass; full pytest green | Log + mark complete_
