"""``django-octave add`` — scaffold a domain app with API stubs."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.markdown import Markdown

from django_octave.cli import app
from django_octave.commands._common import console, handle_errors
from django_octave.project.detect import detect_project
from django_octave.project.patch import patch_installed_apps, patch_urls
from django_octave.rendering.app_context import AppContext
from django_octave.rendering.app_writer import render_app


@app.command("add")
def add_app(
    name: Annotated[
        str | None,
        typer.Argument(help="App module name (snake_case)."),
    ] = None,
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            help="Project root (default: current directory).",
        ),
    ] = Path("."),
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Replace an existing apps/<name> directory.",
        ),
    ] = False,
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="Starter model class name (PascalCase). Default: derived from app name.",
        ),
    ] = None,
) -> None:
    """Add a domain app with DRF API stubs under apps/."""
    from django_octave.prompts.add_app import resolve_add_app_options

    options = resolve_add_app_options(name=name, path=path, force=force, model=model)
    with handle_errors():
        project = detect_project(options.path)
        ctx = AppContext.build(
            project=project,
            raw_name=options.name,
            force=options.force,
            model_name=options.model,
        )
        render_app(ctx)
        patch_installed_apps(ctx.settings_base, ctx.installed_app)
        patch_urls(ctx.urls_path, ctx.app_name)

    console.print(
        Markdown(
            "\n".join(
                [
                    f"# Added `apps.{ctx.app_name}`",
                    "",
                    f"- Model: `{ctx.model_name}`",
                    f"- API: `/{ctx.api_mount}`",
                    "- Registered in `INSTALLED_APPS`",
                    "",
                    "## Next steps",
                    "",
                    "```bash",
                    f"cd {ctx.project_root}",
                    f"uv run python manage.py makemigrations {ctx.app_name}",
                    "uv run python manage.py migrate",
                    "```",
                    "",
                ]
            )
        )
    )
