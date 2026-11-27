"""``django-octave add-celery`` — wire Celery + Redis into a project."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.markdown import Markdown

from django_octave.celery_gen import setup_celery
from django_octave.cli import app
from django_octave.commands._common import console, handle_errors
from django_octave.project.detect import detect_project


@app.command("add-celery")
def add_celery_cmd(
    path: Annotated[
        Path,
        typer.Option("--path", help="Project root (default: current directory)."),
    ] = Path("."),
    force: Annotated[
        bool,
        typer.Option("--force", help="Refresh Celery wiring even if already present."),
    ] = False,
) -> None:
    """Configure Celery, Redis broker settings, and optional Compose services."""
    from django_octave.prompts.add_celery import resolve_add_celery_options

    options = resolve_add_celery_options(path=path, force=force)
    with handle_errors():
        project = detect_project(options.path)
        written = setup_celery(project.root, force=options.force)

    rel = [p.relative_to(project.root) for p in written if p.exists()]
    lines = [
        "# Celery configured",
        "",
        *[f"- Updated `{r}`" for r in rel],
        "",
        "## Next steps",
        "",
        "```bash",
        "uv sync",
        "uv run celery -A config worker -l INFO",
        "uv run celery -A config beat -l INFO",
        "django-octave add-task blog send_digest --every 3600",
        "```",
        "",
        "Do not use `worker --beat` in production — run Beat as a separate process.",
        "",
    ]
    console.print(Markdown("\n".join(lines)))
