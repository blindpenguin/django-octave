"""Interactive prompts for ``django-octave add-permission``."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

console = Console(stderr=True)

PRESET_CHOICES = ("owner", "staff_or_read", "auth_or_read", "tenant_member")


@dataclass(frozen=True, slots=True)
class AddPermissionPromptOptions:
    app: str
    class_name: str
    preset: str
    owner_attr: str
    viewset: str | None
    append: bool
    path: Path
    force: bool


def resolve_add_permission_options(
    *,
    app: str | None,
    class_name: str | None,
    preset: str,
    owner_attr: str,
    viewset: str | None,
    append: bool,
    path: Path,
    force: bool,
) -> AddPermissionPromptOptions:
    interactive = sys.stdin.isatty()
    missing: list[str] = []

    if app is None:
        if interactive:
            app = Prompt.ask("App name", console=console).strip()
        else:
            missing.append("APP")
    if class_name is None:
        if interactive:
            class_name = Prompt.ask(
                "Permission class name (PascalCase, e.g. IsOwner)",
                console=console,
            ).strip()
        else:
            missing.append("CLASS_NAME")

    if missing:
        console.print(
            "[red]Missing required arguments in non-interactive mode:[/red] "
            + ", ".join(missing)
        )
        raise typer.Exit(code=2)

    assert app is not None
    assert class_name is not None

    if interactive and viewset is None:
        if Confirm.ask("Wire to a viewset?", default=False, console=console):
            viewset = Prompt.ask(
                "ViewSet (Model or ModelViewSet)",
                console=console,
            ).strip() or None

    return AddPermissionPromptOptions(
        app=app,
        class_name=class_name,
        preset=preset,
        owner_attr=owner_attr,
        viewset=viewset,
        append=append,
        path=path,
        force=force,
    )
