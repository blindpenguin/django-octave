"""End-to-end proof that the owner preset scopes the whole resource (opt in with ``OCTAVE_E2E=1``).

Generates real projects (plain and multitenant), wires an owner permission to a viewset
and runs the scenarios in `owner_scenarios.py.tmpl` against real Django and DRF.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from .helpers import E2E_ENABLED, SKIP_REASON, build_project, cli, run

pytestmark = [pytest.mark.e2e, pytest.mark.skipif(not E2E_ENABLED, reason=SKIP_REASON)]

SCENARIOS = Path(__file__).parent / "owner_scenarios.py.tmpl"
FIELDS = (
    "title:char,owner:fk:to=users.User,assignee:fk:to=users.User:on_delete=set_null"
)


def _configure(root: Path) -> None:
    cli(
        "add-model", "notes", "Note", "--fields", FIELDS, "--force", "--path", str(root)
    )
    cli(
        "add-permission", "notes", "IsOwner", "--preset", "owner", "--owner-attr", "owner",
        "--viewset", "Note", "--path", str(root),
    )  # fmt: skip


@pytest.fixture(scope="module", params=["plain", "multitenant"])
def project(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    parent = tmp_path_factory.mktemp(f"octave-owner-{request.param}")
    return build_project(
        parent,
        multitenancy=request.param == "multitenant",
        apps=(("notes", "Note"),),
        configure=_configure,
    )


def test_the_generated_projects_own_tests_pass(project: Path) -> None:
    cli("add-test", "notes", "Note", "--force", "--path", str(project))

    done = run(["uv", "run", "pytest", "-q", "-p", "no:cacheprovider"], project)

    assert done.returncode == 0, done.stdout + done.stderr
    assert "test_list_only_returns_own_rows" in (
        project / "tests" / "test_notes_note_api.py"
    ).read_text(encoding="utf-8")


def test_owner_scenarios_pass(project: Path) -> None:
    shutil.copy(SCENARIOS, project / "tests" / "test_owner_scoping.py")

    done = run(
        [
            "uv",
            "run",
            "pytest",
            "-q",
            "tests/test_owner_scoping.py",
            "-p",
            "no:cacheprovider",
        ],
        project,
    )

    assert done.returncode == 0, done.stdout + done.stderr
