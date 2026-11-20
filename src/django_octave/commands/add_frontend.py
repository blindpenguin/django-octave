"""``django-octave add-frontend`` — Vue + Nuxt UI SPA shell."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown

from django_octave.cli import app
from django_octave.frontend_gen import (
    ComposeInjectError,
    CrudSetupError,
    DjangoPatchError,
    FrontendExistsError,
    FrontendSetupError,
    generate_crud_all,
    setup_frontend,
)
from django_octave.frontend_gen.crud_wire import CrudWireError
from django_octave.project.detect import NotOctaveProjectError, detect_project

err_console = Console(stderr=True)
console = Console()


@app.command("add-frontend")
def add_frontend_cmd(
    path: Annotated[
        Path,
        typer.Option("--path", help="Project root (default: current directory)."),
    ] = Path("."),
    register: Annotated[
        bool | None,
        typer.Option(
            "--register/--no-register",
            help="Include signup page + registration API (prompted if omitted).",
        ),
    ] = None,
    crud: Annotated[
        bool | None,
        typer.Option(
            "--crud/--no-crud",
            help="Generate Vue CRUD pages for all ModelViewSets (prompted if omitted).",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Refresh frontend even if already present."),
    ] = False,
) -> None:
    """Scaffold a Vue 3 + Vite + Nuxt UI frontend wired to JWT auth."""
    from django_octave.prompts.add_frontend import resolve_add_frontend_options

    options = resolve_add_frontend_options(
        path=path,
        register=register,
        crud=crud,
        force=force,
    )
    try:
        project = detect_project(options.path)
        written = setup_frontend(
            project.root,
            include_register=options.register,
            force=options.force,
        )
    except (
        NotOctaveProjectError,
        FrontendExistsError,
        FrontendSetupError,
        DjangoPatchError,
        ComposeInjectError,
        FileNotFoundError,
        ValueError,
    ) as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    crud_skips: list[str] = []
    crud_warnings: list[str] = []
    if options.crud:
        try:
            crud_written, crud_warnings, crud_skips = generate_crud_all(
                project.root,
                force=options.force,
            )
            written.extend(crud_written)
        except (CrudSetupError, CrudWireError, ValueError) as exc:
            err_console.print(f"[red]CRUD generation failed: {exc}[/red]")
            raise typer.Exit(code=1) from exc

    rel = sorted({str(p.relative_to(project.root)) for p in written if p.exists()})
    lines = [
        "# Frontend configured",
        "",
        *[f"- Updated `{r}`" for r in rel],
        "",
    ]
    if crud_warnings or crud_skips:
        lines.extend(["## Notes", ""])
        lines.extend(f"- {w}" for w in crud_warnings)
        lines.extend(f"- Skipped: {s}" for s in crud_skips)
        lines.append("")
    lines.extend(
        [
            "## Next steps",
            "",
            "```bash",
            "cd frontend",
            "pnpm install",
            "pnpm dev",
            "```",
            "",
            "API: ensure Django is running (e.g. `uv run python manage.py runserver`) "
            "and `VITE_API_BASE_URL` points at it (see `frontend/.env.example`).",
            "",
        ]
    )
    if (project.root / "docker-compose.yml").is_file():
        lines.extend(
            [
                "With Docker:",
                "",
                "```bash",
                "docker compose up web frontend",
                "```",
                "",
            ]
        )
    console.print(Markdown("\n".join(lines)))
