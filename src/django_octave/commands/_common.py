"""Plumbing shared by the command modules.

Not a command itself (the leading underscore keeps it out of command discovery): the
consoles, the "print the error and exit 1" handler, and the project/app/model checks
that every model-targeting command starts with.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import overload

import typer
from rich.console import Console

from django_octave.errors import OctaveError
from django_octave.models_gen.writer import model_exists
from django_octave.naming import validate_app_name, validate_model_name
from django_octave.project.detect import OctaveProject, detect_project

err_console = Console(stderr=True)
console = Console()

_EXPECTED_ERRORS = (
    OctaveError,
    ValueError,
    FileNotFoundError,
    FileExistsError,
    NotADirectoryError,
)


@contextmanager
def handle_errors(prefix: str | None = None) -> Iterator[None]:
    """Print an expected failure in red to stderr and exit with code 1.

    With ``prefix`` the message reads ``<prefix>: <error>`` (for a later step of a
    command, such as ``CRUD generation failed``). Only the failures a user can cause
    are handled; anything else is a bug and keeps its traceback.
    """
    try:
        yield
    except _EXPECTED_ERRORS as exc:
        message = f"{prefix}: {exc}" if prefix else str(exc)
        err_console.print(f"[red]{message}[/red]")
        raise typer.Exit(code=1) from exc


@dataclass(frozen=True, slots=True)
class Target:
    """A validated project and an existing app that a command acts on."""

    project: OctaveProject
    app: str
    app_dir: Path


@dataclass(frozen=True, slots=True)
class ModelTarget(Target):
    """A :class:`Target` whose model exists in the app's ``models.py``."""

    model: str
    models_source: str


@overload
def resolve_target(path: Path, app: str) -> Target: ...


@overload
def resolve_target(path: Path, app: str, model: str) -> ModelTarget: ...


def resolve_target(path: Path, app: str, model: str | None = None) -> Target:
    """Detect the project and check that the app (and model, if given) exist.

    Names are validated before any file is touched. Raises the same errors, with the
    same messages, that each command used to raise on its own.
    """
    project = detect_project(path)
    app_name = validate_app_name(app)
    model_name = validate_model_name(model) if model is not None else None
    app_dir = project.apps_dir / app_name
    if not app_dir.is_dir():
        msg = f"App apps.{app_name} not found. Run: django-octave add {app_name}"
        raise FileNotFoundError(msg)
    if model_name is None:
        return Target(project=project, app=app_name, app_dir=app_dir)
    models_path = app_dir / "models.py"
    if not models_path.is_file():
        msg = f"models.py not found in apps.{app_name}"
        raise FileNotFoundError(msg)
    source = models_path.read_text(encoding="utf-8")
    if not model_exists(source, model_name):
        msg = (
            f"Model {model_name} not found in apps.{app_name}.models. "
            f"Run: django-octave add-model {app_name} {model_name}"
        )
        raise FileNotFoundError(msg)
    return ModelTarget(
        project=project,
        app=app_name,
        app_dir=app_dir,
        model=model_name,
        models_source=source,
    )
