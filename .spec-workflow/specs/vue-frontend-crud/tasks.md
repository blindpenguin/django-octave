# Tasks Document

- [x] 1.0 Discovery + field mapping
  - [x] 1.1 Resource discovery from viewsets/urls
    - Files: `src/django_octave/frontend_gen/crud_discover.py`, tests
    - Parse `apps/*/views.py` ModelViewSets + `apps/*/urls.py` `router.register` → `ResourceSpec` basics (app, model, plural, api path); soft-skip unresolved
    - Purpose: Single source for per-model and bulk
    - _Leverage: `naming.pluralize`, `pascal_to_snake`, CST/regex patterns from `cst_util`_
    - _Requirements: 1.4, 2.3–2.5, 4.1_
    - _Prompt: Implement the task for spec vue-frontend-crud, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python static-analysis engineer | Task: Implement crud_discover for ResourceSpec listing and single lookup | Restrictions: No Django runtime; soft-skip bulk failures | Success: Unit tests on fixture urls/views | Log with log-implementation then mark [x] in tasks.md_

  - [x] 1.2 CrudField mapping + FK label heuristic
    - Files: `src/django_octave/frontend_gen/crud_fields.py`, tests
    - Map `ModelFieldInfo` → `CrudField` list; omit M2M; readonly id/timestamps; FK related_plural + label_field heuristic; fallback PK input metadata when related unknown
    - Purpose: Deterministic forms/tables
    - _Leverage: `inspect.model_fields`_
    - _Requirements: 4.1–4.6_
    - _Prompt: Implement the task for spec vue-frontend-crud, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Schema/mapping engineer | Task: Implement crud_fields from ModelFieldInfo with FK heuristics | Restrictions: Omit M2M in v1; document skip | Success: Unit tests for scalar + FK + readonly | Log + mark complete_

- [x] 2.0 Page generation + SPA wiring
  - [x] 2.1 Jinja CRUD page templates + shared composable
    - Files: `src/django_octave/templates/frontend_crud/**`, `frontend_gen/crud_pages.py`
    - Render List/Detail/Create/Edit under `frontend/src/pages/<plural>/`; delete via confirm modal on Detail; `useCrudResource` composable + unwrapList; Nuxt UI; PATCH/POST/DELETE via apiJson
    - Purpose: Runnable CRUD UI
    - _Leverage: existing `api/client.ts`, Nuxt UI patterns from shell templates_
    - _Requirements: 1.2, 3.1–3.6, 3.8_
    - _Prompt: Implement the task for spec vue-frontend-crud, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Vue/Nuxt UI template engineer | Task: Add frontend_crud templates and crud_pages renderer | Restrictions: Not full Nuxt; no M2M editors; reuse apiFetch | Success: Render into tmpdir yields 4 pages + composable | Log + mark complete_

  - [x] 2.2 Router + AppLayout nav marker wiring
    - Files: `src/django_octave/frontend_gen/crud_wire.py`, tests; update shell templates if markers missing for fresh scaffolds
    - Inject/replace CRUD routes and nav links with markers; ensure shell `AppLayout`/`router` templates include empty marker regions going forward
    - Purpose: Reachable authenticated pages
    - _Leverage: celery/frontend compose marker style_
    - _Requirements: 3.7_
    - _Prompt: Implement the task for spec vue-frontend-crud, first run spec-workflow-guide to get the workflow guide then implement the task: Role: SPA integration engineer | Task: Marker-based router and nav inject | Restrictions: Parse-safe; do not wipe auth routes | Success: Unit tests on sample router/layout files | Log + mark complete_

  - [x] 2.3 `generate_crud` / `generate_crud_all` orchestrator + force/refuse
    - Files: `src/django_octave/frontend_gen/crud_setup.py`, `__init__.py` exports, tests
    - Gate on frontend/; refuse existing pages without force; bulk soft-skip; call discover→fields→pages→wire
    - Purpose: Shared entry for CLI and add-frontend
    - _Leverage: `scaffold_frontend` / `setup_frontend` patterns_
    - _Requirements: 1.3–1.5, 2.3–2.5_
    - _Prompt: Implement the task for spec vue-frontend-crud, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Generator architect | Task: Orchestrate generate_crud and generate_crud_all | Restrictions: Soft-skip in bulk; no Django runtime | Success: Fixture project generates Recipe CRUD files | Log + mark complete_

- [x] 3.0 CLI surface
  - [x] 3.1 `add-frontend-crud` command + prompts
    - Files: `commands/add_frontend_crud.py`, `prompts/add_frontend_crud.py`, `cli.py`
    - Dual UX; Rich next steps with routes
    - Purpose: Per-model entry point
    - _Leverage: `add_frontend` / `add_viewset` command patterns_
    - _Requirements: 1.1–1.6_
    - _Prompt: Implement the task for spec vue-frontend-crud, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI developer | Task: Wire add-frontend-crud | Restrictions: Thin command | Success: Listed in --help; flag modes work | Log + mark complete_

  - [x] 3.2 Extend `add-frontend` / `new` with `--crud` ask/flags
    - Files: `commands/add_frontend.py`, `prompts/add_frontend.py`, `prompts/new_project.py`, `commands/new.py`, tests that pass `--no-crud` where needed
    - After frontend setup, optionally `generate_crud_all`; interactive ask; non-interactive require flag when frontend on
    - Purpose: Bulk entry point
    - _Leverage: register flag dual UX_
    - _Requirements: 2.1–2.4_
    - _Prompt: Implement the task for spec vue-frontend-crud, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI developer | Task: Add --crud/--no-crud to add-frontend and new | Restrictions: crud only when frontend enabled | Success: Prompt/flag matrix + tests updated | Log + mark complete_

- [x] 4.0 Docs and integration tests
  - [x] 4.1 MkDocs + roadmap
    - Files: `docs/commands/add-frontend-crud.md`, update `add-frontend.md` / `new.md` / `roadmap.md` / `mkdocs.yml`
    - Document commands, FK selects, prerequisites
    - Purpose: Discoverability
    - _Requirements: 5.1, 5.3_
    - _Prompt: Implement the task for spec vue-frontend-crud, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Document frontend CRUD | Restrictions: MDX-safe | Success: Examples match CLI | Log + mark complete_

  - [x] 4.2 CliRunner integration matrix
    - Files: `tests/commands/test_add_frontend_crud.py` (+ extend add-frontend/new tests)
    - Cover help; generate; refuse; force; FK select smoke in generated CreateView; bulk --crud; missing frontend/viewset gates; full pytest green
    - Purpose: End-to-end confidence
    - _Requirements: 5.2_
    - _Prompt: Implement the task for spec vue-frontend-crud, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA | Task: Integration tests for CRUD generators | Restrictions: Keep reasonably fast | Success: Cases pass; suite green | Log + mark complete_
