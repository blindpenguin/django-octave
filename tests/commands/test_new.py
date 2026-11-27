"""CLI tests for django-octave new."""

from __future__ import annotations

import ast
import json
import re
import tomllib
from pathlib import Path

import pytest
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


def test_new_force_overwrites_generated_files_and_keeps_the_rest(
    tmp_path: Path,
) -> None:
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


PAYLOAD = 'My" + __import__("os").getcwd() + "App'


def test_new_refuses_a_project_name_that_would_become_code(tmp_path: Path) -> None:
    result = runner.invoke(app, ["new", PAYLOAD, *_new_args(tmp_path)[2:]])

    assert result.exit_code == 2
    assert "Invalid project name" in _flat(result.output)
    assert list(tmp_path.iterdir()) == []  # nothing was written


@pytest.mark.parametrize("name", ["My App", "Café Münster 2.0", "2fast", "a.b-c_d"])
def test_new_accepts_awkward_names_and_every_generated_file_parses(
    tmp_path: Path, name: str
) -> None:
    args = [
        "new", name, "-d", "sqlite", "--no-docker", "--no-multitenancy",
        "--frontend", "--register", "--no-crud", "--path", str(tmp_path),
    ]  # fmt: skip

    result = runner.invoke(app, args)

    assert result.exit_code == 0, result.output
    root = next(p for p in tmp_path.iterdir() if p.is_dir())
    for path in root.rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    package = json.loads(
        (root / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    assert package["name"].endswith("-frontend")
    settings = (root / "config" / "settings" / "base.py").read_text(encoding="utf-8")
    assert f'"TITLE": "{name} API"' in settings  # the name is data, not code


def test_new_name_without_any_ascii_letter_fails_cleanly_on_the_directory_slug(
    tmp_path: Path,
) -> None:
    # The name itself is allowed (Unicode), but the directory/package slug is ASCII.
    result = runner.invoke(app, ["new", "日本語プロジェクト", *_new_args(tmp_path)[2:]])

    assert result.exit_code == 1
    assert "Cannot derive a valid project slug" in _flat(result.output)
    assert list(tmp_path.iterdir()) == []


def test_new_project_context_refuses_an_unsafe_name_even_without_the_cli(
    tmp_path: Path,
) -> None:
    from django_octave.options import DatabaseChoice
    from django_octave.prompts.new_project import NewProjectOptions
    from django_octave.rendering.context import ProjectContext
    from django_octave.safe_names import InvalidProjectNameError

    options = NewProjectOptions(
        name=PAYLOAD,
        path=tmp_path,
        database=DatabaseChoice.SQLITE,
        docker=False,
        multitenancy=False,
        frontend=False,
        register=False,
        crud=False,
        force=False,
    )

    with pytest.raises(InvalidProjectNameError):
        ProjectContext.from_options(options)
