"""End-to-end proof that models with several relations to one target are valid.

Opt in with ``OCTAVE_E2E=1``. Generates real projects (plain and multitenant), adds one
app per case with ``add-model`` and runs Django's system check, ``makemigrations`` and
``migrate`` against it. Before the ``related_name`` work every clash case failed with
``fields.E304``/``E305``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .helpers import E2E_ENABLED, SKIP_REASON, build_project, cli, run
from .related_cases import ALL_CASES, case_app, case_fields, case_model

pytestmark = [pytest.mark.e2e, pytest.mark.skipif(not E2E_ENABLED, reason=SKIP_REASON)]


@pytest.fixture(scope="module", params=["plain", "multitenant"])
def project(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    parent = tmp_path_factory.mktemp(f"octave-related-{request.param}")
    return build_project(parent, multitenancy=request.param == "multitenant")


def _manage(project: Path, *args: str):
    return run(["uv", "run", "python", "manage.py", *args], project)


@pytest.mark.parametrize(("case", "template"), ALL_CASES, ids=[c for c, _ in ALL_CASES])
def test_model_passes_the_system_check_and_migrates(
    project: Path, case: str, template: str
) -> None:
    app, model = case_app(case), case_model(case)
    cli("add", app, "--model", model, "--path", str(project))
    cli(
        "add-model", app, model, "--fields", case_fields(case, template),
        "--force", "--path", str(project),
    )  # fmt: skip

    checked = _manage(project, "check")
    assert checked.returncode == 0, checked.stdout + checked.stderr

    made = _manage(project, "makemigrations", app)
    assert made.returncode == 0, made.stdout + made.stderr
    migrated = _manage(project, "migrate")
    assert migrated.returncode == 0, migrated.stdout + migrated.stderr
