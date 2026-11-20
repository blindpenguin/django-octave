"""Interactive prompts for ``django-octave add-admin``."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt

console = Console(stderr=True)


@dataclass(frozen=True, slots=True)
class AddAdminPromptOptions:
    app: str
    model: str
    list_display: str | None
    search: str | None
    list_filter: str | None
    ordering: str | None
    date_hierarchy: bool
    path: Path
    force: bool


def resolve_add_admin_options(
    *,
    app: str | None,
    model: str | None,
    list_display: str | None,
    search: str | None,
    list_filter: str | None,
    ordering: str | None,
    no_date_hierarchy: bool,
    path: Path,
    force: bool,
) -> AddAdminPromptOptions:
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

    assert app is not None
    assert model is not None
    return AddAdminPromptOptions(
        app=app,
        model=model,
        list_display=list_display,
        search=search,
        list_filter=list_filter,
        ordering=ordering,
        date_hierarchy=not no_date_hierarchy,
        path=path,
        force=force,
    )
