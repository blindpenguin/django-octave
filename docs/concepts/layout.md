# Project layout

Generated projects use a consistent shape:

```text
myproject/
├── manage.py
├── pyproject.toml
├── .env.example
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
└── tests/                  # pytest-django
```

## Conventions

| Area | Rule |
|------|------|
| Domain code | Live under `apps.<name>` |
| Shared bases | `apps.core` (e.g. `TimeStampedModel`) |
| Settings / URLs | `config/` only |
| Services | Prefer `services.py` for writes; thin viewsets |

## Next

- [add](../commands/add.md) — scaffold a domain app
- [add-model](../commands/add-model.md) — models + stub sync
