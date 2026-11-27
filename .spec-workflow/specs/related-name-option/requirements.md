# Requirements Document

## Introduction

A generated model with two relations to the same target does not pass Django's system check. Reproduce on the current code:

```bash
django-octave add-model notes Note --fields "title:char,owner:fk:to=users.User,assignee:fk:to=users.User"
uv run python manage.py check   # fields.E304: reverse accessor 'User.note_set' clashes
```

The field syntax `name:type[:options]` has no `related_name`, so the only fix today is editing the generated model by hand (the owner-scoping e2e test does exactly that). While proving this, the e2e found a second, independent bug on the same path: any model with a many-to-many field fails `manage.py check` with `admin.E109`, because `add-model` lists every field, m2m included, in the generated admin's `list_display`. Requirement 3.2 (two `m2m` fields pass the check) cannot hold without fixing it, so it is part of this spec (Requirement 7).

This spec adds a validated `related_name=` option and, when a model has several relations to one target and the user gave no name, generates a distinct name per field so the common case works without extra flags. It is roadmap item 11 and a side finding of the owner-scoping work in `docs/code-audit-2026-11-23.md`.

## Alignment with Product Vision

django-octave promises models that work as generated. A field combination that fails `manage.py check` breaks that promise, and it is a natural combination (owner and assignee, author and reviewer, parent and original). The generator should also keep its allow-list rule: every value that reaches generated source is validated first.

## Requirements

### Requirement 1 — Explicit `related_name=` option

**User Story:** As a developer, I want to name the reverse accessor of a relation, so that I control how I reach related rows or turn the reverse relation off.

#### Acceptance Criteria

1. WHEN a field is declared as `name:fk|o2o|m2m:to=Target:related_name=<value>` AND `<value>` is a Python identifier (ASCII letters, digits and `_`, not starting with a digit, not a keyword, at most 64 characters) THEN the generated field SHALL contain `related_name="<value>"`.
2. WHEN `<value>` is `+` THEN the generated field SHALL contain `related_name="+"` (no reverse accessor).
3. WHEN `related_name=` is used on a type other than `fk`, `o2o` or `m2m` THEN parsing SHALL fail with a message that names the option and the field type, like the existing `to=` and `on_delete=` messages.
4. IF `<value>` is empty, contains anything outside the allowed set, is a Python keyword, or contains `%` (no Django interpolation) THEN parsing SHALL fail with a message that shows the rule, and nothing SHALL be written.
5. IF two fields of one model declare the same explicit `related_name` (other than `+`) THEN parsing SHALL fail naming both fields.
6. WHEN the option is given THEN the value SHALL only ever be emitted as a quoted literal that passed the allow-list (no free text reaches generated source).

### Requirement 2 — Automatic distinct names when relations clash

**User Story:** As a developer, I want two relations to the same model to just work, so that I do not have to know about reverse accessors to declare `owner` and `assignee`.

#### Acceptance Criteria

1. WHEN a model's fields contain two or more relations (`fk`, `o2o` or `m2m`) to the same target AND at least two of them have no explicit `related_name` THEN the generator SHALL give each of those fields a distinct `related_name`, so that Django's system check passes.
2. WHEN targets are compared THEN a bare `Model` and `<this app>.Model` SHALL count as the same target, and a self-relation (a model pointing at itself more than once) SHALL be covered too.
3. WHEN a field has an explicit `related_name` THEN the generator SHALL NOT change it and SHALL NOT count it as a clash (a `+` field no longer competes for the default accessor).
4. WHEN a name is generated THEN it SHALL be a valid identifier, deterministic (the same input always gives the same name, so `--force` regeneration is stable), derived from the model and field names, and different from every other generated or explicit `related_name` in the model.
5. WHEN a name is generated THEN the command SHALL tell the user which `related_name` it chose for which field.
6. WHEN a model has at most one relation to each target THEN the generated source SHALL be byte-identical to today's (no `related_name` is added).
7. WHEN relations to different targets are declared THEN no name SHALL be generated for them.

### Requirement 3 — The motivating example passes Django's check

