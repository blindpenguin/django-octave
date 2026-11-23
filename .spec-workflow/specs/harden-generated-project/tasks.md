# Tasks Document

- [x] 1.0 Settings, throttling and tenant model
  - [x] 1.1 Prod host guard and admin-only API docs
    - Files: `src/django_octave/templates/project/config/settings/prod.py.j2`, `src/django_octave/templates/project/.env.example.j2`, `tests/rendering/test_render_project.py`
    - In `prod.py`: raise `ImproperlyConfigured` when `DJANGO_ALLOWED_HOSTS` is unset/empty or `ALLOWED_HOSTS` contains `*`; override `SPECTACULAR_SETTINGS` with `SERVE_PERMISSIONS=[IsAdminUser]` and `SERVE_AUTHENTICATION=[SessionAuthentication]`. `.env.example`: comment that the host list must be changed for production. Render tests for all of it
    - Purpose: Fail fast on host config; hide the API surface in production
    - _Leverage: existing secret-key guard in `prod.py`, `SPECTACULAR_SETTINGS` in `base.py`_
    - _Requirements: 5.1, 5.2, 6.1, 6.2, 6.3, 6.4, 6.5_
    - _Prompt: Implement the task for spec harden-generated-project, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django security engineer | Task: Add the ALLOWED_HOSTS guard and admin-only spectacular overrides to prod.py.j2 as in design.md section 4 | Restrictions: local settings must not change; error messages name DJANGO_ALLOWED_HOSTS and say what to set; no new dependencies | Success: Render tests assert the guards and overrides; every rendered .py parses; log-implementation then mark [x] in tasks.md_

  - [x] 1.2 Auth throttle, `NUM_PROXIES` and token URLs
    - Files: `src/django_octave/templates/project/apps/core/throttling.py.j2` (new), `src/django_octave/templates/project/config/urls.py.j2`, `src/django_octave/templates/project/config/settings/base.py.j2`, `tests/rendering/test_render_project.py`
    - `AuthRateThrottle(AnonRateThrottle)` with scope `auth`; rate `"auth": "10/min"` and `NUM_PROXIES = env.int("DJANGO_NUM_PROXIES", default=0)` in `base.py`; token obtain and refresh paths use `as_view(throttle_classes=[AuthRateThrottle])`. Always generated (not multitenancy-only)
    - Purpose: Stricter limit for credential guessing, correct client identification behind a proxy
    - _Leverage: existing `DEFAULT_THROTTLE_RATES` block, `env` in `base.py`_
    - _Requirements: 3.1, 3.3, 3.4_
    - _Prompt: Implement the task for spec harden-generated-project, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DRF engineer | Task: Add the auth throttle, NUM_PROXIES setting and throttled token URLs per design.md sections 1 and 2 | Restrictions: Keep the stock simplejwt view imports in urls.py so patch_urls keeps working; other endpoints' throttling unchanged; default NUM_PROXIES must be 0 | Success: Render tests assert throttling.py exists in MT and non-MT projects, urls pass throttle_classes, settings contain the rate and NUM_PROXIES; run `tests/frontend_gen` to prove patching still works; log + mark [x]_

  - [x] 1.3 Collision-proof `related_name`
    - Files: `src/django_octave/templates/project/apps/core/models.py.j2`, `tests/rendering/test_render_project.py`
    - `related_name="%(app_label)s_%(class)s_set"` on `TenantAwareModel.tenant`
    - Purpose: Same-named tenant models in different apps no longer clash
    - _Leverage: existing tenant model template_
    - _Requirements: 7.1, 7.2_
    - _Prompt: Implement the task for spec harden-generated-project, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django engineer | Task: Change the related_name on TenantAwareModel.tenant | Restrictions: No other model changes; keep the abstract base abstract | Success: Render test asserts the string; the e2e check in task 4.1 covers the clash; log + mark [x]_

