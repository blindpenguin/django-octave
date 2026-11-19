# Tasks Document

- [x] 1.0 Field DSL and naming helpers
  - [x] 1.1 Add libcst dependency
    - Files: `pyproject.toml`, `uv.lock`
    - `uv add libcst`
    - Purpose: Robust models.py editing
    - _Leverage: design Implementation Notes_
    - _Requirements: NFR architecture_
    - _Prompt: Implement the task for spec add-model, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python packaging | Task: Add libcst via uv | Restrictions: No feature code yet | Success: libcst importable in the project env | Log + mark complete_

  - [x] 1.2 Parse `--field` DSL into `FieldSpec`
    - Files: `src/django_octave/fields/__init__.py`, `src/django_octave/fields/parser.py`
    - Allowlisted types/options; errors for bad tokens; reserved field names
    - Purpose: Safe field input
    - _Leverage: design Field DSL_
    - _Requirements: 3.1–3.5_
    - _Prompt: Implement the task for spec add-model, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer | Task: Implement FieldSpec + parser with unit tests for happy/error cases | Restrictions: No codegen yet | Success: Parser tests cover types and options | Log + mark complete_

  - [x] 1.3 Field codegen + model/plural naming helpers
    - Files: `src/django_octave/fields/codegen.py`, extend `naming.py` as needed
    - Map FieldSpec → Django field source; PascalCase validation; snake + plural URL segment
    - Purpose: Pure generation helpers
    - _Leverage: design codegen table_
    - _Requirements: 3.*, 4.3, 5.4_
    - _Prompt: Implement the task for spec add-model, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer | Task: Implement field source codegen and model naming/plural helpers with tests | Restrictions: No filesystem writes | Success: Snippets match allowlisted Django fields | Log + mark complete_

- [x] 2.0 models.py writer
  - [x] 2.1 Append/replace model class with libcst
    - Files: `src/django_octave/models_gen/writer.py` (or `src/django_octave/models/writer.py`)
    - Ensure imports; append class; `--force` replaces existing class; refuse without force
    - Purpose: Persist model definition
    - _Leverage: libcst, design Writing models.py_
    - _Requirements: 2.4, 4.1–4.4_
    - _Prompt: Implement the task for spec add-model, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python libcst developer | Task: Implement models.py insert/replace with TimeStamped/TenantAware bases | Restrictions: Fail clearly on unparseable files | Success: Unit tests append and force-replace | Log + mark complete_

- [x] 3.0 API stub sync
  - [x] 3.1 Sync serializer, admin, viewset, router for the new model
    - Files: `src/django_octave/models_gen/api_sync.py`
    - Create missing stub files or update existing; idempotent; force regenerates that model’s stubs only
    - Purpose: Keep API usable after add-model
    - _Leverage: add-app templates patterns_
    - _Requirements: 5.1–5.5_
    - _Prompt: Implement the task for spec add-model, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django/DRF engineer | Task: Implement API sync for serializer/admin/views/urls | Restrictions: Do not delete unrelated models’ stubs when detectable | Success: Tests show router + serializer fields updated | Log + mark complete_

- [x] 4.0 CLI and docs
  - [x] 4.1 `django-octave add-model` command + prompts
    - Files: `src/django_octave/commands/add_model.py`, `src/django_octave/prompts/add_model.py`, `cli.py`
    - Orchestrate detect → parse fields → write model → api sync → next steps
    - Purpose: User-facing command
    - _Leverage: add command patterns_
    - _Requirements: 1.*, 2.1–2.3, 6.1_
    - _Prompt: Implement the task for spec add-model, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI developer | Task: Wire add-model Typer command with dual UX | Restrictions: Thin command; logic in modules | Success: Help works; flag mode adds model into app from add | Log + mark complete_

  - [x] 4.2 README documentation for add-model
    - Files: `README.md`
    - Field syntax table/examples; default field behavior
    - Purpose: Discoverability
    - _Leverage: existing README_
    - _Requirements: 6.2_
    - _Prompt: Implement the task for spec add-model, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Document add-model in README | Restrictions: No Spec Workflow content | Success: Examples match CLI | Log + mark complete_

- [x] 5.0 Tests
  - [x] 5.1 Unit tests for parser, codegen, models writer
    - Files: `tests/fields/`, `tests/models_gen/`
    - Purpose: Fast coverage
    - _Requirements: 6.3_
    - _Prompt: Implement the task for spec add-model, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA | Task: Complete unit tests for field/model writer modules | Restrictions: No network | Success: pytest green | Log + mark complete_

  - [x] 5.2 Integration: new → add → add-model matrices
    - Files: `tests/commands/test_add_model.py`
    - Happy path, default field, bad field, duplicate, force, multitenancy base
    - Purpose: End-to-end confidence
    - _Leverage: CliRunner_
    - _Requirements: 6.3_
    - _Prompt: Implement the task for spec add-model, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA | Task: Integration tests for add-model | Restrictions: Keep reasonably fast | Success: All cases pass | Log + mark complete_
