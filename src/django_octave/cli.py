"""Typer application entry for django-octave."""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType

import typer

app = typer.Typer(
    name="django-octave",
    help="Opinionated generator for production-ready Django REST API projects.",
    no_args_is_help=True,
)


@app.callback()
def _root() -> None:
    """Opinionated generator for production-ready Django REST API projects."""


def import_command_modules(package: ModuleType) -> list[str]:
    """Import every public module of ``package`` so its ``@app.command`` handlers attach.

    Modules whose name starts with an underscore (shared helpers) are skipped. An
    import error is not caught: a broken command must stop the CLI, not vanish.
    Returns the imported module names in alphabetical order.
    """
    imported: list[str] = []
    for info in pkgutil.iter_modules(package.__path__):
        if info.name.startswith("_"):
            continue
        importlib.import_module(f"{package.__name__}.{info.name}")
        imported.append(info.name)
    return imported


def _register_commands() -> None:
    from django_octave import commands

    import_command_modules(commands)


_register_commands()


def main() -> None:
    """Console-script entrypoint."""
    app()
