# Tasks Document

- [x] 1.0 Router basename consistency
  - [x] 1.1 App template + context model_snake; rewrite ensure_router_registration
    - Files: `src/django_octave/templates/app/urls.py.j2`, `src/django_octave/rendering/app_context.py`, `src/django_octave/models_gen/cst_util.py`, tests
    - First-app register uses basename=model_snake; sync updates stale basename lines
    - Purpose: reverse() matches add-test
    - _Leverage: pascal_to_snake, pluralize, design registration table_
    - _Requirements: 1.1–1.4_
    - _Prompt: Implement the task for spec generator-polish, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django/DRF generator engineer | Task: Fix app urls template basename and ensure_router_registration rewrite | Restrictions: Keep "" path for starter route; do not break multi-model apps | Success: Unit/integration tests for basename + rewrite; Log with log-implementation then mark [x] in tasks.md_

- [x] 2.0 Factories and API smoke tests
  - [x] 2.1 Cross-app FK SubFactory emission
    - Files: `src/django_octave/api_parts/test_gen.py`, tests
    - Emit SubFactory for other apps’ factories; keep UserFactory special case
    - Purpose: RecipeIngredient-style factories work
    - _Leverage: factory_module_stem, resolve_related_app_and_model_
    - _Requirements: 2.1–2.4_
    - _Prompt: Implement the task for spec generator-polish, first run spec-workflow-guide to get the workflow guide then implement the task: Role: pytest/factory-boy engineer | Task: Wire cross-app SubFactory lines | Restrictions: No M2M factory fields; no hard Django runtime | Success: Unit test asserts SubFactory path for other_app.Model | Log + mark complete_

  - [x] 2.2 AllowAny-aware API test generation
    - Files: `src/django_octave/api_parts/test_gen.py`, `commands/add_test.py` if needed, tests
    - Detect AllowAny on ViewSet; generate anonymous-ok vs deny-auth tests
    - Purpose: Open viewsets do not fail pytest by default
    - _Leverage: design detect_viewset_allows_anonymous_
    - _Requirements: 3.1–3.4_
    - _Prompt: Implement the task for spec generator-polish, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA/generator engineer | Task: AllowAny-aware smoke test stubs | Restrictions: Default to auth-required if views unparseable | Success: Unit tests for both modes; Log + mark complete_

- [x] 3.0 Formatting + regression
  - [x] 3.1 Blank lines between classes + optional ruff format helper
    - Files: `src/django_octave/models_gen/writer.py`, `cst_util.py` upsert paths, small format helper, call sites, tests
    - Ensure spacing after append/replace; best-effort ruff format without hard dep
    - Purpose: Readable multi-model files
    - _Leverage: design spacing notes_
    - _Requirements: 4.1–4.4_
    - _Prompt: Implement the task for spec generator-polish, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python tooling engineer | Task: Fix class spacing and optional ruff format | Restrictions: Ruff optional; writers must guarantee blank lines alone | Success: Two write_model calls leave blank line; Log + mark complete_

  - [x] 3.2 Integration CliRunner coverage + docs touch
    - Files: `tests/commands/…`, `docs/commands/add-test.md` if needed
    - add→add-test reverse; cross-app factory; AllowAny path; full pytest green
    - Purpose: Lock benchmark fixes
    - _Requirements: 5.1–5.2_
    - _Prompt: Implement the task for spec generator-polish, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA | Task: Integration tests for polish fixes | Restrictions: Keep tests reasonably fast | Success: Suite green; Log + mark complete_
