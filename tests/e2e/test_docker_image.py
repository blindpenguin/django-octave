"""Build the generated production image for real (opt in with ``OCTAVE_E2E_DOCKER=1``).

Needs a running Docker daemon and network access (base images, PyPI). Skips cleanly
when either the flag or the daemon is missing. Every image and container it creates
is removed afterwards.
"""

from __future__ import annotations

import secrets
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from .helpers import cli, run


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0  # noqa: S607


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        __import__("os").environ.get("OCTAVE_E2E_DOCKER") != "1",
        reason="set OCTAVE_E2E_DOCKER=1 to run (builds Docker images)",
    ),
    pytest.mark.skipif(not _docker_available(), reason="Docker daemon not available"),
]

DATABASES = ["sqlite", "postgres", "mariadb"]
TAG_PREFIX = "octave-e2e"


def _docker(*args: str, cwd: Path | None = None, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["docker", *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def _sh(image: str, command: str) -> subprocess.CompletedProcess[str]:
    return _docker("run", "--rm", "--entrypoint", "sh", image, "-c", command)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, tuple[Path, str]]]:
    """Generate one Docker-enabled project per database and build its default image."""
    images: dict[str, tuple[Path, str]] = {}
    try:
        for database in DATABASES:
            parent = tmp_path_factory.mktemp(f"octave-docker-{database}")
            cli(
                "new", "demo", "-d", database, "--docker", "--no-multitenancy",
                "--no-frontend", "--path", str(parent),
            )  # fmt: skip
            root = parent / "demo"
            tag = f"{TAG_PREFIX}-{database}-{secrets.token_hex(4)}"
            done = _docker("build", "-q", "-t", tag, ".", cwd=root)
            assert done.returncode == 0, done.stdout + done.stderr
            images[database] = (root, tag)
        yield images
    finally:
        for _, tag in images.values():
            _docker("rmi", "-f", tag)


@pytest.mark.parametrize("database", DATABASES)
def test_image_runs_as_non_root_without_compilers_curl_or_uv(
    built: dict[str, tuple[Path, str]], database: str
) -> None:
    _, tag = built[database]

    assert _docker("run", "--rm", tag, "whoami").stdout.strip() == "app"
    for binary in ("curl", "gcc", "cc", "uv"):
        found = _sh(tag, f"command -v {binary} || echo absent").stdout.strip()
        assert found == "absent", f"{binary} present in the production image: {found}"


@pytest.mark.parametrize("database", DATABASES)
def test_image_has_no_dev_dependencies_and_no_secret_in_its_environment(
    built: dict[str, tuple[Path, str]], database: str
) -> None:
    _, tag = built[database]

    assert "No module named 'pytest'" in _sh(tag, "python -c 'import pytest' 2>&1").stdout
    env = _docker("image", "inspect", tag, "--format", "{{range .Config.Env}}{{println .}}{{end}}")
    assert "DJANGO_SECRET_KEY" not in env.stdout
    assert "DATABASE_URL" not in env.stdout
    cmd = _docker("image", "inspect", tag, "--format", "{{json .Config.Cmd}}").stdout
    assert cmd.startswith('["gunicorn"')  # started from the venv, not `uv run`


@pytest.mark.parametrize(
    ("database", "module"), [("postgres", "psycopg"), ("mariadb", "MySQLdb")]
)
def test_image_contains_a_working_database_driver(
    built: dict[str, tuple[Path, str]], database: str, module: str
) -> None:
    _, tag = built[database]

    done = _sh(tag, f"python -c 'import {module}'")

    assert done.returncode == 0, done.stderr


def _get(url: str, host: str | None = None) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"X-Forwarded-Proto": "https"})  # noqa: S310
    if host:
        request.add_header("Host", host)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            return response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def test_container_serves_admin_with_collected_static_files(
    built: dict[str, tuple[Path, str]],
) -> None:
    _, tag = built["sqlite"]
    name = f"{TAG_PREFIX}-run-{secrets.token_hex(4)}"
    started = _docker(
        "run", "-d", "--name", name, "-p", "127.0.0.1::8000",
        "-e", "DJANGO_SETTINGS_MODULE=config.settings.prod",
        "-e", f"DJANGO_SECRET_KEY={secrets.token_urlsafe(48)}",
        "-e", "DJANGO_ALLOWED_HOSTS=localhost",
        "-e", "DATABASE_URL=sqlite:////tmp/run.sqlite3",
        tag,
    )  # fmt: skip
    assert started.returncode == 0, started.stderr
    try:
        port = _docker("port", name, "8000/tcp").stdout.strip().rsplit(":", 1)[-1]
        base = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 40
        status = 0
        while time.monotonic() < deadline:
            try:
                status, body = _get(f"{base}/admin/login/", host="localhost")
                break
            except OSError:
                time.sleep(1)
        assert status == 200, _docker("logs", name).stdout
        assert "/static/admin/css/base." in body  # manifest-hashed asset
        assert _get(f"{base}/api/schema/", host="localhost")[0] in {401, 403}
        assert _get(f"{base}/admin/login/", host="evil.example")[0] == 400
    finally:
        _docker("rm", "-f", name)


def test_dev_target_still_builds_with_uv_for_compose(
    built: dict[str, tuple[Path, str]],
) -> None:
    root, _ = built["sqlite"]
    tag = f"{TAG_PREFIX}-dev-{secrets.token_hex(4)}"
    try:
        done = _docker("build", "-q", "--target", "dev", "-t", tag, ".", cwd=root)
        assert done.returncode == 0, done.stdout + done.stderr
        assert _sh(tag, "command -v uv").returncode == 0
    finally:
        _docker("rmi", "-f", tag)


def test_build_uses_the_lock_file_when_present(built: dict[str, tuple[Path, str]]) -> None:
    root, _ = built["sqlite"]
    locked = run(["uv", "lock"], root)
    assert locked.returncode == 0, locked.stdout + locked.stderr
    tag = f"{TAG_PREFIX}-locked-{secrets.token_hex(4)}"
    try:
        done = _docker("build", "-t", tag, ".", cwd=root)
        assert done.returncode == 0, done.stdout + done.stderr
        assert "uv sync --locked" in done.stdout + done.stderr
    finally:
        _docker("rmi", "-f", tag)
        (root / "uv.lock").unlink(missing_ok=True)
