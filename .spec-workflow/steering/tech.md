# Technology Stack

## Project Type

Python **CLI generator package** (distributed as `django-octave`) that scaffolds opinionated **Django REST API** applications. Two layers:

1. **Generator** (this repo): installable package + CLI.
2. **Generated projects**: standalone Django apps produced by the CLI.

## Core Technologies

### Primary Language(s)

- **Language**: Python **3.14+** for the generator package; generated projects target the **latest stable Django** and the **newest Python version that Django officially supports** at release time.
- **Package management**: **uv** for the generator and for generated projects.
- **Build backend (generator)**: `uv_build` / `pyproject.toml` as already established in this repo.

### Key Dependencies / Libraries

#### Generator package

| Library | Purpose |
|---------|---------|
| **Typer** | CLI (subcommands, flags, help) |
| **Rich** | Terminal output and interactive prompts |
| **Jinja2** | Project/app templates shipped inside the package |

#### Always included in generated projects

| Library | Purpose |
|---------|---------|
| **Django** | Web framework (latest stable) |
| **djangorestframework** | REST API |
| **drf-spectacular** (+ sidecar) | OpenAPI schema + Swagger/ReDoc |
| **djangorestframework-simplejwt** | JWT authentication |
| **django-filter** | Filtering for viewsets |
| **django-cors-headers** | CORS for API clients |
| **django-environ** | Env-based settings |
| **WhiteNoise** | Static files in production |
| **Gunicorn** | Production WSGI server |
| **Ruff** | Lint + format |
| **pytest**, **pytest-django**, **factory-boy**, **pytest-cov** | Testing |

#### Database drivers (chosen at create time)

| Choice | Driver / notes |
|--------|----------------|
| **SQLite** | Built-in; default for quick starts |
| **PostgreSQL** | `psycopg` (v3) |
| **MariaDB** | `mysqlclient` or equivalent MariaDB-capable driver |

### Application Architecture

- **Generator**: Template-driven CLI; renders Jinja2 trees from `src/django_octave/templates/` into a target directory; no runtime coupling to generated apps after create.
- **Generated app**: Monolithic Django project, API-first:
  - Thin views/viewsets → services/selectors for writes/reads (per project Django rules).
  - Custom user model from day one.
  - `apps.core` for shared abstract models and cross-cutting primitives.
  - Optional **row-level multitenancy** (first-party): tenant FK + scoped managers/middleware/auth integration — rolled in-house for full control. Opt-in **only at project creation**.

### Data Storage

- **Primary storage**: User-selected SQLite | PostgreSQL | MariaDB.
- **Caching**: Not required in v1 defaults (Django local-memory / none); document how to add Redis later if needed.
- **Data formats**: JSON APIs; OpenAPI schema as the contract.

### External Integrations

- **APIs**: Generated projects expose REST + OpenAPI; no mandated third-party SaaS.
- **Protocols**: HTTP/REST.
- **Authentication**: JWT (SimpleJWT) + Django permissions; custom user model.

### Monitoring & Dashboard Technologies

- Not part of the generator product. Generated projects may later add Sentry/etc.; not a create-time requirement for v1.

## Development Environment

### Build & Development Tools

- **Package management**: uv (`uv sync`, `uv add`, `uv run`)
- **CLI entry**: `django-octave` → `django_octave` package
- **Templates**: Jinja2 files inside the package (not an external Cookiecutter repo)
- **Docker (optional at create)**:
  - **Dev**: Compose with app + DB (when not SQLite), hot-reload friendly workflow, `uv`
  - **Prod**: Production Dockerfile + Compose (Gunicorn, env files, non-dev settings)

### Code Quality Tools

- **Static analysis / formatting**: Ruff (generator + generated projects)
- **Testing**: pytest (+ pytest-django in generated projects)
- **Docs**: OpenAPI via Spectacular in generated apps; MkDocs Material (`docs/`, `mkdocs.yml`) + slim README for the generator

### Version Control & Collaboration

- **VCS**: Git
- **License**: **GPL-3.0**
- **Branching**: Prefer simple trunk/GitHub-flow style for this package

## Deployment & Distribution

- **Generator distribution**: PyPI-oriented Python package (`pip`/`uv` install); GPL-3.0.
- **Generated apps**: User-owned codebases; django-octave does **not** generate cloud-provider deploy pipelines.
- **Installation requirements**: Python + uv; Docker optional if user opted in.

## Technical Requirements & Constraints

### Performance Requirements

- CLI generation should complete quickly for a full project tree (seconds, not minutes).
- Generated API defaults should be suitable for solo/small production loads without premature optimization.

### Compatibility Requirements

- **Platform**: Linux/macOS primary; Windows best-effort.
- **Django/Python**: Pin generated deps to current stable at generator release; document upgrade policy.
- **Standards**: OpenAPI 3 via drf-spectacular.

### Security & Compliance

- Env-based secrets; never commit `.env` / credentials.
- Production security settings enabled in prod config (HTTPS headers, cookie flags, `DEBUG=False`, etc.).
- JWT + permission classes as the default API auth story.
- Multitenancy (when enabled): enforce tenant isolation at queryset/manager layer (row-level); document failure modes.

### Scalability & Reliability

- Generated projects are single-deploy monoliths; horizontal scale is the user’s ops concern.
- Docker prod setup should be a solid baseline (process model, static files, DB connectivity), not a full orchestrator.

## Technical Decisions & Rationale

### Decision Log

1. **Typer (+ Rich) over Click/argparse**: Type-hint CLI, excellent subcommands/help, Rich prompts for interactive mode; argparse is too weak for dual interactive/flag UX; Click works but Typer is the better modern default on Python 3.14+.
2. **Jinja2 templates inside the package**: Single distributable artifact; no Cookiecutter network/git dependency at generate time; full control over partials and conditionals (Docker, DB, multitenancy).
3. **Opinionated always-on API stack**: Solo devs want decisions made — DRF, Spectacular, SimpleJWT, filter, CORS, environ, WhiteNoise, Gunicorn, pytest, Ruff, uv.
4. **DB choices limited to SQLite / PostgreSQL / MariaDB**: Covers local, production SQL, and MariaDB shops without maintaining a long driver matrix.
5. **First-party row-level multitenancy**: Full control over models, middleware, and manager semantics; avoid schema-based tenancy and heavy third-party coupling. Create-time only for v1.
6. **Docker = both dev and prod when enabled**: Matches “production-ready” promise; uv in images for consistency with local workflow.
7. **No GraphQL / no admin themes / no cloud deploy generators**: Keeps scope on REST kickstart quality.
8. **GPL-3.0**: Copyleft license for the generator package itself.

## Known Limitations

- **Multitenancy not retrofittable via CLI in v1**: Must choose at `new`; document manual migration path later if demanded.
- **No async/Celery defaults**: Keeps the first project lean; workers are a future optional pack.
- **MariaDB driver pinning**: May need CI verification across OS images when Docker is enabled.
- **Windows Docker/path quirks**: Best-effort; primary verification on Linux.
