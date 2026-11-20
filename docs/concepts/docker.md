# Docker

Docker is **optional** at `django-octave new` (`--docker` / `--no-docker`).

When enabled, the project includes:

- `Dockerfile` (uv-based)
- `docker-compose.yml` — local web (+ DB when not SQLite)
- `docker-compose.prod.yml` — production-oriented Compose

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
