# Requirements Document

## Introduction

Roadmap item 13 says that `--force` adds one extra blank line in front of the regenerated class on every run. Reproducing it on the current code (`b112ef9` plus the format chore) shows a different, larger problem. The blank-line claim does not hold: running any command with `--force` three times gives the same bytes after the first run. What does happen:

1. **`--force` moves the regenerated class to the end of the file.** Both places that replace a class remove it and append the new one: `upsert_class` (`models_gen/cst_util.py`, used by `add-permission`, `add-serializer`, `add-viewset`, `add-admin` and the stubs of `add-model`) and `write_model` (`models_gen/writer.py`). Forcing `IsOwner` in a file that has `IsOwner` and `IsStaff` yields `IsStaff`, `IsOwner`; forcing `PostViewSet` or `PostSerializer` or `Post` moves it behind `TagViewSet`, `TagSerializer` or `Tag`. In a version-controlled project the diff shows a moved class instead of a changed one.
2. **Three commands write top-level definitions with one blank line above them instead of two:** `add-permission` (the first class in a new `permissions.py`), `add-task` (every task it appends to `tasks.py`) and `add-test` (every fixture block it appends to `tests/conftest.py`). `ruff` reports E302 on them. For `permissions.py` the first `--force` then writes two blank lines, so a re-run with the same input shows a one-line diff. This is the only blank-line effect that is real: a spacing mistake on the creating path, not growth on every run.

This spec makes regenerating a class change only that class, in place, and makes the creating and the regenerating path agree on formatting. Other things that look like churn after a `--force` pass are intended and out of scope: `add-model` writes basic admin and viewset stubs and the explicit `add-admin` and `add-viewset` commands write richer ones, and `add-viewset --force` replaces the whole class, so a hand-added action goes with it.

## Alignment with Product Vision

Generated projects live in version control. A regenerate that touches only the regenerated class keeps diffs reviewable and makes `--force` safe to re-run, which the other generator work (all-or-nothing commands, `new --force` that never deletes) already aims for.

## Requirements

### Requirement 1 — A replaced class keeps its place

**User Story:** As a developer, I want `--force` to rewrite a class where it is, so that the diff shows the class changed and nothing else moved.

#### Acceptance Criteria

1. WHEN a command replaces an existing top-level class (`add-permission`, `add-serializer`, `add-viewset`, `add-admin`, `add-model` and the stubs `add-model` syncs) THEN the new class SHALL take the position of the old one, and every other statement, comment and blank line in the file SHALL stay byte-identical.
2. WHEN the replaced class had comments or blank lines directly above it THEN those lines SHALL be kept.
3. WHEN a class is replaced and the caller asks for it to come before an anchor class (nested serializers must precede the parent) THEN the class SHALL end up before the anchor: it SHALL stay where it is if it is already before the anchor, and be moved before it only if it is after.
4. WHEN the class does not exist yet THEN it SHALL be inserted exactly as today (appended, or before the anchor when one is given).
5. WHEN a command without `--force` finds the class already there THEN it SHALL behave as today (leave it, or move it before the anchor).

### Requirement 2 — Creating and regenerating agree on blank lines

**User Story:** As a developer, I want a file to look the same whether a command created it or regenerated it, so that the first `--force` does not show a formatting diff.

#### Acceptance Criteria

1. WHEN `add-permission`, `add-task` or `add-test` create a file or append to one THEN every top-level class, function or decorated fixture they add SHALL have exactly two blank lines above it (between the imports and the first one, and between consecutive ones), and `ruff check --preview --select E301,E302,E303,E305` SHALL report nothing on the result.
2. WHEN any of the generator commands runs with `--force` and the same arguments right after creating its output THEN the files SHALL be byte-identical to the created ones, except where the explicit command intentionally writes a richer class than the one `add-model` stubbed (`add-admin`, `add-viewset`).
3. WHEN the same command with the same arguments and `--force` runs twice THEN the second run SHALL change nothing.

### Requirement 3 — Corrected record

**User Story:** As a maintainer, I want the roadmap to say what was found, so that nobody chases the wrong bug.

#### Acceptance Criteria

1. WHEN this spec is implemented THEN roadmap item 13 SHALL be marked done and its description SHALL be corrected: no growth per run; the real effects were the moved class and the one-line creation difference.
2. WHEN the audit notes mention the blank-line churn THEN they SHALL carry the same correction.

### Requirement 4 — Nothing else changes

**User Story:** As a user, I want everything else to behave as before.

#### Acceptance Criteria

1. WHEN a command creates a file or class that does not exist yet, other than the blank-line fixes in Requirement 2.1, THEN the output SHALL be byte-identical to the current output. A reference project generated from `HEAD` and from the new code SHALL differ only by added blank lines in `permissions.py`, `tasks.py` and `tests/conftest.py`, and nowhere else.
2. WHEN the full test suite and the opt-in e2e suites run THEN they SHALL pass, with no existing test weakened.
3. WHEN a command fails part-way THEN it SHALL still leave the project unchanged (`rollback_on_error`), as today.

## Non-Functional Requirements

### Code Architecture and Modularity
- **Single Responsibility Principle**: one function decides where a class goes and replaces it; the commands and generators do not reorder anything themselves.
- **Modular Design**: `write_model` and `upsert_class` use the same replace-in-place routine, so the two code paths cannot drift again.
- **Clear Interfaces**: any new function is fully annotated and edits the syntax tree with libcst, as the surrounding code does (no string slicing).

### Performance
- No measurable cost: one pass over the module body.

### Security
- No new input reaches generated source. The class source is built exactly as today.

### Reliability
- A file that does not parse keeps failing with the same error naming the file. Replacing never leaves a file that fails to parse (checked by the existing `rollback_on_error` guard).

### Usability
- No new options and no new output. `--force` simply stops moving things.
