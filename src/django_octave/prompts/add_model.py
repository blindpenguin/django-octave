"""Interactive prompts for ``django-octave add-model``."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt

console = Console(stderr=True)


@dataclass(frozen=True, slots=True)
class AddModelOptions:
    app: str
    model: str
    fields: list[str]
    path: Path
    force: bool


def resolve_add_model_options(
    *,
    app: str | None,
    model: str | None,
    fields: list[str] | None,
    path: Path,
    force: bool,
) -> AddModelOptions:
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
    return AddModelOptions(
        app=app,
        model=model,
        fields=list(fields or []),
        path=path,
        force=force,
    )
