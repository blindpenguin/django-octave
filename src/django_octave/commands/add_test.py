"""``django-octave add-test`` — scaffold factories and pytest stubs."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.markdown import Markdown

from django_octave.api_parts.test_gen import StubOptions, write_tests
from django_octave.cli import app
from django_octave.commands._common import console, handle_errors, resolve_target


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
    with handle_errors():
        target = resolve_target(options.path, options.app, options.model)
        written = write_tests(
            target.project.root,
            target.app_dir,
            options=StubOptions(
                app_name=target.app,
                model_name=target.model,
                force=options.force,
            ),
            use_multitenancy=target.project.use_multitenancy,
        )
    project, app_dir, app, model = (
        target.project,
        target.app_dir,
        target.app,
        target.model,
    )

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
