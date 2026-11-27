"""``new`` writes ``.octave.toml`` together with the project."""

from __future__ import annotations

import fnmatch
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from django_octave.cli import app
from django_octave.project import marker as marker_module
from django_octave.project.detect import detect_project
from django_octave.project.marker import FILENAME, SCHEMA, current_version

runner = CliRunner()


def _new(parent: Path, *extra: str, name: str = "proj") -> Path:
    args = ["new", name, "--no-frontend", "--path", str(parent), *extra]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    return parent / name


def _marker_data(root: Path) -> dict[str, object]:
    return tomllib.loads((root / FILENAME).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("database", "docker", "multitenancy"),
    [
        ("sqlite", False, False),
        ("postgres", True, False),
        ("mariadb", True, True),
        ("sqlite", False, True),
    ],
)
def test_new_records_the_options_chosen(
    tmp_path: Path, database: str, docker: bool, multitenancy: bool
) -> None:
    root = _new(
        tmp_path,
        "-d",
        database,
        "--docker" if docker else "--no-docker",
        "--multitenancy" if multitenancy else "--no-multitenancy",
    )

    assert _marker_data(root) == {
        "schema": SCHEMA,
        "generator_version": current_version(),
        "project": {
            "database": database,
            "docker": docker,
            "multitenancy": multitenancy,
        },
        "features": {
            "frontend": False,
            "register": False,
            "crud": False,
            "celery": False,
        },
    }


def test_new_marker_starts_with_the_explaining_comment(tmp_path: Path) -> None:
    root = _new(tmp_path, "-d", "sqlite", "--no-docker", "--no-multitenancy")

    text = (root / FILENAME).read_text(encoding="utf-8")

    assert text.startswith("# Written by django-octave. Commit this file")


def test_new_writes_unknown_when_the_version_cannot_be_determined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(marker_module, "current_version", lambda: "unknown")

    root = _new(tmp_path, "-d", "sqlite", "--no-docker", "--no-multitenancy")

    assert _marker_data(root)["generator_version"] == "unknown"


def test_new_project_is_accepted_by_the_add_commands_of_the_same_version(
    tmp_path: Path,
) -> None:
    root = _new(tmp_path, "-d", "sqlite", "--no-docker", "--no-multitenancy")

    project = detect_project(root)
    result = runner.invoke(app, ["add", "blog", "--path", str(root)])

    assert project.marker is not None
    assert project.marker.generator_version == current_version()
    assert result.exit_code == 0, result.output


def test_new_force_overwrites_a_newer_marker_without_refusing_and_keeps_other_files(
    tmp_path: Path,
) -> None:
    target = tmp_path / "proj"
    target.mkdir()
    (target / "keep.txt").write_text("mine", encoding="utf-8")
    (target / FILENAME).write_text(
        'schema = 1\ngenerator_version = "99.0.0"\n', encoding="utf-8"
    )

    result = runner.invoke(
        app,
        [
            "new", "proj", "-d", "sqlite", "--no-docker", "--no-multitenancy",
            "--no-frontend", "--force", "--path", str(tmp_path),
        ],
    )  # fmt: skip

    assert result.exit_code == 0, result.output
    assert _marker_data(target)["generator_version"] == current_version()
    assert (target / "keep.txt").read_text(encoding="utf-8") == "mine"


def test_the_marker_is_not_ignored_by_the_generated_gitignore(tmp_path: Path) -> None:
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    root = _new(tmp_path, "-d", "sqlite", "--no-docker", "--no-multitenancy")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)  # noqa: S607

    ignored = subprocess.run(  # noqa: S603
        ["git", "check-ignore", "-q", FILENAME],  # noqa: S607
        cwd=root,
        check=False,
    )

    assert ignored.returncode == 1  # 1 means "not ignored"


def test_the_marker_is_not_matched_by_the_generated_dockerignore(
    tmp_path: Path,
) -> None:
    root = _new(tmp_path, "-d", "postgres", "--docker", "--no-multitenancy")
    patterns = [
        line.strip()
        for line in (root / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith(("#", "!"))
    ]

    assert [p for p in patterns if fnmatch.fnmatch(FILENAME, p.rstrip("/"))] == []
