# Tasks Document

- [x] 1.0 Probe first, then validate (N4)
  - [x] 1.1 The probe guard (written first, fails first)
    - Files: `tests/commands/test_option_probe.py` (new)
    - Discover every `click.Option` of type `STRING` (not `--path`) of every command via `typer.main.get_command(app)`; fixture project (`new`, `add blog`, `add-model blog Post`, `add-celery`) rendered once; positional-argument table with a loud failure for unknown arguments; five payloads with marker `octave-probe`; per probe assert no `Traceback`, tree equals the baseline when exit ≠ 0, no executable call to the marker in any `.py` when exit = 0; restore the baseline after each probe. Run it against the current code and record exactly which options fail (expect `add-permission --owner-attr`, `add-viewset --tag`, `add-action --url-path/--url-name/--tag`)
    - Purpose: Prove the problem and make sure no option can be missed again
    - _Leverage: `typer.main.get_command`, `CliRunner`, helpers in `tests/commands/test_add_model.py`_
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
    - _Prompt: Implement the task for spec harden-command-options, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Security-minded test engineer | Task: Write the discovery-based probe test per design.md section 4 and run it against the current code | Restrictions: No hand-maintained option list; no network or uv sync; the test must be fast (under ~30 s); a command with an unknown positional argument must fail the test with a message to extend the table, not skip; restore the project tree after every probe | Success: The test runs, fails for exactly the known options (list them in the log), passes for all others; log-implementation then mark [x] in tasks.md_

  - [x] 1.2 Validators for `--tag`, `--owner-attr`, `--url-path`, `--url-name`
    - Files: `src/django_octave/safe_names.py`, `src/django_octave/commands/add_viewset.py`, `add_action.py`, `add_permission.py`, `src/django_octave/api_parts/viewset_gen.py`, `action_gen.py`, `permission_gen.py`, `tests/naming/test_option_validators.py` (new), `tests/commands/` (extend per command)
    - Add `InvalidOptionError` and the four validators exactly as in design.md section 1. Call them first inside each command's existing `try` and at the top of `write_viewset`, `write_action`, `write_permission` (before any write). Valid values must give byte-identical output to before (golden comparison). Rejected values exit 1 with the one-line message and leave the tree unchanged
    - Purpose: Close the five injection points
    - _Leverage: `validate_project_name` pattern in `safe_names.py`, existing command error handling_
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_
    - _Prompt: Implement the task for spec harden-command-options, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python security engineer | Task: Add the four allow-list validators and wire them into commands and generators per design.md sections 1 and 2 | Restrictions: Allow-lists only; no behaviour change for valid input; keep safe_names.py dependency-free; error text shows the value with !r and states the rule; do not change option names or defaults | Success: Table tests for each validator (incl. keywords, leading/trailing/double slash, spaces in url-name, control characters, 64/65 chars, reproduced payloads); the probe guard from 1.1 now passes for all options; golden comparisons show unchanged output for valid values; log + mark [x]_

- [x] 2.0 Clean failures and rollback
  - [x] 2.1 Parse errors and `rollback_on_error`
    - Files: `src/django_octave/models_gen/cst_util.py`, `src/django_octave/rollback.py` (new), `src/django_octave/commands/add_viewset.py`, `add_action.py`, `add_permission.py`, `add_task.py`, `tests/models_gen/test_cst_util.py`, `tests/test_rollback.py` (new), `tests/commands/`
    - `upsert_class`: wrap the parse of the generated class in `ModelWriteError` naming the path; `upsert_method`: include the path in its message. Add `rollback_on_error(root)` (snapshot, restore on any exception, post-success `ast.parse` verification of changed `.py` files) and use it at the **command level over the project root** (excluding `.venv`, `node_modules`, `.git`, `__pycache__`) in `add-viewset`, `add-action`, `add-permission` and `add-task`. _Deviation from design (found by the probe guard in 1.1):_ `add-permission --viewset <unknown>` and `add-task --crontab <invalid>` also exit 1 after already modifying files, and the wiring step and the beat schedule live outside the app directory, so the rollback must wrap the whole command
    - Purpose: No traceback, no half-written file, tree unchanged on failure
    - _Leverage: `ModelWriteError`, existing command `except` clauses_
    - _Requirements: 2.1, 2.2, 2.3_
    - _Prompt: Implement the task for spec harden-command-options, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python engineer | Task: Implement clean parse errors and the generic rollback helper per design.md section 3 | Restrictions: The helper must not know about permissions or actions; ignore __pycache__ and .pyc; restore created, modified and deleted files; no new dependencies | Success: Unit tests: restore after exception for modified/created/deleted files, verification failure restores and raises, success keeps changes, __pycache__ ignored; cst_util raises ModelWriteError with the path for an unparsable generated class (no raw ParserSyntaxError); CLI tests show a failed command leaves the tree byte-identical; log + mark [x]_

