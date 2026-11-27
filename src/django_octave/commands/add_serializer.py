"""``django-octave add-serializer`` — create or refresh a ModelSerializer."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.markdown import Markdown

from django_octave.api_parts.serializer_gen import (
    SerializerOptions,
    parse_nested_option,
    write_serializer,
)
from django_octave.cli import app
from django_octave.commands._common import console, handle_errors, resolve_target
from django_octave.prompts.add_serializer import csv_to_list


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
        typer.Option(
            "--fields", help="Comma-separated Meta.fields (default: inspected)."
        ),
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
    with handle_errors():
        target = resolve_target(options.path, options.app, options.model)
        ser_path = write_serializer(
            target.app_dir,
            options=SerializerOptions(
                app_name=target.app,
                model_name=target.model,
                fields=csv_to_list(options.fields),
                read_only=csv_to_list(options.read_only),
                include_id=options.include_id,
                force=options.force,
                nested=[parse_nested_option(n) for n in options.nested],
            ),
        )
    project, app, model = target.project, target.app, target.model

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
