#!/usr/bin/env python3
"""Smoke-check an installed django-octave distribution (wheel or sdist).

Intended for CI via::

    uv run --isolated --no-project --with dist/*.whl scripts/smoke_dist.py

Not collected by pytest (no test_* functions).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


def _fail(msg: str) -> None:
    print(f"smoke_dist: FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    try:
        import django_octave
    except ImportError as exc:
        _fail(f"cannot import django_octave: {exc}")

    package_dir = Path(django_octave.__file__).resolve().parent
    templates = package_dir / "templates"
    if not templates.is_dir():
        _fail(f"templates directory missing at {templates}")

    project_tpl = templates / "project"
    app_tpl = templates / "app"
    if not project_tpl.is_dir():
        _fail(f"project templates missing at {project_tpl}")
    if not app_tpl.is_dir():
        _fail(f"app templates missing at {app_tpl}")

    j2 = list(templates.rglob("*.j2"))
    if not j2:
        _fail("no .j2 template files found under templates/")

    if importlib.util.find_spec("django_octave.cli") is None:
        _fail("django_octave.cli not importable")

    # Prefer the installed console script when on PATH; fall back to module main.
    try:
        completed = subprocess.run(
            ["django-octave", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            _fail(
                f"django-octave --help exited {completed.returncode}: "
                f"{completed.stderr or completed.stdout}"
            )
    except FileNotFoundError:
        from django_octave.cli import app

        result = app(args=["--help"], standalone_mode=False)
        if result not in (None, 0):
            _fail(f"cli --help returned {result!r}")

    print(f"smoke_dist: OK (django_octave at {package_dir}, {len(j2)} templates)")


if __name__ == "__main__":
    main()
