"""``django-octave add-viewset`` — create or refresh a ModelViewSet + router."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown

from django_octave.api_parts.serializer_gen import (
    SerializerExistsError,
    SerializerFieldError,
)
from django_octave.api_parts.viewset_gen import (
    ViewSetExistsError,
    ViewSetFieldError,
    ViewSetOptions,
    ViewSetPermissionError,
    write_viewset,
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
from django_octave.rollback import rollback_on_error
from django_octave.safe_names import validate_tag

err_console = Console(stderr=True)
console = Console()


@app.command("add-viewset")
def add_viewset_cmd(
    app_name: Annotated[
        str | None,
        typer.Argument(help="Existing app under apps/."),
    ] = None,
    model_name: Annotated[
        str | None,
        typer.Argument(help="Model class name (PascalCase)."),
    ] = None,
    permission: Annotated[
        str,
        typer.Option(
            "--permission",
            help=(
                "Permission class: IsAuthenticated, AllowAny, IsAdminUser, "
                "or a class in apps.<app>.permissions."
            ),
        ),
    ] = "IsAuthenticated",
    filter_fields: Annotated[
        str | None,
        typer.Option("--filter", help="Comma-separated filterset_fields."),
    ] = None,
    search: Annotated[
        str | None,
        typer.Option("--search", help="Comma-separated search_fields."),
    ] = None,
    ordering: Annotated[
        str | None,
        typer.Option("--ordering", help="Comma-separated ordering_fields."),
    ] = None,
    tag: Annotated[
        str | None,
        typer.Option("--tag", help="Spectacular tag (default: snake_case model)."),
    ] = None,
    path: Annotated[
        Path,
        typer.Option("--path", help="Project root (default: current directory)."),
    ] = Path("."),
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing viewset class."),
    ] = False,
) -> None:
    """Create or refresh a DRF ModelViewSet and ensure router registration."""
    from django_octave.prompts.add_viewset import resolve_add_viewset_options

    options = resolve_add_viewset_options(
        app=app_name,
        model=model_name,
        permission=permission,
        filters=filter_fields,
        search=search,
        ordering=ordering,
        tag=tag,
        path=path,
        force=force,
    )
    try:
        if options.tag is not None:
            validate_tag(options.tag)
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
        with rollback_on_error(project.root):
            views_path, urls_path = write_viewset(
                app_dir,
                options=ViewSetOptions(
                    app_name=app,
                    model_name=model,
                    permission=options.permission,
                    filters=csv_to_list(options.filters),
                    search=csv_to_list(options.search),
                    ordering=csv_to_list(options.ordering),
                    tag=options.tag,
                    force=options.force,
                    use_multitenancy=project.use_multitenancy,
                ),
            )
    except (
        NotOctaveProjectError,
        InvalidAppNameError,
        InvalidModelNameError,
        ViewSetExistsError,
        ViewSetPermissionError,
        ViewSetFieldError,
        SerializerExistsError,
        SerializerFieldError,
        ModelWriteError,
        FileNotFoundError,
        ValueError,
    ) as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(
        Markdown(
            "\n".join(
                [
                    f"# ViewSet `{model}ViewSet`",
                    "",
                    f"- Updated `{views_path.relative_to(project.root)}`",
                    f"- Router: `{urls_path.relative_to(project.root)}`",
                    f"- Permission: `{options.permission}`",
                    "",
                    "## Next steps",
                    "",
                    "```bash",
                    f"cd {project.root}",
                    "uv run python manage.py runserver",
                    "```",
                    "",
                ]
            )
        )
    )
