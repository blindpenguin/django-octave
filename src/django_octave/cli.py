"""Typer application entry for django-octave."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="django-octave",
    help="Opinionated generator for production-ready Django REST API projects.",
    no_args_is_help=True,
)


@app.callback()
def _root() -> None:
    """Opinionated generator for production-ready Django REST API projects."""


def _register_commands() -> None:
    """Import command modules so `@app.command` handlers attach."""
    from django_octave.commands import add as _add  # noqa: F401
    from django_octave.commands import add_action as _add_action  # noqa: F401
    from django_octave.commands import add_admin as _add_admin  # noqa: F401
    from django_octave.commands import add_model as _add_model  # noqa: F401
    from django_octave.commands import add_permission as _add_permission  # noqa: F401
    from django_octave.commands import add_serializer as _add_serializer  # noqa: F401
    from django_octave.commands import add_viewset as _add_viewset  # noqa: F401
    from django_octave.commands import new as _new  # noqa: F401


_register_commands()


def main() -> None:
    """Console-script entrypoint."""
    app()
