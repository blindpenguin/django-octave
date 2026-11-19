# Tasks Document

- [x] 1.0 Naming, detection, and app context
  - [x] 1.1 App name validation and model-name derivation helpers
    - Files: `src/django_octave/naming.py` (or extend `rendering/context.py` carefully)
    - Valid `snake_case` identifier; reserved set (`core`, `users`, …); singular→PascalCase heuristic per design
    - Purpose: Shared pure helpers for `add`
    - _Leverage: `normalize_slug`, design Naming section_
    - _Requirements: 2.4, 3.5_
    - _Prompt: Implement the task for spec add-app, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer | Task: Implement app name validation and model name derivation with unit tests | Restrictions: No CLI yet; keep helpers pure | Success: Tests cover valid/invalid/reserved and plural heuristics | Mark [-]→log-implementation→[x]_

  - [x] 1.2 Project detection and multitenancy probe
    - Files: `src/django_octave/project/__init__.py`, `src/django_octave/project/detect.py`
    - Resolve project root from `--path`; require `apps/`, `config/settings/base.py`, `config/urls.py`; detect TenantAwareModel/middleware
    - Purpose: Safety gate for `add`
    - _Leverage: design Project detection_
    - _Requirements: 2.1, 2.2, 3.3_
    - _Prompt: Implement the task for spec add-app, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer | Task: Implement octave project detection and multitenancy probe with fixture-based tests | Restrictions: Do not patch files yet | Success: Detects valid kickstart trees; fails clearly otherwise | Log + mark complete_

  - [x] 1.3 Define `AppContext` builder
    - Files: `src/django_octave/rendering/app_context.py`
    - Build context from name + detected project (paths, model names, flags)
    - Purpose: Single Jinja/patch input object
    - _Leverage: design AppContext_
    - _Requirements: 3.*, 5.*_
    - _Prompt: Implement the task for spec add-app, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer | Task: Implement AppContext dataclass/builder from validated name + detection result | Restrictions: No filesystem writes | Success: Context fields match design | Log + mark complete_

- [x] 2.0 App templates and renderer
  - [x] 2.1 Jinja templates for domain app + API stubs
    - Files under `src/django_octave/templates/app/`: apps.py, models, admin, serializers, views, urls, services, migrations/__init__, __init__
    - TimeStamped vs TenantAware conditional; ModelViewSet + Spectacular + filterset_fields; router urls
    - Purpose: Generated app contents
    - _Leverage: kickstart core/users style; design template table_
    - _Requirements: 3.1–3.4, 5.1–5.5_
    - _Prompt: Implement the task for spec add-app, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django/DRF engineer | Task: Author app Jinja templates including API stubs and services placeholder | Restrictions: No settings/urls patching here | Success: Templates render with AppContext in a smoke test | Log + mark complete_

  - [x] 2.2 App writer (temp render → `apps/<name>`, force semantics)
    - Files: `src/django_octave/rendering/app_writer.py`, engine helper for app template root
    - Refuse existing without force; with force replace app dir; atomic move
    - Purpose: Safe filesystem write
    - _Leverage: `rendering/writer.py` patterns_
    - _Requirements: 2.3, 2.5_
    - _Prompt: Implement the task for spec add-app, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer | Task: Implement render_app writer with force/collision behavior | Restrictions: Do not patch INSTALLED_APPS/urls yet | Success: Unit tests for create and refuse-existing | Log + mark complete_

- [x] 3.0 Settings and URL patching
  - [x] 3.1 Idempotent INSTALLED_APPS patcher
    - Files: `src/django_octave/project/patch.py` (settings function)
    - Insert `apps.<name>` once into base settings list
    - Purpose: Auto-register app
    - _Leverage: design Patching settings_
    - _Requirements: 4.1, 4.3, NFR reliability_
    - _Prompt: Implement the task for spec add-app, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer | Task: Implement idempotent INSTALLED_APPS patch with tests on sample base.py text | Restrictions: Prefer text/ast-safe approach from design; no silent duplicates | Success: Insert once; second call no-op | Log + mark complete_

  - [x] 3.2 Idempotent config/urls.py include patcher
    - Files: `src/django_octave/project/patch.py` (urls function)
    - Ensure `include` import; append `api/<app>/` include once
    - Purpose: Mount API routes
    - _Leverage: design Patching urls_
    - _Requirements: 4.2, 4.3_
    - _Prompt: Implement the task for spec add-app, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer | Task: Implement idempotent urls.py patcher with tests | Restrictions: Do not break existing JWT/Spectacular routes | Success: Include added once; force re-run safe | Log + mark complete_

- [x] 4.0 CLI wiring and docs
  - [x] 4.1 `django-octave add` command + prompts
    - Files: `src/django_octave/commands/add.py`, `src/django_octave/prompts/add_app.py`, `cli.py` register
    - Wire detect → context → render → patch → next-steps (makemigrations/migrate)
    - Purpose: User-facing command
    - _Leverage: `commands/new.py`, prompts pattern_
    - _Requirements: 1.*, 2.*, 6.3_
    - _Prompt: Implement the task for spec add-app, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI developer | Task: Implement add command with dual UX and full pipeline orchestration | Restrictions: Keep logic in modules; command stays thin | Success: `django-octave add --help` works; flag mode adds app into generated project | Log + mark complete_

  - [x] 4.2 README usage for `add`
    - Files: `README.md`
    - Document interactive + flag examples, name rules, --path/--force
    - Purpose: Discoverability
    - _Leverage: existing README style_
    - _Requirements: 6.2_
    - _Prompt: Implement the task for spec add-app, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Add django-octave add section to README | Restrictions: No Spec Workflow content | Success: Examples match real flags | Log + mark complete_

- [x] 5.0 Tests
  - [x] 5.1 Unit tests for naming, detect, patch
    - Files: `tests/naming/`, `tests/project/`
    - Purpose: Fast coverage of helpers
    - _Leverage: pytest_
    - _Requirements: 6.1_
    - _Prompt: Implement the task for spec add-app, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA engineer | Task: Complete unit tests for naming/detect/patch modules | Restrictions: No network | Success: pytest green for these modules | Log + mark complete_

  - [x] 5.2 Integration: new → add → assert files and wiring
    - Files: `tests/commands/test_add.py`
    - Happy path, reserved names, exists without force, multitenancy model base, force idempotent patches
    - Purpose: End-to-end generator confidence
    - _Leverage: CliRunner, tmp_path, existing `new`_
    - _Requirements: 6.1, 3.3, 4.*, 5.*_
    - _Prompt: Implement the task for spec add-app, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA engineer | Task: Integration tests for add against projects created by new | Restrictions: Keep tests reasonably fast | Success: All add integration cases pass | Log + mark complete_
