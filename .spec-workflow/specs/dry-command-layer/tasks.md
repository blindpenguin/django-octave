# Tasks Document

- [x] 1.0 Baselines and the shared pieces
  - [x] 1.1 Capture baselines
    - Files: `tests/commands/test_cli_help.py` (new), `tests/commands/snapshots/` (new, `--help` text for the root and every command)
    - Record the current `uv run pytest` result (expected 218 passed) and `ruff check` result. Add a test that compares the root `--help` and each command's `--help` (plain output, as in `8594cf2`) with committed snapshots taken on the current code, including command order. Generate one project with every `add-*` command into a scratch directory (outside the repo, scratchpad) with a small script and keep the tree for the final `diff -r`
    - Purpose: Evidence that nothing user-visible changes
    - _Leverage: `tests/commands/` Typer `CliRunner` patterns, the plain-help fix from `8594cf2`_
    - _Requirements: 4.2, 6.1, 6.2_
    - _Prompt: Implement the task for spec dry-command-layer, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA engineer for CLI tools | Task: Capture the before-state per design.md 'Testing Strategy': pytest/ruff baseline, `--help` snapshots with command order, and a reference generated tree | Restrictions: Do not change production code; snapshots come from the unmodified code; keep the reference tree outside the repo | Success: Snapshot test passes on current code; baseline numbers and the reference tree path are written in the implementation log; log-implementation then mark [x] in tasks.md_

  - [x] 1.2 `OctaveError` and attach it to existing exceptions
    - Files: `src/django_octave/errors.py` (new), every module found by `grep -rn "class .*Error" src/django_octave` (`naming.py`, `safe_names.py`, `rollback.py`, `tenancy.py`, `project/detect.py`, `models_gen/`, `api_parts/*_gen.py`, `celery_gen/`, `frontend_gen/`, `rendering/writer.py`), `tests/test_errors.py` (new)
    - Add `class OctaveError(Exception)` with no imports from the package. Add it as an extra first base of each domain exception, keeping the existing `ValueError`/`FileExistsError` base (for example `class InvalidAppNameError(OctaveError, ValueError)`). Names and import paths do not change. Add a test that walks the package, finds every exception class defined in `django_octave`, and asserts it is an `OctaveError` and still an instance of its previous built-in base (pin the previous bases in the test as a table)
    - Purpose: One base type without breaking any existing `except`/`pytest.raises`
    - _Leverage: the grep list above, `pkgutil.walk_packages` for the discovery test_
    - _Requirements: 1.1, 1.2_
    - _Prompt: Implement the task for spec dry-command-layer, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python engineer | Task: Introduce OctaveError per design.md 'errors.py' and attach it to all domain exceptions | Restrictions: Keep every existing name, module path and built-in base; no import cycles (errors.py imports nothing from django_octave); do not touch commands in this task; do not edit existing tests | Success: Full suite still 218+ passed, new test passes and fails if an exception loses its built-in base or lacks OctaveError; ruff clean; log + mark [x]_

  - [x] 1.3 `commands/_common.py`
    - Files: `src/django_octave/commands/_common.py` (new), `tests/commands/test_common.py` (new)
    - Add `err_console`, `console`, `handle_errors()` (context manager catching `OctaveError, ValueError, FileNotFoundError, FileExistsError, NotADirectoryError`, printing `[red]{exc}[/red]` to stderr, raising `typer.Exit(code=1) from exc`), the frozen `Target` dataclass and `resolve_target(path, app, model=None)` with the exact check order and message strings from `add_serializer.py`
    - Purpose: The single home of the repeated plumbing
    - _Leverage: `detect_project`, `validate_app_name`, `validate_model_name`, `model_exists`, the current messages in `add_serializer.py` lines 87-103_
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3_
    - _Prompt: Implement the task for spec dry-command-layer, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python/Typer engineer | Task: Implement _common.py per design.md 'commands/_common.py' | Restrictions: Copy messages byte-for-byte from the current commands; a RuntimeError must propagate; fully annotated; the module name starts with an underscore so discovery skips it | Success: Tests: handle_errors exit code 1 and stderr text for each caught type, RuntimeError passes through; resolve_target returns the expected Target, parametrized byte-exact messages for missing app, missing models.py, missing model, model=None skips the model check, invalid names raise before any file access; log + mark [x]_

