"""The config patchers produce exactly the files they always did (golden files).

The goldens in ``golden/`` were captured from the regex based patchers *before* they were
rewritten on libcst (spec ``libcst-config-patching``). They pin the byte-for-byte output
of ``add`` (settings and urls) and of ``add-frontend``'s urls patch for projects the
generator itself produced, so the rewrite cannot change what users get.

One deliberate difference: the old ``add`` left a stray blank line before the closing ``]``
of ``INSTALLED_APPS``; the settings goldens had exactly that line removed by hand (not
regenerated) when the rewrite dropped it.

Refresh them only on purpose, and review the diff:
``OCTAVE_UPDATE_GOLDENS=1 uv run pytest tests/project/test_patch_golden.py``
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from django_octave.frontend_gen.django_patch import patch_django_for_frontend
from django_octave.options import DatabaseChoice
from django_octave.project.patch import patch_installed_apps, patch_urls
from django_octave.prompts.new_project import NewProjectOptions
from django_octave.rendering.context import ProjectContext
from django_octave.rendering.writer import render_project

GOLDEN_DIR = Path(__file__).parent / "golden"
UPDATE = os.environ.get("OCTAVE_UPDATE_GOLDENS") == "1"

REFRESH_ROUTE = '    path("api/auth/token/refresh/", throttled(TokenRefreshView), name="token_refresh"),\n'


def _urls(root: Path) -> Path:
    return root / "config" / "urls.py"


def _settings(root: Path) -> Path:
    return root / "config" / "settings" / "base.py"


def _add(root: Path, *apps: str) -> None:
    for app in apps:
        patch_installed_apps(_settings(root), f"apps.{app}")
        patch_urls(_urls(root), app)


def _frontend(root: Path, *, register: bool) -> None:
    patch_django_for_frontend(root, include_register=register)


def _before_throttling(root: Path) -> None:
    """A project generated before throttling existed, then given the frontend."""
    stock = _urls(root).read_text(encoding="utf-8")
    stock = stock.replace("from apps.core.throttling import throttled\n\n", "")
    stock = stock.replace(
        "throttled(TokenObtainPairView)", "TokenObtainPairView.as_view()"
    )
    stock = stock.replace("throttled(TokenRefreshView)", "TokenRefreshView.as_view()")
    _urls(root).write_text(stock, encoding="utf-8")
    _frontend(root, register=True)


def _hand_wired_register(root: Path) -> None:
    """The user already routes api/auth/register/ by hand (no managed block)."""
    text = _urls(root).read_text(encoding="utf-8")
    assert REFRESH_ROUTE in text
    hand = '    path("api/auth/register/", my_register, name="my_register"),\n'
    if hand not in text:
        _urls(root).write_text(
            text.replace(REFRESH_ROUTE, REFRESH_ROUTE + hand), encoding="utf-8"
        )
    _frontend(root, register=True)


# scenario name -> (what to do to a fresh project, which files are compared)
SCENARIOS: dict[str, tuple[Callable[[Path], None], tuple[str, ...]]] = {
    "add_blog": (lambda r: _add(r, "blog"), ("urls", "settings")),
    "add_two_apps": (lambda r: _add(r, "blog", "shop"), ("urls", "settings")),
    "frontend_register": (lambda r: _frontend(r, register=True), ("urls",)),
    "frontend_no_register": (lambda r: _frontend(r, register=False), ("urls",)),
    "frontend_register_twice": (
        lambda r: (_frontend(r, register=True), _frontend(r, register=True)),
        ("urls",),
    ),
    "frontend_register_then_off": (
        lambda r: (_frontend(r, register=True), _frontend(r, register=False)),
        ("urls",),
    ),
    "frontend_off_then_register": (
        lambda r: (_frontend(r, register=False), _frontend(r, register=True)),
        ("urls",),
    ),
    "frontend_before_throttling": (_before_throttling, ("urls",)),
    "frontend_hand_wired_register": (_hand_wired_register, ("urls",)),
    "add_then_frontend": (
        lambda r: (_add(r, "blog"), _frontend(r, register=True)),
        ("urls", "settings"),
    ),
    "frontend_then_add": (
        lambda r: (_frontend(r, register=True), _add(r, "shop")),
        ("urls", "settings"),
    ),
}


@pytest.fixture(scope="module")
def template_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    options = NewProjectOptions(
        name="Golden",
        path=tmp_path_factory.mktemp("golden"),
        database=DatabaseChoice.SQLITE,
        docker=False,
        multitenancy=False,
        frontend=False,
        register=False,
        crud=False,
        force=False,
    )
    return render_project(ProjectContext.from_options(options))


@pytest.fixture
def project(template_project: Path, tmp_path: Path) -> Path:
    copy = tmp_path / "proj"
    shutil.copytree(template_project, copy)
    return copy


def _golden(scenario: str, which: str) -> Path:
    return GOLDEN_DIR / f"{scenario}.{which}.golden"


def _read(root: Path, which: str) -> str:
    path = _urls(root) if which == "urls" else _settings(root)
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_patch_output_matches_the_golden_file_byte_for_byte(
    project: Path, scenario: str
) -> None:
    action, files = SCENARIOS[scenario]

    action(project)

    for which in files:
        text = _read(project, which)
        golden = _golden(scenario, which)
        if UPDATE:
            GOLDEN_DIR.mkdir(exist_ok=True)
            golden.write_text(text, encoding="utf-8")
        assert text == golden.read_text(encoding="utf-8"), f"{scenario}: {which}"


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_running_the_scenario_again_changes_nothing(
    project: Path, scenario: str
) -> None:
    action, files = SCENARIOS[scenario]
    action(project)
    first = {which: _read(project, which) for which in files}

    action(project)

    assert {which: _read(project, which) for which in files} == first


def test_every_golden_file_belongs_to_a_scenario_and_the_other_way_round() -> None:
    expected = {
        f"{scenario}.{which}.golden"
        for scenario, (_action, files) in SCENARIOS.items()
        for which in files
    }

    present = {p.name for p in GOLDEN_DIR.glob("*.golden")}

    assert present == expected
