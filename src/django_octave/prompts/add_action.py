"""Interactive prompts for ``django-octave add-action``."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt

console = Console(stderr=True)


@dataclass(frozen=True, slots=True)
class AddActionPromptOptions:
    app: str
    viewset: str
    action_name: str
    detail: bool
    methods: str | None
    url_path: str | None
    url_name: str | None
    permission: str | None
    serializer: str | None
    tag: str | None
    path: Path
    force: bool


def resolve_add_action_options(
    *,
    app: str | None,
    viewset: str | None,
    action_name: str | None,
    detail: bool,
    list_action: bool,
    methods: str | None,
    url_path: str | None,
    url_name: str | None,
    permission: str | None,
    serializer: str | None,
    tag: str | None,
    path: Path,
    force: bool,
) -> AddActionPromptOptions:
    interactive = sys.stdin.isatty()
    missing: list[str] = []

    if app is None:
        if interactive:
            app = Prompt.ask("App name", console=console).strip()
        else:
            missing.append("APP")
    if viewset is None:
        if interactive:
            viewset = Prompt.ask(
                "ViewSet (Model or ModelViewSet)",
                console=console,
            ).strip()
        else:
            missing.append("VIEWSET")
    if action_name is None:
        if interactive:
            action_name = Prompt.ask(
                "Action name (snake_case)",
                console=console,
            ).strip()
        else:
            missing.append("ACTION_NAME")

    if missing:
        console.print(
            "[red]Missing required arguments in non-interactive mode:[/red] "
            + ", ".join(missing)
        )
        raise typer.Exit(code=2)

    assert app is not None
    assert viewset is not None
    assert action_name is not None

    is_detail = False if list_action else detail

    if interactive and methods is None:
        default_methods = "post" if is_detail else "get"
        methods = (
            Prompt.ask(
                "HTTP methods (comma-separated)",
                default=default_methods,
                console=console,
            ).strip()
            or default_methods
        )

    return AddActionPromptOptions(
        app=app,
        viewset=viewset,
        action_name=action_name,
        detail=is_detail,
        methods=methods,
        url_path=url_path,
        url_name=url_name,
        permission=permission,
        serializer=serializer,
        tag=tag,
        path=path,
        force=force,
    )
