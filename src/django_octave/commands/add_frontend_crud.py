"""``django-octave add-frontend-crud`` — Vue CRUD pages for a ModelViewSet."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown

from django_octave.cli import app
from django_octave.frontend_gen import CrudSetupError, generate_crud
from django_octave.frontend_gen.crud_wire import CrudWireError
from django_octave.naming import (
    InvalidAppNameError,
    InvalidModelNameError,
    validate_app_name,
    validate_model_name,
)
from django_octave.project.detect import NotOctaveProjectError, detect_project

err_console = Console(stderr=True)
console = Console()


@app.command("add-frontend-crud")
def add_frontend_crud_cmd(
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
        typer.Option("--force", help="Overwrite existing CRUD pages."),
    ] = False,
    fk_label: Annotated[
        list[str] | None,
        typer.Option(
            "--fk-label",
            help=(
                "Override FK dropdown label attr: FIELD=ATTR "
                "(repeatable). Default: related model __str__ / heuristic. "
                "SPA also prefers API `label` when present."
            ),
        ),
    ] = None,
) -> None:
    """Generate list/detail/create/edit Vue pages for a DRF ModelViewSet."""
    from django_octave.prompts.add_frontend_crud import resolve_add_frontend_crud_options

    options = resolve_add_frontend_crud_options(
        app=app_name,
        model=model_name,
        path=path,
        force=force,
        fk_labels=fk_label,
    )
    try:
        project = detect_project(options.path)
        app = validate_app_name(options.app)
        model = validate_model_name(options.model)
        written, warnings = generate_crud(
            project.root,
            app,
            model,
            force=options.force,
            fk_label_overrides=options.fk_label_overrides,
        )
    except (
        NotOctaveProjectError,
        CrudSetupError,
        CrudWireError,
        InvalidAppNameError,
        InvalidModelNameError,
        FileExistsError,
        FileNotFoundError,
        ValueError,
    ) as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    rel = sorted({str(p.relative_to(project.root)) for p in written if p.exists()})
    # Infer plural from a pages path when possible
    plural = None
    for r in rel:
        if "/pages/" in r and r.endswith("ListView.vue"):
            plural = Path(r).parent.name
            break

    lines = [
        f"# Frontend CRUD for `{app}.{model}`",
        "",
        *[f"- Updated `{r}`" for r in rel],
        "",
    ]
    if warnings:
        lines.extend(["## Notes", "", *[f"- {w}" for w in warnings], ""])
    lines.extend(["## Next steps", ""])
    if plural:
        lines.extend(
            [
                f"Open `/{plural}` while logged in (after `pnpm dev`).",
                "",
                f"- List: `/{plural}`",
                f"- Create: `/{plural}/new`",
                f"- Detail: `/{plural}/:id`",
                f"- Edit: `/{plural}/:id/edit`",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "Run the SPA (`cd frontend && pnpm install && pnpm dev`) "
                "and open the new nav links while authenticated.",
                "",
            ]
        )
    console.print(Markdown("\n".join(lines)))
