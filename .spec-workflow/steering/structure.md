# Project Structure

## Directory Organization

### Generator package (this repository)

```
django-octave/
├── src/django_octave/           # Installable package
│   ├── __init__.py
│   ├── cli.py                   # Typer app / entrypoints
│   ├── commands/                # new, add, … subcommands
│   ├── prompts/                 # Interactive prompt flows (Rich)
│   ├── rendering/               # Jinja2 env, context, writers
│   └── templates/               # Jinja2 project & app templates
│       ├── project/             # Full project skeleton
│       └── app/                 # Single Django app skeleton
├── tests/                       # pytest suite (mirrors package)
├── .spec-workflow/              # Spec / steering artifacts
├── .cursor/rules/               # Agent rules
├── pyproject.toml
├── README.md
└── LICENSE                      # GPL-3.0
```

### Generated Django project (output of `django-octave new`)

Classic Django layout with apps under `apps/`, plus a required `core` app:

```
myproject/
├── manage.py
├── pyproject.toml               # uv-managed; pinned opinionated deps
├── .python-version
├── .env.example
├── README.md
├── config/                      # Django project package (settings, urls, wsgi/asgi)
│   ├── __init__.py
│   ├── settings/                # env-split settings (base/local/prod) via django-environ
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── __init__.py
│   ├── core/                    # Always created — shared primitives
│   │   ├── models.py            # e.g. TimeStampedModel
│   │   ├── apps.py
│   │   └── ...
│   └── <user_apps>/             # Domain apps (via new or django-octave add)
├── tests/                       # Project tests (pytest-django)
├── Dockerfile                   # Present if Docker opted in
├── docker-compose.yml           # Dev-oriented Compose (if Docker)
├── docker-compose.prod.yml      # Prod-oriented Compose (if Docker)
└── ...                          # Ruff/pytest config as agreed in templates
```

When multitenancy is enabled at create time, tenant models, middleware, and managers live primarily under `apps/core/` (and settings/urls wiring under `config/`).

## Naming Conventions

### Files (generator + generated Python)

- **Modules / packages**: `snake_case`
- **Django apps**: short `snake_case` under `apps/`
- **Templates (Jinja2)**: mirror destination paths; use `.j2` suffix where helpful
- **Tests**: `test_*.py` under `tests/`, mirroring package layout
- **Specs**: kebab-case folder names under `.spec-workflow/specs/`

### Code

- **Classes / models**: `PascalCase` (singular model names)
- **Functions / methods / fields**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **CLI commands**: Typer subcommands as kebab-case user-facing names (`new`, `add`)

## Import Patterns

### Import Order

Left to Ruff (`isort` rules). Prefer:

1. Stdlib
2. Third-party
3. First-party (`django_octave`, or generated `config` / `apps.*`)

### Module / Package Organization

- **Generator**: absolute imports from `django_octave.*`
- **Generated projects**: import apps as `apps.core`, `apps.<name>` — ensure `apps` is a package and `INSTALLED_APPS` uses full paths
- Avoid cross-app deep imports; shared types/models belong in `apps.core`

## Code Structure Patterns

### Generator modules

1. CLI parses flags / runs prompts → builds a typed context object
2. Renderer applies Jinja2 templates with that context (conditionals: docker, database, multitenancy)
3. Post-steps: e.g. hint to `uv sync`, migrate, runserver / compose up

### Generated Django apps

Follow project Django rules:

- Models → managers/querysets for single-model logic
- `services.py` for writes / use-cases; optional `selectors.py` for reads
- Thin viewsets; Spectacular annotations co-located with API layer
- `core` holds abstract bases (`TimeStampedModel`, tenant bases when enabled)

### File Organization Principles

- One clear responsibility per module
- Templates colocated by output artifact (`project/` vs `app/`)
- Feature flags in generation expressed as Jinja conditionals, not duplicate full trees when avoidable

## Code Organization Principles

1. **Single responsibility**: generator commands vs rendering vs templates stay separated
2. **Modularity**: new generators (`add` model/api later) plug in without rewriting `new`
3. **Testability**: render contexts and template output are unit-testable without network
4. **Consistency**: generated projects always get `config/`, `apps/`, and `apps.core`

## Module Boundaries

| Boundary | Rule |
|----------|------|
| **Generator vs generated** | No runtime dependency from generated apps back to django-octave |
| **`config` vs `apps`** | `config` = settings/urls/ASGI/WSGI only; domain code in `apps.*` |
| **`apps.core` vs domain apps** | Generic shared primitives in `core`; business domains in their own apps |
| **Multitenancy** | Implemented in `core` + settings middleware; domain models opt into tenant scoping |
| **Docker** | Optional artifacts only; absence must not break non-Docker workflows |
| **Public CLI** | `django-octave` entrypoint is the supported UX; internal modules may change |

## Code Size Guidelines

- Prefer focused modules over large “god” CLI files — split commands and prompt flows
- Keep Jinja templates readable; extract macros/partials for repeated blocks (settings snippets, Docker stages)
- Nesting: avoid deep conditional template sprawl; prefer small partials toggled from context flags

## Documentation Standards

- Generator: README with install, `new` / `add` examples (interactive + flags), option matrix (DB, Docker, multitenancy)
- Generated project: README with how to run (uv / Docker), env vars, OpenAPI URL, migrate/createuser
- Public Python APIs in the generator: typed signatures; docstrings on CLI commands
- Steering and specs live under `.spec-workflow/`; implementation under `src/` and `tests/`
