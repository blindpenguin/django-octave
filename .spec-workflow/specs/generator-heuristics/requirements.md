# Requirements Document

## Introduction

Support-desk and recipe benchmarks (generators-only) are functionally green after earlier polish, but still expose **heuristic and cosmetic defects**: wrong Spectacular tags on `@action`, redundant URL paths (`/api/recipes/recipes/`), weak `Meta.ordering` field choice, scattered duplicate imports, leftover starter models when the first real model has a different name, and nested serializer helpers appended **after** the parent class that references them (NameError for `UserNestedSerializer`).

This spec hardens those generator heuristics so a multi-model, multi-app project needs little or no hand-editing for imports, OpenAPI tags, URLs, ordering, starters, and nested serializer order.

## Alignment with Product Vision

- Solo-dev ergonomics: generated stubs should import, route, and document correctly out of the box.
- Consistency across `add`, `add-model`, `add-serializer`, `add-viewset`, `add-action`, and URL mounting.
- Prefer fixing shared helpers over one-off command patches.

## Requirements

### Requirement 1 — Nested serializer helpers before use

**User Story:** As a developer nesting a `users.User` (or any) FK, I want nested serializer classes defined **before** the parent serializer that references them, so that importing `serializers.py` never raises `NameError`.

#### Acceptance Criteria

1. WHEN `add-serializer --nested …` creates or refreshes a `*NestedSerializer` helper THEN that class SHALL appear in `serializers.py` **above** any parent serializer that references it in the same write.
2. WHEN a later `add-serializer` reuses an existing nested helper THEN the parent upsert SHALL NOT leave the parent class above a newly appended helper (helpers are inserted before the parent, or the file is ordered so definitions precede use).
3. Unit tests SHALL cover nested `users.User` (or equivalent) where the helper is created in the same command as the parent, and where a second nested write would otherwise append after the parent.

### Requirement 2 — Action OpenAPI tags from the target viewset

**User Story:** As a developer adding `@action` methods, I want Spectacular tags to match the **target** viewset’s tag, so that Swagger groups actions with the correct resource.

#### Acceptance Criteria

1. WHEN `add-action` runs without `--tag` THEN the tag SHALL be taken from the target viewset’s own `@extend_schema_view` / nearby tags (not from an earlier class in the file, and not from a fixed lookbehind that captures a previous viewset).
2. WHEN no tag can be detected on the target viewset THEN the fallback SHALL be the viewset stem snake (e.g. `ArticleViewSet` → `article`), not the app name unless that equals the stem.
3. WHEN `--tag` is passed THEN that value SHALL win.
4. Unit tests SHALL cover a `views.py` with two viewsets (different tags) and an action on the **second** class receiving the second tag.

### Requirement 3 — Non-redundant API URL paths

**User Story:** As a developer, I want collection URLs like `/api/tickets/` and `/api/articles/`, not `/api/tickets/tickets/` or `/api/kb/kbs/`.

#### Acceptance Criteria

1. WHEN a domain app is registered in project `urls.py` THEN the include mount SHALL be `api/` (shared prefix), not `api/<app_name>/`.
2. WHEN a viewset is registered on the app router THEN the path SHALL remain the pluralized model snake (as today), yielding `/api/<plural>/…`.
3. WHEN `add-action` prints a route shape hint THEN it SHALL reflect `/api/<plural>/…` (no duplicated app segment).
4. `add` / AppContext summary text SHALL show the corrected mount/API path.
5. Existing projects already using `api/<app>/` are **out of scope** for automatic rewrite; only new `patch_urls` / new app wiring follows the new convention. Idempotent patch SHALL still recognize legacy `api/<app>/` includes as “already wired” for that app (do not double-add) while new apps get `api/` mounts.
6. Unit/integration tests SHALL assert the include form and that plural registration alone forms the public path.

### Requirement 4 — Smarter default `Meta.ordering`

**User Story:** As a developer generating models with `body`/`note` plus a better label field, I want `Meta.ordering` to prefer human label fields, so that lists are not ordered by long text.

#### Acceptance Criteria

1. WHEN choosing a default ordering / `__str__` field THEN the generator SHALL prefer, in order: `name`, `title`, `subject`, `slug`, then other `char`/`slug`/`email` fields, and SHALL **not** prefer `text` fields when any char-like field exists.
2. WHEN only `text` (or no suitable) fields exist THEN existing fallback behavior MAY use text or `pk` as today.
3. Unit tests SHALL cover `TicketMessage`-like fields (`body:text`, `note:char`) ordering by `note` (or another char), not `body`.

### Requirement 5 — Merge duplicate import lines

**User Story:** As a developer after several viewset/action upserts, I want a single `from rest_framework.permissions import …` line (and similar), so that `views.py` is not littered with duplicate imports.

#### Acceptance Criteria

1. WHEN ensuring imports for the same module (e.g. `rest_framework.permissions`) THEN symbols SHALL be merged into one import line when practical.
2. WHEN `add-viewset` / `add-action` / permission wiring adds imports THEN repeated runs SHALL not accumulate duplicate identical import lines for the same module+symbol set.
3. Best-effort: at least merge `from X import A` + `from X import B` into `from X import A, B` for common DRF/permission modules touched by generators; full isort of the whole project is out of scope.
4. Unit tests SHALL cover two permission imports coalescing into one line.

### Requirement 6 — Starter model name on `add`

**User Story:** As a developer scaffolding `accounts` with a first model `Customer` (not `Account`), I want `add` to accept an explicit starter model name, so that I do not leave orphan `Account`/`Kb` models and viewsets.

#### Acceptance Criteria

1. WHEN `django-octave add <app> --model Customer` (or equivalent) is used THEN the starter model, serializer, viewset, router basename/path, and templates SHALL use `Customer` / `customer` / pluralization of that name.
2. WHEN `--model` is omitted THEN behavior SHALL remain derive-from-app-name (today’s `model_name_from_app`).
3. Interactive mode MAY prompt for model name with a default derived from the app.
4. This does **not** require deleting unrelated existing models when a later `add-model` adds a differently named class; the primary fix is naming the starter correctly up front.
5. CLI help and a short docs note SHALL mention `--model`.
6. Tests SHALL cover `add accounts --model Customer` producing `Customer` (not `Account`) in models/urls.

### Requirement 7 — Regression coverage

**User Story:** As a maintainer, I want tests locking these heuristics so support-desk / recipe-style scaffolds stay clean.

#### Acceptance Criteria

1. Tests SHALL cover requirements 1–6 at unit or CLI level as appropriate.
2. Existing pytest suite SHALL remain green.

## Non-Functional Requirements

### Code Architecture and Modularity

- Prefer shared helpers (`detect_viewset_tag`, `str_field_name`, `upsert_class` / insert-before, `ensure_import_lines` / coalesce, `patch_urls`, `AppContext`).
- Keep commands thin.

### Reliability

- Do not break reverse names (`basename` remains model snake).
- Plural path collisions across apps under shared `api/` are acceptable and documented (developers choose unique plurals); no automatic conflict detector required in this spec.

### Usability

- Action route hints and `add` summary must match real URLs.

## Out of Scope

- Auto-migrating existing generated projects from `api/<app>/` to `api/`.
- Removing orphan starter models from already-generated trees.
- Full project-wide isort/ruff import sorting as a required dependency.
- Changing smoke-test coverage beyond what prior specs already require.
- Nested routers / OpenAPI customization beyond tags on `@action`.