- [x] 3.0 Access docs and dependency audit
  - [x] 3.1 "Who can access what" and README pointers
    - Files: `docs/concepts/security.md`, `src/django_octave/templates/project/README.md.j2`, `docs/commands/add-viewset.md`, `docs/commands/add-permission.md`, `tests/rendering/test_render_project.py`
    - Write the section per R4.1 (default `IsAuthenticated`, every authenticated user reads and changes every row outside tenant-scoped models, where `AllowAny` applies, how to restrict, registration implication); add the README sentence and the two links; also the `uv lock` / `uv audit` advice for generated projects (R5.4)
    - Purpose: Make the default visible
    - _Leverage: existing security page, `add-permission` presets documentation_
    - _Requirements: 4.1, 4.2, 4.3, 5.4_
    - _Prompt: Implement the task for spec harden-command-options, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer with a security focus | Task: Document default access and dependency auditing | Restrictions: Be accurate about what is and is not restricted (verify claims against a generated project, e.g. AllowAny only when requested, tenant scoping only with --multitenancy); keep it short; mkdocs strict must pass | Success: Docs build clean (output to scratchpad); a render test asserts the README pointer; claims verified against a real generated project; log + mark [x]_

  - [x] 3.2 `audit.yml`
    - Files: `.github/workflows/audit.yml` (new), `tests/test_workflows.py`, `docs/development/contributing.md`
    - Weekly cron, `pull_request` with `paths: [uv.lock, pyproject.toml]`, `workflow_dispatch`; one job running `uv audit --locked`; pinned actions with version comments; `permissions: {}` and `contents: read`; no secrets. Tests: triggers present, runs `uv audit`, not referenced by `ci.yml`/`release.yml`. Run `uv audit --locked` locally
    - Purpose: Notice vulnerable dependencies without blocking releases
    - _Leverage: pinned SHAs from `ci.yml`, structural tests in `tests/test_workflows.py`_
    - _Requirements: 5.1, 5.2, 5.3_
    - _Prompt: Implement the task for spec harden-command-options, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CI/CD and supply-chain engineer | Task: Add the audit workflow and its tests | Restrictions: Reuse the exact pinned SHAs already in ci.yml; do not add it to the release gate; no third-party audit actions or images | Success: tests/test_workflows.py passes (generic pin/permission checks cover the new file) and new tests assert triggers and the release is independent of audit; `uv audit --locked` passes locally; log + mark [x]_

- [x] 4.0 Verify and record
  - [x] 4.1 Full verification, before/after proof and audit update
    - Files: `docs/code-audit-2026-11-23.md`
    - Run CI's commands (`ruff check src tests`, `pytest`, `mkdocs build --strict`) and both e2e suites. In a throwaway worktree of `HEAD` copy the probe test and show it fails for the five options and passes on the working tree. Mark N4 fixed in the audit; update the status table; record that the probe guard covers all options
    - Purpose: Close the spec with evidence
    - _Leverage: the audit Status section, CI commands from `ci.yml`_
    - _Requirements: All_
    - _Prompt: Implement the task for spec harden-command-options, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Release engineer | Task: Run the full verification, the before/after worktree check, and update the audit | Restrictions: Do not commit; use git worktree (never git stash) for the before check and remove it afterwards; do not reformat unrelated files | Success: Everything green, before/after evidence reported, audit accurate; log + mark [x]_
