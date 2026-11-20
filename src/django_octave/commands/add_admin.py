"""``django-octave add-admin`` — create or refresh a ModelAdmin."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown

from django_octave.api_parts.admin_gen import (
    AdminExistsError,
    AdminFieldError,
    AdminOptions,
    write_admin,
)
from django_octave.cli import app
from django_octave.models_gen.writer import ModelWriteError, model_exists
from django_octave.naming import (
    InvalidAppNameError,
    InvalidModelNameError,
    validate_app_name,
    validate_model_name,
)
from django_octave.project.detect import NotOctaveProjectError, detect_project
from django_octave.prompts.add_serializer import csv_to_list

err_console = Console(stderr=True)
console = Console()


@app.command("add-admin")
def add_admin_cmd(
    app_name: Annotated[
        str | None,
        typer.Argument(help="Existing app under apps/."),
    ] = None,
    model_name: Annotated[
        str | None,
        typer.Argument(help="Model class name (PascalCase)."),
    ] = None,
    list_display: Annotated[
        str | None,
        typer.Option(
            "--list-display",
            help="Comma-separated list_display (default: inspected heuristic).",
        ),
    ] = None,
    search: Annotated[
        str | None,
        typer.Option("--search", help="Comma-separated search_fields."),
    ] = None,
    list_filter: Annotated[
        str | None,
        typer.Option("--filter", help="Comma-separated list_filter."),
    ] = None,
    ordering: Annotated[
        str | None,
        typer.Option("--ordering", help="Comma-separated ModelAdmin.ordering."),
    ] = None,
    no_date_hierarchy: Annotated[
        bool,
        typer.Option(
            "--no-date-hierarchy",
            help="Omit date_hierarchy even when timestamps exist.",
        ),
    ] = False,
    path: Annotated[
        Path,
        typer.Option("--path", help="Project root (default: current directory)."),
    ] = Path("."),
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing ModelAdmin class."),
    ] = False,
) -> None:
    """Create or refresh a Django ModelAdmin for an existing model."""
    from django_octave.prompts.add_admin import resolve_add_admin_options

    options = resolve_add_admin_options(
        app=app_name,
        model=model_name,
        list_display=list_display,
        search=search,
        list_filter=list_filter,
        ordering=ordering,
        no_date_hierarchy=no_date_hierarchy,
        path=path,
        force=force,
    )
    try:
        project = detect_project(options.path)
        app = validate_app_name(options.app)
        model = validate_model_name(options.model)
        app_dir = project.apps_dir / app
        if not app_dir.is_dir():
            raise FileNotFoundError(
                f"App apps.{app} not found. Run: django-octave add {app}"
            )
        models_path = app_dir / "models.py"
        if not models_path.is_file():
            raise FileNotFoundError(f"models.py not found in apps.{app}")
        source = models_path.read_text(encoding="utf-8")
        if not model_exists(source, model):
            raise FileNotFoundError(
                f"Model {model} not found in apps.{app}.models. "
                f"Run: django-octave add-model {app} {model}"
            )
        admin_path = write_admin(
            app_dir,
            options=AdminOptions(
                app_name=app,
                model_name=model,
                list_display=csv_to_list(options.list_display),
                search=csv_to_list(options.search),
                list_filter=csv_to_list(options.list_filter),
                ordering=csv_to_list(options.ordering),
                date_hierarchy=options.date_hierarchy,
                force=options.force,
            ),
        )
    except (
        NotOctaveProjectError,
        InvalidAppNameError,
        InvalidModelNameError,
        AdminExistsError,
        AdminFieldError,
        ModelWriteError,
        FileNotFoundError,
        ValueError,
    ) as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    text = admin_path.read_text(encoding="utf-8")
    m = re.search(r"list_display\s*=\s*\(([^)]*)\)", text)
    n_display = (
        len([p for p in (m.group(1) if m else "").split(",") if p.strip()]) if m else 0
    )

    console.print(
        Markdown(
            "\n".join(
                [
                    f"# Admin `{model}Admin`",
                    "",
                    f"- Updated `{admin_path.relative_to(project.root)}`",
                    f"- `list_display`: {n_display} column(s)",
                    "",
                    "## Next steps",
                    "",
                    "```bash",
                    f"cd {project.root}",
                    "uv run python manage.py createsuperuser",
                    "uv run python manage.py runserver",
                    "# open /admin/",
                    "```",
                    "",
                ]
            )
        )
    )
