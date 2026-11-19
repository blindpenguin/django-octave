# Tasks Document

- [x] 1.0 Package foundation and CLI shell
  - [x] 1.1 Add generator dependencies and entrypoint wiring
    - Files: `pyproject.toml`, `src/django_octave/__init__.py`, `src/django_octave/cli.py`
    - Add runtime deps: typer, rich, jinja2; dev deps: pytest, ruff (and pytest config as needed)
    - Wire `[project.scripts] django-octave` to Typer app; replace hello-world stub
    - Purpose: Installable CLI shell
    - _Leverage: existing `pyproject.toml`, steering `tech.md`_
    - _Requirements: 1.1, 7.3, 8.1_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python packaging engineer | Task: Add Typer/Rich/Jinja2 deps and a minimal Typer app entry so `django-octave --help` works | Restrictions: Do not implement `new` logic yet; do not expand scope to templates; use uv for dependency changes | _Leverage: pyproject.toml, src/django_octave/__init__.py | _Requirements: 1.1, 7.3, 8.1 | Success: `uv run django-octave --help` shows the app; entrypoint is not the hello stub | After coding: set this task [-]→[x] in tasks.md and call log-implementation with artifacts_

  - [x] 1.2 Implement `new` command flags and help (no render yet)
    - Files: `src/django_octave/commands/__init__.py`, `src/django_octave/commands/new.py`, `src/django_octave/cli.py`
    - Flags: name/path, `--database`, `--docker/--no-docker`, `--multitenancy/--no-multitenancy`, `--force`, defaults per design
    - Register command on Typer app; document help text
    - Purpose: Dual-UX surface without generation
    - _Leverage: `cli.py`, design § Components_
    - _Requirements: 1.1, 1.3, 1.4_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI developer (Typer) | Task: Implement `django-octave new` with flags and validation enums; stub body that does not write files yet | Restrictions: No Jinja rendering yet; defaults sqlite/docker off/multitenancy off | _Leverage: cli.py, design.md | _Requirements: 1.1, 1.3, 1.4 | Success: Help lists all flags; invalid database rejected by Typer | Log implementation then mark complete_

  - [x] 1.3 Interactive prompts for missing options
    - Files: `src/django_octave/prompts/__init__.py`, `src/django_octave/prompts/new_project.py`, `src/django_octave/commands/new.py`
    - Prompt for name, database, docker, multitenancy when missing and TTY; fail clearly when non-interactive and incomplete
    - Purpose: Interactive UX
    - _Leverage: Rich, `commands/new.py`_
    - _Requirements: 1.2, 1.4_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI UX developer | Task: Add Rich prompts merging into the new-command flow; non-TTY missing flags → non-zero exit | Restrictions: Do not render project yet | _Leverage: prompts/, commands/new.py | _Requirements: 1.2, 1.4 | Success: Interactive run asks only for missing values; CI-style missing flags errors | Log + mark complete_

- [x] 2.0 Rendering pipeline
  - [x] 2.1 Define `ProjectContext` and derivation helpers
    - Files: `src/django_octave/rendering/__init__.py`, `src/django_octave/rendering/context.py`, `src/django_octave/rendering/versions.py`
    - Typed context + slug normalization + DB deps / `include_db_service` / version pins module
    - Purpose: Single source of truth for templates
    - _Leverage: design § ProjectContext, tech.md pins_
    - _Requirements: 4.1–4.5, 8.2_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer | Task: Implement ProjectContext dataclass and pure helpers for slug, package lists, compose DB service flag, version constants | Restrictions: No filesystem writes | _Leverage: design.md Data Models | _Requirements: 4.*, 8.2 | Success: Unit-testable pure functions; clear types | Log + mark complete_

  - [x] 2.2 Jinja environment and atomic project writer
    - Files: `src/django_octave/rendering/engine.py`, `src/django_octave/rendering/writer.py`
    - Load templates from package; render to temp then move; refuse non-empty without force
    - Purpose: Safe generation
    - _Leverage: Jinja2, importlib.resources_
    - _Requirements: 2.5, 8.1, 8.2, NFR reliability_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer | Task: Implement Jinja loader from package templates and atomic writer with force semantics | Restrictions: Templates may still be minimal placeholders | _Leverage: rendering/context.py | _Requirements: 2.5, 8.* | Success: Writes into tmp_path; non-empty without force raises/exits cleanly | Log + mark complete_

  - [x] 2.3 Wire `new` to context + render + next-steps output
    - Files: `src/django_octave/commands/new.py`, optionally `src/django_octave/rendering/summary.py`
    - Build context from flags/prompts; call renderer; print uv/migrate/runserver or compose hints
    - Purpose: End-to-end command path
    - _Leverage: tasks 1.* and 2.1–2.2_
    - _Requirements: 1.5, 7.1_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI developer | Task: Connect new command to ProjectContext + renderer + Rich success summary | Restrictions: Full template content can still be incomplete if later tasks own files—but command must invoke renderer | _Requirements: 1.5, 7.1 | Success: `new` with flags produces a directory and prints next steps | Log + mark complete_

