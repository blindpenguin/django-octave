"""``django-octave add-model`` — add a model with fields and sync API stubs."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown

from django_octave.cli import app
from django_octave.fields.parser import (
    FieldParseError,
    parse_fields,
    split_compact_fields,
)
from django_octave.models_gen.api_sync import sync_api_stubs
from django_octave.models_gen.writer import (
    ModelExistsError,
    ModelWriteError,
    write_model,
)
from django_octave.naming import (
    InvalidAppNameError,
    InvalidModelNameError,
    validate_app_name,
    validate_model_name,
)
from django_octave.project.detect import NotOctaveProjectError, detect_project

err_console = Console(stderr=True)
console = Console()


@app.command("add-model")
def add_model_cmd(
    app_name: Annotated[
        str | None,
        typer.Argument(help="Existing app under apps/."),
    ] = None,
    model_name: Annotated[
        str | None,
        typer.Argument(help="Model class name (PascalCase)."),
    ] = None,
    field: Annotated[
        list[str] | None,
        typer.Option(
            "--field",
            "-f",
            help="Field as name:type[:options]. Repeatable. Default: name:char:max=255.",
        ),
    ] = None,
    fields: Annotated[
        str | None,
        typer.Option(
            "--fields",
            help=(
                "Compact comma-separated field specs "
                "(e.g. title:char:max=200,published:bool). "
                "May be combined with repeatable --field."
            ),
        ),
    ] = None,
    path: Annotated[
        Path,
        typer.Option("--path", help="Project root (default: current directory)."),
    ] = Path("."),
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing model and its stubs."),
    ] = False,
) -> None:
    """Add a Django model with fields and keep API stubs in sync."""
    from django_octave.prompts.add_model import resolve_add_model_options

    merged_fields = list(field or [])
    if fields is not None:
        merged_fields.extend(split_compact_fields(fields))

    options = resolve_add_model_options(
        app=app_name,
        model=model_name,
        fields=merged_fields,
        path=path,
        force=force,
    )
    try:
        project = detect_project(options.path)
        app = validate_app_name(options.app)
        model = validate_model_name(options.model)
        fields = parse_fields(options.fields)
        app_dir = project.apps_dir / app
        if not app_dir.is_dir():
            raise FileNotFoundError(
                f"App apps.{app} not found. Run: django-octave add {app}"
            )
        models_path = app_dir / "models.py"
        write_model(
            models_path,
            model_name=model,
            fields=fields,
            use_multitenancy=project.use_multitenancy,
            force=options.force,
        )
        sync_api_stubs(
            app_dir,
            app_name=app,
            model_name=model,
            fields=fields,
            force=options.force,
            use_multitenancy=project.use_multitenancy,
        )
    except (
        NotOctaveProjectError,
        InvalidAppNameError,
        InvalidModelNameError,
        FieldParseError,
        ModelExistsError,
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
                    f"# Added model `{model}` to `apps.{app}`",
                    "",
                    f"- Fields: {', '.join(f.name for f in fields)}",
                    "- Serializer / admin / viewset / router updated",
                    "",
                    "## Next steps",
                    "",
                    "```bash",
                    f"cd {project.root}",
                    f"uv run python manage.py makemigrations {app}",
                    "uv run python manage.py migrate",
                    "```",
                    "",
                ]
            )
        )
    )
