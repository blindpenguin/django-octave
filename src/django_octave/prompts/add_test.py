"""Interactive prompts for ``django-octave add-test``."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt

console = Console(stderr=True)


@dataclass(frozen=True, slots=True)
class AddTestPromptOptions:
    app: str
    model: str
    path: Path
    force: bool


def resolve_add_test_options(
    *,
    app: str | None,
    model: str | None,
    path: Path,
    force: bool,
) -> AddTestPromptOptions:
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
    return AddTestPromptOptions(app=app, model=model, path=path, force=force)