**User Story:** As a developer, I want the example from the roadmap to work unchanged, so that I can trust the generated model.

#### Acceptance Criteria

1. WHEN `add-model notes Note --fields "title:char,owner:fk:to=users.User,assignee:fk:to=users.User"` runs on a generated project THEN `manage.py check` SHALL pass with no hand edit.
2. WHEN the same is done for two `m2m` and for two `o2o` fields to one target, and for a self-relation declared twice, THEN `manage.py check` SHALL pass too.
3. WHEN the model has explicit names (`owner:fk:to=users.User:related_name=owned_notes` plus an unnamed `assignee`) THEN `manage.py check` SHALL pass and `owned_notes` SHALL be used as written.

### Requirement 4 — The rest of the generator keeps working

**User Story:** As a developer, I want serializers, viewsets, admin, tests, the SPA CRUD pages and owner scoping to work on such models, so that the fix is not only skin deep.

#### Acceptance Criteria

1. WHEN a model has fields with `related_name` (explicit or generated) THEN `add-serializer`, `add-viewset`, `add-admin`, `add-test`, `add-frontend-crud` and `add-permission --preset owner --viewset` SHALL produce the same output as for the same model without `related_name`.
2. WHEN the generated project's own tests run for the motivating example THEN they SHALL pass.
3. WHEN the owner-scoping e2e test builds its `Note` model THEN it SHALL no longer patch the model by hand.

### Requirement 5 — Documentation

**User Story:** As a user, I want the option documented, so that I know it exists and what the automatic names look like.

#### Acceptance Criteria

1. WHEN the docs are built THEN `docs/commands/add-model.md` SHALL list `related_name=` with its rule, an example and the automatic-name behavior.
2. WHEN this spec is implemented THEN roadmap item 11 SHALL be marked done and the side finding in the audit notes SHALL be updated.

### Requirement 6 — Nothing else changes

**User Story:** As a user of existing projects, I want current field declarations to behave as before.

#### Acceptance Criteria

1. WHEN any field declaration valid today is parsed THEN the result SHALL be the same except for the new rule in Requirement 2.1.
2. WHEN the full test suite runs THEN it SHALL pass without weakening an existing test, and `tests/commands/test_option_probe.py` SHALL still pass.
3. WHEN generation runs for models without clashes THEN the generated tree SHALL be byte-identical to the current output (same reference-project diff as in `dry-command-layer`).

### Requirement 7 — Many-to-many fields no longer break the admin check

**User Story:** As a developer, I want a model with a many-to-many field to pass `manage.py check` as generated, so that the documented `tags:m2m:to=Tag` example works.

#### Acceptance Criteria

1. WHEN `add-model` creates or refreshes a model's admin THEN the generated `list_display` SHALL NOT contain any `m2m` field, and every other field SHALL stay in the same position as today.
2. WHEN a model has a single `m2m` field THEN `manage.py check`, `makemigrations` and `migrate` SHALL pass with no hand edit.
3. WHEN a model has no `m2m` field THEN the generated admin SHALL be byte-identical to today's.
4. WHEN a model has only `m2m` fields besides the generated ones THEN `list_display` SHALL still be valid (`id` and the timestamp fields remain).

## Non-Functional Requirements

### Code Architecture and Modularity
- **Single Responsibility Principle**: parsing and validating the option lives in `fields/parser.py`; the clash detection and name generation live next to the code that emits model source, not in the commands.
- **Modular Design**: the field specs a command parsed are the single source for both the model and the printed note, so there is no second pass over raw strings.
- **Clear Interfaces**: any new function is fully annotated; `FieldSpec` stays a frozen dataclass.

### Performance
- No measurable cost: the clash check is linear in the number of fields.

### Security
- `related_name` is on an allow-list (identifier or `+`) and is emitted only as a quoted literal. The `--field` and `--fields` options stay covered by the injection probe test.

### Reliability
- The command stays all-or-nothing: an invalid or duplicate name leaves the project untouched.

### Usability
- Error messages state the rule and the field. The note about generated names tells the user how to override them (`related_name=`).
