"""Inject frontend services into docker-compose.yml / docker-compose.prod.yml."""

from __future__ import annotations

from pathlib import Path

COMPOSE_MARKER_BEGIN = "# --- django-octave frontend begin ---"
COMPOSE_MARKER_END = "# --- django-octave frontend end ---"


class ComposeInjectError(ValueError):
    """Raised when compose injection cannot complete safely."""


def build_dev_frontend_service(*, has_web: bool) -> str:
    """Vite dev server service block for ``docker-compose.yml``."""
    depends = (
        """
    depends_on:
      - web
"""
        if has_web
        else ""
    )
    return f"""{COMPOSE_MARKER_BEGIN}
  frontend:
    image: node:22-alpine
    working_dir: /app
    volumes:
      - ./frontend:/app
    ports:
      - "5173:5173"
    environment:
      VITE_API_BASE_URL: http://localhost:8000
    command: sh -c "corepack enable && pnpm install && pnpm dev --host 0.0.0.0 --port 5173"{depends}
{COMPOSE_MARKER_END}
"""


def build_prod_frontend_service(*, has_web: bool) -> str:
    """Production nginx SPA service for ``docker-compose.prod.yml``."""
    depends = (
        """
    depends_on:
      - web
"""
        if has_web
        else ""
    )
    return f"""{COMPOSE_MARKER_BEGIN}
  frontend:
    build:
      context: ./frontend
    ports:
      - "8080:80"{depends}
{COMPOSE_MARKER_END}
"""


def _services_body_bounds(text: str) -> tuple[int, int]:
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
            end_idx = i
            break
    start = sum(len(x) for x in lines[:start_idx])
    end = sum(len(x) for x in lines[:end_idx])
    return start, end


def inject_compose_frontend(
    compose_path: Path,
    *,
    prod: bool = False,
    force: bool = False,
) -> bool:
    """Inject frontend service into ``compose_path``.

    Returns True if the file was modified. Missing file → False (no error).
    """
    if not compose_path.is_file():
        return False

    text = compose_path.read_text(encoding="utf-8")
    has_web = "  web:" in text
    block = (
        build_prod_frontend_service(has_web=has_web)
        if prod
        else build_dev_frontend_service(has_web=has_web)
    )
    if not block.endswith("\n"):
        block += "\n"

    if COMPOSE_MARKER_BEGIN in text:
        if not force:
            return False
        start = text.index(COMPOSE_MARKER_BEGIN)
        end = text.index(COMPOSE_MARKER_END) + len(COMPOSE_MARKER_END)
        if end < len(text) and text[end] == "\n":
            end += 1
        compose_path.write_text(text[:start] + block + text[end:], encoding="utf-8")
        return True

    if "  frontend:" in text and not force:
        raise ComposeInjectError(
            f"{compose_path}: frontend service already present without "
            "django-octave markers. Use --force to replace via markers."
        )

    _body_start, body_end = _services_body_bounds(text)
    prefix = "\n" if body_end > 0 and text[body_end - 1] != "\n" else ""
    text = text[:body_end] + prefix + "\n" + block + text[body_end:]
    compose_path.write_text(text, encoding="utf-8")
    return True


def inject_project_compose(root: Path, *, force: bool = False) -> list[Path]:
    """Inject into dev and/or prod compose files when present."""
    written: list[Path] = []
    for path, is_prod in (
        (root / "docker-compose.yml", False),
        (root / "docker-compose.prod.yml", True),
    ):
        if inject_compose_frontend(path, prod=is_prod, force=force):
            written.append(path)
    return written
