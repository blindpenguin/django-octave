"""Make a generator command all-or-nothing.

``rollback_on_error`` snapshots the files under a project root; when the command
fails part-way (any exception) the snapshot is restored, and when it succeeds every
Python file it changed is checked to still parse. A failed command therefore never
leaves half-written files behind.
"""

from __future__ import annotations

import ast
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

IGNORED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "staticfiles",
        "site",
        "dist",
        "media",
    }
)


class GeneratedCodeError(ValueError):
    """Raised when a command would leave a Python file that does not parse."""


def _snapshot(root: Path) -> dict[Path, bytes]:
    files: dict[Path, bytes] = {}
    for current, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for name in names:
            path = Path(current) / name
            if path.is_file() and not path.is_symlink():
                files[path] = path.read_bytes()
    return files


def _restore(root: Path, before: dict[Path, bytes]) -> None:
    for current, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for name in names:
            path = Path(current) / name
            if path not in before:
                path.unlink()
    for path, data in before.items():
        if not path.exists() or path.read_bytes() != data:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    # Remove directories the command created and left empty (deepest first).
    for current, dirs, _names in os.walk(root, topdown=False):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        directory = Path(current)
        if directory != root and not any(directory.iterdir()):
            directory.rmdir()


def _verify(root: Path, before: dict[Path, bytes]) -> None:
    for path, data in _snapshot(root).items():
        if path.suffix != ".py" or before.get(path) == data:
            continue
        try:
            ast.parse(data)
        except SyntaxError as exc:
            where = path.relative_to(root)
            msg = f"Generated code in {where} does not parse ({exc.msg}, line {exc.lineno})"
            raise GeneratedCodeError(msg) from exc


@contextmanager
def rollback_on_error(root: Path) -> Iterator[None]:
    """Restore ``root`` if the body raises or leaves an unparsable Python file."""
    before = _snapshot(root)
    try:
        yield
        _verify(root, before)
    except BaseException:
        _restore(root, before)
        raise
