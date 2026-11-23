# Tasks Document

- [x] 1.0 Field input hardening (G2, G3)
  - [x] 1.1 Validate field names and normalise defaults in the parser
    - Files: `src/django_octave/fields/parser.py`, `tests/fields/test_parser.py`
    - Reject Python keywords and `MODEL_API_NAMES` as field names. Add `_normalise_default(type_key, field_name, raw)` per the design table (char-like: any string; int; bool via `_parse_bool`; finite decimal; uuid token or canonical UUID; date/datetime/fk/o2o/m2m: error). Call it where `default=` is parsed. Add the `':' not supported` hint to the unknown-option error when it follows a `default=` segment
    - Purpose: Reject what cannot be turned into a safe literal or identifier, before any file is touched
    - _Leverage: `FieldParseError`, `_parse_bool`, `RESERVED_FIELD_NAMES`, existing `tests/fields/test_parser.py` style_
    - _Requirements: 2.2, 2.3, 2.4, 2.6, 3.1, 3.2, 3.3, 3.4_
    - _Prompt: Implement the task for spec harden-generator, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python engineer focused on input validation | Task: Add field-name validation and default normalisation to fields/parser.py as described in design.md sections 3 | Restrictions: Keep FieldParseError the only error type; do not change FieldSpec's shape; existing valid inputs (including documented `published:bool:default=false`) must behave exactly as before; stdlib only | Success: Parametrised tests cover every valid/invalid row of the design table, keywords and API names, the unchanged valid names, and the colon hint; log-implementation then mark [x] in tasks.md_

  - [x] 1.2 Make codegen format validated defaults only
    - Files: `src/django_octave/fields/codegen.py`, `tests/fields/test_codegen.py` (new or existing equivalent)
    - Rewrite `_default_expr` with one branch per type and no `return raw` fall-through: `json.dumps(raw, ensure_ascii=False)` for text types and decimal, `True`/`False`, `str(int(raw))`, `uuid.uuid4` / `uuid.UUID("…")`, and `ValueError` for anything else. Extend `needs_uuid_import` to any uuid field with a default
    - Purpose: Generated models can never contain an expression copied from the CLI
    - _Leverage: `field_source`, `needs_uuid_import`, `models_gen/writer.py::_ensure_imports`_
    - _Requirements: 2.1, 2.3, 2.5, 4.1_
    - _Prompt: Implement the task for spec harden-generator, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python code-generation engineer | Task: Make _default_expr literal-only per design.md section 4 and extend needs_uuid_import | Restrictions: No fall-through; output for already-supported inputs (bool/int/char/decimal) stays byte-identical except that string escaping now uses json.dumps; do not touch relation handling | Success: Tests assert escaped output for quotes, backslashes, newlines, non-ASCII and empty strings, `ast.parse` of every emitted line, the reproduced `__import__('os')` payload only ever appears inside a string literal, and ValueError for hand-built unsupported combinations; log + mark [x]_

  - [x] 1.3 Integration: add-model with every supported default
    - Files: `tests/commands/test_add_model.py` (extend)
    - Run `add-model` with one field of each default-capable type and assert `models.py` parses and imports `uuid` when needed. Run it with an invalid default and a keyword name and assert exit code 1, the message, and that no files changed
    - Purpose: Prove the CLI path end to end, including "nothing written on error"
    - _Leverage: existing helpers in `tests/commands/test_add_model.py`_
    - _Requirements: 2.1, 2.2, 2.4, 3.1, 4.1_
    - _Prompt: Implement the task for spec harden-generator, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA engineer | Task: Add CLI-level tests for defaults and field names | Restrictions: No network; follow test naming `test_<unit>_<condition>_<expected>`; use parametrize | Success: Tests fail without 1.1/1.2 and pass with them; log + mark [x]_

