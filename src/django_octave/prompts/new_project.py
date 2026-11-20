"""Interactive prompts for `django-octave new`."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

from django_octave.options import DatabaseChoice

console = Console(stderr=True)


@dataclass(frozen=True, slots=True)
class NewProjectOptions:
    """Resolved options for project creation (flags + prompts)."""

    name: str
    path: Path
    database: DatabaseChoice
    docker: bool
    multitenancy: bool
    frontend: bool
    register: bool
    crud: bool
    force: bool


def resolve_new_project_options(
    *,
    name: str | None,
    path: Path,
    database: DatabaseChoice | None,
    docker: bool | None,
    multitenancy: bool | None,
    frontend: bool | None,
    register: bool | None,
    crud: bool | None,
    force: bool,
) -> NewProjectOptions:
    """Fill missing options via prompts when stdin is a TTY; else fail."""
    interactive = sys.stdin.isatty()
    missing: list[str] = []

    if name is None:
        if interactive:
            name = Prompt.ask("Project name", console=console).strip()
            if not name:
                raise typer.BadParameter("Project name must not be empty.")
        else:
            missing.append("name (argument)")

    if database is None:
        if interactive:
            choice = Prompt.ask(
                "Database",
                choices=[c.value for c in DatabaseChoice],
                default=DatabaseChoice.SQLITE.value,
                console=console,
            )
            database = DatabaseChoice(choice)
        else:
            missing.append("--database")

    if docker is None:
        if interactive:
            docker = Confirm.ask("Include Docker (dev + prod)?", default=False, console=console)
        else:
            missing.append("--docker / --no-docker")

    if multitenancy is None:
        if interactive:
            multitenancy = Confirm.ask(
                "Enable row-level multitenancy?",
                default=False,
                console=console,
            )
        else:
            missing.append("--multitenancy / --no-multitenancy")

    if frontend is None:
        if interactive:
            frontend = Confirm.ask(
                "Include Vue + Nuxt UI frontend?",
                default=False,
                console=console,
            )
        else:
            missing.append("--frontend / --no-frontend")

    if frontend:
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
    else:
        register = False
        crud = False

    if missing:
        joined = ", ".join(missing)
        console.print(
            f"[red]Missing required options in non-interactive mode:[/red] {joined}\n"
            "Pass flags or run in a terminal to use prompts."
        )
        raise typer.Exit(code=2)

    assert name is not None
    assert database is not None
    assert docker is not None
    assert multitenancy is not None
    assert frontend is not None
    assert register is not None
    assert crud is not None

    return NewProjectOptions(
        name=name,
        path=path,
        database=database,
        docker=docker,
        multitenancy=multitenancy,
        frontend=frontend,
        register=register,
        crud=crud,
        force=force,
    )
