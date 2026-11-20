"""Interactive prompts for ``django-octave add-frontend``."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm

console = Console(stderr=True)


@dataclass(frozen=True, slots=True)
class AddFrontendOptions:
    path: Path
    register: bool
    crud: bool
    force: bool


def resolve_add_frontend_options(
    *,
    path: Path,
    register: bool | None,
    crud: bool | None,
    force: bool,
) -> AddFrontendOptions:
    """Fill register/crud via prompt when TTY; else require flags."""
    interactive = sys.stdin.isatty()
    missing: list[str] = []

    if register is None:
        if interactive:
            register = Confirm.ask(
                "Include registration (signup page + API)?",
                default=False,
                console=console,
            )
        else:
            missing.append("--register / --no-register")

    if crud is None:
        if interactive:
            crud = Confirm.ask(
                "Generate Vue CRUD pages for all ModelViewSets?",
                default=False,
                console=console,
            )
        else:
            missing.append("--crud / --no-crud")

    if missing:
        console.print(
            "[red]Missing required options in non-interactive mode:[/red] "
            + ", ".join(missing)
            + "\n"
            "Pass flags or run in a terminal to use prompts."
        )
        raise typer.Exit(code=2)

    assert register is not None
    assert crud is not None
    return AddFrontendOptions(
        path=path, register=register, crud=crud, force=force
    )
