"""Interactive prompts for ``django-octave add``."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt

console = Console(stderr=True)


@dataclass(frozen=True, slots=True)
class AddAppOptions:
    name: str
    path: Path
    force: bool


def resolve_add_app_options(
    *,
    name: str | None,
    path: Path,
    force: bool,
) -> AddAppOptions:
    interactive = sys.stdin.isatty()
    if name is None:
        if interactive:
            name = Prompt.ask("App name (snake_case)", console=console).strip()
            if not name:
                raise typer.BadParameter("App name must not be empty.")
        else:
            console.print(
                "[red]Missing required option in non-interactive mode:[/red] "
                "name (argument)\nPass an app name or run in a terminal."
            )
            raise typer.Exit(code=2)
    return AddAppOptions(name=name, path=path, force=force)
