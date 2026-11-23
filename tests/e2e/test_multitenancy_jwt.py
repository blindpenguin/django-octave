"""End-to-end proof that multitenancy works for JWT clients.

Generates a real project, installs it with ``uv sync`` (network) and runs a
scenario suite plus the project's own generated tests inside it.

Opt in with ``OCTAVE_E2E=1 uv run pytest -m e2e``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from django_octave.cli import app

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.environ.get("OCTAVE_E2E") != "1",
        reason="set OCTAVE_E2E=1 to run (generates a project and runs uv sync)",
    ),
]

SCENARIOS = Path(__file__).parent / "tenancy_jwt_scenarios.py.tmpl"
runner = CliRunner()


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        args, cwd=cwd, capture_output=True, text=True, check=False, timeout=900
    )


def _cli(*args: str) -> None:
    result = runner.invoke(app, list(args))
    assert result.exit_code == 0, result.output


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    parent = tmp_path_factory.mktemp("octave-e2e")
    _cli(
        "new", "demo", "-d", "sqlite", "--no-docker", "--multitenancy",
        "--no-frontend", "--path", str(parent),
    )  # fmt: skip
    root = parent / "demo"
    _cli("add", "notes", "--path", str(root))
    _cli("add-test", "notes", "Note", "--path", str(root))
    shutil.copy(root / ".env.example", root / ".env")
    for step in (["uv", "sync"], ["uv", "run", "python", "manage.py", "makemigrations"]):
        done = _run(step, root)
        assert done.returncode == 0, done.stdout + done.stderr
    return root


def test_generated_project_suite_passes(project: Path) -> None:
    done = _run(["uv", "run", "pytest", "-q"], project)

    assert done.returncode == 0, done.stdout + done.stderr


def test_jwt_tenant_scenarios_pass(project: Path) -> None:
    shutil.copy(SCENARIOS, project / "tests" / "test_tenancy_jwt.py")

    done = _run(["uv", "run", "pytest", "-q", "tests/test_tenancy_jwt.py"], project)

    assert done.returncode == 0, done.stdout + done.stderr
