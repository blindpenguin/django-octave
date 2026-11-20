"""``django-octave add-test`` — scaffold factories and pytest stubs."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown

from django_octave.api_parts.test_gen import (
    StubExistsError,
    StubOptions,
    write_tests,
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

err_console = Console(stderr=True)
console = Console()


@app.command("add-test")
def add_test_cmd(
    app_name: Annotated[
        str | None,
        typer.Argument(help="Existing app under apps/."),
    ] = None,
    model_name: Annotated[
        str | None,
        typer.Argument(help="Model class name (PascalCase)."),
    ] = None,
    path: Annotated[
        Path,
        typer.Option("--path", help="Project root (default: current directory)."),
    ] = Path("."),
    force: Annotated[
        bool,
        typer.Option(
            "--force", help="Replace existing factory/test files for this model."
        ),
    ] = False,
) -> None:
    """Create factory-boy factory and pytest stubs for a model."""
    from django_octave.prompts.add_test import resolve_add_test_options

    options = resolve_add_test_options(
        app=app_name,
        model=model_name,
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
        written = write_tests(
            project.root,
            app_dir,
            options=StubOptions(
                app_name=app,
                model_name=model,
                force=options.force,
            ),
            use_multitenancy=project.use_multitenancy,
        )
    except (
        NotOctaveProjectError,
        InvalidAppNameError,
        InvalidModelNameError,
        StubExistsError,
        ModelWriteError,
        FileNotFoundError,
        ValueError,
    ) as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    lines = [
        f"# Tests for `{app}.{model}`",
        "",
        *[f"- Updated `{p.relative_to(project.root)}`" for p in written],
        "",
        "## Run",
        "",
        "```bash",
        f"cd {project.root}",
        "uv run pytest",
        "```",
        "",
    ]
    views = app_dir / "views.py"
    if not views.is_file() or f"class {model}ViewSet" not in views.read_text(
        encoding="utf-8"
    ):
        lines.insert(
            2,
            f"- No `{model}ViewSet` found — wrote model smoke tests "
            f"(run `add-viewset` then `add-test --force` for API tests).",
        )
        lines.insert(3, "")
    console.print(Markdown("\n".join(lines)))
