# django-octave — enhancement ideas

Captured for later. Aligned with `.spec-workflow/steering/product.md`.  
Pick items and open a Spec Workflow spec before implementing.

## Already shipped

| Command | Role |
|---------|------|
| `new` | Kickstart project (DRF, Spectacular, JWT, DB, optional Docker/tenancy) |
| `add` | Domain app + API stubs |
| `add-model` | Model + field DSL + stub sync |
| `add-serializer` | ModelSerializer field control |
| `add-viewset` | ModelViewSet + router; auto-serializer |
| GitHub Release CI | Tag → build → smoke → GitHub Release assets |

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

## Suggested next work (backend / generator)

### Generators (`add-*` family)

1. **`add-action`** — custom `@action` on an existing viewset  
2. **`add-admin`** — regenerate/refine ModelAdmin (`list_display`, search, filters)  
3. **`add-test`** — pytest + factory stubs for a model/viewset  
4. **`add-permission`** — project-local permission class + wire into a viewset  
5. **Nested/related serializers** — **Done:** spec `related-serializers` (FK/O2O/M2M DSL + PK/`--nested` modes)

### Kickstart / project quality

6. **Hardening pack** — DRF throttling / rate limiting; tighten security defaults where needed  
7. **Observability** — optional Sentry wiring (steering “Potential Enhancements”)  
8. **Health/readiness endpoints** — simple ops routes in `apps.core`  
9. **CI for generated projects** — GitHub Actions (pytest/ruff) template when opted in  

### Generator DX

10. **`check` / `doctor`** — validate an octave project (layout, `INSTALLED_APPS`, missing stubs)  
11. **`upgrade-templates`** — refresh generated files from newer octave versions (diff-based / careful)  
12. **PyPI Trusted Publishing** — follow-on to GitHub Release CI  

## Suggested priority

1. ~~`related-serializers`~~ (shipped)  
2. `add-permission` → `add-action`  
3. `add-admin` / `add-test`  
4. Vue + Nuxt UI frontend scaffolding  
5. `doctor` / `check` · Sentry / hardening  

Also remind: Spec dashboard via `./scripts/spec-dashboard.sh` when approving.

## Explicit non-goals (still)

- Cloud deploy generators  
- GraphQL  
- Admin UI themes  
- Schema-based multitenancy packages  
- Adding multitenancy to an existing project  
- Full Nuxt as the frontend host  
- React / non-Vue SPA frameworks  
- Celery as a required default  

## How to use this list

1. Choose one item (or a tight pair).  
2. Create a Spec Workflow spec (`requirements` → `design` → `tasks`).  
3. Implement via MCP tasks; mark items here done or link the spec when useful.
