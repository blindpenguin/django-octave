"""End-to-end proof of the generated-project hardening (opt in with ``OCTAVE_E2E=1``).

Generates real projects (with and without multitenancy, with the SPA backend), installs
them with ``uv sync`` and exercises production settings against real Django.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from .helpers import (
    E2E_ENABLED,
    SKIP_REASON,
    build_project,
    env_file_without,
    prod_env,
    run,
)

pytestmark = [pytest.mark.e2e, pytest.mark.skipif(not E2E_ENABLED, reason=SKIP_REASON)]

HERE = Path(__file__).parent
HARDENING = HERE / "hardening_scenarios.py.tmpl"
PROXY = HERE / "proxy_scenarios.py.tmpl"
APPS = (("notes", "Item"), ("things", "Item"))  # same class name in two apps (audit S2)
ALLOWED_DEPLOY_WARNINGS = {"security.W021", "drf_spectacular.W002"}


@pytest.fixture(scope="module", params=["multitenant", "plain"])
def project(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Path:
    parent = tmp_path_factory.mktemp(f"octave-hardening-{request.param}")
    multitenancy = request.param == "multitenant"
    root = build_project(parent, multitenancy=multitenancy, apps=APPS if multitenancy else ())
    done = run(["uv", "run", "python", "manage.py", "collectstatic", "--noinput"], root, prod_env(root))
    assert done.returncode == 0, done.stdout + done.stderr
    return root


def _manage(project: Path, *args: str, **env: str | None):
    return run(["uv", "run", "python", "manage.py", *args], project, prod_env(project, **env))


def test_collectstatic_writes_the_manifest(project: Path) -> None:
    assert (project / "staticfiles" / "staticfiles.json").is_file()


def test_deploy_check_has_no_errors_and_only_known_warnings(project: Path) -> None:
    done = _manage(project, "check", "--deploy", "--fail-level", "ERROR")

    assert done.returncode == 0, done.stdout + done.stderr
    codes = set(re.findall(r"\((\w+\.[EW]\d+)\)", done.stdout + done.stderr))
    assert codes <= ALLOWED_DEPLOY_WARNINGS, f"unexpected deploy warnings: {codes}"


def test_prod_refuses_to_boot_without_allowed_hosts(project: Path) -> None:
    with env_file_without(project, "DJANGO_ALLOWED_HOSTS"):
        done = _manage(project, "check", DJANGO_ALLOWED_HOSTS=None)

    assert done.returncode != 0
    assert "DJANGO_ALLOWED_HOSTS is not set" in done.stderr


def test_prod_refuses_to_boot_with_a_wildcard_host(project: Path) -> None:
    done = _manage(project, "check", DJANGO_ALLOWED_HOSTS="example.com,*")

    assert done.returncode != 0
    assert "must not contain '*'" in done.stderr


def test_prod_boots_with_explicit_hosts(project: Path) -> None:
    done = _manage(project, "check", DJANGO_ALLOWED_HOSTS="example.com,www.example.com")

    assert done.returncode == 0, done.stderr


def test_same_named_tenant_models_in_two_apps_pass_the_system_check(project: Path) -> None:
    if not (project / "apps" / "things").is_dir():
        pytest.skip("only the multitenancy project has two apps")

    done = run(["uv", "run", "python", "manage.py", "check"], project)

    assert done.returncode == 0, done.stdout + done.stderr


def _copy(template: Path, project: Path, name: str) -> str:
    target = project / "tests" / name
    shutil.copy(template, target)
    return f"tests/{name}"


def test_production_scenarios_pass(project: Path) -> None:
    scenario = _copy(HARDENING, project, "test_hardening_prod.py")

    done = run(["uv", "run", "pytest", "-q", scenario, "-p", "no:cacheprovider"], project, prod_env(project))

    assert done.returncode == 0, done.stdout + done.stderr


def test_rate_limits_use_the_real_client_address_behind_one_proxy(project: Path) -> None:
    scenario = _copy(PROXY, project, "test_hardening_proxy.py")
    env = prod_env(project, DJANGO_NUM_PROXIES="1")

    done = run(["uv", "run", "pytest", "-q", scenario, "-p", "no:cacheprovider"], project, env)

    assert done.returncode == 0, done.stdout + done.stderr
