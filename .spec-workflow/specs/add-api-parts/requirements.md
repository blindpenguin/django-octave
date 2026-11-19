# Requirements Document

## Introduction

**add-api-parts** adds two composable CLI commands for full control over the API layer of an existing domain app:

- **`django-octave add-serializer`** — create or regenerate a ModelSerializer for an existing model (field selection, read-only fields).
- **`django-octave add-viewset`** — create or regenerate a ModelViewSet (permissions, filters, search, ordering, Spectacular tags) and ensure router registration.

Together with `add` / `add-model`, these complete the core “per-part” generator family for serializers and viewsets.

**Out of scope:** nested/related serializers; custom `@action` endpoints beyond a documented optional stub; GraphQL; regenerating models; OpenAPI-only schema tweaks unrelated to viewsets; admin generators.

## Alignment with Product Vision

Supports the product direction of dedicated `add-*` commands for solo-dev control, and the vision of richer API scaffolding on top of kickstart + app/model generators.

## Requirements

### Requirement 1 — Shared preconditions and dual UX

**User Story:** As a solo Django developer, I want both commands to work against a real octave project/app/model with prompts or flags, so that I can script or explore safely.

#### Acceptance Criteria

1. WHEN the user runs `django-octave --help` THEN both `add-serializer` and `add-viewset` SHALL be listed.
2. WHEN either command runs THEN the system SHALL detect an octave-style project (`--path`, default cwd) using the same markers as `add` / `add-model`.
3. WHEN either command runs THEN required inputs SHALL include app name and model name (PascalCase); missing values prompt on TTY or exit non-zero non-interactively.
4. IF the app or model does not exist in `apps/<app>/models.py` THEN the system SHALL fail with a clear error (suggest `add` / `add-model`).
5. Both commands SHALL support `--force` to replace an existing serializer/viewset class of the same name; without `--force`, refuse duplicates.
6. Both commands SHALL print a short success summary (files touched / next hints).

### Requirement 2 — `add-serializer`

**User Story:** As a solo Django developer, I want to generate or refresh a serializer for a model with explicit field control, so that my API contract matches what I intend.

#### Acceptance Criteria

1. WHEN `add-serializer APP MODEL` succeeds THEN the system SHALL ensure `apps/<app>/serializers.py` contains `<Model>Serializer` as a `ModelSerializer` bound to that model.
2. WHEN `--fields` is provided (comma-separated field names) THEN `Meta.fields` SHALL use exactly those fields (plus design-documented automatic inclusion of `id` if requested via flag or default policy — design picks: **include `id` unless `--no-id`**).
3. WHEN `--fields` is omitted THEN the system SHALL include model concrete field names discovered from `models.py` (excluding reverse relations), plus `id`, `created_at`, `updated_at` when present on the model/base.
4. WHEN `--read-only` is provided (comma-separated) THEN those fields SHALL appear in `Meta.read_only_fields` (always include `id` / timestamps when they are in fields, unless overridden carefully — design documents merge rules).
5. WHEN `--force` is set THEN an existing `<Model>Serializer` SHALL be replaced; imports for the model SHALL be ensured.
6. IF a listed `--fields` / `--read-only` name is not a known model field THEN the system SHALL fail with a parse/validation error naming the bad field.

### Requirement 3 — `add-viewset`

**User Story:** As a solo Django developer, I want to generate or refresh a viewset and router entry for a model, so that permissions and filtering match my API needs.

#### Acceptance Criteria

1. WHEN `add-viewset APP MODEL` succeeds THEN the system SHALL ensure `apps/<app>/views.py` contains `<Model>ViewSet` as a `ModelViewSet` using `<Model>.objects.all()` and `<Model>Serializer`.
2. IF `<Model>Serializer` is missing THEN the system SHALL either auto-create a default serializer (same defaults as `add-serializer` without extra flags) **or** fail and tell the user to run `add-serializer` first — **prefer auto-create default serializer** so `add-viewset` alone is usable.
3. WHEN the command succeeds THEN `apps/<app>/urls.py` SHALL register the viewset on a pluralized route with a stable basename (idempotent; `--force` may refresh registration path/basename if design allows, but must not duplicate registers).
4. Permission default SHALL be `IsAuthenticated`; optional `--permission` allowlist (e.g. `IsAuthenticated`, `AllowAny`, `IsAdminUser`) SHALL set `permission_classes`.
5. Optional `--filter` (repeatable or comma-separated) SHALL set `filterset_fields`; when omitted, use a sensible default from simple model fields (char/bool/int/slug/uuid/email) similar to `add-model` sync.
6. Optional `--search` and `--ordering` SHALL set `search_fields` / `ordering_fields` (defaults from char-like fields / common fields when omitted).
7. Spectacular `@extend_schema_view` tags SHALL default to the model’s snake_case name; optional `--tag` overrides.
8. WHEN `--force` is set THEN an existing `<Model>ViewSet` SHALL be replaced and imports ensured.

### Requirement 4 — Consistency with existing generators

**User Story:** As a solo Django developer, I want these commands to play nicely with apps created by `add` / `add-model`, so that I can refine stubs without starting over.

#### Acceptance Criteria

1. Commands SHALL reuse project detection, naming validation, and libcst-based class upsert patterns from prior specs where practical.
2. Generated code style SHALL match existing stub conventions (typing imports, IsAuthenticated, spectacular helpers).
3. Running `add-serializer` then `add-viewset` (or viewset alone with auto-serializer) SHALL leave a coherent import graph (no missing symbols).

### Requirement 5 — Docs and tests

**User Story:** As a maintainer, I want README docs and tests covering both commands.

#### Acceptance Criteria

1. README SHALL document `add-serializer` and `add-viewset` with examples and main flags.
2. Tests SHALL cover: happy paths after `new`→`add`→`add-model`; field selection validation; refuse without force; force replace; viewset router registration; auto-serializer when missing for viewset; bad app/model errors.

## Non-Functional Requirements

### Code Architecture and Modularity

- Separate command modules; shared “inspect model fields from models.py” helper; shared class upsert utilities extracted if duplicated with `add-model` sync.
- No runtime dependency from generated apps on django-octave.

### Performance

- Each command completes in well under a second for typical apps.

### Security

- Permission allowlist only; no arbitrary permission class import paths from user strings beyond the allowlist.

### Reliability

- Fail closed on unparseable Python; never silently skip writing when the user asked to create a missing stub.

### Usability

- Help text shows examples; errors suggest the sibling command when serializer/model is missing.