- [x] 2.0 Auth API module and user list
  - [x] 2.1 Move `AUTH_API_MODULE` to a template with throttles and tenant-scoped user list
    - Files: `src/django_octave/templates/frontend_django/auth_api.py.j2` (new), `src/django_octave/frontend_gen/django_patch.py`, `src/django_octave/frontend_gen/__init__.py` (if it re-exports), `tests/frontend_gen/test_django_patch.py`
    - Render the module with Jinja (`use_multitenancy` from `detect_project(root)`); `EmailTokenObtainPairView` and `RegisterView` get `throttle_classes = [AuthRateThrottle]`; with multitenancy `UserListView(TenantScopedMixin, ListAPIView)` filters `memberships__tenant=self.request.tenant`. Keep the "already has UserListView → leave alone unless `--force`" rule. Remove the string constant
    - Purpose: Close the cross-tenant email exposure and throttle login/register; make the module lintable
    - _Leverage: `write_auth_api`, `detect_project`, `TenantScopedMixin`, the Jinja environment settings used in `rendering/engine.py`_
    - _Requirements: 3.2, 3.5, 3.6, 4.1, 4.2, 4.3, 4.4_
    - _Prompt: Implement the task for spec harden-generated-project, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python/Django engineer | Task: Replace AUTH_API_MODULE with a Jinja template and the tenant-scoped user list per design.md section 3 | Restrictions: Do not change the fields exposed by the user list (id, email, label); non-multitenancy output must keep the current behaviour; do not break patch_urls; the template must be packaged (check pyproject includes it, as other templates are) | Success: Tests cover MT and non-MT rendering (ast.parse, mixin and filter present only in MT, throttles present), idempotent re-run, force regeneration, and that patch_urls still wires both views; log + mark [x]_

  - [x] 2.2 `DJANGO_NUM_PROXIES` for SPA projects
    - Files: `src/django_octave/frontend_gen/django_patch.py` (`build_frontend_env_block`), `tests/frontend_gen/test_django_patch.py`
    - Add `patch_env_proxies`: append `DJANGO_NUM_PROXIES=1` with an explanatory comment to `.env.example` unless the file already sets it (never overrides a value). _Deviation from design:_ not part of the marker block, because `patch_env_cors` only merges the existing `CORS_ALLOWED_ORIGINS` line and never adds the block when that line exists
    - Purpose: Auth throttling identifies real clients behind the SPA's nginx instead of sharing one bucket
    - _Leverage: `patch_env_cors`, `_ENV_MARKER_BEGIN/END`_
    - _Requirements: 3.1_
    - _Prompt: Implement the task for spec harden-generated-project, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Generator engineer | Task: Extend the managed .env.example block with DJANGO_NUM_PROXIES=1 | Restrictions: Do not touch values outside the marker block; re-running must not duplicate the line | Success: Tests for fresh, re-run and pre-existing .env.example; log + mark [x]_