- [x] 3.0 Core generated project templates (always-on)
  - [x] 3.1 Root project files: pyproject, env example, README, manage.py, tooling
    - Files under `src/django_octave/templates/project/`: `pyproject.toml.j2`, `.env.example.j2`, `README.md.j2`, `manage.py.j2`, Ruff/pytest config, `.python-version.j2`, `.gitignore.j2`
    - Opinionated deps; DB-conditional packages; uv-oriented
    - Purpose: Generated project metadata and docs
    - _Leverage: design Implementation Notes, requirements 3 & 7_
    - _Requirements: 3.1, 3.2, 3.7, 4.*, 7.1, 7.2_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django platform engineer | Task: Author root Jinja templates for packaging, env example, README next steps, manage.py, lint/test config | Restrictions: No Docker files here; keep secrets out of repo files | _Requirements: 3.*, 7.* | Success: Rendered tree has runnable metadata for sqlite baseline | Log + mark complete_

  - [x] 3.2 `config/` package: settings split, urls, wsgi/asgi
    - Templates: `config/settings/{base,local,prod}.py.j2`, `config/urls.py.j2`, `config/wsgi.py.j2`, `config/asgi.py.j2`, `__init__` files
    - django-environ; DRF; Spectacular; JWT routes; CORS; WhiteNoise; security in prod
    - Purpose: Project wiring only
    - _Leverage: structure.md, django.mdc conventions_
    - _Requirements: 2.1, 2.4, 3.2–3.6, 3.8_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django settings expert | Task: Template config package with env-based settings and API/OpenAPI/JWT URL wiring | Restrictions: No domain models in config | _Requirements: 2.*, 3.* | Success: base/local/prod coherent; Spectacular + SimpleJWT urls present | Log + mark complete_

  - [x] 3.3 `apps.core` with `TimeStampedModel` and package layout
    - Templates: `apps/__init__.py`, `apps/core/{apps,models,admin}.py.j2` (minimal admin ok)
    - Purpose: Shared primitives always present
    - _Leverage: structure.md core app_
    - _Requirements: 2.2, 2.3_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django developer | Task: Template apps package and core TimeStampedModel | Restrictions: Multitenancy models belong in later task | _Requirements: 2.2, 2.3 | Success: INSTALLED_APPS includes apps.core; abstract timestamps exist | Log + mark complete_

  - [x] 3.4 `apps.users` custom user (email USERNAME_FIELD) + admin
    - Templates: `apps/users/**`, AUTH_USER_MODEL in base settings template
    - Purpose: Custom user from day one
    - _Leverage: design AUTH_USER_MODEL decision_
    - _Requirements: 3.3, 3.4_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django auth developer | Task: Template apps.users with email-based User and wire AUTH_USER_MODEL + admin | Restrictions: Do not implement social auth | _Requirements: 3.3, 3.4 | Success: Generated settings point at apps.users.User; migrations path clear in README | Log + mark complete_

  - [x] 3.5 Generated tests skeleton and JWT/Spectacular smoke placeholders
    - Templates: `tests/conftest.py.j2`, basic test that settings load / API urls reverse
    - Purpose: pytest-django ready
    - _Leverage: testing.mdc_
    - _Requirements: 3.7_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA/Django tester | Task: Add generated pytest skeleton proving project imports and key URL names exist | Restrictions: Avoid fragile full E2E in template | _Requirements: 3.7 | Success: Template tests are valid pytest-django starters | Log + mark complete_

- [x] 4.0 Database-specific template behavior
  - [x] 4.1 SQLite / PostgreSQL / MariaDB settings and dependency conditionals
    - Files: settings templates, `pyproject.toml.j2`, `.env.example.j2`, context helpers if needed
    - Engines, URLs, psycopg / mysqlclient conditionals
    - Purpose: Requirement 4 completeness
    - _Leverage: ProjectContext derivation_
    - _Requirements: 4.1–4.5_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django DBA-minded developer | Task: Finish DB conditionals across settings, env example, and pyproject deps for sqlite/postgres/mariadb | Restrictions: No Docker compose in this task | _Requirements: 4.* | Success: Three render fixtures differ correctly on engine and deps | Log + mark complete_

