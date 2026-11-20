"""Best-effort formatting of generated Python files."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def format_written_python(path: Path) -> bool:
    """Run ``ruff format`` on ``path`` if ruff is available.

    Returns True if formatting ran successfully. Never raises for missing ruff.
    """
    path = Path(path)
    if not path.is_file():
        return False
    ruff = shutil.which("ruff")
    if ruff is None:
        return False
    try:
        result = subprocess.run(
            [ruff, "format", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return result.returncode == 0
