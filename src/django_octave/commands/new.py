"""`django-octave new` — create an opinionated Django REST API project."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from django_octave.cli import app
from django_octave.options import DatabaseChoice

console = Console()
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
    frontend: Annotated[
        bool | None,
        typer.Option(
            "--frontend/--no-frontend",
            help="Scaffold Vue + Nuxt UI frontend after create.",
        ),
    ] = None,
    register: Annotated[
        bool | None,
        typer.Option(
            "--register/--no-register",
            help="With --frontend: include signup page + registration API.",
        ),
    ] = None,
    crud: Annotated[
        bool | None,
        typer.Option(
            "--crud/--no-crud",
            help="With --frontend: generate Vue CRUD for all ModelViewSets.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help=(
                "Generate into a non-empty directory: generated files are overwritten, "
                "everything else is kept."
            ),
        ),
    ] = False,
    celery: Annotated[
        bool,
        typer.Option(
            "--celery/--no-celery",
            help="Wire Celery + Redis after project create (default: off).",
        ),
    ] = False,
) -> None:
    """Create a production-ready Django REST API project."""
    from django_octave.celery_gen import CelerySetupError, setup_celery
    from django_octave.frontend_gen import (
        ComposeInjectError,
        CrudSetupError,
        DjangoPatchError,
        FrontendSetupError,
        generate_crud_all,
        setup_frontend,
    )
    from django_octave.frontend_gen.crud_wire import CrudWireError
    from django_octave.prompts.new_project import resolve_new_project_options
    from django_octave.rendering.context import ProjectContext
    from django_octave.rendering.summary import print_next_steps
    from django_octave.rendering.writer import TargetExistsError, render_project_report

    options = resolve_new_project_options(
        name=name,
        path=path,
        database=database,
        docker=docker,
        multitenancy=multitenancy,
        frontend=frontend,
        register=register,
        crud=crud,
        force=force,
    )
    try:
        ctx = ProjectContext.from_options(options)
        report = render_project_report(ctx)
    except (TargetExistsError, NotADirectoryError, ValueError) as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    if report.overwritten:
        console.print(
            f"[yellow]Overwrote {report.overwritten} existing file(s); "
            "files outside the generated tree were kept.[/yellow]"
        )

    if options.frontend:
        try:
            setup_frontend(
                ctx.target_dir,
                include_register=options.register,
                project_name=ctx.project_name,
                project_slug_name=ctx.project_slug,
            )
        except (
            FrontendSetupError,
            DjangoPatchError,
            ComposeInjectError,
            FileExistsError,
            ValueError,
        ) as exc:
            err_console.print(f"[red]Frontend setup failed: {exc}[/red]")
            raise typer.Exit(code=1) from exc
        if options.crud:
            try:
                generate_crud_all(ctx.target_dir, force=False)
            except (CrudSetupError, CrudWireError, ValueError) as exc:
                err_console.print(f"[red]CRUD generation failed: {exc}[/red]")
                raise typer.Exit(code=1) from exc

    if celery:
        try:
            setup_celery(ctx.target_dir)
        except (CelerySetupError, FileExistsError, ValueError) as exc:
            err_console.print(f"[red]Celery setup failed: {exc}[/red]")
            raise typer.Exit(code=1) from exc

    print_next_steps(ctx)
