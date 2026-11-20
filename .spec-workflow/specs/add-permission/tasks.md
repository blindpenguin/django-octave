# Tasks Document

- [x] 1.0 Permission generator core
  - [x] 1.1 Preset source builders + upsert into permissions.py
    - Files: `src/django_octave/api_parts/permission_gen.py`
    - Presets `owner`, `staff_or_read`, `auth_or_read`, `tenant_member`; create file header; upsert class; force/refuse
    - Purpose: Generate BasePermission subclasses
    - _Leverage: cst_util, design Presets_
    - _Requirements: 2.1–2.5_
    - _Prompt: Implement the task for spec add-permission, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DRF engineer | Task: Implement permission_gen presets and file upsert with unit tests | Restrictions: No CLI yet; fail closed on owner attr miss at runtime in generated code | Success: Unit tests cover each preset source and force behavior | Log + mark complete_

  - [x] 1.2 Optional viewset wiring
    - Files: `src/django_octave/api_parts/permission_gen.py` (extend)
    - Resolve `{Model}ViewSet`; replace or `--append` `permission_classes`; ensure imports
    - Purpose: One-step attach to viewset
    - _Leverage: class_exists, add_to_import_
    - _Requirements: 3.1–3.4_
    - _Prompt: Implement the task for spec add-permission, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python libcst/text engineer | Task: Wire permission onto viewset permission_classes | Restrictions: Clear error if viewset missing | Success: Unit tests replace and append paths | Log + mark complete_

- [x] 2.0 CLI and add-viewset integration
  - [x] 2.1 `add-permission` command + prompts
    - Files: `src/django_octave/commands/add_permission.py`, prompts, `cli.py`
    - Dual UX; `--preset`, `--owner-attr`, `--viewset`, `--append`, `--force`; gate tenant preset on multitenancy
    - Purpose: User-facing command
    - _Leverage: add-serializer command patterns_
    - _Requirements: 1.1–1.5_
    - _Prompt: Implement the task for spec add-permission, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI developer | Task: Wire add-permission Typer command | Restrictions: Thin command | Success: Listed in --help; flag mode creates permissions.py | Log + mark complete_

  - [x] 2.2 Extend add-viewset permission resolution
    - Files: `src/django_octave/api_parts/viewset_gen.py`, command if needed
    - Stock allowlist OR class in `apps.<app>.permissions`; update imports
    - Purpose: Custom permissions usable from add-viewset
    - _Leverage: design resolve_permission_
    - _Requirements: 4.1–4.3_
    - _Prompt: Implement the task for spec add-permission, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DRF engineer | Task: Resolve custom permissions in add-viewset | Restrictions: Keep stock behavior | Success: Tests for stock, local, and missing name | Log + mark complete_

- [x] 3.0 Docs and tests
  - [x] 3.1 README for add-permission
    - Files: `README.md`
    - Document presets, wiring, add-viewset custom permission
    - Purpose: Discoverability
    - _Requirements: 5.1_
    - _Prompt: Implement the task for spec add-permission, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Document add-permission in README | Restrictions: MDX-safe | Success: Examples match CLI | Log + mark complete_

  - [x] 3.2 Integration CliRunner matrices
    - Files: `tests/commands/test_add_permission.py`, update viewset tests
    - Create/refuse/force; presets; tenant gate; wire viewset; add-viewset custom permission
    - Purpose: End-to-end confidence
    - _Requirements: 5.2_
    - _Prompt: Implement the task for spec add-permission, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA | Task: Integration tests for add-permission | Restrictions: Keep reasonably fast | Success: All cases pass | Log + mark complete_
