"""Every add-* command refuses a project that a newer django-octave generated.

The commands are discovered from the Typer definition and each needs an entry in
``ARGUMENTS``, so a new command cannot skip the check unnoticed.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from django_octave.cli import app
from django_octave.project import marker as marker_module
from django_octave.project.marker import (
    FILENAME,
    SCHEMA,
    Marker,
    current_version,
    read_marker,
    write_marker,
)

runner = CliRunner()

# Arguments that get each command past option resolution to ``detect_project``.
ARGUMENTS: dict[str, list[str]] = {
    "add": ["notes2"],
    "add-action": ["notes", "Note", "go"],
    "add-admin": ["notes", "Note"],
    "add-celery": [],
    "add-frontend": ["--no-register", "--no-crud"],
    "add-frontend-crud": ["notes", "Note"],
    "add-model": ["notes", "Tag", "--fields", "name:char"],
    "add-permission": ["notes", "IsProbe"],
    "add-serializer": ["notes", "Note"],
    "add-task": ["notes", "job"],
    "add-test": ["notes", "Note"],
    "add-viewset": ["notes", "Note"],
}
COMMANDS = sorted(typer.main.get_command(app).commands)
NEWER = "99.0.0"


def _cli(*args: str) -> None:
    result = runner.invoke(app, list(args))
    assert result.exit_code == 0, result.output


def _marker(**overrides: object) -> Marker:
    values: dict[str, object] = {
        "schema": SCHEMA,
        "generator_version": current_version(),
        "database": "sqlite",
        "docker": False,
        "multitenancy": False,
        "frontend": False,
        "register": False,
        "crud": False,
        "celery": False,
    }
    values.update(overrides)
    return Marker(**values)  # type: ignore[arg-type]


def _squashed(output: str) -> str:
    """Output without whitespace: Rich wraps long lines (even inside a word)."""
    return "".join(output.split())


def _tree(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


@pytest.fixture(scope="module")
def template_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    parent = tmp_path_factory.mktemp("marker-refusal")
    _cli(
        "new", "proj", "-d", "sqlite", "--no-docker", "--no-multitenancy",
        "--no-frontend", "--path", str(parent),
    )  # fmt: skip
    root = parent / "proj"
    _cli("add", "notes", "--model", "Note", "--path", str(root))
    (root / FILENAME).unlink(missing_ok=True)  # each test decides what the marker is
    return root


@pytest.fixture
def project(template_project: Path, tmp_path: Path) -> Path:
    copy = tmp_path / "proj"
    shutil.copytree(template_project, copy)
    return copy


def test_every_command_except_new_is_covered_by_the_table() -> None:
    assert set(COMMANDS) - {"new"} == set(ARGUMENTS)


@pytest.mark.parametrize("command", sorted(ARGUMENTS))
def test_command_refuses_a_newer_project_and_writes_nothing(
    project: Path, command: str
) -> None:
    write_marker(project, _marker(generator_version=NEWER))
    before = _tree(project)

    result = runner.invoke(app, [command, *ARGUMENTS[command], "--path", str(project)])

    assert result.exit_code == 1, result.output
    assert "Traceback" not in result.output
    flat = _squashed(result.output)
    assert NEWER in flat
    assert current_version() in flat
    assert "pgradedjango-octave" in flat
    assert _tree(project) == before


@pytest.mark.parametrize("command", sorted(ARGUMENTS))
def test_command_refuses_a_newer_marker_schema(project: Path, command: str) -> None:
    write_marker(project, _marker(schema=SCHEMA + 1))
    before = _tree(project)

    result = runner.invoke(app, [command, *ARGUMENTS[command], "--path", str(project)])

    assert result.exit_code == 1, result.output
    assert "newerdjango-octave" in _squashed(result.output)
    assert _tree(project) == before


@pytest.mark.parametrize("command", sorted(ARGUMENTS))
def test_command_names_the_file_when_the_marker_is_invalid(
    project: Path, command: str
) -> None:
    (project / FILENAME).write_text("schema = [", encoding="utf-8")
    before = _tree(project)

    result = runner.invoke(app, [command, *ARGUMENTS[command], "--path", str(project)])

    assert result.exit_code == 1, result.output
    flat = _squashed(result.output)
    assert FILENAME in flat
    assert "fixordeletethefile" in flat
    assert _tree(project) == before


@pytest.mark.parametrize("generated", ["0.0.1", "unknown", None])
def test_add_model_works_with_an_older_unknown_or_missing_marker(
    project: Path, generated: str | None
) -> None:
    if generated is not None:
        write_marker(project, _marker(generator_version=generated))

    result = runner.invoke(
        app, ["add-model", *ARGUMENTS["add-model"], "--path", str(project)]
    )

    assert result.exit_code == 0, result.output
    assert "class Tag" in (project / "apps" / "notes" / "models.py").read_text(
        encoding="utf-8"
    )


def test_add_model_in_a_project_without_a_marker_creates_no_marker(
    project: Path,
) -> None:
    result = runner.invoke(
        app, ["add-model", *ARGUMENTS["add-model"], "--path", str(project)]
    )

    assert result.exit_code == 0, result.output
    assert read_marker(project) is None
    assert not (project / FILENAME).exists()


def test_a_marker_from_the_running_version_is_accepted(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(marker_module, "current_version", lambda: "0.3.0")
    write_marker(project, _marker(generator_version="0.3.0"))

    result = runner.invoke(
        app, ["add-model", *ARGUMENTS["add-model"], "--path", str(project)]
    )

    assert result.exit_code == 0, result.output
