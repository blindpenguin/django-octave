# Requirements Document

## Introduction

**related-serializers** extends django-octave so domain models can declare **relations** and APIs can expose them as **primary-key links** and optional **read-only nested** objects — enough for a Vue client to render related data without hand-wiring DRF relation fields.

Scope covers:

1. **Model field DSL** — `fk` / `o2o` / `m2m` types on `add-model` (and codegen into `models.py`).
2. **Serializer generation** — detect relation fields; default to writable PK (or PK-only) representation; optional nested read serializers via `add-serializer` flags.
3. **Docs + tests** for the new DSL and serializer modes.

**Out of scope:** writable nested creates/updates; arbitrary nesting depth > 1; GraphQL; automatic reverse-relation serializers for every `related_name`; generating related models that do not exist yet; full CRUD UI pages.

## Alignment with Product Vision

Unblocks richer REST payloads for the planned Vue + Nuxt UI client while staying opinionated and composable with existing `add-model` / `add-serializer` / `add-viewset` commands.

## Requirements

### Requirement 1 — Relation field types on `add-model`

**User Story:** As a solo Django developer, I want to declare ForeignKey / OneToOne / ManyToMany fields in the field DSL, so that models can express domain relationships without editing by hand.

#### Acceptance Criteria

1. WHEN the user passes `--field name:fk:to=app.Model` (or equivalent documented syntax) THEN `add-model` SHALL generate a `models.ForeignKey` with an allowlisted `on_delete` (default `CASCADE`, optional override).
2. WHEN the user passes `--field name:o2o:to=…` THEN the system SHALL generate `OneToOneField` with the same `to` / `on_delete` rules.
3. WHEN the user passes `--field name:m2m:to=…` THEN the system SHALL generate `ManyToManyField` (blank default opinionated as documented).
4. IF `to=` is missing or malformed THEN the system SHALL fail with a clear parse error.
5. IF the target model string is not a valid dotted `app_label.Model` or bare `Model` (same-app) per design THEN the system SHALL fail with a clear error.
6. Existing scalar types (`char`, `int`, …) SHALL keep working unchanged.

### Requirement 2 — Field inspection understands relations

**User Story:** As a generator, I want relation fields discovered from `models.py`, so that serializers can treat them differently from scalars.

#### Acceptance Criteria

1. WHEN inspecting a model THEN `ForeignKey`, `OneToOneField`, and `ManyToManyField` assignments SHALL be detected (as today or extended) with enough metadata to know they are relations (and target when parseable from AST).
2. Relation field names SHALL appear in available serializer field names like other concrete fields.
3. Reverse relations (undeclared on the class body) SHALL NOT be auto-included unless explicitly requested by a future flag (default: exclude).

### Requirement 3 — Default related representation on serializers

**User Story:** As a solo Django developer, I want relation fields in serializers to default to primary-key style, so that create/update stay simple.

#### Acceptance Criteria

1. WHEN `add-serializer` runs and the model has relation fields included in `Meta.fields` THEN those fields SHALL default to DRF primary-key related behavior (ModelSerializer default / explicit `PrimaryKeyRelatedField` as design chooses) — not nested objects.
2. WHEN `--fields` lists a relation name THEN it SHALL be valid the same way as scalar names.
3. M2M fields included in fields SHALL be represented as a list of PKs by default.

### Requirement 4 — Optional read-only nested serializers

**User Story:** As a solo Django developer, I want to opt into nested read representations for selected relations, so that list/detail payloads can include related object summaries for a UI.

#### Acceptance Criteria

1. WHEN the user passes a documented nest flag (e.g. `--nested author` or `--nested author=AuthorSerializer`) THEN `add-serializer` SHALL emit a nested serializer usage for that relation that is **read-only** on the parent (writes still use PK field or are omitted per design — design picks one clear rule).
2. IF a nested target serializer class is missing THEN the system SHALL either auto-create a minimal nested serializer for the related model (same app or importable) **or** fail with a hint to run `add-serializer` on the related model first — **prefer auto-create a slim nested serializer** (id + str/common fields) so one command stays usable.
3. Nesting SHALL be **one level deep** only (nested serializers do not themselves nest further in this spec).
4. Without nest flags, behavior remains PK-style (Requirement 3).
5. `--force` SHALL replace the parent serializer (and generated nested helper classes owned by this command) per existing force semantics.

### Requirement 5 — CLI / docs / tests

**User Story:** As a maintainer, I want docs and tests covering relation DSL and nested serializer modes.

#### Acceptance Criteria

1. README SHALL document relation field syntax and `--nested` (or equivalent) usage with examples.
2. Tests SHALL cover: parsing fk/o2o/m2m; codegen snippets; inspect detects relations; add-serializer PK default; add-serializer with nest flag; bad `to=` / unknown nest field errors.
3. Dual UX (flags + TTY prompts for missing app/model) SHALL match existing add-* patterns; nest/relation options may be flag-only in v1 if prompting would be noisy (document that).

## Non-Functional Requirements

### Code Architecture and Modularity
- Extend `fields/parser.py` + `fields/codegen.py` rather than a parallel DSL.
- Reuse `inspect/model_fields.py` and `api_parts/serializer_gen.py`.
- Keep viewset command unchanged unless a tiny import fix is required.

### Security
- Do not auto-expose reverse relations or admin-only models.
- Nested serializers remain read-only on the parent to avoid mass-assignment surprises.

### Reliability
- Fail closed on unparseable relation targets or missing related model classes when nesting requires them.

### Usability
- Opinionated defaults: `on_delete=CASCADE` for FK/O2O; PK relations unless `--nested` is passed.
