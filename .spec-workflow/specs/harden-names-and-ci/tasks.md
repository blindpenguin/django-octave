# Tasks Document

- [x] 1.0 Safe project names (N1)
  - [x] 1.1 Name validator and the `new` / render guards
    - Files: `src/django_octave/safe_names.py` (new; was `naming.py`, moved to avoid an import cycle), `src/django_octave/prompts/new_project.py`, `src/django_octave/rendering/context.py`, `src/django_octave/commands/new.py`, `tests/naming/` (extend or add `test_project_name.py`), `tests/commands/test_new.py`
    - Add `PROJECT_NAME_RE`, `PROJECT_SLUG_RE`, `InvalidProjectNameError`, `is_safe_project_name`, `validate_project_name`, `is_safe_slug`. Call `validate_project_name` in `resolve_new_project_options` (map to `typer.BadParameter`) and in `ProjectContext.from_options` (inside `new`'s existing error handling, exit 1). Tests: accepted/rejected tables, the reproduced payload writes nothing, accepted awkward names generate files that parse (`ast`, `tomllib`, `json`)
    - Purpose: CLI text can never become code through the project name
    - _Leverage: `validate_app_name` pattern in `naming.py`, `normalize_slug`, existing `tests/commands/test_new.py` helpers_
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.6_
    - _Prompt: Implement the task for spec harden-names-and-ci, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python security engineer | Task: Add the project-name allow-list validator and wire it into new per design.md sections 1 and 2 | Restrictions: Allow-list only (no deny-list); show the rejected value with !r; slug/directory rules unchanged; avoid circular imports; no new dependencies | Success: Tests cover every accepted and rejected case incl. Unicode, control characters, RTL override, 64/65 chars; the payload `My" + __import__("os").getcwd() + "App` is refused and nothing is written; generated Python/TOML/JSON parse for awkward allowed names; log-implementation then mark [x] in tasks.md_

  - [x] 1.2 Safe derivation fallbacks and the frontend render guard
    - Files: `src/django_octave/frontend_gen/detect.py`, `src/django_octave/frontend_gen/setup.py`, `tests/frontend_gen/test_detect.py` (new or extend), `tests/frontend_gen/test_render.py`
    - `project_display_name`: use the README title only when safe, else the slug. `project_slug`: use the `pyproject.toml` name only when `is_safe_slug`, else `normalize_slug(root.name)`. `render_frontend`: raise `FrontendSetupError` for an unsafe name or slug
    - Purpose: `add-frontend` cannot be fed unsafe text through files the user edited
    - _Leverage: `project_display_name`, `project_slug`, `FrontendSetupError`, `normalize_slug`_
    - _Requirements: 1.4, 1.5_
    - _Prompt: Implement the task for spec harden-names-and-ci, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python engineer | Task: Add safe fallbacks for derived names and the render guard per design.md sections 2 and 3 | Restrictions: Never fail add-frontend because of an odd README title (fall back silently); safe titles keep working exactly as before; no behaviour change for valid projects | Success: Tests: README heading with quotes/braces → slug, safe heading → used, no README → slug, pyproject name with a quote → sanitised directory name, render_frontend raises for unsafe name/slug, and `add-frontend` on a project whose README title is hostile generates a package.json that parses as JSON; log + mark [x]_

- [x] 2.0 Registration password rules (N2)
  - [x] 2.1 Validate the password against the account's attributes
    - Files: `src/django_octave/templates/frontend_django/auth_api.py.j2`, `tests/frontend_gen/test_django_patch.py`, `tests/e2e/hardening_scenarios.py.tmpl`
    - Call `validate_password(attrs["password"], user=User(email=attrs["email"]))`, convert Django `ValidationError` to `serializers.ValidationError({"password": list(exc.messages)})`; keep the mismatch and duplicate-email shapes. First reproduce the weakness against a real generated project (register with `alice@example.com` / `alice@example`) and compare the weak-password error shape before and after. Add an e2e scenario: similar password → 400 with `password` key and no user created; strong password → 201
    - Purpose: The declared password policy is actually enforced
    - _Leverage: `render_auth_api`, existing scenario helpers in `tests/e2e/hardening_scenarios.py.tmpl`_
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
    - _Prompt: Implement the task for spec harden-names-and-ci, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django/DRF engineer | Task: Make registration use the user-aware password validation per design.md section 4 | Restrictions: Never save the helper User instance; existing mismatch/duplicate responses unchanged; template must stay valid for multitenancy and plain variants | Success: Unit tests assert the rendered module parses and contains the user-aware call; e2e scenario passes with OCTAVE_E2E=1 and fails on pre-change HEAD (git worktree, not stash); log + mark [x]_

- [x] 3.0 CI, release gate and pinned actions (G5)
  - [x] 3.1 Workflows, Dependabot and lint cleanliness
    - Files: `.github/workflows/ci.yml` (new), `.github/workflows/release.yml`, `.github/workflows/docs.yml`, `.github/dependabot.yml` (new), `src/django_octave/commands/add_frontend_crud.py` (import order via `ruff --fix` only), `tests/test_workflows.py` (new)
    - `ci.yml` with `test` and `e2e` jobs exactly as in design.md section 5; `release.yml` gets `verify: uses: ./.github/workflows/ci.yml` and `release` gains `needs: verify`; every `uses:` pinned to the resolved SHA with a version comment (re-resolve with `git ls-remote` before writing); Dependabot for `github-actions`; fix the remaining `ruff check` error. `tests/test_workflows.py`: YAML structure assertions from the design
    - Purpose: Nothing is published untested; no mutable action references
    - _Leverage: existing steps in `release.yml` and `docs.yml`, `scripts/` (unchanged)_
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_
    - _Prompt: Implement the task for spec harden-names-and-ci, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CI/CD and supply-chain security engineer | Task: Add the CI workflow, gate the release on it, pin all actions by SHA, add Dependabot, and add the workflow structure test | Restrictions: permissions {} at the top and contents: read per job; no secrets in ci.yml; no pull_request_target; do not change what release.yml publishes; do not add ruff format --check; do not use third-party lint images | Success: tests/test_workflows.py passes and fails if a tag-pinned action or missing needs is introduced; the exact CI commands (ruff check, pytest, mkdocs --strict, both e2e suites) pass locally; log + mark [x]_

- [x] 4.0 Docs, hygiene and wrap-up
  - [x] 4.1 Docs, `.gitignore`, audit and final verification
    - Files: `docs/concepts/security.md`, `docs/commands/new.md`, `docs/commands/add-frontend.md`, `.gitignore`, `docs/development/contributing.md` (CI note), `docs/code-audit-2026-11-23.md`
    - Document: the project-name rule and the add-frontend fallback; CORS origins for production; admin login not rate limited (django-axes / network restriction); refresh tokens not revocable (short lifetimes or token_blacklist); registration password check; what CI runs. Add `.claude/settings.local.json` to `.gitignore`. Record N1–N3 and G5 in the audit (new findings, fixed). Run the full verification: `uv run ruff check src tests`, `uv run pytest`, `mkdocs build --strict` (output to the scratchpad), `OCTAVE_E2E=1 … -m e2e`, `OCTAVE_E2E_DOCKER=1 …`
    - Purpose: Documented, verified, audit current
    - _Leverage: existing docs structure, the audit Status section_
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
    - _Prompt: Implement the task for spec harden-names-and-ci, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer and release engineer | Task: Write the docs, update .gitignore and the audit, run the full verification | Restrictions: Do not commit; keep docs short; do not reformat unrelated files | Success: Everything green, audit accurate, summary reported; log + mark [x]_
