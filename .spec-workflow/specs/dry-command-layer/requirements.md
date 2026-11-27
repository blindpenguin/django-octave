# Requirements Document

## Introduction

The CLI command layer (`src/django_octave/commands/`) repeats the same plumbing in every command: a hand-written `except (A, B, C, …)` tuple (16 of them), a private `Console(stderr=True)` per module (14 instances), and an identical "detect project → validate app → check `apps/<app>` → check `models.py` → check the model exists" block in `add-serializer`, `add-viewset`, `add-admin` and `add-test`. `cli.py` also imports 13 command modules by name. This spec removes that duplication **without changing any user-visible behavior or generated output**. It covers items 1, 2 and 5 of section 3 of `docs/code-audit-2026-11-23.md` (shared error base, command helper, auto-registration, dead code). The libcst URL patching (item 4), the large-module rework (item 6) and `.octave.toml` are separate specs.

## Alignment with Product Vision

django-octave is meant to stay small and predictable. A single error contract and a single target-resolution helper mean new `add-*` commands cost less to write and cannot forget a failure mode (the earlier all-or-nothing and injection fixes each had to be applied command by command).

## Requirements

### Requirement 1 — One error base for expected failures

**User Story:** As a maintainer, I want every expected, user-facing generator failure to derive from one base class, so that commands catch one type instead of maintaining their own tuples.

#### Acceptance Criteria

1. WHEN the package defines its domain exceptions THEN they SHALL derive from a new `OctaveError`, keeping their existing names and import paths.
2. IF an exception currently derives from `ValueError` or `FileExistsError` and callers (including tests) rely on that THEN it SHALL remain an instance of that type as well (multiple inheritance), so existing `pytest.raises(...)` checks still pass.
3. WHEN a command fails with an expected error THEN it SHALL print the message to stderr in red and exit with code 1, exactly as today.
4. WHEN an unexpected exception occurs (not an `OctaveError`, `FileNotFoundError` or other type caught today) THEN the command SHALL NOT swallow it more broadly than it does today.

### Requirement 2 — Shared command error handling

**User Story:** As a maintainer, I want one helper that turns `OctaveError` into "red message + exit 1", so that no command repeats the `try/except/Exit` block or creates its own stderr console.

#### Acceptance Criteria

1. WHEN a command body raises `OctaveError` (or the other error types caught today) THEN a shared context manager or decorator SHALL print it and raise `typer.Exit(code=1)`.
2. WHEN the refactor is complete THEN `commands/` SHALL contain at most one `Console(stderr=True)` definition, in the shared module.
3. WHEN a command previously caught a type not covered by `OctaveError` (for example `FileNotFoundError`, `NotADirectoryError`) THEN that type SHALL still produce the same message and exit code.

### Requirement 3 — One target-resolution helper

**User Story:** As a maintainer, I want one `resolve_target(app, model)` helper, so that the project/app/model checks are written once.

#### Acceptance Criteria

1. WHEN `add-serializer`, `add-viewset`, `add-admin` or `add-test` run THEN they SHALL obtain the project, app directory, validated names and models source from one shared helper.
2. WHEN the app directory, `models.py` or the model is missing THEN the error messages SHALL be byte-identical to today's, including the `Run: django-octave add …` hints.
3. WHEN a command needs only the app (no model) THEN the helper SHALL support that without checking the model.

### Requirement 4 — Auto-discovered command registration

**User Story:** As a maintainer, I want commands to register themselves from the `commands` package, so that adding a command does not require editing `cli.py`.

#### Acceptance Criteria

1. WHEN `django_octave.cli` is imported THEN every command module in `django_octave.commands` SHALL be imported by `pkgutil.iter_modules` (or equivalent) and attach its `@app.command`.
2. WHEN `django-octave --help` runs THEN the list of commands and their help text SHALL be identical to today's.
3. IF a command module fails to import THEN the error SHALL surface (not be hidden).

### Requirement 5 — Remove dead and redundant code

**User Story:** As a maintainer, I want the unreachable and duplicated branches listed in the audit removed, so that the code says what it does.

#### Acceptance Criteria

1. WHEN `django_patch.patch_urls` is simplified THEN the no-op `if not force and skip_register and include_register: pass` and the unused `force` parameter SHALL be removed, and all callers updated.
2. WHEN `naming.validate_app_name` is simplified THEN the unreachable second digit check SHALL be removed, with the accepted and rejected names unchanged (covered by a test).
3. WHEN `rendering/writer.py` is simplified THEN the unreachable `elif target.exists() and not target.is_dir()` branch SHALL be removed after confirming it is unreachable.
4. WHEN `fields/codegen.py` is simplified THEN the three identical `char`/`slug`/`email` `max_length` branches SHALL be merged with identical output.

### Requirement 6 — Behavior and output preserved

**User Story:** As a user of the generator, I want nothing to change, so that I can ignore this refactor.

#### Acceptance Criteria

1. WHEN the full test suite runs THEN it SHALL pass (218 tests at the time of the audit) with no test weakened; tests may be added or moved.
2. WHEN every `add-*` and `new` command runs against the same inputs as before THEN the generated files SHALL be byte-identical (checked by running the opt-in e2e suites, `OCTAVE_E2E=1`).
3. WHEN `tests/commands/test_option_probe.py` runs THEN it SHALL still discover every free-text option and pass.
4. WHEN `rollback_on_error` wraps a command THEN the all-or-nothing behavior SHALL be unchanged.

## Non-Functional Requirements

### Code Architecture and Modularity
- **Single Responsibility Principle**: shared command plumbing lives in one module (for example `commands/_common.py`); commands keep only their own logic.
- **Modular Design**: `OctaveError` lives in its own small module with no imports from generators, to avoid import cycles.
- **Dependency Management**: generator modules (`api_parts/`, `celery_gen/`, …) import `OctaveError`; `commands/` imports from generators, never the reverse.
- **Clear Interfaces**: `resolve_target` returns a small frozen dataclass, fully annotated.
- **Size**: the net change SHALL be a reduction of lines in `commands/` (audit estimate: 300–400).

### Performance
- No measurable change to CLI start-up time beyond module discovery (command modules are imported today anyway).

### Security
- The validation order in each command (name allow-lists before any file write) SHALL be preserved, because the option-probe test and the injection guards depend on it.

### Reliability
- No half-written files: commands that use `rollback_on_error` keep doing so, and the shared error handler runs outside the rollback scope as today.

### Usability
- Messages, exit codes, `--help` output and Markdown summaries are unchanged.
