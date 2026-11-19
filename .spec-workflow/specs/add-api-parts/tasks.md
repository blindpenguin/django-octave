# Tasks Document

- [x] 1.0 Shared CST helpers and field inspection
  - [x] 1.1 Extract libcst upsert/import helpers
    - Files: `src/django_octave/models_gen/cst_util.py`, refactor `models_gen/api_sync.py`
    - Move `_upsert_class`, class-exists/remove, import ensure, router registration primitives into shared module; keep `api_sync` behavior unchanged
    - Purpose: One upsert path for add-model sync and API-part commands
    - _Leverage: existing `api_sync.py`, design Code Reuse_
    - _Requirements: 4.1_
    - _Prompt: Implement the task for spec add-api-parts, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python libcst developer | Task: Extract cst_util and refactor api_sync without behavior change | Restrictions: No CLI changes yet | Success: Existing add-model/api_sync tests still pass | Log + mark complete_

  - [x] 1.2 Model field inspector via libcst
    - Files: `src/django_octave/inspect/model_fields.py` (or `models_gen/inspect_fields.py`)
    - List concrete `models.*Field` assignment names; treat `id` always available; add `created_at`/`updated_at` when bases include TimeStamped/TenantAware; expose AST type heuristics for filterable/searchable fields
    - Purpose: Serializer/viewset defaults without Django runtime
    - _Leverage: design Field inspection_
    - _Requirements: 2.3, 2.6, 3.5–3.6_
    - _Prompt: Implement the task for spec add-api-parts, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python libcst developer | Task: Implement field inspector + heuristics with unit tests on sample models.py snippets | Restrictions: No Django import of target project | Success: Tests cover timestamp bases and Field AST types | Log + mark complete_

- [x] 2.0 Serializer generator
  - [x] 2.1 Build and upsert ModelSerializer
    - Files: `src/django_octave/api_parts/serializer_gen.py`
    - `SerializerOptions`; default fields = inspected + id (+ timestamps when applicable); `--fields` / `--read-only` validation; `--no-id`; create `serializers.py` if missing; upsert `<Model>Serializer`; ensure model import
    - Purpose: Dedicated serializer generation
    - _Leverage: cst_util, inspector, add stubs style_
    - _Requirements: 2.1–2.6, 4.2–4.3_
    - _Prompt: Implement the task for spec add-api-parts, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DRF engineer | Task: Implement serializer_gen with unit tests for options matrices | Restrictions: Thin on filesystem; clear ModelWriteError-style failures | Success: Generated Meta.fields/read_only_fields match options | Log + mark complete_

- [x] 3.0 Viewset generator
  - [x] 3.1 Build and upsert ModelViewSet + router
    - Files: `src/django_octave/api_parts/viewset_gen.py`
    - `ViewSetOptions`; permission allowlist; default filter/search/ordering from AST heuristics; spectacular tags; auto-create default serializer if missing; upsert viewset; ensure router.register
    - Purpose: Standalone viewset generation with coherent imports
    - _Leverage: serializer_gen, cst_util, existing router helper_
    - _Requirements: 3.1–3.8, 4.2–4.3_
    - _Prompt: Implement the task for spec add-api-parts, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DRF engineer | Task: Implement viewset_gen including auto-serializer and router ensure | Restrictions: Permission allowlist only | Success: Unit tests cover permission/filter/tag/auto-serializer paths | Log + mark complete_

- [x] 4.0 CLI and docs
  - [x] 4.1 `add-serializer` and `add-viewset` commands + prompts
    - Files: `src/django_octave/commands/add_serializer.py`, `commands/add_viewset.py`, prompts, `cli.py`
    - Dual UX (flags/TTY); detect project; validate app/model; `--force`; success summary; register both on Typer app
    - Purpose: User-facing commands
    - _Leverage: add-model command patterns_
    - _Requirements: 1.1–1.6_
    - _Prompt: Implement the task for spec add-api-parts, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI developer | Task: Wire both Typer commands with dual UX | Restrictions: Thin commands; logic in api_parts | Success: Both listed in --help; flag mode works against new→add→add-model project | Log + mark complete_

  - [x] 4.2 README documentation
    - Files: `README.md`
    - Document both commands with examples and main flags; MDX-safe backticks for paths
    - Purpose: Discoverability
    - _Leverage: existing README_
    - _Requirements: 5.1_
    - _Prompt: Implement the task for spec add-api-parts, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Document add-serializer and add-viewset in README | Restrictions: No Spec Workflow content | Success: Examples match CLI | Log + mark complete_

- [x] 5.0 Tests
  - [x] 5.1 Unit tests for inspector, serializer_gen, viewset_gen, cst_util
    - Files: `tests/inspect/`, `tests/api_parts/`, update `tests/models_gen/` if needed
    - Purpose: Fast coverage
    - _Requirements: 5.2_
    - _Prompt: Implement the task for spec add-api-parts, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA | Task: Complete unit tests for shared modules | Restrictions: No network | Success: pytest green for unit suite | Log + mark complete_

  - [x] 5.2 Integration: CliRunner matrices for both commands
    - Files: `tests/commands/test_add_serializer.py`, `tests/commands/test_add_viewset.py`
    - Happy path after `new`→`add`→`add-model`; field/permission validation; refuse without force; force replace; viewset auto-serializer; router registration; bad app/model
    - Purpose: End-to-end confidence
    - _Leverage: CliRunner_
    - _Requirements: 5.2_
    - _Prompt: Implement the task for spec add-api-parts, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA | Task: Integration tests for add-serializer and add-viewset | Restrictions: Keep reasonably fast | Success: All cases pass | Log + mark complete_
