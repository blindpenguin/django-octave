# Tasks Document

- [x] 1.0 libcst method upsert + action builder
  - [x] 1.1 `method_exists` + `upsert_method` in cst_util
    - Files: `src/django_octave/models_gen/cst_util.py`, `tests/models_gen/test_writer.py` (or new `tests/models_gen/test_cst_util.py`)
    - Detect method on class; append or force-replace FunctionDef; ensure imports via existing helpers
    - Purpose: Surgical injection into existing viewset classes
    - _Leverage: upsert_class, class_exists, libcst_
    - _Requirements: 2.1, 2.6_
    - _Prompt: Implement the task for spec add-action, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python libcst engineer | Task: Add method_exists and upsert_method with unit tests | Restrictions: Do not change upsert_class behavior; clear parse errors | Success: Tests cover append, refuse path (caller), force replace | Log with log-implementation then mark [x] in tasks.md_

  - [x] 1.2 `action_gen` builders + write_action
    - Files: `src/django_octave/api_parts/action_gen.py`, `tests/api_parts/test_action_gen.py`
    - ActionOptions; validate snake_case name + HTTP methods; build detail/list stubs; tag detect; permission/serializer kwargs; orchestrate upsert + imports
    - Purpose: Core generator for `@action` stubs
    - _Leverage: resolve_viewset_class_name, resolve_permission, class_exists, design stubs_
    - _Requirements: 2.1–2.6, 3.1–3.2, 4.1–4.4_
    - _Prompt: Implement the task for spec add-action, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DRF engineer | Task: Implement action_gen with detail/list stubs and unit tests | Restrictions: No CLI yet; detail stub must use get_object(); no urls.py edits | Success: Unit tests for build, tag detect, force/refuse, permission/serializer paths | Log + mark complete_

- [x] 2.0 CLI
  - [x] 2.1 `add-action` command + prompts
    - Files: `src/django_octave/commands/add_action.py`, `src/django_octave/prompts/add_action.py`, `src/django_octave/cli.py`
    - Dual UX; `--detail`/`--list`, `--methods`, `--url-path`, `--url-name`, `--permission`, `--serializer`, `--tag`, `--force`, `--path`
    - Purpose: User-facing command
    - _Leverage: add_permission / add_viewset command patterns_
    - _Requirements: 1.1–1.5_
    - _Prompt: Implement the task for spec add-action, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI developer | Task: Wire add-action Typer command | Restrictions: Thin command; logic stays in action_gen | Success: Listed in --help; flag mode injects action into views.py | Log + mark complete_

- [x] 3.0 Docs and tests
  - [x] 3.1 README for add-action
    - Files: `README.md`
    - Document flags and detail/list examples; note router auto-discovers actions
    - Purpose: Discoverability
    - _Requirements: 5.1_
    - _Prompt: Implement the task for spec add-action, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Document add-action in README | Restrictions: MDX-safe backticks | Success: Examples match CLI | Log + mark complete_

  - [x] 3.2 Integration CliRunner matrices
    - Files: `tests/commands/test_add_action.py`
    - Create detail/list; refuse/force; missing viewset; bad name; permission + serializer options
    - Purpose: End-to-end confidence
    - _Requirements: 5.2_
    - _Prompt: Implement the task for spec add-action, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA | Task: Integration tests for add-action | Restrictions: Keep reasonably fast | Success: All cases pass; full pytest green | Log + mark complete_
