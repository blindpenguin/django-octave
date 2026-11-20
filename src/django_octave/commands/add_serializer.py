"""``django-octave add-serializer`` — create or refresh a ModelSerializer."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown

from django_octave.api_parts.serializer_gen import (
    SerializerExistsError,
    SerializerFieldError,
    SerializerOptions,
    parse_nested_option,
    write_serializer,
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


@app.command("add-serializer")
def add_serializer_cmd(
    app_name: Annotated[
        str | None,
        typer.Argument(help="Existing app under apps/."),
    ] = None,
    model_name: Annotated[
        str | None,
        typer.Argument(help="Model class name (PascalCase)."),
    ] = None,
    fields: Annotated[
        str | None,
        typer.Option("--fields", help="Comma-separated Meta.fields (default: inspected)."),
    ] = None,
    read_only: Annotated[
        str | None,
        typer.Option("--read-only", help="Comma-separated read_only_fields."),
    ] = None,
    no_id: Annotated[
        bool,
        typer.Option("--no-id", help="Omit id from Meta.fields."),
    ] = False,
    nested: Annotated[
        list[str] | None,
        typer.Option(
            "--nested",
            "-n",
            help="Relation to nest read-only (repeatable). Form: field or field=ClassName.",
        ),
    ] = None,
    path: Annotated[
        Path,
        typer.Option("--path", help="Project root (default: current directory)."),
    ] = Path("."),
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing serializer class."),
    ] = False,
) -> None:
    """Create or refresh a DRF ModelSerializer for an existing model."""
    from django_octave.prompts.add_serializer import resolve_add_serializer_options

    options = resolve_add_serializer_options(
        app=app_name,
        model=model_name,
        fields=fields,
        read_only=read_only,
        no_id=no_id,
        nested=nested,
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
        ser_path = write_serializer(
            app_dir,
            options=SerializerOptions(
                app_name=app,
                model_name=model,
                fields=csv_to_list(options.fields),
                read_only=csv_to_list(options.read_only),
                include_id=options.include_id,
                force=options.force,
                nested=[parse_nested_option(n) for n in options.nested],
            ),
        )
    except (
        NotOctaveProjectError,
        InvalidAppNameError,
        InvalidModelNameError,
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
                    f"# Serializer `{model}Serializer`",
                    "",
                    f"- Updated `{ser_path.relative_to(project.root)}`",
                    "",
                    "## Next steps",
                    "",
                    "```bash",
                    f"django-octave add-viewset {app} {model}",
                    "```",
                    "",
                ]
            )
        )
    )
