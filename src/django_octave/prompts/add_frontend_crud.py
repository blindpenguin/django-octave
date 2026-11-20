"""Interactive prompts for ``django-octave add-frontend-crud``."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt

from django_octave.frontend_gen.str_label import parse_fk_label_overrides

console = Console(stderr=True)


@dataclass(frozen=True, slots=True)
class AddFrontendCrudOptions:
    app: str
    model: str
    path: Path
    force: bool
    fk_label_overrides: dict[str, str]


def resolve_add_frontend_crud_options(
    *,
    app: str | None,
    model: str | None,
    path: Path,
    force: bool,
    fk_labels: list[str] | None = None,
) -> AddFrontendCrudOptions:
    interactive = sys.stdin.isatty()
    missing: list[str] = []

    if app is None:
        if interactive:
            app = Prompt.ask("App name", console=console).strip()
        else:
            missing.append("APP")
    if model is None:
        if interactive:
            model = Prompt.ask("Model name (PascalCase)", console=console).strip()
        else:
            missing.append("MODEL")

    if missing:
        console.print(
            "[red]Missing required arguments in non-interactive mode:[/red] "
            + ", ".join(missing)
        )
        raise typer.Exit(code=2)

    try:
        overrides = parse_fk_label_overrides(fk_labels)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    assert app is not None
    assert model is not None
    return AddFrontendCrudOptions(
        app=app,
        model=model,
        path=path,
        force=force,
        fk_label_overrides=overrides,
    )
