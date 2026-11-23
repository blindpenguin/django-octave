# Docker

Docker is **optional** at `django-octave new` (`--docker` / `--no-docker`).

When enabled, the project includes:

- `Dockerfile` with a `dev` stage and a minimal production `runtime` stage
- `docker-compose.yml` — local web (+ DB when not SQLite)
- `docker-compose.prod.yml` — production-oriented Compose

## Image stages

| Stage | Used by | Contents |
|-------|---------|----------|
| `dev` | `docker-compose.yml`, injected Celery services (`target: dev`) | uv, build tools, dev dependencies. The project is bind-mounted and run with `uv run`. |
| `builder` | build only | Compilers and `uv`; creates the virtualenv without dev dependencies. |
| `runtime` (default, last) | `docker build .`, `docker-compose.prod.yml` | Slim Python image, the virtualenv, your code, collected static files. No compilers, `curl` or `uv`. Runs as user `app` and starts Gunicorn directly. |

```bash
docker build .                  # production image
docker build --target dev .     # development image
```

The production image runs `collectstatic` while it is built, so `/admin/` works out of the box (WhiteNoise's manifest storage needs the collected files). The command uses placeholder values on that single `RUN` line (a dummy secret key, a placeholder host and a throw-away SQLite URL). They are not stored in the image environment and no database is contacted. If `collectstatic` fails, the build fails.

### Lock file

Run `uv lock` once and commit `uv.lock`. With a lock file the build installs exactly those versions (`uv sync --locked`); without one it still builds, but resolves fresh versions each time.

### Configuration at runtime

Pass configuration as environment variables, for example via `env_file: .env` in Compose. Prod settings need `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` and refuse to start without them. See [Security](security.md).

## Typical local flow

```bash
cp .env.example .env
docker compose up --build
```

Adjust env vars for Postgres/MariaDB credentials to match Compose service names.

## Celery + Compose

If you later run [`add-celery`](../commands/add-celery.md), octave injects `redis`, `worker`, and `beat` services into `docker-compose.yml` when that file exists. Broker URLs under Compose should use the service hostname, e.g. `redis://redis:6379/0` (injected services set this via `environment`).

## Without Docker

Omit Docker at create time and run with `uv` + a local database as usual. You can still develop against SQLite with zero containers.
