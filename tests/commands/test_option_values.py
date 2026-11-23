"""Valid option values keep producing the same code; invalid ones are refused cleanly."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()
BAD = 'x", __import__("os").system("octave-probe"), "y'


def _flat(text: str) -> str:
    return " ".join(text.replace("│", " ").split())


@pytest.fixture
def project(tmp_path: Path) -> Path:
    def run(*args: str) -> None:
        result = runner.invoke(app, list(args))
        assert result.exit_code == 0, result.output

    run("new", "demo", "-d", "sqlite", "--no-docker", "--no-multitenancy", "--no-frontend",
        "--path", str(tmp_path))  # fmt: skip
    root = tmp_path / "demo"
    run("add", "blog", "--path", str(root))
    run("add-model", "blog", "Post", "--fields", "title:char,body:text", "--path", str(root))
    return root


def _tree(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and ".venv" not in p.parts
    }


def _views(root: Path) -> str:
    return (root / "apps" / "blog" / "views.py").read_text(encoding="utf-8")


def test_add_viewset_accepts_a_normal_tag(project: Path) -> None:
    result = runner.invoke(
        app, ["add-viewset", "blog", "Post", "--tag", "Blog Posts", "--force", "--path", str(project)]
    )

    assert result.exit_code == 0, result.output
    assert _views(project).count('tags=["Blog Posts"]') == 6  # one per viewset operation


def test_add_action_accepts_normal_url_path_url_name_and_tag(project: Path) -> None:
    result = runner.invoke(
        app,
        ["add-action", "blog", "Post", "publish", "--detail", "--methods", "post",
         "--url-path", "v1/publish", "--url-name", "publish-now", "--tag", "Blog Posts",
         "--force", "--path", str(project)],
    )  # fmt: skip

    assert result.exit_code == 0, result.output
    views = _views(project)
    ast.parse(views)
    assert 'url_path="v1/publish"' in views
    assert 'url_name="publish-now"' in views
    assert 'tags=["Blog Posts"]' in views


def test_add_permission_accepts_a_normal_owner_attr(project: Path) -> None:
    result = runner.invoke(
        app,
        ["add-permission", "blog", "IsOwner", "--preset", "owner", "--owner-attr", "created_by",
         "--path", str(project)],
    )  # fmt: skip

    assert result.exit_code == 0, result.output
    permissions = (project / "apps" / "blog" / "permissions.py").read_text(encoding="utf-8")
    ast.parse(permissions)
    assert 'owner_attr = "created_by"' in permissions
    assert "getattr(obj, self.owner_attr, None)" in permissions


@pytest.mark.parametrize(
    ("args", "option"),
    [
        (["add-viewset", "blog", "Post", "--tag", BAD, "--force"], "--tag"),
        (["add-action", "blog", "Post", "publish", "--tag", BAD], "--tag"),
        (["add-action", "blog", "Post", "publish", "--url-path", BAD], "--url-path"),
        (["add-action", "blog", "Post", "publish", "--url-name", BAD], "--url-name"),
        (["add-permission", "blog", "IsOwner", "--preset", "owner", "--owner-attr", BAD], "--owner-attr"),
    ],
    ids=["viewset-tag", "action-tag", "action-url-path", "action-url-name", "permission-owner-attr"],
)
def test_rejected_option_exits_1_with_one_line_and_changes_nothing(
    project: Path, args: list[str], option: str
) -> None:
    before = _tree(project)

    result = runner.invoke(app, [*args, "--path", str(project)])

    assert result.exit_code == 1
    assert f"Invalid {option}" in _flat(result.output)
    assert "Traceback" not in result.output
    assert _tree(project) == before


def test_add_action_ignores_an_unsafe_tag_found_in_the_existing_viewset(project: Path) -> None:
    views_path = project / "apps" / "blog" / "views.py"
    views_path.write_text(
        views_path.read_text(encoding="utf-8").replace('tags=["post"]', 'tags=["a/b c"]'),
        encoding="utf-8",
    )

    result = runner.invoke(
        app, ["add-action", "blog", "Post", "ping", "--force", "--path", str(project)]
    )

    assert result.exit_code == 0, result.output
    ast.parse(_views(project))
    assert "def ping" in _views(project)
    # the detected value 'a/b c' is not copied into the new method; the default tag is used
    method = _views(project).split("def ping")[0].rsplit("@extend_schema", 1)[-1]
    assert "a/b c" not in method


def test_add_permission_for_an_unknown_viewset_leaves_no_half_written_file(project: Path) -> None:
    before = _tree(project)

    result = runner.invoke(
        app,
        ["add-permission", "blog", "IsMine", "--preset", "auth_or_read", "--viewset", "Nope",
         "--path", str(project)],
    )  # fmt: skip

    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert _tree(project) == before  # permissions.py was not left behind


def test_add_task_with_an_invalid_crontab_leaves_the_project_untouched(project: Path) -> None:
    assert runner.invoke(app, ["add-celery", "--path", str(project)]).exit_code == 0
    before = _tree(project)

    result = runner.invoke(
        app, ["add-task", "blog", "nightly", "--crontab", "not a cron", "--path", str(project)]
    )

    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert _tree(project) == before


def test_a_command_that_would_write_broken_python_is_rolled_back(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    permissions = project / "apps" / "blog" / "permissions.py"

    def broken_write(app_dir: Path, *, options: object) -> Path:
        (app_dir / "permissions.py").write_text("class Broken(:\n", encoding="utf-8")
        return app_dir / "permissions.py"

    monkeypatch.setattr("django_octave.commands.add_permission.write_permission", broken_write)
    before = _tree(project)

    result = runner.invoke(
        app, ["add-permission", "blog", "IsMine", "--preset", "owner", "--path", str(project)]
    )

    assert result.exit_code == 1
    assert "does not parse" in _flat(result.output)
    assert "permissions.py" in _flat(result.output)
    assert not permissions.exists()
    assert _tree(project) == before
