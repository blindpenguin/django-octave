"""CLI tests for django-octave add-task."""

from __future__ import annotations

import ast
from pathlib import Path

from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()


def _project(tmp_path: Path) -> Path:
    assert (
        runner.invoke(
            app,
            [
                "new",
                "proj",
                "-d",
                "sqlite",
                "--no-docker",
                "--no-multitenancy",
        "--no-frontend",
                "--path",
                str(tmp_path),
            ],
        ).exit_code
        == 0
    )
    root = tmp_path / "proj"
    assert runner.invoke(app, ["add", "blog", "--path", str(root)]).exit_code == 0
    return root


def test_add_task_help() -> None:
    assert "add-task" in runner.invoke(app, ["--help"]).stdout
    assert runner.invoke(app, ["add-task", "--help"]).exit_code == 0


def test_add_task_requires_celery(tmp_path: Path) -> None:
    root = _project(tmp_path)
    result = runner.invoke(
        app,
        ["add-task", "blog", "send_digest", "--path", str(root)],
    )
    assert result.exit_code == 1
    assert "add-celery" in result.output


def test_add_task_every_refuse_force(tmp_path: Path) -> None:
    root = _project(tmp_path)
    assert runner.invoke(app, ["add-celery", "--path", str(root)]).exit_code == 0
    result = runner.invoke(
        app,
        [
            "add-task",
            "blog",
            "send_digest",
            "--every",
            "60",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 0, result.output
    tasks = root / "apps" / "blog" / "tasks.py"
    assert tasks.is_file()
    ast.parse(tasks.read_text(encoding="utf-8"))
    celery = (root / "config" / "celery.py").read_text(encoding="utf-8")
    assert "60.0" in celery

    refused = runner.invoke(
        app,
        ["add-task", "blog", "send_digest", "--path", str(root)],
    )
    assert refused.exit_code == 1

    forced = runner.invoke(
        app,
        [
            "add-task",
            "blog",
            "send_digest",
            "--bind",
            "--crontab",
            "0 9 * * *",
            "--force",
            "--path",
            str(root),
        ],
    )
    assert forced.exit_code == 0, forced.output
    assert "bind=True" in tasks.read_text(encoding="utf-8")
    assert "crontab(" in (root / "config" / "celery.py").read_text(encoding="utf-8")


def test_add_task_invalid_crontab(tmp_path: Path) -> None:
    root = _project(tmp_path)
    assert runner.invoke(app, ["add-celery", "--path", str(root)]).exit_code == 0
    result = runner.invoke(
        app,
        [
            "add-task",
            "blog",
            "noop",
            "--crontab",
            "bad",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 1
