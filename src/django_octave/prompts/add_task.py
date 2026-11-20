"""Interactive prompts for ``django-octave add-task``."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

console = Console(stderr=True)


@dataclass(frozen=True, slots=True)
class AddTaskPromptOptions:
    app: str
    task_name: str
    bind: bool
    every: float | None
    crontab: str | None
    path: Path
    force: bool


def resolve_add_task_options(
    *,
    app: str | None,
    task_name: str | None,
    bind: bool,
    every: float | None,
    crontab: str | None,
    path: Path,
    force: bool,
) -> AddTaskPromptOptions:
    interactive = sys.stdin.isatty()
    missing: list[str] = []

    if app is None:
        if interactive:
            app = Prompt.ask("App name", console=console).strip()
        else:
            missing.append("APP")
    if task_name is None:
        if interactive:
            task_name = Prompt.ask(
                "Task name (snake_case)",
                console=console,
            ).strip()
        else:
            missing.append("TASK_NAME")

    if missing:
        console.print(
            "[red]Missing required arguments in non-interactive mode:[/red] "
            + ", ".join(missing)
        )
        raise typer.Exit(code=2)

    assert app is not None
    assert task_name is not None

    if interactive and every is None and crontab is None:
        if Confirm.ask("Add a Beat schedule?", default=False, console=console):
            mode = Prompt.ask(
                "Schedule type",
                choices=["every", "crontab"],
                default="every",
                console=console,
            )
            if mode == "every":
                raw = Prompt.ask("Interval seconds", default="3600", console=console)
                every = float(raw)
            else:
                crontab = Prompt.ask(
                    "Crontab (5 fields)",
                    default="0 * * * *",
                    console=console,
                )

    return AddTaskPromptOptions(
        app=app,
        task_name=task_name,
        bind=bind,
        every=every,
        crontab=crontab,
        path=path,
        force=force,
    )
