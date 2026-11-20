# Tasks Document

- [x] 1.0 Relation field DSL and codegen
  - [x] 1.1 Extend FieldSpec parser for fk/o2o/m2m
    - Files: `src/django_octave/fields/parser.py`, tests under `tests/fields/`
    - Add types `fk`/`o2o`/`m2m`; require `to=`; optional `on_delete` for fk/o2o; validate tokens
    - Purpose: Safe relation declarations
    - _Leverage: existing FieldSpec/ALLOWED_TYPES_
    - _Requirements: 1.1–1.6_
    - _Prompt: Implement the task for spec related-serializers, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer | Task: Extend field parser for relations with unit tests | Restrictions: No models.py writes yet | Success: Parser tests cover happy/error cases for fk/o2o/m2m | Log + mark complete_

  - [x] 1.2 Codegen ForeignKey / OneToOne / ManyToMany snippets
    - Files: `src/django_octave/fields/codegen.py`, tests
    - Map FieldSpec → Django field source; on_delete mapping; m2m blank default; set_null implies null
    - Purpose: Persist relations via add-model writer
    - _Leverage: field_source, design Field DSL_
    - _Requirements: 1.1–1.3_
    - _Prompt: Implement the task for spec related-serializers, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer | Task: Implement relation field_source codegen with tests | Restrictions: No CLI changes | Success: Snippets match design examples | Log + mark complete_

- [x] 2.0 Inspection metadata for relations
  - [x] 2.1 Capture RelationInfo (kind + to) from AST
    - Files: `src/django_octave/inspect/model_fields.py`, `tests/inspect/`
    - Extend ModelFieldInfo with relations map; parse string/Name targets; filterable includes fk/o2o
    - Purpose: Serializer/viewset heuristics know relations
    - _Leverage: existing inspector_
    - _Requirements: 2.1–2.3_
    - _Prompt: Implement the task for spec related-serializers, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python libcst developer | Task: Extend field inspector with RelationInfo | Restrictions: No Django runtime | Success: Tests detect fk/o2o/m2m and to= targets | Log + mark complete_

- [x] 3.0 Serializer nesting
  - [x] 3.1 Nested options + slim NestedSerializer + parent field emission
    - Files: `src/django_octave/api_parts/serializer_gen.py`
    - NestedRef / SerializerOptions.nested; auto-create `{Model}NestedSerializer`; parent nested read_only; FK/O2O add `*_id` for writes when nested; M2M nested read-only
    - Purpose: Optional one-level nested read payloads
    - _Leverage: cst_util, inspector, design Serializer generation_
    - _Requirements: 3.1–3.3, 4.1–4.5_
    - _Prompt: Implement the task for spec related-serializers, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DRF engineer | Task: Implement nested serializer generation | Restrictions: Depth 1 only; no writable nested creates | Success: Unit tests for PK default and nested mode | Log + mark complete_

  - [x] 3.2 Wire `--nested` on add-serializer CLI
    - Files: `src/django_octave/commands/add_serializer.py`, prompts if needed
    - Repeatable `--nested`; pass into SerializerOptions
    - Purpose: User-facing nest control
    - _Leverage: add-serializer command patterns_
    - _Requirements: 4.*, 5.3_
    - _Prompt: Implement the task for spec related-serializers, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI developer | Task: Add --nested to add-serializer | Restrictions: Thin command | Success: Help lists --nested; flag reaches generator | Log + mark complete_

- [x] 4.0 Docs and tests
  - [x] 4.1 README relation DSL + nested examples
    - Files: `README.md`
    - Document fk/o2o/m2m syntax and `--nested`
    - Purpose: Discoverability
    - _Requirements: 5.1_
    - _Prompt: Implement the task for spec related-serializers, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Document relations and nesting in README | Restrictions: MDX-safe backticks | Success: Examples match CLI | Log + mark complete_

  - [x] 4.2 Integration CliRunner matrices
    - Files: `tests/commands/test_add_model.py` and/or `test_add_serializer.py`
    - Author+Post with fk; add-serializer --nested; bad to=/nest errors; force
    - Purpose: End-to-end confidence
    - _Requirements: 5.2_
    - _Prompt: Implement the task for spec related-serializers, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA | Task: Integration tests for relation DSL and nesting | Restrictions: Keep reasonably fast | Success: All cases pass | Log + mark complete_
