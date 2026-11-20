"""Interactive prompts for ``django-octave add-serializer``."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt

console = Console(stderr=True)


@dataclass(frozen=True, slots=True)
class AddSerializerPromptOptions:
    app: str
    model: str
    fields: str | None
    read_only: str | None
    include_id: bool
    nested: list[str]
    path: Path
    force: bool


def _parse_csv_option(raw: str | None) -> list[str] | None:
    if raw is None or not raw.strip():
        return None
    return [p.strip() for p in raw.split(",") if p.strip()]


def resolve_add_serializer_options(
    *,
    app: str | None,
    model: str | None,
    fields: str | None,
    read_only: str | None,
    no_id: bool,
    nested: list[str] | None,
    path: Path,
    force: bool,
) -> AddSerializerPromptOptions:
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

    include_id = not no_id

    assert app is not None
    assert model is not None
    return AddSerializerPromptOptions(
        app=app,
        model=model,
        fields=fields,
        read_only=read_only,
        include_id=include_id,
        nested=list(nested or []),
        path=path,
        force=force,
    )


def csv_to_list(raw: str | None) -> list[str] | None:
    return _parse_csv_option(raw)
