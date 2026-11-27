"""``add`` is all-or-nothing, and never leaves a broken ``urls.py`` or settings file.

Before this was fixed, ``add`` rendered the app and patched settings before it patched
the URLs, so a refused patch left a half-added app; and some file shapes made it exit 0
with an unparseable ``urls.py`` or the app registered in the wrong list.
"""

from __future__ import annotations

import ast
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()


def _cli(*args: str) -> None:
    result = runner.invoke(app, list(args))
    assert result.exit_code == 0, result.output


@pytest.fixture(scope="module")
def template_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    parent = tmp_path_factory.mktemp("add-rollback")
    _cli(
        "new", "proj", "-d", "sqlite", "--no-docker", "--no-multitenancy",
        "--no-frontend", "--path", str(parent),
    )  # fmt: skip
    return parent / "proj"


@pytest.fixture
def project(template_project: Path, tmp_path: Path) -> Path:
    copy = tmp_path / "proj"
    shutil.copytree(template_project, copy)
    return copy


def _tree(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


def _squashed(output: str) -> str:
    """Output without whitespace: Rich wraps long lines, even inside a word."""
    return "".join(output.split())


def _urls(root: Path) -> Path:
    return root / "config" / "urls.py"


def _settings(root: Path) -> Path:
    return root / "config" / "settings" / "base.py"


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new), encoding="utf-8")


def _add(project: Path, name: str = "blog"):
    return runner.invoke(app, ["add", name, "--path", str(project)])


def test_add_that_cannot_patch_the_urls_exits_1_and_leaves_the_project_unchanged(
    project: Path,
) -> None:
    _edit(_urls(project), "urlpatterns = [", "urlpatterns = base_patterns + [")
    before = _tree(project)

    result = _add(project)

    assert result.exit_code == 1, result.output
    assert "Traceback" not in result.output
    assert 'path("api/",include("apps.blog.urls")),' in _squashed(result.output)
    assert _tree(project) == before
    assert not (project / "apps" / "blog").exists()


def test_add_that_cannot_patch_the_settings_exits_1_and_leaves_the_project_unchanged(
    project: Path,
) -> None:
    _settings(project).write_text(
        "DJANGO_APPS = ['django.contrib.admin']\nINSTALLED_APPS = DJANGO_APPS + []\n",
        encoding="utf-8",
    )
    before = _tree(project)

    result = _add(project)

    assert result.exit_code == 1, result.output
    assert "Traceback" not in result.output
    assert "INSTALLED_APPS" in _squashed(result.output)
    assert _tree(project) == before
    assert not (project / "apps" / "blog").exists()


def test_add_with_a_urls_file_that_does_not_parse_exits_1_and_changes_nothing(
    project: Path,
) -> None:
    _urls(project).write_text("urlpatterns = [\ndef broken(:\n", encoding="utf-8")
    before = _tree(project)

    result = _add(project)

    assert result.exit_code == 1, result.output
    assert "urls.py" in _squashed(result.output)
    assert _tree(project) == before


@pytest.mark.parametrize(
    ("old", "new"),
    [
        pytest.param(
            "from django.urls import path\n",
            "from django.urls import (\n    path,\n)\n",
            id="parenthesized-import",
        ),
        pytest.param(
            '    path("admin/", admin.site.urls),\n',
            '    path("admin/", admin.site.urls),\n    re_path(r"^legacy[0-9]]/$", legacy),\n',
            id="bracket-in-string",
        ),
        pytest.param("    ),\n]\n", "    )\n]\n", id="no-trailing-comma"),
    ],
)
def test_add_leaves_a_parseable_urls_file_that_includes_the_app(
    project: Path, old: str, new: str
) -> None:
    _edit(_urls(project), old, new)

    result = _add(project)

    assert result.exit_code == 0, result.output
    patched = _urls(project).read_text(encoding="utf-8")
    ast.parse(patched)
    assert "apps.blog.urls" in patched


def test_add_registers_the_app_in_installed_apps_when_that_list_is_on_one_line(
    project: Path,
) -> None:
    text = _settings(project).read_text(encoding="utf-8")
    start = text.index("INSTALLED_APPS = [")
    end = text.index("\n]", start) + 2
    entries = [
        line.strip().rstrip(",")
        for line in text[start:end].splitlines()[1:-1]
        if line.strip() and not line.strip().startswith("#")
    ]
    _settings(project).write_text(
        text[:start] + "INSTALLED_APPS = [" + ", ".join(entries) + "]\n" + text[end:],
        encoding="utf-8",
    )

    result = _add(project)

    assert result.exit_code == 0, result.output
    tree = ast.parse(_settings(project).read_text(encoding="utf-8"))
    lists = {
        t.id: [e.value for e in node.value.elts if isinstance(e, ast.Constant)]  # type: ignore[attr-defined]
        for node in tree.body
        if isinstance(node, ast.Assign)
        for t in node.targets
        if isinstance(t, ast.Name) and isinstance(node.value, ast.List)
    }
    assert "apps.blog" in lists["INSTALLED_APPS"]
    assert "apps.blog" not in lists["MIDDLEWARE"]