- [x] 3.0 Docker and SPA container
  - [x] 3.1 Multi-stage Dockerfile with `collectstatic`
    - Files: `src/django_octave/templates/project/Dockerfile.j2`, `tests/rendering/test_render_project.py`
    - Stages `dev` (today's behaviour), `builder` (build tools, `uv sync --no-dev`, `--locked` when `uv.lock` exists), `runtime` last (no curl/compilers/uv, MariaDB runtime library only for MariaDB, `PATH` with the venv, non-root `app`, `collectstatic` as `app` with build-only variables on that single `RUN`, `CMD ["gunicorn", …]`)
    - Purpose: Secure, reproducible production image whose admin works
    - _Leverage: existing Dockerfile content for the `dev` stage, `is_mariadb` flag_
    - _Requirements: 1.1, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5_
    - _Prompt: Implement the task for spec harden-generated-project, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Container/Docker engineer | Task: Rewrite the Dockerfile template per design.md section 6 | Restrictions: Keep Docker files gated by use_docker; python_version/uv version pins stay; build-only SECRET_KEY must be on the RUN line, never in ENV; runtime must run as USER app; the last stage must be runtime | Success: Render tests assert stage order, flags, absence of curl/uv run in runtime, MariaDB library only in runtime for MariaDB; the real image build is verified in task 4.2; log + mark [x]_

  - [x] 3.2 Compose files, Celery services and generated docs
    - Files: `src/django_octave/templates/project/docker-compose.yml.j2`, `docker-compose.prod.yml.j2`, `src/django_octave/celery_gen/compose.py`, `src/django_octave/templates/project/README.md.j2`, `src/django_octave/rendering/summary.py`, `tests/rendering/test_render_project.py`, `tests/celery_gen/`
    - Dev compose and the injected Celery worker/beat use `build: {context: ., target: dev}`; prod compose drops `command:` (image `CMD`); README/next steps tell users to run `uv lock` and commit it, and to set `DJANGO_ALLOWED_HOSTS`
    - Purpose: The new image layout does not break dev or Celery, and users get the lock-file advice
    - _Leverage: `build_compose_services`, existing compose tests_
    - _Requirements: 2.3, 2.6, 6.5_
    - _Prompt: Implement the task for spec harden-generated-project, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Generator engineer | Task: Update compose templates, the Celery compose block and generated docs per design.md sections 7 and 9 | Restrictions: Do not change the SPA service build; keep injection markers and refuse-without-force behaviour; existing celery tests updated rather than deleted | Success: Tests assert target: dev in dev compose and both Celery services, no command in prod compose, README text; log + mark [x]_

  - [x] 3.3 SPA nginx security headers
    - Files: `src/django_octave/templates/frontend/nginx.conf.j2`, `tests/frontend_gen/test_render.py`
    - Server-level `add_header … always` for `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`; no `add_header` inside locations
    - Purpose: Baseline browser protections for the SPA container
    - _Leverage: existing nginx template_
    - _Requirements: 8.1, 8.3_
    - _Prompt: Implement the task for spec harden-generated-project, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Web infrastructure engineer | Task: Add the three security headers to the SPA nginx template | Restrictions: Do not change proxy or try_files behaviour; no CSP | Success: Render test asserts the headers and that no location defines add_header; `nginx -t` passes in the nginx:alpine image (manual check in 4.3); log + mark [x]_

- [x] 4.0 Proof and docs
  - [x] 4.1 E2E: prod-settings behaviour on a real generated project
    - Files: `tests/e2e/test_hardening.py` (new), `tests/e2e/tenancy_jwt_scenarios.py.tmpl` (add an autouse cache-clear fixture), `tests/e2e/hardening_scenarios.py.tmpl` (new)
    - Opt-in (`OCTAVE_E2E=1`). Generate non-MT and MT projects (MT with `add-frontend --register`), then run scenario files under `DJANGO_SETTINGS_MODULE=config.settings.prod` with documented env (secret ≥50 chars, `DJANGO_ALLOWED_HOSTS`, sqlite `DATABASE_URL`, `secure=True` requests): `check --deploy` has no errors; `collectstatic` succeeds; `/admin/login/` 200; schema anonymous 401/403 and logged-in admin 200; boot without hosts and with `*` fails; 11th token request in a minute → 429 + `Retry-After`; two same-named models in different apps pass `check`; MT user list shows only the current tenant's members and 403 without the header; non-MT user list unchanged
    - Purpose: Prove S2–S7 against real Django
    - _Leverage: `tests/e2e/test_multitenancy_jwt.py` fixtures and helpers_
    - _Requirements: 1.2, 3.1, 3.3, 4.1, 4.2, 5.2, 5.3, 6.1, 6.2, 7.2, 9.2_
    - _Prompt: Implement the task for spec harden-generated-project, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA automation engineer | Task: Write the opt-in e2e hardening suite | Restrictions: Never runs by default; use tmp dirs only; clear throttle cache between tests; verify at least one scenario fails against the pre-change templates (git worktree of HEAD, not stash) | Success: Suite passes with OCTAVE_E2E=1 and fails on pre-change HEAD for the relevant scenarios; log + mark [x]_

  - [x] 4.2 Docker image verification (opt-in)
    - Files: `tests/e2e/test_docker_image.py` (new)
    - Opt-in (`OCTAVE_E2E_DOCKER=1`, skip when `docker info` fails): build the default stage for SQLite, Postgres and MariaDB projects; assert `whoami` is `app`, `curl` and `gcc` absent, image `Env` has no `DJANGO_SECRET_KEY`, runtime has no `uv`; run the SQLite image with a real env and `GET /admin/login/` returns 200 with static assets; `docker build --target dev` succeeds
    - Purpose: Prove S5 and S9 against a real build, not just rendered text
    - _Leverage: the generation helpers from 4.1_
    - _Requirements: 1.1, 1.2, 2.4, 2.5, 9.3_
    - _Prompt: Implement the task for spec harden-generated-project, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DevOps QA engineer | Task: Write the opt-in Docker verification test and run it here | Restrictions: Remove images and containers it creates; unique tags; generous timeouts; skip cleanly without Docker | Success: Test passes locally with OCTAVE_E2E_DOCKER=1; any Dockerfile defect it finds is fixed in 3.1; log + mark [x]_

  - [x] 4.3 Docs, audit update and final check
    - Files: `docs/concepts/docker.md`, `docs/concepts/multitenancy.md`, `docs/development/contributing.md`, `docs/code-audit-2026-11-23.md`
    - Document: image stages and `--target dev`, `uv lock`, `collectstatic`, how an admin opens the API docs in prod, `DJANGO_ALLOWED_HOSTS`, `DJANGO_NUM_PROXIES`, auth rate limit and registration residual risk, token storage in `localStorage` and CSP recommendation, the SPA tenant-header known gap, `related_name` upgrade note, how to run both e2e suites. Run `uv run pytest`, ruff on touched files, `mkdocs build --strict`, both e2e suites, `nginx -t` via `nginx:alpine`. Update audit statuses S2–S9 and the Status section
    - Purpose: Documented, verified, audit current
    - _Leverage: existing docs structure, audit Status section_
    - _Requirements: 2.6, 3.6, 5.4, 6.5, 7.3, 8.2, 9.1, 9.4_
    - _Prompt: Implement the task for spec harden-generated-project, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer and release engineer | Task: Write the docs, run the full verification, update the audit | Restrictions: Do not commit; do not fix unrelated Ruff findings; mkdocs output goes to the scratchpad | Success: Everything green, audit statuses accurate, summary reported; log + mark [x]_
