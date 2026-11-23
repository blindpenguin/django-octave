# Requirements Document

## Introduction

Generated CRUD **list** pages currently use Nuxt UI `UTable`, which is awkward on phones (horizontal scroll, cramped columns, tiny action buttons). Replace tables with a **Gmail-style vertical list**: full-width tappable rows with a primary title line and optional muted secondary line, suited to Android/iOS and desktop alike.

Scope is the **list view template** (and related generator context/tests/docs). Detail/create/edit stay as they are unless a tiny shared helper is needed for row labels. No new backend APIs.

## Alignment with Product Vision

django-octave’s optional Vue frontend should feel usable on day one on real devices, not only wide desktops. Opinionated defaults (one list pattern, not table-vs-list toggles) match product principles. Builds on `vue-frontend-crud` + `vue-app-shell` without changing the generator’s Python/Jinja architecture.

## Requirements

### Requirement 1

**User Story:** As a developer using a generated SPA on a phone, I want CRUD collections as a vertical list of rows, so that I can browse and open items without horizontal scrolling or dense tables.

#### Acceptance Criteria

1. WHEN a CRUD list page is generated THEN the system SHALL NOT use `UTable` (or equivalent wide data-table) as the primary collection UI.
2. WHEN the list has items THEN the system SHALL render a vertical stack of full-width rows suitable for touch (comfortable tap targets, no reliance on hover-only actions).
3. WHEN the viewport is narrow (phone-sized) THEN the list SHALL remain readable without horizontal page/list scrolling for normal field content.
4. WHEN the same list is viewed on desktop THEN the same list pattern SHALL be used (no separate desktop table mode in v1).

### Requirement 2

**User Story:** As an end user, I want each row to show a clear primary label and useful secondary context, so that I can scan the list like Gmail/inbox UIs.

#### Acceptance Criteria

1. WHEN a row is rendered THEN the system SHALL show a **primary** text line derived from the resource’s preferred label (existing `label_field` / API `label` when present, else a sensible first list field).
2. WHEN secondary list fields exist THEN the system SHALL show up to a small number of muted secondary values on the row (design picks count/layout; omit empty values when practical).
3. WHEN primary label data is missing THEN the system SHALL fall back to a stable identifier (e.g. `#id` or first available field) so the row is never blank.
4. Field **labels** shown as captions (if any) SHALL use the existing humanized label helpers already used by CRUD pages.

### Requirement 3

**User Story:** As an end user, I want tapping a row to open the item, so that navigation matches inbox-style apps.

#### Acceptance Criteria

1. WHEN the user activates a row (tap/click) THEN the system SHALL navigate to that resource’s **detail** route.
2. WHEN the list page is shown THEN separate per-row “View” / “Edit” table action buttons SHALL NOT be required; edit remains available from the detail page (and/or a single optional trailing affordance if design adds one—must not clutter mobile).
3. WHEN the page header “New” control is present THEN it SHALL remain available (create flow unchanged).

### Requirement 4

**User Story:** As a developer regenerating CRUD, I want empty, loading, and error states to stay clear, so that the list does not look broken on first load or API failure.

#### Acceptance Criteria

1. WHEN the list is loading THEN the system SHALL show a loading indication (text or Nuxt UI primitive).
2. WHEN the list request fails THEN the system SHALL show an error alert (existing pattern).
3. WHEN the list succeeds with zero items THEN the system SHALL show an empty state message (not a blank card).

### Requirement 5

**User Story:** As a generator maintainer, I want tests and docs updated for the new list UI, so that regeneration and docs stay accurate.

#### Acceptance Criteria

1. WHEN generator unit tests assert list page output THEN they SHALL expect the list-row pattern (not `UTable` columns).
2. WHEN docs describe CRUD list UI THEN they SHALL mention the responsive list (not “table”) briefly under add-frontend-crud (or add-frontend shell notes if relevant).
3. Existing CRUD behaviors (routes, auth guard, API list fetch) SHALL remain unchanged aside from presentation.

## Non-Functional Requirements

### Code Architecture and Modularity
- Change primarily lives in `templates/frontend_crud/pages/ListView.vue.j2` (+ minimal context tweaks in `crud_pages.py` if needed for primary/secondary field selection).
- Prefer Nuxt UI primitives already in the SPA (`UButton`, `UCard` optional, links, icons) over custom CSS frameworks.
- No new npm dependencies unless design proves an existing Nuxt UI component is insufficient.

### Performance
- List still loads the full collection client-side as today (no pagination requirement in this spec).
- Row rendering SHALL stay simple (no heavy per-cell components).

### Security
- No change to auth or API; list remains behind existing SPA auth.

### Reliability
- Generator tests covering list templates SHALL stay green; regenerate benchmarks after implementation for visual check.

### Usability
- Touch-friendly row height; primary text truncated with ellipsis when long; secondary text muted and truncated.
- Visual density closer to mail clients than spreadsheets.
