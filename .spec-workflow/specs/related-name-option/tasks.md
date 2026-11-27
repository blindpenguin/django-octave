# Tasks Document

- [x] 1.0 The proof first, then the parser and codegen
  - [x] 1.1 E2E that reproduces the failure on the current code
    - Files: `tests/e2e/test_related_names.py` (new), `tests/e2e/related_cases.py` (new, the case table shared with the unit tests)
    - Opt-in (`OCTAVE_E2E=1`). Generate a project, then for each case run `add-model` in its own app and `manage.py check`: fk+fk to `users.User`, m2m+m2m, o2o+o2o, fk+o2o, a self-relation declared twice, one explicit `related_name=` plus one unnamed, and the roadmap example (`owner` and `assignee`). After `check`, run `makemigrations --check --dry-run` is NOT used (the project has no migrations for the new apps); instead run `makemigrations <app>` and `migrate` on SQLite to prove the models are usable. Run it now and record which cases fail on the current code (expected: all clash cases fail with `fields.E304`/`E305`; the explicit case fails because the option is unknown)
    - Purpose: Evidence before the change; reused as the after-proof
    - _Leverage: `tests/e2e/helpers.py` (`build_project`, `cli`, `run`), the structure of `tests/e2e/test_owner_scoping.py`_
    - _Requirements: 3.1, 3.2, 3.3_
    - _Prompt: Implement the task for spec related-name-option, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA automation engineer | Task: Write the opt-in e2e per design.md 'End-to-End Testing' and run it against the current code | Restrictions: Never runs by default; tmp dirs only; do not change generator code in this task | Success: The cases run end to end and the failures on the current code are logged by name; log-implementation then mark [x] in tasks.md_

  - [x] 1.2 Parser: `related_name=` option
    - Files: `src/django_octave/fields/parser.py`, `tests/fields/test_parser.py`
    - Add `FieldSpec.related_name: str | None = None` (last attribute). Add the `related_name` branch in `parse_field` (relation types only, message in the style of `to=`/`on_delete=`), `_validate_related_name` (`+` or `^[A-Za-z_][A-Za-z0-9_]{0,63}$`, not a keyword, not ending in `_`, no `__`), and the duplicate-explicit-name check in `parse_fields` naming both fields
    - Purpose: Accept and validate the option; nothing is emitted yet
    - _Leverage: the existing option loop, `FieldParseError`, `keyword`_
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 6.1_
    - _Prompt: Implement the task for spec related-name-option, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python engineer | Task: Implement the parser changes per design.md 'fields/parser.py (extended)' | Restrictions: Allow-list only (no escaping); every declaration valid today parses to the same FieldSpec; fully annotated; do not touch codegen yet | Success: Tests cover valid identifiers and `+` on fk/o2o/m2m, rejection on every other type, a parametrized invalid table (keyword, hyphen, `%`, `%(class)s`, trailing `_`, `__`, empty, 65 chars, `x", y="`), duplicates, and unchanged results for existing declarations; log + mark [x]_

  - [x] 1.3 Codegen: emit `related_name`
    - Files: `src/django_octave/fields/codegen.py`, `tests/fields/test_codegen.py`, `tests/inspect/` (a case in the existing model inspector tests)
    - In the relation branch of `field_source` add `related_name="<value>"` after `on_delete`. Add inspector tests proving a model with `related_name` still reports the same fields and relations
    - Purpose: The option reaches the generated model
    - _Leverage: `field_source`, `inspect/model_fields.py`_
    - _Requirements: 1.1, 1.2, 1.6, 4.1, 6.1_
    - _Prompt: Implement the task for spec related-name-option, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python engineer | Task: Emit the argument per design.md 'fields/codegen.py (extended)' | Restrictions: Output for specs without related_name is byte-identical; the value is only emitted as a quoted literal; do not reformat unrelated test lines (use targeted edits, not ruff format on whole drifted files) | Success: Tests: position after on_delete for fk/o2o and for m2m (no on_delete), `+`, absent when None, existing outputs unchanged, the generated line parses with `ast`; inspector unaffected; log + mark [x]_

