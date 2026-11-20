# Tasks Document

- [x] 1.0 Auth identity + AuthLayout
  - [x] 1.1 Persist email at login/logout in tokens + useAuth
    - Files: `templates/frontend/src/auth/tokens.ts.j2`, `useAuth.ts.j2`, tests asserting generated snippets
    - Store `octave_email` on login/register; clear on logout; export `getUserEmail`
    - Purpose: User menu identity without new API
    - _Leverage: existing token helpers_
    - _Requirements: 2.3–2.5_
    - _Prompt: Implement the task for spec vue-app-shell, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Auth client engineer | Task: Persist and clear display email with JWT helpers | Restrictions: No token logging; no /me endpoint required | Success: Generated useAuth/tokens include email helpers; unit/string tests pass | Log with log-implementation then mark [x] in tasks.md_

  - [x] 1.2 AuthLayout + guest page wiring
    - Files: `templates/frontend/src/layouts/AuthLayout.vue.j2`, update `LoginView.vue.j2` / `RegisterView.vue.j2` to be content-only (no full-page chrome duplication)
    - Centered guest chrome; pages keep card forms
    - Purpose: Separate auth experience
    - _Leverage: existing Login/Register UCard patterns_
    - _Requirements: 1.1_
    - _Prompt: Implement the task for spec vue-app-shell, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Vue layout engineer | Task: Add AuthLayout and slim guest pages | Restrictions: No sidebar on guest routes | Success: Templates render; login/register still usable | Log + mark complete_

- [x] 2.0 App shell layout + router
  - [x] 2.1 AppLayout with Nuxt UI Dashboard chrome
    - Files: `templates/frontend/src/layouts/AppLayout.vue.j2` (replace header-strip)
    - `UDashboardGroup` + sidebar + panel; navbar with project name + user dropdown (logout); `crudNavItems` JS marker region; Home + CRUD nav via `UNavigationMenu`; `h-dvh` / body scroll only
    - Purpose: Usable app chrome + responsive drawer (Nuxt default)
    - _Leverage: Nuxt UI dashboard docs; getUserEmail_
    - _Requirements: 1.2, 2.1–2.4, 3.1–3.4, 4.1–4.4, 5.1–5.3_
    - _Prompt: Implement the task for spec vue-app-shell, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Nuxt UI dashboard engineer | Task: Rebuild AppLayout as dashboard shell with sidebar markers and user menu | Restrictions: Prefer Nuxt UI primitives; keep marker begin/end strings stable once chosen | Success: Layout template complete with empty CRUD nav markers | Log + mark complete_

  - [x] 2.2 Nested Vue Router (auth vs app)
    - Files: `templates/frontend/src/router/index.ts.j2`
    - Guest routes under AuthLayout; authenticated parent AppLayout with children (home + CRUD marker block as child routes); guards unchanged in behavior
    - Purpose: Layouts applied once via router
    - _Leverage: existing beforeEach guards_
    - _Requirements: 1.2–1.3_
    - _Prompt: Implement the task for spec vue-app-shell, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Vue Router engineer | Task: Nest guest/auth routes under layouts | Restrictions: Do not break redirect-to-login; CRUD marker block must remain injectable | Success: Router template has nested structure + empty CRUD child markers | Log + mark complete_

  - [x] 2.3 Content-only Home + CRUD page templates
    - Files: `HomeView.vue.j2`, `templates/frontend_crud/pages/*.vue.j2`
    - Remove AppLayout import/wrappers from home and CRUD pages
    - Purpose: Pages fill panel body only
    - _Leverage: existing page content_
    - _Requirements: 1.4_
    - _Prompt: Implement the task for spec vue-app-shell, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Vue page engineer | Task: Strip layout wrappers from Home and CRUD pages | Restrictions: Keep CRUD behavior; no duplicate site headers | Success: Pages render without AppLayout; crud_pages tests updated | Log + mark complete_

- [x] 3.0 CRUD wire + generator tests/docs
  - [x] 3.1 Update crud_wire for child routes + JS nav items
    - Files: `frontend_gen/crud_wire.py`, `tests/frontend_gen/test_crud_wire.py`
    - New NAV markers (`// --- django-octave crud nav …`); `build_nav_body` emits `{ label, to }` entries; `build_routes_body` emits child route objects (`path: 'plural'`, …); ensure-insert for new AppLayout/router shapes
    - Purpose: CRUD generation fills sidebar + nested router
    - _Leverage: existing wire_crud API_
    - _Requirements: 3.1–3.2, 6.2–6.3_
    - _Prompt: Implement the task for spec vue-app-shell, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Generator integration engineer | Task: Adapt crud_wire to dashboard nav + nested routes | Restrictions: Parse-safe; do not wipe auth routes | Success: Unit tests on sample router/layout | Log + mark complete_

  - [x] 3.2 Docs + CliRunner / render test updates
    - Files: `docs/commands/add-frontend.md`, `docs/roadmap.md`, `tests/frontend_gen/*`, `tests/commands/test_add_frontend*.py` as needed
    - Document app shell; assert AuthLayout/AppLayout/markers; keep suite green
    - Purpose: Discoverability + regression safety
    - _Requirements: 6.1–6.5_
    - _Prompt: Implement the task for spec vue-app-shell, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Docs + QA | Task: Document shell and update generator tests | Restrictions: Keep tests reasonably fast | Success: Docs updated; full pytest green | Log + mark complete_
