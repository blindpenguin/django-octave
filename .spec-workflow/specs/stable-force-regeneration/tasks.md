# Tasks Document

- [x] 1.0 Failing tests first, then the in-place replace
  - [x] 1.1 Tests that show the problems on the current code
    - Files: `tests/models_gen/test_cst_util.py` (extend), `tests/models_gen/test_writer.py` (extend), `tests/commands/test_force_regeneration.py` (new)
    - Write the tests for Requirements 1 and 2 and run them against the unmodified code; record which fail. Unit: `upsert_class` with `force` on the first, a middle and the last of three classes (order and the bytes of the others unchanged); a comment above the replaced class is kept; one blank line above the replaced class stays one; anchor cases (class before the anchor stays, class after it moves before it, missing class inserted before it, no anchor appends); non-force with an existing class unchanged. `write_model` with `force` keeps the model's position. Commands: for `add-permission`, `add-serializer`, `add-viewset`, `add-admin` and `add-model`, a file with two classes and `--force` on the first changes only that class; the same command twice with `--force` changes nothing. Spacing: `add-permission` creates a file that equals the one after its first `--force`; appended tasks and appended fixture blocks have exactly two blank lines above them and `ruff check --preview --select E301,E302,E303,E305` is clean (skip with a reason if ruff is not importable)
    - Purpose: Evidence before the change; the same tests are the proof afterwards
    - _Leverage: `tests/commands/test_add_permission.py` and `test_add_model.py` project helpers, the existing cst_util tests_
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3_
    - _Prompt: Implement the task for spec stable-force-regeneration, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA engineer for generators | Task: Write the tests described in design.md 'Testing Strategy' and run them on the current code | Restrictions: Do not change production code; append to existing test files with targeted edits (do not reformat or rename existing helpers, check for name clashes first); each test asserts one behavior | Success: The failing set matches the findings (moved class on force, one-blank-line creation for permissions, tasks and conftest), the cases that already hold pass; the list of failing tests is in the log; log-implementation then mark [x] in tasks.md_

  - [x] 1.2 `replace_class_in_module` and `upsert_class`
    - Files: `src/django_octave/models_gen/cst_util.py`
    - Add `replace_class_in_module(module, class_name, addition, *, before=None)` as in design.md: replace at the old index with the old class's `leading_lines` on the first new statement; move before the anchor only when the old class is after it; append or insert before the anchor, with `_with_blank_leading`, when the class is missing. Change the `exists and force` branch of `upsert_class` to parse once and call it. Keep imports, reading and writing, the non-force path, `ensure_class_before` and the error messages unchanged. Remove `_RemoveClass` from `upsert_class` only if nothing else needs it there (`write_model` is handled in 2.1)
    - Purpose: `--force` stops moving classes for every command that uses `upsert_class`
    - _Leverage: `_top_level_class_index`, `_with_blank_leading`, `ModelWriteError`_
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.3_
    - _Prompt: Implement the task for spec stable-force-regeneration, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python engineer comfortable with libcst | Task: Implement replace_class_in_module and use it in upsert_class per design.md | Restrictions: libcst only (no string slicing); no file I/O in the new function; the non-force behavior and error messages must not change; fully annotated | Success: The unit and command tests from 1.1 for upsert_class users pass, the suite is green, ruff clean; log + mark [x]_

- [x] 2.0 The other replace site and the spacing
  - [x] 2.1 `write_model` uses the same routine
    - Files: `src/django_octave/models_gen/writer.py`
    - Replace the remove-then-append block with `replace_class_in_module(module, model_name, class_module.body)` after `_ensure_imports`; drop the now unused `_RemoveClass` use and the hand-written `leading_lines` block in this function (keep `_RemoveClass` itself if something else still imports it, otherwise delete it). `format_written_python` still runs afterwards
    - Purpose: models.py keeps its class order on `add-model --force`; one routine for both sites
    - _Leverage: `replace_class_in_module`_
    - _Requirements: 1.1, 1.4, 4.2_
    - _Prompt: Implement the task for spec stable-force-regeneration, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python engineer | Task: Switch write_model to the shared routine per design.md | Restrictions: Same behavior for a model that does not exist yet (appended with two blank lines); same errors; check `grep -rn _RemoveClass src tests` before removing anything | Success: The write_model and add-model tests from 1.1 pass, the suite is green; log + mark [x]_

  - [x] 2.2 Two blank lines when creating or appending
    - Files: `src/django_octave/api_parts/permission_gen.py`, `src/django_octave/celery_gen/task_gen.py`, `src/django_octave/api_parts/test_gen.py`
    - `write_permission`: when `permissions.py` does not exist, write only the header and continue into the existing `upsert_class` call (no `header + class_src` write). `_upsert_task_in_module`: append with `text.rstrip() + "\n\n\n" + stub`. `ensure_test_fixtures`: append the fixture blocks with two blank lines above the first decorator (`source.rstrip() + "\n\n"` plus the block without its leading newline), for both the base block and the tenant block; nothing is appended when the fixtures exist
    - Purpose: Creating and regenerating agree; the created files pass E302
    - _Leverage: `_with_blank_leading` via `upsert_class`, the existing fixture blocks_
    - _Requirements: 2.1, 2.2, 2.3, 4.1_
    - _Prompt: Implement the task for spec stable-force-regeneration, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python engineer | Task: Apply the three spacing changes per design.md | Restrictions: Replacing an existing task or an existing permission class must not change (in place, as before); do not touch content other than blank lines; no change when the fixtures already exist | Success: The spacing tests from 1.1 pass (ruff E30x clean on created and appended files; `add-permission` created file equals its first `--force`), the suite is green; log + mark [x]_

- [x] 3.0 Docs and close-out
  - [x] 3.1 Roadmap, audit and final verification
    - Files: `docs/roadmap.md`, `docs/code-audit-2026-11-23.md` (untracked notes), no other production code
    - Mark roadmap item 13 done and correct its description (no growth per run; the real effects were the moved class and the missing blank line when creating), move it to the shipped table as in the previous specs; add the same correction to the audit notes. Run `uv run ruff check`, `uv run ruff format --check`, `uv run pytest`, the docs build (`uv run mkdocs build --strict`) and `OCTAVE_E2E=1 uv run pytest -m e2e` (wait for the exit line of the log). Generate the reference project from a worktree of `HEAD` and from the working tree, both with `uv run python` (ruff on PATH), and `diff -r -x .ruff_cache`: the only differences must be added blank lines in `permissions.py`, `tasks.py` and `tests/conftest.py`
    - Purpose: Prove requirements 3 and 4
    - _Leverage: `gen_reference.py` from the scratchpad of the earlier specs (regenerate it if the scratchpad is gone)_
    - _Requirements: 3.1, 3.2, 4.1, 4.2, 4.3_
    - _Prompt: Implement the task for spec stable-force-regeneration, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA/release engineer | Task: Correct the records and run the full verification per design.md 'Testing Strategy' | Restrictions: Do not edit tests to get green; do not commit; read the e2e log only after its exit line; report any unexpected diff faithfully | Success: All checks pass, the tree diff shows only the expected blank-line additions, results in the log; log + mark [x]_