- [x] 5.0 Optional Docker templates
  - [x] 5.1 Dockerfile + compose dev/prod with uv; omit when disabled
    - Templates: `Dockerfile.j2`, `docker-compose.yml.j2`, `docker-compose.prod.yml.j2`; writer skips when `use_docker` false
    - DB service only when postgres/mariadb; prod uses Gunicorn; dev runserver
    - Purpose: Optional Docker
    - _Leverage: design Docker section_
    - _Requirements: 5.1–5.4, 4.5_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DevOps/Docker engineer | Task: Author Docker templates and ensure renderer omits them when docker=false; compose DB service rules | Restrictions: No cloud deploy files | _Requirements: 5.* | Success: docker on/off and sqlite vs postgres compose outputs match design | Log + mark complete_

  - [x] 5.2 Document Docker vs local flows in generated README partials
    - Files: `README.md.j2` sections
    - Purpose: Usability
    - _Leverage: task 3.1 README_
    - _Requirements: 5.2, 5.3, 7.1_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer/engineer | Task: Ensure generated README documents uv local flow and conditional Docker compose flows | Restrictions: No Spec Workflow mentions | _Requirements: 5.2, 7.1 | Success: README branches clearly on docker flag | Log + mark complete_

- [x] 6.0 Optional multitenancy templates
  - [x] 6.1 Tenant models, Membership, TenantAwareModel, managers
    - Templates under `apps/core/` (and migrations guidance); conditionals on `use_multitenancy`
    - Purpose: Row-level foundations
    - _Leverage: design multitenancy models_
    - _Requirements: 6.1, 6.2_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django multitenancy developer | Task: Template Tenant, Membership, TenantAwareModel + managers; inactive when flag false | Restrictions: No third-party tenancy packages; create-time only | _Requirements: 6.1, 6.2 | Success: Flag on renders models; flag off omits them | Log + mark complete_

  - [x] 6.2 Tenant middleware, settings wiring, fail-closed behavior docs
    - Templates: `apps/core/middleware.py.j2`, settings INSTALLED/MIDDLEWARE conditionals, README tenancy section
    - Header `X-Tenant-ID`; contextvar; write without tenant raises; read empty
    - Purpose: Request-scoped isolation
    - _Leverage: design middleware_
    - _Requirements: 6.1–6.3, NFR security_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django middleware developer | Task: Template tenant middleware and settings hooks; document header and fail-closed rules | Restrictions: Do not add retrofit CLI | _Requirements: 6.* | Success: Middleware only when enabled; documented behavior matches design | Log + mark complete_

- [x] 7.0 Generator tests and polish
  - [x] 7.1 Unit tests for context derivation and render matrices
    - Files: `tests/rendering/test_context.py`, `tests/rendering/test_render_project.py`
    - Matrix: db × docker × multitenancy file presence/content checks
    - Purpose: Prevent option-matrix regressions
    - _Leverage: pytest, tmp_path_
    - _Requirements: 8.3_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA engineer | Task: Write unit tests for ProjectContext and render output matrices | Restrictions: Keep tests fast; mark heavy manage.py check separately if added | _Requirements: 8.3 | Success: `uv run pytest` covers key conditionals | Log + mark complete_

  - [x] 7.2 CLI tests for help, non-interactive errors, successful new
    - Files: `tests/commands/test_new.py`
    - Typer CliRunner; force/empty-dir behavior
    - Purpose: Dual UX reliability
    - _Leverage: typer.testing_
    - _Requirements: 1.*, 2.5_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA/CLI tester | Task: Cover help, missing-flag failure, successful generate with flags, refuse non-empty without force | Restrictions: No network | _Requirements: 1.*, 2.5 | Success: CLI tests stable in CI | Log + mark complete_

  - [x] 7.3 Optional smoke: generated sqlite project `manage.py check`
    - Files: `tests/integration/test_generated_check.py` (pytest marker `slow` or `integration`)
    - Generate → uv sync → manage.py check when feasible
    - Purpose: Catch broken templates
    - _Leverage: tmp_path, uv_
    - _Requirements: design testing E2E_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Integration engineer | Task: Add marked integration smoke for sqlite no-docker generated project | Restrictions: Skip cleanly if uv/network constraints demand; do not require Docker | _Requirements: design E2E | Success: Marker test documented in README or pyproject | Log + mark complete_

  - [x] 7.4 Update package README usage section for `django-octave new`
    - Files: `README.md` (generator repo)
    - Document install and example interactive/flag invocations (still early but accurate)
    - Purpose: User-facing entry docs
    - _Leverage: product README style_
    - _Requirements: 7.1_
    - _Prompt: Implement the task for spec project-kickstart, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Add concise usage for django-octave new to the package README | Restrictions: No Spec Workflow content | _Requirements: 7.1 | Success: README shows real CLI examples matching flags | Log + mark complete_