- [ ] 2.0 Migrate the commands
  - [x] 2.1 Model-targeting commands use `resolve_target`
    - Files: `src/django_octave/commands/add_serializer.py`, `add_viewset.py`, `add_admin.py`, `add_test.py`
    - Replace each command's `try/except` tuple and the detect/validate/exists block with `with handle_errors():` and `resolve_target(...)`. Keep `validate_tag` before `resolve_target` and the `rollback_on_error` block inside in `add_viewset`. Use the shared consoles. Drop imports that become unused
    - Purpose: Remove the most duplicated block (four copies)
    - _Leverage: `commands/_common.py`, existing command tests, `tests/commands/test_option_probe.py`_
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 6.1, 6.3, 6.4_
    - _Prompt: Implement the task for spec dry-command-layer, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python/Typer engineer | Task: Migrate the four commands per design.md 'commands/add_serializer.py, add_viewset.py, add_admin.py, add_test.py' | Restrictions: No change to messages, order of validation, summaries or rollback scope; do not edit existing tests; no unrelated refactors | Success: Full suite and option probe pass unchanged, help snapshots identical, net lines removed; log + mark [x]_

  - [x] 2.2 Remaining commands use `handle_errors`
    - Files: `src/django_octave/commands/add.py`, `add_model.py`, `add_permission.py`, `add_action.py`, `add_task.py`, `add_celery.py`, `add_frontend.py`, `add_frontend_crud.py`, `new.py`
    - Replace each `except (…) as exc: err_console.print…; raise typer.Exit` with `handle_errors()` and use the shared consoles. Where a command handles an error in more than one place (`new.py`, `add_frontend.py`), keep the control flow and only swap the repeated print-and-exit. Commands that need only app resolution may use `resolve_target(path, app)`; do not force it where the flow differs
    - Purpose: One error path for every command
    - _Leverage: `commands/_common.py`_
    - _Requirements: 1.3, 1.4, 2.1, 2.2, 2.3, 6.1, 6.3, 6.4_
    - _Prompt: Implement the task for spec dry-command-layer, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python/Typer engineer | Task: Migrate the remaining commands per design.md | Restrictions: Same messages and exit codes; do not widen what is caught (a bug must still traceback); keep rollback_on_error inside handle_errors; no behavior changes in new/add-frontend flows; do not edit existing tests | Success: `grep -c "Console(stderr=True)" src/django_octave/commands/*.py` shows only `_common.py`; suite, option probe and help snapshots pass; log + mark [x]_

- [ ] 3.0 Registration and dead code
  - [x] 3.1 Auto-discover commands
    - Files: `src/django_octave/cli.py`, `tests/commands/test_cli_help.py`
    - Replace `_register_commands` with `pkgutil.iter_modules(commands.__path__)` and `importlib.import_module`, skipping names that start with `_`, with no try/except around the import. If `--help` order differs from the snapshot, fix the order explicitly (sort key or a pinned tuple) so the snapshot stays unchanged. Add a test that a new module dropped in `commands/` registers without editing `cli.py` (use a temporary package path via monkeypatch) and that an import error propagates
    - Purpose: Adding a command no longer touches `cli.py`
    - _Leverage: the snapshots from 1.1_
    - _Requirements: 4.1, 4.2, 4.3_
    - _Prompt: Implement the task for spec dry-command-layer, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python engineer | Task: Implement discovery per design.md 'cli.py' | Restrictions: Help text and command order must equal the snapshots; do not hide import errors; do not move `app` out of cli.py | Success: Snapshots unchanged and green, discovery tests pass, the 13 named imports are gone; log + mark [x]_

  - [x] 3.2 Remove dead code, each pinned first
    - Files: `src/django_octave/frontend_gen/django_patch.py`, `src/django_octave/naming.py`, `src/django_octave/rendering/writer.py`, `src/django_octave/fields/codegen.py`, plus tests in `tests/frontend_gen/`, `tests/test_naming.py`, `tests/rendering/`, `tests/fields/`
    - For each item first add a test that pins today's behavior (accepted and rejected app names including `project_1x`-style cases; "target is a file" in the writer; `max_length` output for `char`/`slug`/`email`; both `patch_urls` call paths), run it green on the old code, then remove: the no-op `if not force and skip_register and include_register: pass` and the unused `force` parameter of `patch_urls` (update both callers); the unreachable digit check in `validate_app_name`; the unreachable `elif target.exists() and not target.is_dir()` branch in `rendering/writer.py` (confirm first which earlier check covers it); merge the three identical `max_length` branches in `codegen.py`. If an item turns out to be reachable, leave it, and record why in the log
    - Purpose: Code that says what it does
    - _Leverage: the audit's item 5 list_
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.1_
    - _Prompt: Implement the task for spec dry-command-layer, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python engineer focused on safe refactoring | Task: Remove the four dead/redundant pieces per design.md 'Dead-code removals' | Restrictions: Test first, on unmodified code; output must be byte-identical; one logical commit-sized change per item; do not remove anything proven reachable | Success: Pinning tests green before and after each removal, suite green, ruff clean; log + mark [x]_

- [ ] 4.0 Verification and close-out
  - [x] 4.1 Final verification and audit status
    - Files: `docs/code-audit-2026-11-23.md` (untracked, notes only), no production code
    - Run `uv run ruff check`, `uv run pytest`, `OCTAVE_E2E=1 uv run pytest -m e2e` and once `OCTAVE_E2E_DOCKER=1` for the Docker e2e. Regenerate the reference project with the final code and `diff -r` it against the tree from 1.1 (expect no differences). Count lines removed in `commands/` against the baseline. Update section 3 status in the audit doc (items 1, 2, 5 done; 3 partly done earlier; 4, 6, 7 open)
    - Purpose: Prove requirement 6 and keep the audit current
    - _Leverage: baselines from 1.1_
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
    - _Prompt: Implement the task for spec dry-command-layer, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA/release engineer | Task: Run the full verification in design.md 'Testing Strategy' and record results | Restrictions: Do not weaken or edit tests to get green; report any tree diff or failure faithfully; do not commit (the user commits) | Success: All checks pass, tree diff is empty, line reduction and test counts are in the log, audit doc updated; log + mark [x]_
