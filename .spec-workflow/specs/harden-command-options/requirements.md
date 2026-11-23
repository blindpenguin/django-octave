# Requirements Document

## Introduction

Audit finding **N4**: several `add-*` commands copy a free-text option into generated Python without validating it. Reproduced against a real project with payloads that parse:

| Option | Generated code | Runs when |
|--------|----------------|-----------|
| `add-permission --owner-attr` | `getattr(obj, "<value>", None)` in `has_object_permission` | every object-permission check |
| `add-viewset --tag` | `extend_schema(tags=["<value>"])` (six times per viewset) | `views.py` is imported |
| `add-action --url-path`, `--url-name` | `@action(url_path="<value>", url_name="<value>")` | `views.py` is imported |
| `add-action --tag` | `extend_schema(tags=["<value>"])` | `views.py` is imported |

With a payload that does **not** parse, `add-permission` writes a broken `permissions.py` and exits 0, and `add-viewset`/`add-action` crash with a traceback.

This is the same bug class as G2 (field defaults) and N1 (project name). The risk is small, since you type the option yourself, but each fix so far has been one option at a time, and N4 exists because the probe of the other commands was never done. This spec therefore fixes the five options **and** adds a guard that probes *every* free-text option of *every* command, so a new option cannot reintroduce the problem.

Two small, related items are included because they came out of the same security review:

- **Default access is undocumented.** Generated viewsets use `IsAuthenticated` with no ownership scoping, so in a non-multitenant project any logged-in user can read and change every row. That is a legitimate default for many admin-style apps, but it must be stated.
- **No dependency audit.** Nothing checks the generator's own dependencies for known vulnerabilities. `uv audit` (built into the pinned uv) reports none today.

Verified safe by the probe (no change needed, only a regression guard): `add-admin` list options, `add-action --permission/--serializer/--methods`, `add-task --crontab/--every/names`, `add-serializer --nested`, filter/search/ordering options, positional app/model/action/task/class names.

Out of scope: changing the default permission class, scoping generated viewsets by owner, locking generated projects, adding pagination.

## Alignment with Product Vision

A generator must never turn text on the command line into executable code, and must fail with a clear message, not a traceback or a half-written file, when it cannot honour an option. Secure defaults must also be *visible*: users should learn from the docs, not from an incident, that generated APIs are open to every authenticated user.

## Requirements

### Requirement 1 — free-text options are validated before they reach code generation

**User Story:** As a developer passing options to `add-*` commands, I want unsafe values refused with a clear message, so that generated files never contain code I did not write.

#### Acceptance Criteria

1. WHEN `add-viewset --tag` or `add-action --tag` receives a value THEN the system SHALL accept only 1–64 characters from letters, digits, space, `.`, `-` and `_`, starting with a letter or digit; otherwise it SHALL exit 1 with a one-line message naming the option, the rejected value (shown with `!r`) and the rule, and write nothing.
2. WHEN `add-permission --owner-attr` receives a value THEN the system SHALL accept only a valid Python identifier that is not a keyword; otherwise exit 1 as above.
3. WHEN `add-action --url-path` receives a value THEN the system SHALL accept only 1–64 characters from letters, digits, `-`, `_` and `/` (no leading or trailing `/`, no `//`), the characters Django routers and OpenAPI treat as a literal path segment; otherwise exit 1 as above.
4. WHEN `add-action --url-name` receives a value THEN the system SHALL accept only 1–64 characters from letters, digits, `-` and `_`, starting with a letter or digit; otherwise exit 1 as above.
5. WHEN a value is accepted THEN the generated code SHALL be byte-for-byte what the same value produced before this change (no behaviour change for valid input).
6. WHEN any of these checks fail THEN no file SHALL be created or modified, and the output SHALL NOT contain a traceback.
7. The validators SHALL live in one module (the existing leaf `safe_names.py`), each with its own error type derived from `ValueError`, and SHALL be applied where the options are first resolved (CLI/prompts layer) **and** where the code is generated (generator layer), so programmatic callers are protected too.

### Requirement 2 — generation failures are reported cleanly

**User Story:** As a developer, I want a clear error when the generator cannot update a file, so that I never see a stack trace or a broken file.

