"""Pin every ``--help`` text (and the command order) of the CLI.

The snapshots were taken before the command layer was de-duplicated (spec
``dry-command-layer``); they fail if a refactor changes a command's name, order, options
or help text. To refresh them on purpose run:
``OCTAVE_UPDATE_SNAPSHOTS=1 uv run pytest tests/commands/test_cli_help.py``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from django_octave.cli import app

SNAPSHOTS = Path(__file__).parent / "snapshots"
COMMANDS = [
    "add",
    "add-action",
    "add-admin",
    "add-celery",
    "add-frontend",
    "add-frontend-crud",
    "add-model",
    "add-permission",
    "add-serializer",
    "add-task",
    "add-test",
    "add-viewset",
    "new",
]

runner = CliRunner(env={"COLUMNS": "100", "NO_COLOR": "1", "TERM": "dumb"})


def _help(*args: str) -> str:
    result = runner.invoke(app, [*args, "--help"])
    assert result.exit_code == 0, result.output
    return result.output


def _check(name: str, text: str) -> None:
    path = SNAPSHOTS / f"{name}.txt"
    if os.environ.get("OCTAVE_UPDATE_SNAPSHOTS") == "1":
        path.write_text(text, encoding="utf-8")
    assert text == path.read_text(encoding="utf-8")


def test_cli_help_root_lists_commands_in_snapshot_order() -> None:
    _check("root", _help())


@pytest.mark.parametrize("command", COMMANDS)
def test_cli_help_command_matches_snapshot(command: str) -> None:
    _check(command, _help(command))


def test_cli_help_snapshot_covers_every_registered_command() -> None:
    registered = sorted(c.name for c in app.registered_commands if c.name)

    assert registered == sorted(COMMANDS)
