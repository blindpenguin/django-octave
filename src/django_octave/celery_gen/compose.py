"""Inject Redis / Celery worker / Beat services into docker-compose.yml."""

from __future__ import annotations

from pathlib import Path

COMPOSE_MARKER_BEGIN = "# --- django-octave celery begin ---"
COMPOSE_MARKER_END = "# --- django-octave celery end ---"


class ComposeInjectError(ValueError):
    """Raised when compose injection cannot complete safely."""


def build_compose_services(*, has_db: bool, has_web: bool) -> str:
    """Return indented YAML service block (under ``services:``)."""
    depends_worker: list[str] = ["redis"]
    if has_web:
        depends_worker.append("web")
    if has_db:
        depends_worker.append("db")
    worker_deps = "\n".join(f"      - {d}" for d in depends_worker)
    return f"""{COMPOSE_MARKER_BEGIN}
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  worker:
    build: .
    command: uv run celery -A config worker -l INFO
    env_file:
      - .env
    volumes:
      - .:/app
    depends_on:
{worker_deps}
    environment:
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0

  beat:
    build: .
    command: uv run celery -A config beat -l INFO
    env_file:
      - .env
    volumes:
      - .:/app
    depends_on:
      - redis
      - worker
    environment:
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0
{COMPOSE_MARKER_END}
"""


def _services_body_bounds(text: str) -> tuple[int, int]:
    """Return (start, end) indices of content under top-level ``services:``.

    End is the start of the next top-level key (e.g. ``volumes:``) or EOF.
    """
    lines = text.splitlines(keepends=True)
    start_idx: int | None = None
    for i, line in enumerate(lines):
        if line.rstrip() == "services:" or line.startswith("services:"):
            start_idx = i + 1
            break
    if start_idx is None:
        raise ComposeInjectError("No top-level 'services:' key found in compose file")

    end_idx = len(lines)
    for i in range(start_idx, len(lines)):
        line = lines[i]
        if (
            line.strip()
            and not line.startswith((" ", "\t"))
            and not line.startswith("#")
        ):
            # next top-level key
            end_idx = i
            break
    start = sum(len(lines[i]) for i in range(start_idx))
    # recalculate properly
    start = sum(len(x) for x in lines[:start_idx])
    end = sum(len(x) for x in lines[:end_idx])
    return start, end


def inject_compose_services(compose_path: Path, *, force: bool = False) -> bool:
    """Inject celery services into ``compose_path``.

    Returns True if the file was modified.
    """
    if not compose_path.is_file():
        return False

    text = compose_path.read_text(encoding="utf-8")
    has_db = bool("\n  db:" in text or text.startswith("  db:") or "\n  db:\n" in text)
    # also match "  db:" at start of services body
    has_db = "  db:" in text
    has_web = "  web:" in text

    block = build_compose_services(has_db=has_db, has_web=has_web)
    if not block.endswith("\n"):
        block += "\n"

    if COMPOSE_MARKER_BEGIN in text:
        if not force:
            return False
        start = text.index(COMPOSE_MARKER_BEGIN)
        end = text.index(COMPOSE_MARKER_END) + len(COMPOSE_MARKER_END)
        if end < len(text) and text[end] == "\n":
            end += 1
        text = text[:start] + block + text[end:]
        compose_path.write_text(text, encoding="utf-8")
        return True

    # Refuse if redis/worker/beat already present without markers
    if ("  redis:" in text or "  worker:" in text or "  beat:" in text) and not force:
        raise ComposeInjectError(
            f"{compose_path}: redis/worker/beat already present without "
            "django-octave markers. Use --force to replace via markers."
        )

    # Insert before next top-level key after services, or at end of services body
    try:
        body_start, body_end = _services_body_bounds(text)
    except ComposeInjectError:
        raise

    # Insert at end of services body (before volumes etc.)
    insert_at = body_end
    # ensure newline before block
    prefix = ""
    if insert_at > 0 and text[insert_at - 1] != "\n":
        prefix = "\n"
    elif insert_at > 0 and text[insert_at - 1] == "\n":
        # add blank line separation if previous line isn't blank
        pass
    if insert_at < len(text) and not text[insert_at:].startswith("\n") and prefix == "":
        # keep existing
        pass
    text = text[:insert_at] + prefix + "\n" + block + text[insert_at:]
    compose_path.write_text(text, encoding="utf-8")
    return True
