"""``django-octave add-celery`` — wire Celery + Redis into a project."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown

from django_octave.celery_gen import CeleryExistsError, CelerySetupError, setup_celery
from django_octave.celery_gen.compose import ComposeInjectError
from django_octave.cli import app
from django_octave.project.detect import NotOctaveProjectError, detect_project

err_console = Console(stderr=True)
console = Console()


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
    try:
        project = detect_project(options.path)
        written = setup_celery(project.root, force=options.force)
    except (
        NotOctaveProjectError,
        CeleryExistsError,
        CelerySetupError,
        ComposeInjectError,
        FileNotFoundError,
        ValueError,
    ) as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

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
