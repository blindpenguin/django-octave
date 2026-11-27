"""Shared helpers for the opt-in end-to-end suites (not collected as tests)."""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()

E2E_ENABLED = os.environ.get("OCTAVE_E2E") == "1"
SKIP_REASON = "set OCTAVE_E2E=1 to run (generates a project and runs uv sync)"


def run(
    args: list[str], cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        args,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )


def cli(*args: str) -> None:
    result = runner.invoke(app, list(args))
    assert result.exit_code == 0, result.output


def prod_env(project: Path, **overrides: str | None) -> dict[str, str]:
    """Environment for running a generated project with ``config.settings.prod``.

    A value of ``None`` removes the variable.
    """
    env = {
        "PATH": os.environ["PATH"],
        "HOME": os.environ.get("HOME", str(project)),
        "DJANGO_SETTINGS_MODULE": "config.settings.prod",
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(48),
        "DJANGO_ALLOWED_HOSTS": "example.com",
        "DATABASE_URL": f"sqlite:///{project / 'e2e-prod.sqlite3'}",
    }
    for key, value in overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return env


@contextmanager
def env_file_without(project: Path, *keys: str) -> Iterator[None]:
    """Temporarily drop ``keys`` from the project's ``.env`` (it also feeds settings)."""
    env_path = project / ".env"
    original = env_path.read_text(encoding="utf-8")
    kept = [
        line
        for line in original.splitlines()
        if not any(line.startswith(f"{key}=") for key in keys)
    ]
    env_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    try:
        yield
    finally:
        env_path.write_text(original, encoding="utf-8")


def build_project(
    parent: Path,
    *,
    multitenancy: bool,
    apps: tuple[tuple[str, str], ...] = (),
    configure: Callable[[Path], None] | None = None,
) -> Path:
    """Generate a project with the SPA backend (register on), sync it, make migrations.

    ``configure`` runs after the apps are added and before dependencies are synced,
    so a test can reshape models and wiring before the first migration is made.
    """
    cli(
        "new", "demo", "-d", "sqlite", "--no-docker",
        "--multitenancy" if multitenancy else "--no-multitenancy",
        "--frontend", "--register", "--no-crud", "--path", str(parent),
    )  # fmt: skip
    root = parent / "demo"
    for app_name, model in apps:
        cli("add", app_name, "--model", model, "--path", str(root))
    if configure is not None:
        configure(root)
    shutil.copy(root / ".env.example", root / ".env")
    for step in (
        ["uv", "sync"],
        ["uv", "run", "python", "manage.py", "makemigrations"],
    ):
        done = run(step, root)
        assert done.returncode == 0, done.stdout + done.stderr
    return root
