# Requirements Document

## Introduction

Three findings from the code audit concern the generator itself, not the projects it emits:

- **G1 — `new --force` deletes the existing directory.** The help text says "Allow generating into a non-empty directory", but `render_project` runs `shutil.rmtree(target)` and then moves the new tree in. The user's own files are lost, and the operation is not atomic: a failure between the delete and the move leaves neither tree.
- **G2 — arbitrary Python from `default=`.** `fields/codegen.py::_default_expr` falls through to `return raw` for any type without a specific branch. Reproduced: `x:date:default=__import__('os').getcwd()` emits `x = models.DateField(default=__import__('os').getcwd())`. String defaults are escaped by hand, so an embedded newline breaks the literal.
- **G3 — keywords and API names as field names.** `class:char` generates `class = models.CharField(...)`, a `SyntaxError` in the output. Names such as `save` or `delete` would silently shadow Django model methods.

The generator runs on a developer's machine, so the risk is small, but all three are cheap to fix, and a generator should never turn untrusted-looking CLI text into executable code or delete a directory under a flag that sounds additive.

Decisions already made with the user: `--force` **overwrites template files and never deletes anything else**.

Out of scope: project-side hardening (separate spec `harden-generated-project`), new field types, and supporting date/datetime defaults (they are rejected, not interpreted).

## Alignment with Product Vision

The product is an opinionated generator that people run against real directories. It must be predictable (flags do what their help says), must emit valid code for every accepted input, and must reject input it cannot translate safely instead of passing it through.

## Requirements

### Requirement 1 — `new --force` never deletes

**User Story:** As a developer re-running `new --force` on a directory that already holds work, I want only the generated files to be overwritten, so that my own files survive.

#### Acceptance Criteria

1. WHEN the target directory exists and is non-empty AND `--force` is not given THEN the system SHALL refuse with the existing "use --force" message and write nothing.
2. WHEN `--force` is given AND the target exists THEN the system SHALL write each generated file into the target, overwriting files with the same path, AND SHALL NOT delete or modify any file that is not part of the generated tree.
3. WHEN the target exists AND is not a directory THEN the system SHALL fail with a clear "not a directory" error (this branch is currently unreachable).
4. IF any path the system would write is, or passes through, a symbolic link inside the target THEN the system SHALL refuse before writing anything and name the link; it SHALL NOT write through it.
5. WHEN generation (templates rendering) fails THEN the system SHALL leave the target directory untouched, as today (render to a temporary directory first).
6. WHEN `--force` overwrote existing files THEN the system SHALL tell the user how many files were overwritten.
7. WHEN the target does not exist or is empty THEN behaviour and output SHALL be unchanged.

### Requirement 2 — field defaults are validated, never executed

**User Story:** As a developer passing `default=` on a field, I want the value turned into a safe literal or rejected, so that generated models never contain code I did not write.

#### Acceptance Criteria

1. WHEN a default is given for `char`, `text`, `email`, `url` or `slug` THEN the system SHALL emit it as a correctly escaped string literal, including values containing quotes, backslashes, newlines or non-ASCII characters.
2. WHEN the default for `int` is not a valid integer, or for `decimal` is not a valid decimal number, or for `bool` is not one of the accepted true/false tokens THEN the system SHALL fail with a `FieldParseError` naming the field and value (no uncaught `ValueError`, no silent fallback to `False`).
3. WHEN the default for `uuid` is `uuid` or `uuid4` THEN the system SHALL emit `uuid.uuid4`; WHEN it is a valid UUID string THEN the system SHALL emit a UUID literal; otherwise it SHALL fail with a `FieldParseError`.
4. WHEN a default is given for `date`, `datetime`, `fk`, `o2o` or `m2m` THEN the system SHALL fail with a `FieldParseError` saying defaults are not supported for that type. Today these values are passed through (date/datetime) or ignored (relations).
5. WHEN any accepted default is emitted THEN the output SHALL contain only literals or the known `uuid.uuid4` reference; no other expression SHALL ever be copied from the CLI into source.
6. WHEN the `:` field syntax carries a value containing `:` (for example `default=12:30`) THEN the system SHALL either parse it correctly or fail with a clear message; it SHALL NOT misparse silently.

### Requirement 3 — field names are valid and non-shadowing

**User Story:** As a developer naming a field, I want names that would break the model rejected immediately, so that I do not get a syntax error or a model with a hidden bug.

#### Acceptance Criteria

1. WHEN a field name is a Python keyword THEN the system SHALL fail with a `FieldParseError` stating it is a keyword.
2. WHEN a field name matches a Django `Model` API member the generator would shadow (at least `save`, `delete`, `clean`, `full_clean`, `validate_unique`, `refresh_from_db`, `from_db`, `check`, `serializable_value`) THEN the system SHALL fail with a `FieldParseError`.
3. WHEN the name is already reserved (`id`, `pk`, `objects`, `all_objects`, …) THEN the existing error SHALL be unchanged.
4. WHEN a name is valid THEN behaviour SHALL be unchanged.

### Requirement 4 — regression safety and docs

**User Story:** As a maintainer, I want these behaviours pinned by tests and documented, so that they stay fixed.

#### Acceptance Criteria

1. WHEN tests run THEN they SHALL cover every acceptance criterion above, including a rendered-output assertion that a model generated from every supported default type passes `ast.parse`.
2. WHEN `--force` is documented THEN `docs/commands/new.md` and the CLI help SHALL state that files outside the generated tree are kept and generated files are overwritten.
3. WHEN field syntax is documented THEN `docs/commands/add-model.md` SHALL list which types accept `default=` and the accepted forms.

## Non-Functional Requirements

### Code Architecture and Modularity
- **Single Responsibility Principle**: validation of defaults and names lives in `fields/parser.py` (parse time); `fields/codegen.py` only formats already-validated values; tree merging lives in `rendering/writer.py`.
- **Modular Design**: one helper that converts a validated `FieldSpec` default into source; no per-type copies elsewhere.
- **Dependency Management**: standard library only.
- **Clear Interfaces**: `FieldSpec` keeps its fields; `FieldParseError` stays the single error type for field input.

### Performance
- Negligible; one pass over the template tree and one over the target for symlink checks.

### Security
- Fail closed: any default or name the generator cannot translate to a safe literal or identifier is rejected.
- No write follows a symlink inside the target.

### Reliability
- A render failure never modifies the target. A copy failure part-way may leave a partially updated target; the error SHALL say which file failed.

### Usability
- Error messages name the field and the offending value and say what is allowed.
