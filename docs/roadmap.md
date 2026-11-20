# django-octave — enhancement ideas

Captured for later. Aligned with `.spec-workflow/steering/product.md`.  
Pick items and open a Spec Workflow spec before implementing.

## Already shipped

| Item | Role | Spec |
|------|------|------|
| `new` | Kickstart project (DRF, Spectacular, JWT, DB, optional Docker/tenancy) | `project-kickstart` |
| `add` | Domain app + API stubs | `add-app` |
| `add-model` | Model + field DSL + stub sync (incl. FK/O2O/M2M) | `add-model` |
| `add-serializer` | ModelSerializer field control; PK or `--nested` relations | `add-api-parts`, `related-serializers` |
| `add-viewset` | ModelViewSet + router; auto-serializer; stock/local permissions | `add-api-parts` |
| `add-permission` | Local `BasePermission` presets + optional viewset wire | `add-permission` |
| `add-action` | Inject DRF `@action` (detail/list) onto existing viewset | `add-action` |
| `add-admin` | Refine ModelAdmin (display/search/filter/select_related) | `add-admin` |
| `add-test` | factory-boy + pytest API/model stubs | `add-test` |
| `add-celery` / `add-task` | Opt-in Celery+Redis, Compose workers/Beat, `@shared_task` stubs | `add-celery` |
| GitHub Release CI | Tag → build → smoke → GitHub Release assets | `github-release-ci` |

## Planned: Vue + Nuxt UI frontend scaffolding

**Product decision:** optional frontend is in scope. Stack is **Vue 3 + Vite + Vue Router + Nuxt UI** — the UI component library via `@nuxt/ui`’s Vite/Vue plugin. **Not** full Nuxt (no Nitro, no Nuxt file-based app host).

Official Vue install path: [@nuxt/ui Vue installation](https://ui.nuxt.com/docs/getting-started/installation/vue) (`@nuxt/ui` + `tailwindcss`, `ui()` Vite plugin, `vue-plugin`, `UApp`).

### Likely shape (to refine in a spec)

| Topic | Working assumption |
|-------|-------------------|
| Layout | `frontend/` beside Django (`config/`, `apps/`) |
| Entry | Opt-in at `new` (`--frontend` / prompt) and/or `django-octave add-frontend` for existing projects |
| Auth | Talk to existing SimpleJWT endpoints; login page + token storage + API client |
| CORS | Ensure generated Django CORS settings allow the Vite origin in dev |
| Docker | Optional: serve/build frontend in Compose when Docker was chosen |
| Depth (v1) | Shell app: router, Nuxt UI theme, auth against JWT, one authenticated home — not a full CRUD UI generator yet |

### Out of frontend scope (unless product changes again)

- Full Nuxt meta-framework  
- React / other SPA frameworks  
- GraphQL client  
- Server-side rendering as a requirement for v1  

### Spec name (when ready)

Suggested: `vue-nuxt-ui-frontend` (kebab-case).

## Suggested next work

### Frontend

1. Vue + Nuxt UI frontend scaffolding (`vue-nuxt-ui-frontend`)  

### Kickstart / project quality

2. **Hardening pack** — DRF throttling / rate limiting; tighten security defaults where needed  
3. **Observability** — optional Sentry wiring (steering “Potential Enhancements”)  
4. **Health/readiness endpoints** — simple ops routes in `apps.core`  
5. **CI for generated projects** — GitHub Actions (pytest/ruff) template when opted in  

### Generator DX

6. **`check` / `doctor`** — validate an octave project (layout, `INSTALLED_APPS`, missing stubs)  
7. **`upgrade-templates`** — refresh generated files from newer octave versions (diff-based / careful)  
8. **PyPI Trusted Publishing** — follow-on to GitHub Release CI  

## Suggested priority

1. Vue + Nuxt UI frontend scaffolding (`vue-nuxt-ui-frontend`)  
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
