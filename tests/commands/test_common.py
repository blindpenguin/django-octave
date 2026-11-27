"""Tests for the shared command plumbing in ``commands/_common.py``."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from django_octave.cli import app
from django_octave.commands._common import (
    ModelTarget,
    Target,
    handle_errors,
    resolve_target,
)
from django_octave.errors import OctaveError
from django_octave.naming import InvalidAppNameError, InvalidModelNameError
from django_octave.project.detect import NotOctaveProjectError

runner = CliRunner()


class _Boom(OctaveError):
    """An expected failure that is not a ValueError."""


@pytest.fixture(scope="module")
def project_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A generated project with app ``blog`` and model ``Post`` (read-only use)."""
    parent = tmp_path_factory.mktemp("common")
    root = parent / "proj"
    commands = [
        [
            "new",
            "proj",
            "-d",
            "sqlite",
            "--no-docker",
            "--no-multitenancy",
            "--no-frontend",
            "--path",
            str(parent),
        ],
        ["add", "blog", "--path", str(root)],
        [
            "add-model",
            "blog",
            "Post",
            "--field",
            "title:char:max=200",
            "--path",
            str(root),
        ],
    ]
    for args in commands:
        result = runner.invoke(app, args)
        assert result.exit_code == 0, result.output
    return root


@pytest.mark.parametrize(
    "exc",
    [
        _Boom("octave"),
        ValueError("value"),
        FileNotFoundError("missing"),
        FileExistsError("exists"),
        NotADirectoryError("not a dir"),
    ],
    ids=lambda e: type(e).__name__,
)
def test_handle_errors_expected_failure_prints_message_and_exits_1(
    exc: Exception, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(typer.Exit) as raised, handle_errors():
        raise exc

    assert raised.value.exit_code == 1
    assert str(exc) in capsys.readouterr().err


def test_handle_errors_prefix_is_prepended_to_the_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(typer.Exit) as raised, handle_errors("CRUD generation failed"):
        raise ValueError("no viewsets")

    assert raised.value.exit_code == 1
    assert "CRUD generation failed: no viewsets" in capsys.readouterr().err


def test_handle_errors_unexpected_exception_keeps_its_traceback() -> None:
    with pytest.raises(RuntimeError, match="bug"), handle_errors():
        raise RuntimeError("bug")


def test_handle_errors_without_failure_does_nothing() -> None:
    with handle_errors():
        value = 1 + 1

    assert value == 2


def test_resolve_target_with_model_returns_validated_target(project_root: Path) -> None:
    target = resolve_target(project_root, "blog", "Post")

    assert isinstance(target, ModelTarget)
    assert target.project.root == project_root.resolve()
    assert target.app == "blog"
    assert target.model == "Post"
    assert target.app_dir == project_root.resolve() / "apps" / "blog"
    assert target.models_source is not None
    assert "class Post" in target.models_source


def test_resolve_target_normalizes_the_app_name(project_root: Path) -> None:
    target = resolve_target(project_root, " Blog ", "Post")

    assert target.app == "blog"


def test_resolve_target_without_model_skips_the_model_checks(
    project_root: Path,
) -> None:
    target = resolve_target(project_root, "blog")

    assert isinstance(target, Target)
    assert not isinstance(target, ModelTarget)
    assert target.app_dir.is_dir()


def test_resolve_target_without_model_still_requires_the_app(
    project_root: Path,
) -> None:
    with pytest.raises(FileNotFoundError, match="App apps.nope not found"):
        resolve_target(project_root, "nope")


def test_resolve_target_missing_app_message_matches_the_old_commands(
    project_root: Path,
) -> None:
    with pytest.raises(FileNotFoundError) as raised:
        resolve_target(project_root, "nope", "Post")

    assert str(raised.value) == "App apps.nope not found. Run: django-octave add nope"


def test_resolve_target_missing_models_py_message_matches_the_old_commands(
    project_root: Path,
) -> None:
    models_path = project_root / "apps" / "blog" / "models.py"
    original = models_path.read_bytes()
    models_path.unlink()
    try:
        with pytest.raises(FileNotFoundError) as raised:
            resolve_target(project_root, "blog", "Post")
    finally:
        models_path.write_bytes(original)

    assert str(raised.value) == "models.py not found in apps.blog"


def test_resolve_target_missing_model_message_matches_the_old_commands(
    project_root: Path,
) -> None:
    with pytest.raises(FileNotFoundError) as raised:
        resolve_target(project_root, "blog", "Ghost")

    assert str(raised.value) == (
        "Model Ghost not found in apps.blog.models. "
        "Run: django-octave add-model blog Ghost"
    )


def test_resolve_target_not_a_project_raises_before_anything_else(
    tmp_path: Path,
) -> None:
    with pytest.raises(NotOctaveProjectError):
        resolve_target(tmp_path, "blog", "Post")


@pytest.mark.parametrize(
    ("app_name", "model_name", "expected"),
    [
        ("class", "Post", InvalidAppNameError),
        ("blog", "post", InvalidModelNameError),
        ("blog", "Post; import os", InvalidModelNameError),
    ],
)
def test_resolve_target_invalid_names_are_rejected_before_any_file_access(
    project_root: Path,
    app_name: str,
    model_name: str,
    expected: type[Exception],
) -> None:
    with pytest.raises(expected):
        resolve_target(project_root, app_name, model_name)
