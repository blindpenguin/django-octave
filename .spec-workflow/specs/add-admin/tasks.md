# Tasks Document

- [x] 1.0 Admin generator core
  - [x] 1.1 Heuristics + `build_admin_class` + `write_admin`
    - Files: `src/django_octave/api_parts/admin_gen.py`, `tests/api_parts/test_admin_gen.py`
    - Resolve list_display/search/list_filter/list_select_related/date_hierarchy; overrides + validation; upsert `{Model}Admin` with `@admin.register`
    - Purpose: Generate refined ModelAdmin from inspected fields
    - _Leverage: inspect_model_fields, searchable_names, upsert_class, design heuristics_
    - _Requirements: 2.1–2.5, 3.1–3.4, 4.1–4.2_
    - _Prompt: Implement the task for spec add-admin, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django admin engineer | Task: Implement admin_gen heuristics and write_admin with unit tests | Restrictions: No CLI yet; no themes/format_html; leave api_sync add-model stub unchanged | Success: Unit tests cover defaults, timestamps, FK select_related, overrides, force/refuse | Log with log-implementation then mark [x] in tasks.md_

- [x] 2.0 CLI
  - [x] 2.1 `add-admin` command + prompts
    - Files: `src/django_octave/commands/add_admin.py`, `src/django_octave/prompts/add_admin.py`, `src/django_octave/cli.py`
    - Dual UX; `--list-display`, `--search`, `--filter`, `--ordering`, `--no-date-hierarchy`, `--force`, `--path`
    - Purpose: User-facing command
    - _Leverage: add_serializer / add_viewset command patterns_
    - _Requirements: 1.1–1.6_
    - _Prompt: Implement the task for spec add-admin, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI developer | Task: Wire add-admin Typer command | Restrictions: Thin command; logic in admin_gen | Success: Listed in --help; flag mode writes admin.py | Log + mark complete_

- [x] 3.0 Docs and tests
  - [x] 3.1 README for add-admin
    - Files: `README.md`
    - Document heuristics summary and override flags
    - Purpose: Discoverability
    - _Requirements: 5.1_
    - _Prompt: Implement the task for spec add-admin, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Document add-admin in README | Restrictions: MDX-safe; no admin themes | Success: Examples match CLI | Log + mark complete_

  - [x] 3.2 Integration CliRunner matrices
    - Files: `tests/commands/test_add_admin.py`
    - Create/refuse/force; overrides; bad field; missing model; date_hierarchy / select_related smoke
    - Purpose: End-to-end confidence
    - _Requirements: 5.2_
    - _Prompt: Implement the task for spec add-admin, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA | Task: Integration tests for add-admin | Restrictions: Keep reasonably fast | Success: All cases pass; full pytest green | Log + mark complete_
