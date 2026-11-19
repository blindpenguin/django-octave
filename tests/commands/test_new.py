"""CLI tests for django-octave new."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()


def test_help_lists_new() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "new" in result.stdout


def test_new_help_lists_flags() -> None:
    result = runner.invoke(app, ["new", "--help"])
    assert result.exit_code == 0
    assert "--database" in result.stdout
    assert "--docker" in result.stdout
    assert "--multitenancy" in result.stdout
    assert "--force" in result.stdout


def test_missing_name_noninteractive_exits_2() -> None:
    result = runner.invoke(
        app,
        ["new", "-d", "sqlite", "--no-docker", "--no-multitenancy"],
    )
    assert result.exit_code == 2


def test_new_generates_project(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "new",
            "cli_demo",
            "-d",
            "sqlite",
            "--no-docker",
            "--no-multitenancy",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "cli_demo" / "manage.py").is_file()


def test_new_refuses_non_empty(tmp_path: Path) -> None:
    target = tmp_path / "cli_demo"
    target.mkdir()
    (target / "existing.txt").write_text("x", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "new",
            "cli_demo",
            "-d",
            "sqlite",
            "--no-docker",
            "--no-multitenancy",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1
