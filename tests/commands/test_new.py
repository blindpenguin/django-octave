"""CLI tests for django-octave new."""

from __future__ import annotations

import re
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
    assert "--frontend" in result.stdout
    assert "--register" in result.stdout
    assert "--crud" in result.stdout
    assert "--force" in result.stdout


def test_missing_name_noninteractive_exits_2() -> None:
    result = runner.invoke(
        app,
        [
            "new",
            "-d",
            "sqlite",
            "--no-docker",
            "--no-multitenancy",
            "--no-frontend",
        ],
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
            "--no-frontend",
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
            "--no-frontend",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1


def _new_args(tmp_path: Path, *extra: str) -> list[str]:
    return [
        "new", "cli_demo", "-d", "sqlite", "--no-docker", "--no-multitenancy",
        "--no-frontend", "--path", str(tmp_path), *extra,
    ]  # fmt: skip


def _flat(text: str) -> str:
    """Collapse whitespace and Rich box-drawing borders so wrapped text can be matched."""
    return " ".join(re.sub(r"[│╭╮╰╯─]", " ", text).split())


def test_new_force_help_says_generated_files_are_overwritten_and_rest_kept() -> None:
    result = runner.invoke(app, ["new", "--help"])

    text = _flat(result.stdout)
    assert "overwritten" in text
    assert "everything else is kept" in text


def test_new_force_overwrites_generated_files_and_keeps_the_rest(tmp_path: Path) -> None:
    assert runner.invoke(app, _new_args(tmp_path)).exit_code == 0
    target = tmp_path / "cli_demo"
    (target / "notes.txt").write_text("mine", encoding="utf-8")
    (target / "manage.py").write_text("# edited", encoding="utf-8")

    result = runner.invoke(app, _new_args(tmp_path, "--force"))

    assert result.exit_code == 0, result.output
    assert "Overwrote" in _flat(result.output)
    assert "files outside the generated tree were kept" in _flat(result.output)
    assert (target / "notes.txt").read_text(encoding="utf-8") == "mine"
    assert "# edited" not in (target / "manage.py").read_text(encoding="utf-8")


def test_new_force_on_fresh_target_prints_no_overwrite_note(tmp_path: Path) -> None:
    result = runner.invoke(app, _new_args(tmp_path, "--force"))

    assert result.exit_code == 0, result.output
    assert "Overwrote" not in result.output


def test_new_force_refuses_symlinked_directory(tmp_path: Path) -> None:
    target = tmp_path / "cli_demo"
    target.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (target / "apps").symlink_to(outside, target_is_directory=True)

    result = runner.invoke(app, _new_args(tmp_path, "--force"))

    assert result.exit_code == 1
    assert "Refusing to write through symlink" in _flat(result.output)
    assert list(outside.iterdir()) == []


def test_new_target_that_is_a_file_exits_1_without_traceback(tmp_path: Path) -> None:
    (tmp_path / "cli_demo").write_text("file", encoding="utf-8")

    result = runner.invoke(app, _new_args(tmp_path, "--force"))

    assert result.exit_code == 1
    assert "not a directory" in _flat(result.output)
    assert "Traceback" not in result.output
