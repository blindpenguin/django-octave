# django-octave — enhancement ideas

Captured for later. Aligned with `.spec-workflow/steering/product.md`.  
Current package: **0.2.2**. Pick items and open a Spec Workflow spec before implementing.

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

**Not** full Nuxt. React / GraphQL / SSR remain out of scope. M2M editors are deferred.

## Suggested next work

### Multitenancy DX (from `mt_demo`)

1. **Tenant-aware factories & smoke tests** — wire `tenant=` (and membership) in factories; stop blanket-skipping API tests when tenancy is on  
2. **Tenant test fixtures** — reusable `tenant` / `tenant_client` helpers in generated `conftest`  

### Kickstart / project quality

3. **Hardening pack** — DRF throttling / rate limiting; tighten security defaults where needed  
4. **Observability** — optional Sentry wiring  
5. **Health/readiness endpoints** — simple ops routes in `apps.core`  
6. **CI for generated projects** — GitHub Actions (pytest/ruff) template when opted in  

### Generator DX

7. **`check` / `doctor`** — validate an octave project (layout, `INSTALLED_APPS`, missing stubs)  
8. **`upgrade-templates`** — refresh generated files from newer octave versions (diff-based / careful)  
9. **PyPI Trusted Publishing** — follow-on to GitHub Release CI  

## Suggested priority

1. Tenant-aware test/factory DX (close the multitenancy smoke gap)  
2. `doctor` / `check` · hardening · Sentry / health  
3. Generated-project CI · PyPI Trusted Publishing · `upgrade-templates`  

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
