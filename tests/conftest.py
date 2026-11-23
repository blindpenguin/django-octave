"""Test-session setup shared by every test module."""

from __future__ import annotations

import os

# Typer forces ANSI styling when GITHUB_ACTIONS, FORCE_COLOR or PY_COLORS is set
# (read once, when typer.rich_utils is imported). Several tests compare plain `--help`
# text, which colour codes split into pieces, so make sure none of them is set before
# django_octave (and with it typer) is imported. This conftest loads before any test module.
for _variable in ("GITHUB_ACTIONS", "FORCE_COLOR", "PY_COLORS"):
    os.environ.pop(_variable, None)
