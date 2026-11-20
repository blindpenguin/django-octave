# Requirements Document

## Introduction

Upgrade the generated Vue + Nuxt UI SPA from a thin temporary shell into a **usable app chrome**: separate layouts for auth vs the authenticated app, a top **app bar** (brand + user menu), a **sidebar** for primary navigation (including CRUD links), and a **responsive** drawer on small screens. The viewport is a fixed app frame; **only the main content region scrolls**.

This changes generator templates under `templates/frontend/` (and CRUD nav wiring markers), so `add-frontend` / `--force` and CRUD regenerate produce the new shell. Existing projects refresh via `--force` (documented).

## Alignment with Product Vision

Supports the optional Vue client as a real day-one UI—not a throwaway demo—while staying API-first (JWT REST). Keeps Nuxt UI (not full Nuxt). Opinionated layout reduces solo-dev chrome work so they ship domain CRUD sooner.

## Requirements

### Requirement 1 — Dual layouts (auth vs app)

**User Story:** As a solo developer, I want login/register on a focused auth layout and the rest of the app in a full chrome layout, so guest and authenticated experiences feel intentional.

#### Acceptance Criteria

1. WHEN the user visits guest routes (`/login`, optional `/register`) THEN the system SHALL render an **AuthLayout** (no app sidebar/app bar chrome; centered card-style content as today or improved).
2. WHEN the user visits authenticated routes (home, CRUD pages, etc.) THEN the system SHALL render an **AppLayout** (app bar + sidebar/drawer + content).
3. WHEN routing is configured THEN layouts SHALL be applied via Vue Router (nested routes and/or layout components)—pages SHALL NOT each re-implement chrome.
4. CRUD page templates SHALL continue to work inside AppLayout without embedding their own full-page chrome (no duplicate headers).

### Requirement 2 — App bar

**User Story:** As an authenticated user, I want a persistent top bar with the app name and my account menu, so I always know where I am and can sign out.

#### Acceptance Criteria

1. WHEN AppLayout is shown THEN an app bar SHALL appear at the top spanning the content width (beside or above the sidebar per design; design picks visual alignment with sidebar).
2. WHEN the app bar is shown THEN the **project/app name** SHALL appear on the **left** (link to home).
3. WHEN the app bar is shown THEN a **user dropdown** SHALL appear on the **right**, showing the current user’s identity (email preferred).
4. WHEN the user opens the dropdown THEN at least **Log out** SHALL be available; selecting it SHALL clear tokens and navigate to login.
5. IF the email/identity is not already available client-side THEN the system SHALL obtain it in a documented way (e.g. persist email at login and/or `GET` current-user endpoint wired with frontend auth)—design picks one approach; SHALL NOT leave the menu as an empty anonymous control.

### Requirement 3 — Sidebar navigation

**User Story:** As an authenticated user, I want a sidebar menu of app sections (including generated CRUD resources), so I can move between areas without hunting links in a header strip.

#### Acceptance Criteria

1. WHEN AppLayout is shown on desktop (breakpoint per design) THEN a **sidebar** SHALL show primary nav links (Home + CRUD resources via existing marker injection, relocated from the old header strip).
2. WHEN CRUD generation runs THEN nav markers SHALL inject into the **sidebar** (not the old horizontal header list).
3. WHEN a nav link matches the current route THEN it SHALL have a clear active state.
4. Nav labels for CRUD resources SHALL remain human-readable (model name / existing labeling).

### Requirement 4 — Responsive drawer

**User Story:** As a user on a phone, I want the menu in a slide-over drawer so the content uses the full width until I open navigation.

#### Acceptance Criteria

1. WHEN the viewport is below the desktop breakpoint THEN the sidebar SHALL NOT permanently consume horizontal space; navigation SHALL be available via a control in the app bar (e.g. menu icon).
2. WHEN that control is activated THEN a **drawer/slide-over** SHALL open with the same nav items as the desktop sidebar.
3. WHEN a nav item is selected on mobile OR the user dismisses the drawer THEN the drawer SHALL close.
4. Motion SHALL be intentional and not janky (Nuxt UI drawer/slideover preferred over custom inventiveness).

### Requirement 5 — Viewport and scrolling

**User Story:** As a user browsing long lists/forms, I want only the main content to scroll while the app bar and sidebar stay fixed, so chrome never scrolls away.

#### Acceptance Criteria

1. WHEN AppLayout is shown THEN the overall shell SHALL fill the viewport height (`100dvh` / equivalent) without document-level double scrollbars as the default.
2. WHEN content overflows THEN **only the main content region** SHALL scroll; app bar and sidebar/drawer chrome SHALL remain fixed in place.
3. WHEN content is short THEN the content area SHALL still use available space (no awkward centered max-width-only strip as the sole layout—design may keep readable max-width *inside* the scroll region, but the shell uses full available width/height).

### Requirement 6 — Generator integration and refresh

**User Story:** As a maintainer, I want new and refreshed frontends to get this shell, and tests/docs to stay accurate.

#### Acceptance Criteria

1. WHEN `add-frontend` / `new --frontend` scaffolds THEN the new layouts and router structure SHALL be included.
2. WHEN `add-frontend --force` runs THEN shell templates SHALL refresh to the new layout (CRUD markers preserved/rewired per design).
3. WHEN `add-frontend-crud` / `--crud` runs THEN sidebar nav markers SHALL update correctly.
4. Generator/unit tests SHALL cover: layout files present; router uses dual layout pattern; nav markers still inject; `pnpm`-level full build MAY remain optional but TypeScript/template render smoke SHALL pass in existing test style.
5. MkDocs (`add-frontend` / related) SHALL briefly describe the app shell (auth vs app, sidebar, user menu).

## Non-Functional Requirements

### Code Architecture and Modularity
- Keep chrome in `layouts/`; pages stay content-only.
- Reuse Nuxt UI primitives (`UDashboard*`, `UNavigationMenu`, `USlideover`/`UDashboardSidebar`, `UDropdownMenu`, etc. as available in pinned `@nuxt/ui`) rather than bespoke CSS frameworks.
- Preserve CRUD marker contract (begin/end comments); update location + `crud_wire.py` together.

### Performance
- Layout chrome SHALL be light; no heavy client fetches on every navigation beyond identity if cached.
- Avoid layout shift when opening the mobile drawer.

### Security
- User menu SHALL NOT expose tokens; logout clears stored JWT material.
- Identity endpoint (if added) SHALL require authentication.

### Reliability
- Guest/auth route guards remain intact.
- Marker inject remains parse-safe if sidebar markup changes slightly (ensure helpers tolerate missing markers by inserting them once).

### Usability
- Touch-friendly menu control on mobile.
- Clear active route in sidebar.
- App name and user email readable at a glance.

## Out of scope

- Full design system / theming studio; dark-mode toggle (unless trivial with existing Nuxt UI defaults).
- Multi-tenant switcher UI; role-based nav hiding (API still enforces permissions).
- Replacing Vue Router or adopting full Nuxt.
- Rewriting all CRUD page internals beyond fitting the content slot (list/table UX polish is separate).
- Persist sidebar collapsed preference across sessions (nice-to-have; not required for v1 of this spec).