- [x] 2.0 `new --force` never deletes (G1)
  - [x] 2.1 Merge placement in the writer
    - Files: `src/django_octave/rendering/writer.py`, `tests/rendering/test_render_project.py`, `tests/rendering/test_render_force.py` (new)
    - Add `RenderReport`, `TargetSymlinkError`, `TargetWriteError`, `render_project_report`; keep `render_project -> Path` as a thin wrapper. `_check_target` (not-a-directory first, then non-empty without force), `_place` (move when target missing, else symlink check along every write path, then `copy2` file by file counting overwrites, wrapping `OSError`). Remove `shutil.rmtree`
    - Purpose: `--force` overwrites generated files and keeps everything else; fixes the nested-project bug for existing empty targets
    - _Leverage: existing render loop, `_should_skip`, `_destination_name`, `TargetExistsError`_
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_
    - _Prompt: Implement the task for spec harden-generator, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python filesystem engineer | Task: Implement the merge placement described in design.md section 1 | Restrictions: Never delete or modify files outside the generated tree; never write through a symlink; render must still happen in a temp dir; keep render_project's signature and return type; no new dependencies | Success: Tests cover foreign file survives, same-path file overwritten, count, refusal without force, existing-empty-dir regression (project at target, not target/slug), target is a file, symlinked dir and file on write paths (nothing written), unwritable destination message names the file, render failure leaves target untouched; log + mark [x]_

  - [x] 2.2 Wire `new`: report, errors, help text
    - Files: `src/django_octave/commands/new.py`, `tests/commands/test_new.py`
    - Use `render_project_report`; catch `(ValueError, NotADirectoryError)`; print `Overwrote N existing file(s); files outside the generated tree were kept.` when N > 0; update the `--force` help text. CLI tests for the overwrite note, a surviving custom file, and the symlink refusal (exit 1, message)
    - Purpose: Users see what `--force` did and get clean errors instead of tracebacks
    - _Leverage: `err_console`, existing `tests/commands/test_new.py` helpers_
    - _Requirements: 1.3, 1.4, 1.6, 4.1, 4.2_
    - _Prompt: Implement the task for spec harden-generator, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI engineer | Task: Wire the new writer API and messages into the `new` command | Restrictions: Do not change other options; keep exit codes (1 on error); the frontend/celery steps after render are untouched | Success: CLI tests pass; help text states generated files are overwritten and everything else is kept; log + mark [x]_

- [x] 3.0 Docs and verification
  - [x] 3.1 Update docs
    - Files: `docs/commands/new.md`, `docs/commands/add-model.md`
    - `new.md`: replace "Allow non-empty target directory" with the real semantics (overwrite generated files, keep others, refuse symlinks, reports count). `add-model.md`: table of which types accept `default=` and in what form; date/datetime/relations rejected; keyword and Django method names rejected; values cannot contain `:` (and the `default=a:unique` caveat)
    - Purpose: Documented behaviour matches the code
    - _Leverage: existing doc structure, `mkdocs.yml`_
    - _Requirements: 4.2, 4.3_
    - _Prompt: Implement the task for spec harden-generator, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Document the new --force semantics and default/field-name rules | Restrictions: Short; match existing style; no unrelated edits | Success: `uv run mkdocs build --strict` clean (output to the scratchpad dir); log + mark [x]_

  - [x] 3.2 Final check and manual verification
    - Files: none new
    - Run `uv run pytest`, `uv run ruff check` on touched files, `mkdocs build --strict`. Manually: generate a project, add a custom file, run `new --force` over it and confirm the file survives; run the reproduced payloads (`x:date:default=__import__('os').getcwd()`, `class:char`) and confirm both are rejected. Update `docs/code-audit-2026-11-23.md` statuses for G1, G2, G3 (and G4 if touched)
    - Purpose: Close the spec and keep the audit current
    - _Leverage: existing test suite, the audit doc's Status section_
    - _Requirements: All_
    - _Prompt: Implement the task for spec harden-generator, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Release engineer | Task: Run full verification, do the two manual checks, update the audit doc | Restrictions: Do not commit; do not fix unrelated Ruff findings | Success: Suite green, manual checks pass, audit doc updated, summary reported; log + mark [x]_
