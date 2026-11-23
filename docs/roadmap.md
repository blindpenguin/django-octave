# django-octave — enhancement ideas

Captured for later. Aligned with `.spec-workflow/steering/product.md`.  
Current package: **0.3.0**. Pick items and open a Spec Workflow spec before implementing.

## Already shipped

### Kickstart & domain generators

| Item | Role | Spec |
|------|------|------|
| `new` | Kickstart (DRF, Spectacular, JWT, DB, optional Docker / tenancy / Celery) | `project-kickstart` |
| `add` | Domain app + stubs; optional `--model` starter name | `add-app`, `generator-heuristics` |
| `add-model` | Field DSL (`--field` / `--fields`) + stub sync (FK/O2O/M2M) | `add-model` |
| `add-serializer` | Field control; PK or `--nested` relations | `add-api-parts`, `related-serializers` |
| `add-viewset` | ModelViewSet + router; stock/local permissions | `add-api-parts` |
| `add-permission` | Local `BasePermission` presets + optional viewset wire | `add-permission` |
| `add-action` | DRF `@action` (detail/list) on existing viewset | `add-action` |
| `add-admin` | Refined ModelAdmin | `add-admin` |
| `add-test` | factory-boy + pytest API/model stubs | `add-test` |
| `add-celery` / `add-task` | Opt-in Celery+Redis, Compose workers/Beat, task stubs | `add-celery` |

### Generator quality (benchmark-driven)

| Item | Role | Spec |
|------|------|------|
| Generator polish | Basename/`reverse`, cross-app SubFactories, AllowAny tests, class spacing | `generator-polish` |
| Generator heuristics | Nested serializer order, action tags, shared `api/` mounts, smarter `Meta.ordering`, import coalesce, `add --model` | `generator-heuristics` |
| Quiet local start | `staticfiles/.gitkeep`, local WhiteNoise finders; `UserFactory` via `factory.django.Password` | (follow-on to heuristics) |

### Docs & release

| Item | Role | Spec |
|------|------|------|
| User docs site | MkDocs Material under `docs/`, slim README, GitHub Pages | `user-docs` |
| Docs ↔ release | Pages deploys on release publish only (master/PR = strict build CI) | (follow-on to `user-docs`) |
| GitHub Release CI | Tag → build → smoke → Release assets | `github-release-ci` |
| Conventional Commits | Claude commit rule (`CLAUDE.md`) + `scripts/release-notes.py` wired into release body | (no formal spec) |

Verified by generators-only scaffolds: recipe / support-desk (API green), multitenancy (`mt_demo`), Docker+Postgres (`docker_demo`).

### Frontend

| Item | Role | Spec |
|------|------|------|
| `add-frontend` / `new --frontend` | Vue 3 + Vite + Vue Router + Nuxt UI shell; JWT login; optional register; CORS; Compose when Docker | `vue-nuxt-ui-frontend` |
| `add-frontend-crud` / `--crud` | Full CRUD Vue pages per ModelViewSet; FK label selects; bulk on add-frontend/new | `vue-frontend-crud` |
| App shell upgrade | AuthLayout + Nuxt UI Dashboard AppLayout (sidebar/drawer, user menu, nested router, content-only pages) | `vue-app-shell` |
| Responsive CRUD lists | Gmail-style vertical list rows instead of tables on generated list pages | `responsive-crud-list` |

**Not** full Nuxt. React / GraphQL / SSR remain out of scope. M2M editors are deferred.

## Suggested next work

### Multitenancy DX (from `mt_demo`)

1. ~~**Tenant-aware factories & smoke tests**~~ — done (`fix-multitenancy-jwt`)  
2. ~~**Tenant test fixtures**~~ — done (`fix-multitenancy-jwt`)  

### Kickstart / project quality

3. **Hardening pack** — DRF throttling / rate limiting; tighten security defaults where needed  
4. **Observability** — optional Sentry wiring  
5. **Health/readiness endpoints** — simple ops routes in `apps.core`  
6. **CI for generated projects** — GitHub Actions (pytest/ruff) template when opted in  

### Generator DX

7. **`check` / `doctor`** — validate an octave project (layout, `INSTALLED_APPS`, missing stubs)  
8. **`upgrade-templates`** — refresh generated files from newer octave versions (diff-based / careful)  
9. **PyPI Trusted Publishing** — follow-on to GitHub Release CI  

### Known gaps (found during the security review)

None of these is a vulnerability; each is something users will run into. The list is ordered by how likely that is.

10. **SPA tenant picker** — with `--multitenancy --frontend` the generated SPA never sends `X-Tenant-ID`, so every tenant endpoint it calls (CRUD pages, the user list) answers `403`. Needs a way to list the user's tenants (for example `GET /api/tenants/` from the memberships), a picker in the app layout, the chosen tenant remembered in the client, and the header added in `api/client.ts`. Today this is only documented in `docs/concepts/multitenancy.md` ("Known limitations").  
11. **`related_name` in the field syntax** — `name:type[:options]` has no `related_name`, so two foreign keys from one model to the same target (for example `owner:fk:to=users.User` and `assignee:fk:to=users.User`) generate a model that fails Django's system check (`fields.E304`, reverse accessor clash). Reproduce: `add-model notes Note --fields "title:char,owner:fk:to=users.User,assignee:fk:to=users.User"`, then `manage.py check`. Suggested: a validated `related_name=` option (identifier or `+`), and/or generate `related_name="+"` automatically when a model has more than one foreign key to the same target. Workaround today: edit the generated model by hand.  
12. **Pagination for list endpoints** — generated viewsets return every row (no `DEFAULT_PAGINATION_CLASS`), which is an availability risk on large tables. It was left out deliberately: the generated SPA list pages would silently show only the first page. Do both together: DRF `PageNumberPagination` with a bounded page size, and paging controls in the SPA list view.  
13. **Blank-line churn when a class is re-inserted** — `add-permission ... --force` (and any command that replaces a class through `upsert_class`) adds one extra blank line in front of the regenerated class on every run. Cosmetic and pre-existing; found while checking idempotency of the owner wiring. Reproduce: run `add-permission <app> <Class> --preset owner --force` twice and diff `permissions.py`. Fix in `models_gen/cst_util.py` (`upsert_class` / `_with_blank_leading`): normalise to exactly two blank lines.  

## Suggested priority

1. `doctor` / `check` · hardening · Sentry / health  
2. Generated-project CI · PyPI Trusted Publishing · `upgrade-templates`  

Approvals: `./scripts/spec-dashboard.sh` → Spec Workflow dashboard.

## Explicit non-goals (still)

- Cloud deploy generators  
- GraphQL  
- Admin UI themes  
- Schema-based multitenancy packages  
- Adding multitenancy to an already-generated project  
- Full Nuxt as the frontend host  
- React / non-Vue SPA frameworks  
- Celery as a **required** default (optional `add-celery` is in scope)  

## How to use this list

1. Choose one item (or a tight pair).  
2. Create a Spec Workflow spec (`requirements` → `design` → `tasks`).  
3. Implement via MCP tasks; move finished items into **Already shipped** and refresh priority.  
4. Prefer Conventional Commits (`feat` / `fix` / `docs` / …) so release notes stay extractable.
