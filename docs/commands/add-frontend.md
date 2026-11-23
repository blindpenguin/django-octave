# add-frontend

Scaffold an optional **Vue 3 + Vite + Vue Router + Nuxt UI** SPA under `frontend/`, wired to SimpleJWT.

This is **not** full Nuxt (no Nitro / Nuxt file-based host) — only the `@nuxt/ui` Vite plugin.

## Examples

```bash
uv run django-octave add-frontend --no-register --no-crud
uv run django-octave add-frontend --register --crud --path /path/to/project
uv run django-octave add-frontend --register --no-crud --force
```

At create time:

```bash
uv run django-octave new myapi \
  -d sqlite \
  --no-docker \
  --no-multitenancy \
  --frontend \
  --no-register \
  --no-crud
```

Interactive runs prompt for frontend (on `new`), then registration and CRUD when frontend is enabled.

## Flags

| Option | Notes |
|--------|--------|
| `--register` / `--no-register` | Signup page + `POST /api/auth/register/` (required non-interactive) |
| `--crud` / `--no-crud` | Generate Vue CRUD for all discoverable ModelViewSets (required non-interactive) |
| `--force` | Refresh an existing `frontend/` (also refreshes CRUD pages when `--crud`) |
| `--path` | Project root (default: `.`) |

## Security notes

- Login, token refresh and registration are rate limited (default 10/min per client). `.env.example` gets `DJANGO_NUM_PROXIES=1`, because the SPA's nginx is a reverse proxy; see [Security](../concepts/security.md#rate-limits).
- `GET /api/users/` is tenant-scoped in multitenancy projects (see [Multitenancy](../concepts/multitenancy.md#the-user-list)).
- The SPA title comes from the README's first `# ` heading when it is a valid project name, otherwise from the project slug; see [Security](../concepts/security.md#project-names).
- Registration also rejects passwords that are too similar to the email.
- Tokens live in `localStorage`; the SPA's nginx sends basic security headers. Details in [Security](../concepts/security.md#the-generated-spa).

## What it writes

- `frontend/` — Vite + Vue + Nuxt UI shell (login, authenticated home; optional register)
- `apps/users/auth_api.py` — email JWT obtain + register view
- `config/urls.py` — email token view; optional register route
- `.env.example` — CORS origins for Vite (`5173`) and prod SPA (`8080`)
- If Compose exists: `frontend` service in `docker-compose.yml` (Vite) and `docker-compose.prod.yml` (nginx)
- With `--crud`: pages under `frontend/src/pages/<plural>/` plus router/nav wiring (see [add-frontend-crud](add-frontend-crud.md))

## App shell

Generated SPA uses two layouts:

- **AuthLayout** — centered guest chrome for `/login` (and optional `/register`); no sidebar
- **AppLayout** — Nuxt UI **Dashboard** chrome (`UDashboardGroup` + sidebar + panel): Home + CRUD items in the sidebar, project name in the navbar, user email dropdown with Log out

Authenticated routes nest under `AppLayout`; CRUD pages are **content-only** (no per-page header chrome). Scroll lives in the panel body; the shell uses `h-dvh`.

On `--force`, re-run CRUD (`--crud` or `add-frontend-crud`) so sidebar nav markers stay filled.

## Local run

```bash
# Terminal 1 — API
uv run python manage.py runserver

# Terminal 2 — SPA
cd frontend
pnpm install
pnpm dev
```

Copy `frontend/.env.example` → `frontend/.env` if needed (`VITE_API_BASE_URL=http://localhost:8000`).

## Docker

```bash
docker compose up web frontend
```

Prod compose builds `frontend/Dockerfile` and serves the SPA on port **8080**, proxying `/api/` to `web`.

## Auth

- Login always: `POST /api/auth/token/` with `{ "email", "password" }`
- Optional register: `POST /api/auth/register/` then auto-login
- User list for SPA FK selects: `GET /api/users/` (authenticated; `id` + `email`)
- Tokens stored in `localStorage` (`octave_access` / `octave_refresh`); display email in `octave_email` (cleared on logout) for the app-bar user menu

## Next

- [add-frontend-crud](add-frontend-crud.md) — per-model CRUD pages
- [new](new.md)
- [Docker](../concepts/docker.md)
