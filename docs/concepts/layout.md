# Project layout

Generated projects use a consistent shape:

```text
myproject/
├── manage.py
├── pyproject.toml
├── .env.example
├── .octave.toml            # generator version + options chosen (commit it)
├── staticfiles/            # empty STATIC_ROOT (.gitkeep) for WhiteNoise
├── config/                 # Django project package
│   ├── settings/           # base / local / prod (django-environ)
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── celery.py           # only after add-celery
├── apps/
│   ├── core/               # always present — shared primitives
│   ├── users/              # custom user model
│   └── <domain>/           # your apps (django-octave add)
├── frontend/               # optional — Vue + Nuxt UI SPA (add-frontend / --frontend)
└── tests/                  # pytest-django
```

## Conventions

| Area | Rule |
|------|------|
| Domain code | Live under `apps.<name>` |
| Shared bases | `apps.core` (e.g. `TimeStampedModel`) |
| Settings / URLs | `config/` only |
| API routes | Domain apps mount under shared `api/`; collections are `/api/<model_plural>/` |
| Static (local) | Finders + WhiteNoise; prod still uses compressed manifest storage |
| Services | Prefer `services.py` for writes; thin viewsets |

## Next

- [add](../commands/add.md) — scaffold a domain app
- [add-model](../commands/add-model.md) — models + stub sync
- [add-frontend](../commands/add-frontend.md) — optional Vue SPA
