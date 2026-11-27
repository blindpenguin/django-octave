"""``--force`` rewrites a class where it is, and creating matches regenerating.

Before this was fixed, replacing a class removed it and appended the new one, so forcing
the first of two classes moved it behind the second, and three commands wrote one blank
line above a definition instead of two.
"""

from __future__ import annotations

import ast
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()


def _cli(*args: str) -> None:
    result = runner.invoke(app, list(args))
    assert result.exit_code == 0, result.output


@pytest.fixture(scope="module", params=["plain", "multitenant"])
def template_project(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    """A project with app ``notes``: models Note, Post, Tag and two permission classes."""
    parent = tmp_path_factory.mktemp(f"force-{request.param}")
    _cli(
        "new", "proj", "-d", "sqlite", "--no-docker",
        "--multitenancy" if request.param == "multitenant" else "--no-multitenancy",
        "--no-frontend", "--path", str(parent),
    )  # fmt: skip
    root = parent / "proj"
    path = ["--path", str(root)]
    _cli("add", "notes", "--model", "Note", *path)
    _cli("add-model", "notes", "Post", "--fields", "title:char", *path)
    _cli("add-model", "notes", "Tag", "--fields", "label:char", *path)
    _cli("add-permission", "notes", "IsOwner", "--preset", "owner", *path)
    _cli("add-permission", "notes", "IsStaff", "--preset", "staff_or_read", *path)
    return root


@pytest.fixture
def project(template_project: Path, tmp_path: Path) -> Path:
    """A private copy, so tests can regenerate freely."""
    copy = tmp_path / "proj"
    shutil.copytree(template_project, copy)
    return copy


def _class_sources(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    return {
        n.name: ast.get_source_segment(text, n) or ""
        for n in ast.parse(text).body
        if isinstance(n, ast.ClassDef)
    }


def _function_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]


def _blank_line_problems(path: Path) -> str:
    """Output of ruff's blank-line rules for ``path`` (empty when clean)."""
    if importlib.util.find_spec("ruff") is None:
        pytest.skip("ruff is not installed")
    done = subprocess.run(  # noqa: S603
        [
            sys.executable, "-m", "ruff", "check", "--isolated", "--preview",
            "--select", "E301,E302,E303,E305", "--output-format", "concise", str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )  # fmt: skip
    return "" if done.returncode == 0 else done.stdout + done.stderr


# (file, command, class that is regenerated); the class has another one after it.
REPLACE_CASES = [
    pytest.param(
        "permissions.py",
        ["add-permission", "notes", "IsOwner", "--preset", "owner"],
        "IsOwner",
        id="add-permission",
    ),
    pytest.param(
        "serializers.py",
        ["add-serializer", "notes", "Post"],
        "PostSerializer",
        id="add-serializer",
    ),
    pytest.param(
        "views.py", ["add-viewset", "notes", "Post"], "PostViewSet", id="add-viewset"
    ),
    pytest.param(
        "admin.py", ["add-admin", "notes", "Post"], "PostAdmin", id="add-admin"
    ),
    pytest.param(
        "models.py",
        ["add-model", "notes", "Post", "--fields", "title:char"],
        "Post",
        id="add-model",
    ),
]


@pytest.mark.parametrize(("filename", "command", "target"), REPLACE_CASES)
def test_force_regenerates_the_class_in_place_and_changes_nothing_else(
    project: Path, filename: str, command: list[str], target: str
) -> None:
    path = project / "apps" / "notes" / filename
    before = _class_sources(path)
    assert list(before).index(target) < len(before) - 1  # a class follows it

    _cli(*command, "--force", "--path", str(project))

    after = _class_sources(path)
    assert list(after) == list(before)
    for name in before:
        if name != target:
            assert after[name] == before[name], name


@pytest.mark.parametrize(("filename", "command", "target"), REPLACE_CASES)
def test_force_twice_with_the_same_arguments_changes_nothing(
    project: Path, filename: str, command: list[str], target: str
) -> None:
    path = project / "apps" / "notes" / filename
    _cli(*command, "--force", "--path", str(project))
    first = path.read_bytes()

    _cli(*command, "--force", "--path", str(project))

    assert path.read_bytes() == first


def test_add_permission_creates_the_same_file_that_force_regenerates(
    project: Path,
) -> None:
    path = project / "apps" / "notes" / "permissions.py"
    path.unlink()  # so the command takes its "create the file" path
    command = [
        "add-permission",
        "notes",
        "IsFresh",
        "--preset",
        "owner",
        "--path",
        str(project),
    ]
    _cli(*command)
    created = path.read_bytes()

    _cli(*command, "--force")

    assert path.read_bytes() == created


def test_a_new_permissions_file_has_two_blank_lines_above_the_first_class(
    template_project: Path, tmp_path: Path
) -> None:
    # Build a project that has no permissions.py yet.
    root = tmp_path / "proj"
    shutil.copytree(template_project, root)
    (root / "apps" / "notes" / "permissions.py").unlink()

    _cli("add-permission", "notes", "IsOwner", "--preset", "owner", "--path", str(root))

    assert _blank_line_problems(root / "apps" / "notes" / "permissions.py") == ""


def test_appended_tasks_have_two_blank_lines_above_them(project: Path) -> None:
    path = project / "apps" / "notes" / "tasks.py"
    _cli("add-celery", "--path", str(project))
    _cli("add-task", "notes", "digest", "--every", "60", "--path", str(project))
    _cli("add-task", "notes", "cleanup", "--every", "120", "--path", str(project))

    assert _function_names(path) == ["digest", "cleanup"]
    assert _blank_line_problems(path) == ""


def test_forcing_a_task_keeps_its_place_and_the_spacing(project: Path) -> None:
    path = project / "apps" / "notes" / "tasks.py"
    _cli("add-celery", "--path", str(project))
    _cli("add-task", "notes", "digest", "--every", "60", "--path", str(project))
    _cli("add-task", "notes", "cleanup", "--every", "120", "--path", str(project))
    before = path.read_text(encoding="utf-8")

    _cli(
        "add-task",
        "notes",
        "digest",
        "--every",
        "60",
        "--force",
        "--path",
        str(project),
    )

    assert path.read_text(encoding="utf-8") == before


def test_conftest_fixtures_have_two_blank_lines_above_them(project: Path) -> None:
    path = project / "tests" / "conftest.py"
    _cli("add-test", "notes", "Post", "--path", str(project))

    assert path.is_file()
    assert _blank_line_problems(path) == ""
