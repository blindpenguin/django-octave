"""Unit tests for add-task generation and beat_schedule merge."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from typer.testing import CliRunner

from django_octave.celery_gen.setup import setup_celery
from django_octave.celery_gen.task_gen import (
    CrontabError,
    TaskExistsError,
    TaskGenError,
    TaskOptions,
    parse_crontab,
    validate_task_name,
    write_task,
)
from django_octave.cli import app

runner = CliRunner()


def _project_with_app(tmp_path: Path) -> Path:
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
    setup_celery(root)
    return root


def test_validate_task_name_and_crontab() -> None:
    assert validate_task_name("send_digest") == "send_digest"
    with pytest.raises(TaskGenError):
        validate_task_name("SendDigest")
    assert parse_crontab("0 8 * * *")["hour"] == "8"
    with pytest.raises(CrontabError):
        parse_crontab("0 8 *")


def test_write_task_stub_and_schedule(tmp_path: Path) -> None:
    root = _project_with_app(tmp_path)
    path = write_task(
        root,
        options=TaskOptions(
            app_name="blog",
            task_name="send_digest",
            every=3600.0,
        ),
    )
    text = path.read_text(encoding="utf-8")
    ast.parse(text)
    assert "@shared_task" in text
    assert "def send_digest()" in text
    celery = (root / "config" / "celery.py").read_text(encoding="utf-8")
    assert '"blog.send_digest"' in celery
    assert "3600.0" in celery
    assert "apps.blog.tasks.send_digest" in celery

    with pytest.raises(TaskExistsError):
        write_task(
            root,
            options=TaskOptions(app_name="blog", task_name="send_digest"),
        )

    write_task(
        root,
        options=TaskOptions(
            app_name="blog",
            task_name="send_digest",
            bind=True,
            crontab="0 8 * * 1",
            force=True,
        ),
    )
    text = path.read_text(encoding="utf-8")
    assert "bind=True" in text
    assert "def send_digest(self)" in text
    celery = (root / "config" / "celery.py").read_text(encoding="utf-8")
    assert "crontab(" in celery
    assert 'hour="8"' in celery
    assert "from celery.schedules import crontab" in celery


def test_write_task_requires_celery(tmp_path: Path) -> None:
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
    with pytest.raises(TaskGenError, match="add-celery"):
        write_task(
            root,
            options=TaskOptions(app_name="blog", task_name="noop"),
        )
