"""`django-octave new` — create an opinionated Django REST API project."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from django_octave.cli import app
from django_octave.options import DatabaseChoice

err_console = Console(stderr=True)


@app.command("new")
def new_project(
    name: Annotated[
        str | None,
        typer.Argument(help="Project directory name."),
    ] = None,
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            help="Parent directory for the project (default: current directory).",
        ),
    ] = Path("."),
    database: Annotated[
        DatabaseChoice | None,
        typer.Option(
            "--database",
            "-d",
            help="Database backend.",
            case_sensitive=False,
        ),
    ] = None,
    docker: Annotated[
        bool | None,
        typer.Option(
            "--docker/--no-docker",
            help="Include Dockerfile and Compose files for dev and prod.",
        ),
    ] = None,
    multitenancy: Annotated[
        bool | None,
        typer.Option(
            "--multitenancy/--no-multitenancy",
            help="Enable first-party row-level multitenancy.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Allow generating into a non-empty directory.",
        ),
    ] = False,
) -> None:
    """Create a production-ready Django REST API project."""
    from django_octave.prompts.new_project import resolve_new_project_options
    from django_octave.rendering.context import ProjectContext
    from django_octave.rendering.summary import print_next_steps
    from django_octave.rendering.writer import TargetExistsError, render_project

    options = resolve_new_project_options(
        name=name,
        path=path,
        database=database,
        docker=docker,
        multitenancy=multitenancy,
        force=force,
    )
    ctx = ProjectContext.from_options(options)
    try:
        render_project(ctx)
    except TargetExistsError as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    print_next_steps(ctx)
