# Tasks Document

- [x] 1.0 Test generator core
  - [x] 1.1 Factory builders + UserFactory + write factory files
    - Files: `src/django_octave/api_parts/test_gen.py`, `tests/api_parts/test_test_gen.py`
    - Map inspected fields to factory_boy attrs; per-model `tests/factories/<app>_<snake>.py`; ensure `UserFactory`; force/refuse
    - Purpose: Generate factories for models
    - _Leverage: inspect_model_fields, design field mapping_
    - _Requirements: 2.1–2.5_
    - _Prompt: Implement the task for spec add-test, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django/pytest engineer | Task: Implement factory generation in test_gen with unit tests | Restrictions: No CLI yet; omit M2M/file/JSON; no broken cross-app SubFactory without TODO | Success: Unit tests cover factory source and force/refuse | Log with log-implementation then mark [x] in tasks.md_

  - [x] 1.2 API/model test modules + conftest fixtures
    - Files: `src/django_octave/api_parts/test_gen.py` (extend), unit tests
    - Detect viewset → API tests with reverse basename; else model smoke; ensure api_client/auth_client/user fixtures; tenant skip when multitenancy+TenantAware
    - Purpose: Runnable pytest stubs
    - _Leverage: class_exists, pascal_to_snake, design stubs_
    - _Requirements: 3.1–3.4, 4.1–4.2_
    - _Prompt: Implement the task for spec add-test, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DRF/pytest engineer | Task: Generate API or model test modules and idempotent conftest fixtures | Restrictions: Omit flaky create if payload unclear; skip tenant cases clearly | Success: Unit tests for viewset vs model paths and fixture ensure | Log + mark complete_

- [x] 2.0 CLI
  - [x] 2.1 `add-test` command + prompts
    - Files: `src/django_octave/commands/add_test.py`, `src/django_octave/prompts/add_test.py`, `src/django_octave/cli.py`
    - Dual UX; `--path`, `--force`; orchestrate write_tests
    - Purpose: User-facing command
    - _Leverage: add_admin command patterns_
    - _Requirements: 1.1–1.6_
    - _Prompt: Implement the task for spec add-test, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI developer | Task: Wire add-test Typer command | Restrictions: Thin command; logic in test_gen | Success: Listed in --help; flag mode writes factory + tests | Log + mark complete_

- [x] 3.0 Docs and tests
  - [x] 3.1 README for add-test
    - Files: `README.md`
    - Document paths, fixtures, pytest command
    - Purpose: Discoverability
    - _Requirements: 5.1_
    - _Prompt: Implement the task for spec add-test, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Document add-test in README | Restrictions: MDX-safe | Success: Examples match CLI | Log + mark complete_

  - [x] 3.2 Integration CliRunner matrices
    - Files: `tests/commands/test_add_test.py`
    - With viewset; without viewset; refuse/force; missing model; ast.parse smoke on outputs
    - Purpose: End-to-end confidence
    - _Requirements: 5.2_
    - _Prompt: Implement the task for spec add-test, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA | Task: Integration tests for add-test | Restrictions: Keep reasonably fast; no mandatory full target pytest unless cheap | Success: All cases pass; full generator pytest green | Log + mark complete_
