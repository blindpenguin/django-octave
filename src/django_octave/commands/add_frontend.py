"""``django-octave add-frontend`` — Vue + Nuxt UI SPA shell."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.markdown import Markdown

from django_octave.cli import app
from django_octave.commands._common import console, handle_errors
from django_octave.frontend_gen import generate_crud_all, setup_frontend
from django_octave.project.detect import detect_project
from django_octave.rollback import rollback_on_error


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
    with handle_errors():
        project = detect_project(options.path)
        with rollback_on_error(project.root):
            written = setup_frontend(
                project.root,
                include_register=options.register,
                force=options.force,
            )

    crud_skips: list[str] = []
    crud_warnings: list[str] = []
    if options.crud:
        # A failing CRUD step undoes only itself: the frontend above stays, as before.
        with handle_errors("CRUD generation failed"), rollback_on_error(project.root):
            crud_written, crud_warnings, crud_skips = generate_crud_all(
                project.root,
                force=options.force,
            )
            written.extend(crud_written)

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
