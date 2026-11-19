# Requirements Document

## Introduction

**add-model** introduces `django-octave add-model`: add a concrete Django model to an existing domain app under `apps/`, with declared fields, and keep the app’s API surface coherent (serializer fields, admin, viewset filters where applicable). This is the first of a family of **per-part commands** (`add-model`, and later serializer/viewset/etc.) so solo developers retain full control without only using the coarse `add` app scaffold.

**Out of scope for this spec:** FK/M2M to arbitrary models beyond a small supported set (design may allow `ForeignKey` to `users.User` / same-app models with limits); custom managers; migrations generation inside the CLI (user still runs `makemigrations`); GraphQL; changing `django-octave add` to require fields (starter `name` model from `add` remains).

**Product direction (non-binding for later specs):** Prefer dedicated commands for app parts (`add-model`, `add-serializer`, `add-viewset`, …) rather than one mega-generator.

## Alignment with Product Vision

Extends opinionated API scaffolding with finer control after kickstart + `add`. Matches future vision of richer generators while keeping the CLI composable.

## Requirements

### Requirement 1 — CLI command and dual UX

**User Story:** As a solo Django developer, I want `django-octave add-model` with prompts or flags, so that I can add models scriptably or interactively.

#### Acceptance Criteria

1. WHEN the user runs `django-octave --help` THEN the system SHALL list `add-model`.
2. WHEN the user runs `add-model` THEN required inputs SHALL include: target app name, model name, and at least one field definition (or a documented default field set if none provided — design chooses; prefer requiring explicit fields or defaulting to `name:char`).
3. WHEN stdin is a TTY and required values are missing THEN the system SHALL prompt for them.
4. WHEN run non-interactively with missing required values THEN the system SHALL exit non-zero without hanging.
5. Flags SHALL include `--path` (project root) and `--force` behavior for replacing an existing model of the same name (design specifies: refuse by default).

### Requirement 2 — Project and app preconditions

**User Story:** As a solo Django developer, I want clear failures when the project or app is wrong, so that I do not corrupt unrelated code.

#### Acceptance Criteria

1. WHEN `add-model` runs THEN the system SHALL detect a django-octave-style project (same markers as `add`).
2. IF `apps/<app>` does not exist THEN the system SHALL fail and suggest `django-octave add <app>`.
3. IF the model name is invalid (not PascalCase / not a valid Python class name) THEN the system SHALL reject it.
4. IF a model class with that name already exists in the app’s `models.py` (or models package) AND `--force` is not set THEN the system SHALL refuse.
5. Reserved / conflicting names (e.g. colliding with imports) SHALL be rejected with a clear message (design lists rules).

### Requirement 3 — Field declarations

**User Story:** As a solo Django developer, I want to declare fields in a simple CLI form, so that the model matches my domain without hand-writing boilerplate every time.

#### Acceptance Criteria

1. WHEN adding a model THEN the user SHALL be able to pass repeated `--field` options in a documented `name:type[:options]` form (example: `--field title:char:max=255 --field published:bool:default=false`).
2. The system SHALL support at least these field types in v1: `char`, `text`, `int`, `bool`, `decimal`, `date`, `datetime`, `email`, `url`, `slug`, `uuid` (UUIDField).
3. Common options SHALL include nullability (`null`/`blank`), `default`, `max` (for CharField), `unique`, and for decimal `max_digits`/`decimal_places` as documented in design.
4. IF an unknown type or malformed field string is provided THEN the system SHALL fail with a parse error naming the bad token.
5. Generated fields SHALL follow project Python/Django conventions (`snake_case` field names).

### Requirement 4 — Model generation and base class

**User Story:** As a solo Django developer, I want the new model to use `TimeStampedModel` or `TenantAwareModel` appropriately, so that it matches the project’s core primitives.

#### Acceptance Criteria

1. WHEN the project has multitenancy detected THEN new models SHALL subclass `TenantAwareModel`; OTHERWISE `TimeStampedModel`.
2. WHEN a model is added THEN it SHALL be written into the app’s models module in a maintainable way (design: append to `models.py` or `models/<model>.py` + import — prefer approach that is robust for repeated adds).
3. WHEN a model is added THEN `__str__` SHALL be defined using a sensible field (prefer `name` or `title` if present; else first CharField; else `pk`).
4. WHEN a model is added THEN `Meta.ordering` MAY be set when an obvious field exists (design detail).

### Requirement 5 — Keep API stubs in sync (opinionated minimum)

**User Story:** As a solo Django developer, I want serializer/admin/viewset updated for the new model, so that I am not left with an orphan model after `add-model`.

#### Acceptance Criteria

1. WHEN a model is added to an app that already has DRF stub patterns from `django-octave add` THEN the system SHALL add or update serializer, viewset registration, admin registration, and router basename for the new model (without removing unrelated existing models’ stubs when detectable).
2. IF the app has no serializer/views/urls yet THEN the system SHALL create the same stub file set as `add` would for that model (or fail with guidance to run `add` first — design picks one; prefer creating stubs for the new model).
3. Serializer `Meta.fields` SHALL include the declared fields plus timestamps/`id` as appropriate.
4. ViewSet SHALL expose the new model with `IsAuthenticated`, and `filterset_fields` for suitable simple fields (char/bool/int/slug/uuid at minimum).
5. This spec does **not** require a separate `add-serializer` command yet; in-sync updates are part of `add-model` so the API remains usable.

### Requirement 6 — UX output, docs, tests

**User Story:** As a maintainer and user, I want docs and tests so `add-model` stays reliable.

#### Acceptance Criteria

1. On success, the CLI SHALL print next steps including `makemigrations` / `migrate`.
2. README SHALL document `add-model`, field syntax, and examples.
3. Tests SHALL cover: field parsing; happy-path add-model into an app from `add`; reject bad fields; refuse duplicate model without force; multitenancy base class; serializer contains new fields.

## Non-Functional Requirements

### Code Architecture and Modularity

- Reuse `detect_project`, naming helpers, and patch/render patterns from `add-app`.
- Field parser and model code generation as dedicated modules (testable without Typer).
- Prefer AST-aware or carefully structured append strategies for `models.py` over brittle regex where practical (design decides).

### Performance

- Command completes in well under a second excluding user migrate.

### Security

- No execution of user field strings as code; map types through an allowlist only.

### Reliability

- Fail closed on ambiguous file structure; never partially claim success if model write succeeded but API stub update failed without saying so.

### Usability

- `--help` shows field type allowlist summary and example `--field` lines.
- Command naming is consistent with future `add-*` family (`add-model`, not `model-add`).