- [x] 2.0 Resolving clashes and wiring
  - [x] 2.1 `fields/related.py`
    - Files: `src/django_octave/fields/related.py` (new), `tests/fields/test_related.py` (new)
    - Implement `ResolvedFields` and `resolve_related_names(fields, *, app, model)` per the design: normalise targets (bare `Model` becomes `<app>.Model`), group fk/o2o/m2m together by target among fields without an explicit name, name each member of a group of two or more `<pascal_to_snake(model)>_<field>` cleaned of `__` and a trailing `_`, suffix `_2`, `_3` on collision with an explicit or earlier generated name, leave everything else untouched
    - Purpose: The "just works" behavior for the common case
    - _Leverage: `naming.pascal_to_snake`, `FieldSpec`, `RELATION_TYPES`_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 2.7_
    - _Prompt: Implement the task for spec related-name-option, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python engineer | Task: Implement resolve_related_names per design.md 'fields/related.py (new)' | Restrictions: Pure function (no files, no Django); deterministic; never changes explicit names; returns new FieldSpec objects (frozen), same order; fully annotated | Success: Table-driven tests: two fk; fk+m2m; fk+o2o; bare vs app-qualified target; self-relation twice; single relation untouched; different targets untouched; explicit name untouched and not counted; one explicit plus one unnamed untouched; three unnamed; collision with an explicit name gets a suffix; CamelCase and acronym models; field names that would give `__` or trailing `_`; same input gives same output; log + mark [x]_

  - [x] 2.2 Wire into `add-model`
    - Files: `src/django_octave/commands/add_model.py`, `tests/commands/test_add_model.py`, `tests/commands/test_option_probe.py` (one payload case)
    - After `parse_fields`, call `resolve_related_names(fields, app=app, model=model)`; pass `resolved.fields` to `write_model` and `sync_api_stubs`; add the `## related_name` section to the summary when `resolved.generated` is not empty. Keep the order inside `handle_errors()`
    - Purpose: The user-facing behavior
    - _Leverage: `commands/_common.py` (`handle_errors`, `console`), the existing summary in `add_model.py`_
    - _Requirements: 1.6, 2.1, 2.5, 4.1, 6.2_
    - _Prompt: Implement the task for spec related-name-option, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python/Typer engineer | Task: Wire the resolver and the summary section per design.md 'commands/add_model.py (extended)' | Restrictions: No change for commands/models without a clash; invalid or duplicate names exit 1 and leave models.py unchanged; do not edit existing tests | Success: Tests: the motivating command writes distinct names and prints the section; `--force` re-run gives identical bytes; explicit names are written as given with no section; serializer/viewset/admin stubs equal those of the equivalent model without clashes; invalid option exits 1 with models.py unchanged; probe passes; log + mark [x]_

  - [x] 2.3 Admin `list_display` without many-to-many fields
    - Files: `src/django_octave/models_gen/api_sync.py`, `tests/models_gen/test_api_sync.py` (new or extend the existing admin stub tests)
    - In `_admin_class` build `display_names` from the fields whose `type_key` is not `m2m`; keep `id`, the order of the other fields and the timestamp fields. Write the tests first and run them on the unmodified code: an m2m field must be absent (fails before), other output unchanged (passes before), an m2m-only model keeps `id` and the timestamps, a model without m2m is byte-identical
    - Purpose: Requirement 3.2 cannot hold without it; also fixes the documented `tags:m2m:to=Tag` example
    - _Leverage: `FieldSpec.type_key`, the m2m skip in `admin_gen.default_list_display`_
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
    - _Prompt: Implement the task for spec related-name-option, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python engineer | Task: Exclude m2m fields from the admin list_display built by add-model per design.md 'models_gen/api_sync.py (extended)' | Restrictions: Test first on the unmodified code; no change to the serializer, viewset or search_fields; output for models without m2m is byte-identical; do not touch add-admin | Success: Tests pass after the change and the m2m-absence test failed before it; ruff clean; log + mark [x]_

- [x] 3.0 End to end, docs and close-out
  - [x] 3.1 Make the e2e pass and drop the workaround
    - Files: `tests/e2e/test_related_names.py`, `tests/e2e/test_owner_scoping.py`
    - Re-run the new e2e from 1.1 against the finished code; it must pass for every case, including the m2m ones (`single_m2m`, `m2m_m2m`, `fk_m2m`). In `test_owner_scoping.py` delete the hand patch of `assignee` (the `re.sub` block and its comment) and the `import re` if it becomes unused, so the owner/assignee model is used exactly as generated
    - Purpose: Prove the requirement on real generated projects
    - _Leverage: results recorded in 1.1_
    - _Requirements: 3.1, 3.2, 3.3, 4.2, 4.3, 7.2_
    - _Prompt: Implement the task for spec related-name-option, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA automation engineer | Task: Run the e2e from 1.1 on the finished code and remove the manual related_name patch in the owner-scoping e2e | Restrictions: Do not weaken any scenario; report any failure faithfully | Success: `OCTAVE_E2E=1 uv run pytest -m e2e` passes, including owner scoping without the patch; log + mark [x]_

  - [x] 3.2 Docs, roadmap and audit notes
    - Files: `docs/commands/add-model.md`, `docs/roadmap.md`, `docs/code-audit-2026-11-23.md` (untracked notes)
    - Document `related_name=` in the field DSL section (rule, example with `+`, the automatic-name behavior and the `<model>_<field>` scheme, the cross-app caveat). Mark roadmap item 11 done. Update the side finding in the audit notes. Add one line about m2m fields no longer being listed in the admin
    - Purpose: Users can discover the option and the default
    - _Leverage: existing sections of `docs/commands/add-model.md`_
    - _Requirements: 5.1, 5.2_
    - _Prompt: Implement the task for spec related-name-option, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Update the docs per requirement 5 | Restrictions: Match the existing docs style; state only what the code does; the docs build must stay green | Success: Docs describe option, automatic names and the caveat; roadmap and audit updated; log + mark [x]_

  - [x] 3.3 Final verification
    - Files: none (no production code)
    - Run `uv run ruff check`, `uv run pytest`, `OCTAVE_E2E=1 uv run pytest -m e2e`, and the docs build used by CI. Regenerate the dry-command-layer reference project (`gen_reference.py`) with the final code and `diff -r -x .ruff_cache` it against a tree generated from `HEAD`'s parent state (the reference from before this spec) to prove byte-identical output when no clash exists
    - Purpose: Prove requirement 6
    - _Leverage: the reference-project script and tree from the previous spec (regenerate the baseline from `git stash`-free means: a worktree of the commit before this spec)_
    - _Requirements: 6.1, 6.2, 6.3_
    - _Prompt: Implement the task for spec related-name-option, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA/release engineer | Task: Run the full verification per design.md 'Testing Strategy' and record the results | Restrictions: Do not edit tests to get green; do not commit; report any diff or failure faithfully | Success: All checks pass, the tree diff is empty, results in the log; log + mark [x]_
