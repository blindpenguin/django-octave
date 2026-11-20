# Requirements Document

## Introduction

**vue-frontend-crud** extends the optional Vue + Nuxt UI SPA (from `vue-nuxt-ui-frontend`) with **full CRUD page generation** for DRF ModelViewSet resources: list, detail, create, edit, and delete (with confirm).

Users get:

1. **`django-octave add-frontend-crud APP Model`** — generate (or refresh) CRUD pages for one model at a time.
2. **Bulk option on `add-frontend`** (and `new --frontend`) — optionally scaffold CRUD for every discoverable ModelViewSet / registered router model already in the project.

Forms use Nuxt UI. **Foreign keys** are **simple selects** populated from the related resource’s list API, labeled by a sensible display field (`name` / `title` / `str`-like first string field — design picks the heuristic).

**Out of scope:** Full Nuxt; React; GraphQL; admin themes; nested inline formsets / M2M chip editors; file/image upload widgets beyond a basic text URL or skip; custom `@action` pages; OpenAPI-driven codegen as the primary path (static analysis of generated Django/SPA files is fine); multi-tenant UI chrome beyond what the API already enforces.

**Prerequisite:** `frontend/` from `add-frontend` / `new --frontend` must exist (or be created in the same command flow before CRUD generation).

## Alignment with Product Vision

Continues “API-first, optional Vue client”: the SPA remains a thin client over JWT REST. Dual UX (flags + prompts). Opinionated Nuxt UI pages keep solo-dev time on domain models, not table boilerplate.

## Requirements

### Requirement 1 — Per-model `add-frontend-crud`

**User Story:** As a solo Django developer, I want to generate CRUD pages for one app model, so that I can grow the SPA as I add APIs.

#### Acceptance Criteria

1. WHEN the user runs `django-octave --help` THEN `add-frontend-crud` SHALL be listed.
2. WHEN `django-octave add-frontend-crud APP MODEL` runs on an octave project with `frontend/` present THEN the system SHALL generate Nuxt UI pages for that model: **list**, **detail**, **create**, **edit**, plus **delete** with confirmation (design picks confirm UX: modal vs dedicated step).
3. WHEN `frontend/` is missing THEN fail with a hint to run `add-frontend` first (unless the command is invoked as part of an `add-frontend` flow that creates it first).
4. WHEN the model lacks a discoverable ModelViewSet / router registration THEN fail with a clear error (hint `add-viewset`).
5. WHEN pages for that model already exist and `--force` is absent THEN refuse; with `--force`, refresh generated CRUD files carefully.
6. Dual UX: flags for path/force; interactive prompts where useful (design); non-interactive must not hang.

### Requirement 2 — Bulk CRUD at frontend scaffold time

**User Story:** As a solo Django developer, I want an option when adding the frontend to generate CRUD for all current API models, so that a demo/admin-ish SPA appears in one pass.

#### Acceptance Criteria

1. WHEN `add-frontend` (or `new --frontend`) runs **interactively** THEN after (or as part of) frontend setup the system SHALL **ask** whether to generate CRUD pages for all discoverable viewset models (default off or documented opinion).
2. WHEN non-interactive THEN `--crud` / `--no-crud` (names finalized in design) SHALL control bulk generation; if frontend is enabled and the flag is missing, fail with a clear message listing required flags (same dual-UX pattern as register).
3. WHEN bulk is accepted THEN for each discoverable eligible model the same page set as Requirement 1 SHALL be generated (shared implementation).
4. WHEN no eligible models exist THEN succeed without error and print that no CRUD pages were generated.
5. Bulk SHALL skip models that cannot be resolved safely (log/print skip reason) rather than failing the whole frontend scaffold unless `--strict` is chosen (design: prefer soft-skip for v1).

### Requirement 3 — Full CRUD page behavior

**User Story:** As a solo Django developer, I want list/detail/create/edit/delete against the ModelViewSet API, so that basic data management works without hand-written Vue.

#### Acceptance Criteria

1. **List** SHALL fetch the collection endpoint (respect pagination if the API returns DRF page shape `{count,next,previous,results}` — design handles both paged and plain arrays), show a Nuxt UI table/list of key fields, and link to detail/edit/create.
2. **Detail** SHALL fetch one object by pk and display fields (read-only).
3. **Create** SHALL POST a form to the collection endpoint; on success navigate to detail or list (design pick).
4. **Edit** SHALL load the object, PUT/PATCH (design pick; prefer PATCH if partial-friendly) to the detail endpoint; on success navigate to detail or list.
5. **Delete** SHALL require explicit confirmation, then DELETE the detail endpoint; on success navigate to list.
6. API errors (4xx validation, 403, 404) SHALL surface user-visible messages (field errors when DRF returns them).
7. Routes SHALL be registered in the Vue router and reachable from an authenticated layout nav (or model index links on home) — design picks nav structure.
8. Pages SHALL reuse the existing JWT `apiFetch` / auth guards (authenticated routes).

### Requirement 4 — Field inference and FK selects

**User Story:** As a solo Django developer, I want forms and tables derived from the model/serializer without manual field lists, including usable FK pickers.

#### Acceptance Criteria

1. Generated fields SHALL be inferred from the Django model and/or serializer used by the viewset (design picks primary source; must be deterministic).
2. Scalar types (char, text, int, bool, decimal, date/datetime, email, slug, etc.) SHALL map to appropriate Nuxt UI inputs.
3. **ForeignKey** fields on write forms SHALL render a **select** loaded from the related model’s list API when that related resource is routable; option **label** SHALL use a heuristic (`name`, `title`, `email`, or first CharField / `__str__` proxy — documented in design).
4. IF the related list endpoint cannot be discovered THEN the FK field SHALL fall back to a numeric/text PK input (and print a warning), not abort generation.
5. Read-only / auto fields (`id`, timestamps if present, non-editable) SHALL be omitted from create/edit or shown read-only on detail only.
6. M2M in v1 MAY be omitted or PK multi-select if cheap; design must state the choice (prefer omit with note if costly).

### Requirement 5 — Docs and tests

**User Story:** As a maintainer, I want docs and generator tests so CRUD scaffolding stays reliable.

#### Acceptance Criteria

1. MkDocs SHALL document `add-frontend-crud`, bulk `--crud` / prompt on `add-frontend` / `new --frontend`, page set, FK select behavior, and prerequisites.
2. Generator tests SHALL cover: help listing; refuse without frontend; refuse without force; generate pages for a fixture model/viewset; bulk flag on/off; FK select wiring smoke; missing viewset gate.
3. Roadmap SHALL list frontend CRUD as shipped when implementation completes (or in-progress until then).

## Non-Functional Requirements

### Code Architecture and Modularity
- Extend `frontend_gen/` (or sibling package) with shared page writers used by both bulk and per-model CLI.
- Reuse existing frontend templates, auth client, and router patterns; do not fork a second SPA stack.
- Idempotent refuse/`--force` consistent with other `add-*` commands.

### Performance
- List pages may fetch one page of results; no infinite-scroll requirement in v1.
- FK selects may load related lists once per form mount (acceptable for solo-dev scale).

### Security
- No secrets in generated frontend; rely on JWT client already in place.
- Do not weaken Django permissions; UI still subject to API 401/403.

### Reliability
- Parse-safe edits to Vue router and layout nav.
- Soft-skip undocumented edge models in bulk mode rather than leaving a broken SPA.

### Usability
- Dual UX; Rich next-step output with routes and `pnpm dev` reminder.
- Opinionated Nuxt UI look consistent with the shell from `vue-nuxt-ui-frontend`.
