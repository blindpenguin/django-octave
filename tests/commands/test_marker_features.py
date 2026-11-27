"""The feature flags in ``.octave.toml`` follow ``new``, ``add-celery`` and ``add-frontend``."""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from django_octave.cli import app
from django_octave.project.marker import (
    FILENAME,
    MarkerError,
    read_marker,
    write_marker,
)

runner = CliRunner()
OLD = "0.0.1"


def _run(*args: str, expect: int = 0) -> str:
    result = runner.invoke(app, list(args))
    assert result.exit_code == expect, result.output
    return result.output


def _features(root: Path) -> tuple[bool, bool, bool, bool]:
    marker = read_marker(root)
    assert marker is not None
    return (marker.frontend, marker.register, marker.crud, marker.celery)


def _tree(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


# --- new ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("flags", "expected"),
    [
        (["--frontend", "--register", "--crud", "--celery"], (True, True, True, True)),
        (["--frontend", "--no-register", "--no-crud"], (True, False, False, False)),
        (["--frontend", "--register", "--no-crud"], (True, True, False, False)),
        (["--no-frontend", "--celery"], (False, False, False, True)),
        (["--no-frontend"], (False, False, False, False)),
    ],
    ids=["everything", "bare-frontend", "frontend-register", "celery-only", "nothing"],
)
def test_new_records_the_features_it_set_up(
    tmp_path: Path, flags: list[str], expected: tuple[bool, bool, bool, bool]
) -> None:
    _run(
        "new",
        "proj",
        "-d",
        "sqlite",
        "--no-docker",
        "--no-multitenancy",
        *flags,
        "--path",
        str(tmp_path),
    )

    assert _features(tmp_path / "proj") == expected


# --- add-celery / add-frontend -------------------------------------------------------------


@pytest.fixture(scope="module")
def template_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    parent = tmp_path_factory.mktemp("marker-features")
    _run(
        "new",
        "proj",
        "-d",
        "sqlite",
        "--no-docker",
        "--no-multitenancy",
        "--no-frontend",
        "--path",
        str(parent),
    )
    root = parent / "proj"
    marker = read_marker(root)
    assert marker is not None
    write_marker(root, replace(marker, generator_version=OLD))
    return root


@pytest.fixture
def project(template_project: Path, tmp_path: Path) -> Path:
    copy = tmp_path / "proj"
    shutil.copytree(template_project, copy)
    return copy


def test_add_celery_sets_celery_and_changes_nothing_else_in_the_marker(
    project: Path,
) -> None:
    before = read_marker(project)

    _run("add-celery", "--path", str(project))

    after = read_marker(project)
    assert after is not None and before is not None
    assert after.celery is True
    assert replace(after, celery=False) == before
    assert after.generator_version == OLD


@pytest.mark.parametrize(
    ("flags", "expected"),
    [
        (["--register", "--crud"], (True, True, True)),
        (["--register", "--no-crud"], (True, True, False)),
        (["--no-register", "--no-crud"], (True, False, False)),
    ],
)
def test_add_frontend_sets_frontend_and_what_it_applied(
    project: Path, flags: list[str], expected: tuple[bool, bool, bool]
) -> None:
    _run("add-frontend", *flags, "--path", str(project))

    marker = read_marker(project)
    assert marker is not None
    assert (marker.frontend, marker.register, marker.crud) == expected
    assert marker.celery is False
    assert marker.generator_version == OLD


def test_add_frontend_register_follows_the_latest_run(project: Path) -> None:
    _run("add-frontend", "--register", "--no-crud", "--path", str(project))
    assert _features(project)[:2] == (True, True)

    _run(
        "add-frontend", "--no-register", "--no-crud", "--force", "--path", str(project)
    )

    assert _features(project)[:2] == (True, False)


def test_add_frontend_crud_only_turns_on(project: Path) -> None:
    _run("add-frontend", "--register", "--crud", "--path", str(project))
    assert _features(project)[2] is True

    _run("add-frontend", "--register", "--no-crud", "--force", "--path", str(project))

    assert _features(project)[2] is True


def test_a_project_without_a_marker_stays_without_one(project: Path) -> None:
    (project / FILENAME).unlink()

    _run("add-celery", "--path", str(project))
    _run("add-frontend", "--register", "--crud", "--path", str(project))

    assert not (project / FILENAME).exists()


# --- failures leave the project consistent --------------------------------------------------


def _fail_to_update(*_args: object, **_kwargs: object) -> bool:
    raise MarkerError("cannot write the marker")


def test_add_celery_leaves_the_project_unchanged_when_the_marker_cannot_be_updated(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "django_octave.celery_gen.setup.update_features", _fail_to_update
    )
    before = _tree(project)

    output = _run("add-celery", "--path", str(project), expect=1)

    assert "cannot write the marker" in " ".join(output.split())
    assert _tree(project) == before
    assert not (project / "config" / "celery.py").exists()


def test_add_frontend_leaves_the_project_unchanged_when_the_marker_cannot_be_updated(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "django_octave.frontend_gen.setup.update_features", _fail_to_update
    )
    before = _tree(project)

    _run("add-frontend", "--register", "--no-crud", "--path", str(project), expect=1)

    assert _tree(project) == before
    assert not (project / "frontend").exists()


def test_a_failing_crud_step_keeps_the_frontend_and_its_marker(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "django_octave.frontend_gen.crud_setup.update_features", _fail_to_update
    )

    output = _run(
        "add-frontend", "--register", "--crud", "--path", str(project), expect=1
    )

    assert "CRUD generation failed" in " ".join(output.split())
    assert (project / "frontend").is_dir()
    assert _features(project) == (True, True, False, False)


def test_a_failing_crud_step_removes_the_pages_it_generated(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _run("add", "notes", "--model", "Note", "--path", str(project))
    _run("add-frontend", "--register", "--no-crud", "--path", str(project))
    before = _tree(project)
    monkeypatch.setattr(
        "django_octave.frontend_gen.crud_setup.update_features", _fail_to_update
    )

    _run(
        "add-frontend",
        "--register",
        "--crud",
        "--force",
        "--path",
        str(project),
        expect=1,
    )

    assert _tree(project) == before
    assert _features(project) == (True, True, False, False)
