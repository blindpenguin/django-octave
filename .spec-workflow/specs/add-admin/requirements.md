# Requirements Document

## Introduction

**add-admin** adds `django-octave add-admin` to create or refresh a Django `ModelAdmin` for an existing model in `apps/<app>/admin.py`, with opinionated `list_display`, `search_fields`, `list_filter`, and light performance helpers (`list_select_related` for FKs, `date_hierarchy` when timestamps exist). Solo developers get a usable changelist without hand-editing admin stubs that `add-model` already scaffolds thinly.

**Out of scope:** Admin UI themes / custom skins (product non-goal); inlines; custom admin actions; `SimpleListFilter` subclasses; `UserAdmin` / auth model specialization; `get_queryset` overrides beyond `list_select_related`; autocomplete/raw_id as required defaults (optional flag only if cheap — prefer omit in v1); GraphQL or Vue admin replacements.

## Alignment with Product Vision

Completes the backend `add-*` surface so domain models are operable in stock Django admin. Opinionated defaults over open-ended customization; dual UX for solo-dev ergonomics.

## Requirements

### Requirement 1 — Command and dual UX

**User Story:** As a solo Django developer, I want `add-admin` with flags or prompts, so that I can script or explore safely.

#### Acceptance Criteria

1. WHEN the user runs `django-octave --help` THEN `add-admin` SHALL be listed.
2. WHEN the command runs THEN it SHALL detect an octave project (`--path`, default cwd) like other add-* commands.
3. Required inputs SHALL be app name and model name (PascalCase). Missing values prompt on TTY or exit non-zero non-interactively.
4. IF the model is missing from `apps/<app>/models.py` THEN the command SHALL fail with a hint to run `add-model`.
5. The command SHALL support `--force` to replace an existing `{Model}Admin` class; without `--force`, refuse duplicates.
6. Success output SHALL name the admin file and summarize key options set (e.g. list_display count).

### Requirement 2 — ModelAdmin generation from inspected fields

**User Story:** As a solo Django developer, I want a sensible ModelAdmin from my model fields, so that the changelist is immediately useful.

#### Acceptance Criteria

1. WHEN `add-admin` succeeds THEN `apps/<app>/admin.py` SHALL contain `@admin.register(Model)` and `class {Model}Admin(admin.ModelAdmin)` (create file with imports if missing).
2. WHEN no explicit field overrides are given THEN the generator SHALL inspect `models.py` (same inspector as serializers/viewsets) and set:
   - **`list_display`**: `id` + a capped set of concrete fields (prefer ~4–8 columns: identifiers/bools/FKs first; include `created_at`/`updated_at` when the model has timestamp bases; omit large `TextField` / `JSONField` / binary-like from display by default).
   - **`search_fields`**: searchable text-like fields (Char/Slug/Email/Text); empty tuple if none.
   - **`list_filter`**: low-cardinality-friendly fields (Boolean, FK, and optionally Char/Slug when few); include date fields for filtering when present; empty if none suitable.
3. WHEN the model has FK/O2O fields included in `list_display` THEN `list_select_related` SHALL list those relation names (performance default).
4. WHEN the model has `created_at` (timestamp base) THEN `date_hierarchy = "created_at"` SHALL be set (or the first available DateTimeField among timestamps — prefer `created_at`).
5. Generated class SHALL ensure imports for `admin` and the model.

### Requirement 3 — Optional field overrides

**User Story:** As a solo Django developer, I want to override display/search/filter lists via flags, so that I can tune without editing by hand.

#### Acceptance Criteria

1. WHEN `--list-display`, `--search`, or `--filter` (comma-separated) is provided THEN those lists SHALL replace the corresponding auto heuristics (after validating names against inspected available fields / relations).
2. WHEN an unknown field name is provided THEN the command SHALL fail listing valid names.
3. WHEN `--no-date-hierarchy` is set THEN `date_hierarchy` SHALL be omitted even if timestamps exist.
4. Optional `--ordering` (comma-separated) SHALL set `ordering` on the ModelAdmin when provided.

### Requirement 4 — Coexistence with add-model stubs

**User Story:** As a solo Django developer, I want `add-admin` to refine what `add-model` already wrote, so that I am not stuck with a minimal stub.

#### Acceptance Criteria

1. WHEN `{Model}Admin` already exists from `add-model` / prior run and `--force` is set THEN the class SHALL be replaced with the refined version.
2. WHEN the class exists without `--force` THEN the command SHALL refuse (same pattern as add-serializer).
3. `add-model` behavior MAY remain unchanged in this spec (thin stub is fine); `add-admin` is the intentional refine path. (Optional follow-up: have add-model call shared admin builder — not required for v1.)

### Requirement 5 — Docs and tests

**User Story:** As a maintainer, I want README docs and tests for add-admin.

#### Acceptance Criteria

1. README SHALL document `add-admin`, heuristics summary, override flags, and `--force`.
2. Tests SHALL cover: help listing; create admin; refuse without force; force replace; list_display/search/filter overrides; bad field name; missing model; timestamp → date_hierarchy; FK → list_select_related smoke.

## Non-Functional Requirements

### Code Architecture and Modularity
- New module `src/django_octave/api_parts/admin_gen.py` (or `models_gen/admin_gen.py` — prefer **`api_parts/admin_gen.py`** for consistency with serializer/viewset gens, even though admin is Django not DRF).
- Reuse `inspect_model_fields`, `upsert_class`, `add_to_import`, `detect_project`, naming validators.
- Thin Typer command + prompts; shared heuristics extractable so a later add-model refactor can call them (no requirement to refactor add-model now).

### Performance
- Prefer `list_select_related` for displayed FKs; avoid putting unbounded TextFields in `list_display` by default.

### Security
- Do not generate HTML/`format_html` callables in v1 (XSS surface); field names only.
- No changes to admin auth / permissions.

### Reliability
- Refuse unparseable `admin.py` / `models.py` with clear errors; never silently corrupt files.

### Usability
- Dual UX; Rich success summary; MDX-safe README.
- Product non-goal remains: no admin themes.