#### Acceptance Criteria

1. WHEN a CST/parse error occurs while inserting a generated class or method (for example the existing `Could not parse method source`) THEN the command SHALL exit 1 with a message naming the target file, and SHALL NOT print a traceback.
2. WHEN `add-permission` writes `permissions.py` THEN the system SHALL confirm the result parses as Python before it replaces the file; on failure it SHALL leave the existing file untouched and exit 1.
3. WHEN a command exits 1 for these reasons THEN the project tree SHALL be byte-for-byte unchanged.

### Requirement 3 — a guard probes every free-text option

**User Story:** As a maintainer, I want a test that tries to inject code through every option of every command, so that new options are covered automatically.

#### Acceptance Criteria

1. WHEN the test suite runs THEN a test SHALL discover every `str`-typed option of every registered command from the Typer/Click definition (excluding `--path`, which is a filesystem path), without a hand-maintained list of options.
2. WHEN each option is invoked with a parseable code-injection payload and with a non-parseable one THEN the command SHALL either exit non-zero **or** produce only files in which the payload is not executable (checked with `ast`: no call to the payload's function outside a string literal), AND the output SHALL NOT contain a traceback.
3. WHEN the probe finds an option it cannot supply required positional values for THEN the test SHALL fail with a message asking to extend the fixture table (so new commands cannot be skipped silently).
4. WHEN the guard runs against the code before this change THEN it SHALL fail for exactly the options in the table above (verified once in a throwaway worktree).
5. The guard SHALL be fast (no network, no `uv sync`), part of the default suite.

### Requirement 4 — default access is documented

**User Story:** As a developer evaluating the generator, I want to know who can read and change data by default, so that I can add ownership rules where I need them.

#### Acceptance Criteria

1. WHEN reading `docs/concepts/security.md` THEN a "Who can access what" section SHALL state: generated viewsets use `IsAuthenticated`; any authenticated user can list, read, create, update and delete every row of those models (except tenant-scoped models, where the tenant limits access); where `AllowAny` applies; how to restrict access (`add-permission --preset owner`, `--viewset`, per-action permissions, custom `get_queryset`); and that registration (when enabled) lets anyone create an account that then has this access.
2. WHEN reading the generated project's `README.md` THEN it SHALL contain a short pointer to that section.
3. WHEN reading `docs/commands/add-viewset.md` and `docs/commands/add-permission.md` THEN each SHALL link to the section.

### Requirement 5 — dependency audit

**User Story:** As a maintainer, I want known-vulnerable dependencies to be noticed, so that I can update them.

#### Acceptance Criteria

1. WHEN `uv.lock` or `pyproject.toml` changes in a pull request, and once a week, and on manual dispatch THEN a workflow SHALL run `uv audit` against the locked dependencies and fail on known vulnerabilities.
2. The audit workflow SHALL use the same conventions as the others: SHA-pinned actions with version comments, `permissions: {}` at the top and `contents: read` per job, no secrets, and SHALL be covered by `tests/test_workflows.py`.
3. The release gate (`ci.yml`) SHALL NOT depend on the audit, so an unrelated advisory cannot block a hotfix release.
4. WHEN reading `docs/concepts/security.md` THEN it SHALL recommend `uv lock` and `uv audit` for generated projects (the generator does not lock them), and `docs/development/contributing.md` SHALL describe the audit workflow.

## Non-Functional Requirements

### Code Architecture and Modularity
- **Single Responsibility Principle**: validators in `safe_names.py`; commands only call them; the probe test lives in its own module.
- **Modular Design**: one validator per rule; no per-option copies of the same regex.
- **Dependency Management**: no new Python dependencies (`uv audit` is part of the pinned uv).
- **Clear Interfaces**: new error types subclass `ValueError`, which every command already catches and turns into exit 1.

### Performance
- The probe test creates one scratch project (render only) and runs CLI commands in-process; target under 30 seconds.

### Security
- Allow-lists only (no deny-lists); the same value is checked at two layers; errors never echo raw control characters.

### Reliability
- Failed commands leave the project tree untouched; the guard prevents regressions as options are added.

### Usability
- Each rejection names the option, shows the value and states the rule in one line.
