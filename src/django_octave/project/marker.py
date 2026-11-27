"""The ``.octave.toml`` marker at the root of a generated project.

It records which django-octave generated the project and the options chosen. ``new``
writes it, the feature commands keep the feature flags in step, and ``detect_project``
reads it so that an ``add-*`` command refuses a project from a newer django-octave.

Only validated values are ever written (booleans, the three database names, an integer
and a version that matches a pattern), so no free text can reach the file. Reading uses
the standard library ``tomllib``; the flat file is written by hand.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, replace
from importlib import metadata
from pathlib import Path

from django_octave.errors import OctaveError
from django_octave.options import DatabaseChoice

FILENAME = ".octave.toml"
SCHEMA = 1
"""Marker format number this version reads and writes."""

UNKNOWN = "unknown"

_DATABASES = frozenset(choice.value for choice in DatabaseChoice)
_FEATURES = ("frontend", "register", "crud", "celery")
_VERSION_RE = re.compile(r"[0-9]+(?:\.[0-9]+){0,3}[A-Za-z0-9.+-]{0,32}")
_RELEASE_RE = re.compile(r"[0-9]+(?:\.[0-9]+)*")
_FIX = "fix or delete the file"

_HEADER = (
    "# Written by django-octave. Commit this file; the add-* commands read it.\n"
    "# It records the version that generated the project and the options chosen.\n"
    "# django-octave rewrites it when you add a feature, so keep hand edits out.\n"
)


class MarkerError(OctaveError, ValueError):
    """Raised when the marker is invalid, or the project is from a newer django-octave."""


@dataclass(frozen=True, slots=True)
class Marker:
    """The contents of ``.octave.toml``."""

    schema: int
    generator_version: str
    """Version of the django-octave that generated the project (or ``"unknown"``)."""

    database: str
    docker: bool
    multitenancy: bool
    frontend: bool
    register: bool
    crud: bool
    celery: bool


def _valid_version(value: str) -> bool:
    return value == UNKNOWN or _VERSION_RE.fullmatch(value) is not None


def current_version() -> str:
    """Version of the running django-octave, or ``"unknown"`` if it cannot be told."""
    try:
        version = metadata.version("django-octave")
    except metadata.PackageNotFoundError:
        return UNKNOWN
    return version if _valid_version(version) else UNKNOWN


def new_marker(*, database: str, docker: bool, multitenancy: bool) -> Marker:
    """A marker for a project that has just been generated (no optional feature yet)."""
    return Marker(
        schema=SCHEMA,
        generator_version=current_version(),
        database=database,
        docker=docker,
        multitenancy=multitenancy,
        frontend=False,
        register=False,
        crud=False,
        celery=False,
    )


def _validate_for_write(marker: Marker) -> None:
    if type(marker.schema) is not int or marker.schema < 1:
        msg = f"Refusing to write {FILENAME}: invalid schema {marker.schema!r}"
        raise MarkerError(msg)
    if not _valid_version(marker.generator_version):
        msg = f"Refusing to write {FILENAME}: invalid generator_version {marker.generator_version!r}"
        raise MarkerError(msg)
    if marker.database not in _DATABASES:
        msg = f"Refusing to write {FILENAME}: invalid database {marker.database!r}"
        raise MarkerError(msg)


def _toml_bool(value: bool) -> str:
    return "true" if value else "false"


def render_marker(marker: Marker) -> str:
    """The TOML text for ``marker`` (validated first)."""
    _validate_for_write(marker)
    return (
        f"{_HEADER}"
        f"schema = {marker.schema}\n"
        f'generator_version = "{marker.generator_version}"\n'
        "\n"
        "[project]\n"
        f'database = "{marker.database}"\n'
        f"docker = {_toml_bool(marker.docker)}\n"
        f"multitenancy = {_toml_bool(marker.multitenancy)}\n"
        "\n"
        "[features]\n"
        f"frontend = {_toml_bool(marker.frontend)}\n"
        f"register = {_toml_bool(marker.register)}\n"
        f"crud = {_toml_bool(marker.crud)}\n"
        f"celery = {_toml_bool(marker.celery)}\n"
    )


def write_marker(root: Path, marker: Marker) -> Path:
    """Write ``marker`` to ``root/.octave.toml`` and return the path."""
    path = root / FILENAME
    path.write_text(render_marker(marker), encoding="utf-8")
    return path


def _problem(path: Path, problem: str) -> MarkerError:
    return MarkerError(f"{path}: {problem}; {_FIX}")


def _table(path: Path, data: dict[str, object], name: str) -> dict[str, object]:
    table = data.get(name)
    if not isinstance(table, dict):
        raise _problem(path, f"missing the [{name}] table")
    return table


def _bool(path: Path, table: dict[str, object], section: str, key: str) -> bool:
    value = table.get(key)
    if type(value) is not bool:
        raise _problem(path, f"{key} in [{section}] must be true or false")
    return value


def read_marker(root: Path) -> Marker | None:
    """Read ``root/.octave.toml``; ``None`` when there is no such file.

    Raises :class:`MarkerError` (naming the file) when it is not a valid marker.
    """
    path = root / FILENAME
    if not path.is_file():
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise _problem(path, f"not valid TOML ({exc})") from exc

    schema = data.get("schema")
    if type(schema) is not int or schema < 1:
        raise _problem(path, "schema must be a whole number of 1 or more")
    version = data.get("generator_version")
    if not isinstance(version, str) or not _valid_version(version):
        raise _problem(path, "generator_version must be a version such as 0.3.0")

    project = _table(path, data, "project")
    database = project.get("database")
    if not isinstance(database, str) or database not in _DATABASES:
        allowed = ", ".join(sorted(_DATABASES))
        raise _problem(path, f"database in [project] must be one of: {allowed}")
    features = _table(path, data, "features")
    return Marker(
        schema=schema,
        generator_version=version,
        database=database,
        docker=_bool(path, project, "project", "docker"),
        multitenancy=_bool(path, project, "project", "multitenancy"),
        frontend=_bool(path, features, "features", "frontend"),
        register=_bool(path, features, "features", "register"),
        crud=_bool(path, features, "features", "crud"),
        celery=_bool(path, features, "features", "celery"),
    )


def update_features(root: Path, **changes: bool) -> bool:
    """Set feature flags in an existing marker; return whether the file was written.

    Nothing is written (and no file is created) when the project has no marker, so old
    projects stay as they are. Only the named flags change; the version and the other
    options are kept.
    """
    for name, value in changes.items():
        if name not in _FEATURES:
            msg = f"{name!r} is not a feature flag (use one of {', '.join(_FEATURES)})"
            raise TypeError(msg)
        if type(value) is not bool:
            msg = f"feature flag {name!r} must be a bool, not {type(value).__name__}"
            raise TypeError(msg)
    marker = read_marker(root)
    if marker is None:
        return False
    write_marker(root, replace(marker, **changes))
    return True


def _release(version: str) -> tuple[int, ...] | None:
    """The numeric release of ``version`` (``0.4.0.dev1`` -> ``(0, 4, 0)``)."""
    match = _RELEASE_RE.match(version)
    if match is None:
        return None
    return tuple(int(part) for part in match.group().split("."))


def check_compatible(marker: Marker, *, running: str | None = None) -> None:
    """Refuse a marker written by a newer django-octave than the one running.

    Both the marker format (``schema``) and the generator version are checked. The
    check is skipped when either version is unknown.
    """
    if marker.schema > SCHEMA:
        msg = (
            f"{FILENAME} was written by a newer django-octave (marker schema "
            f"{marker.schema}; this version reads up to {SCHEMA}). "
            "Upgrade django-octave and try again."
        )
        raise MarkerError(msg)
    current = running if running is not None else current_version()
    if UNKNOWN in (marker.generator_version, current):
        return
    generated = _release(marker.generator_version)
    now = _release(current)
    if generated is None or now is None:
        return
    size = max(len(generated), len(now))
    pad = (0,) * size
    if (*generated, *pad)[:size] > (*now, *pad)[:size]:
        msg = (
            f"This project was generated by django-octave {marker.generator_version}, "
            f"but you are running {current}. Upgrade django-octave and try again."
        )
        raise MarkerError(msg)
