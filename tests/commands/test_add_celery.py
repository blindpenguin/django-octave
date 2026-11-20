"""CLI tests for django-octave add-celery."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()


def _new(tmp_path: Path, *, docker: bool = False) -> Path:
    args = [
        "new",
        "proj",
        "-d",
        "sqlite",
        "--docker" if docker else "--no-docker",
        "--no-multitenancy",
        "--path",
        str(tmp_path),
    ]
    assert runner.invoke(app, args).exit_code == 0
    return tmp_path / "proj"


def test_add_celery_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert "add-celery" in result.stdout
    assert runner.invoke(app, ["add-celery", "--help"]).exit_code == 0


def test_add_celery_refuse_force(tmp_path: Path) -> None:
    root = _new(tmp_path)
    result = runner.invoke(app, ["add-celery", "--path", str(root)])
    assert result.exit_code == 0, result.output
    assert (root / "config" / "celery.py").is_file()

    refused = runner.invoke(app, ["add-celery", "--path", str(root)])
    assert refused.exit_code == 1

    forced = runner.invoke(app, ["add-celery", "--force", "--path", str(root)])
    assert forced.exit_code == 0, forced.output


def test_new_with_celery_flag(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "new",
            "celproj",
            "-d",
            "sqlite",
            "--no-docker",
            "--no-multitenancy",
            "--celery",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    root = tmp_path / "celproj"
    assert (root / "config" / "celery.py").is_file()
    assert "celery[redis]" in (root / "pyproject.toml").read_text(encoding="utf-8")


def test_add_celery_compose_project(tmp_path: Path) -> None:
    root = _new(tmp_path, docker=True)
    result = runner.invoke(app, ["add-celery", "--path", str(root)])
    assert result.exit_code == 0, result.output
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    assert "  worker:" in compose
    assert "celery -A config worker" in compose
