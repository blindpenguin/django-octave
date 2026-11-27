"""``detect_project`` reads ``.octave.toml`` and refuses a project from a newer version."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.project import marker as marker_module
from django_octave.project.detect import NotOctaveProjectError, detect_project
from django_octave.project.marker import (
    FILENAME,
    SCHEMA,
    Marker,
    MarkerError,
    write_marker,
)


def _fake_project(root: Path, *, tenancy_files: bool = False) -> Path:
    """The smallest tree ``detect_project`` accepts."""
    (root / "apps").mkdir(parents=True)
    (root / "apps" / "__init__.py").write_text("", encoding="utf-8")
    settings = root / "config" / "settings"
    settings.mkdir(parents=True)
    (settings / "base.py").write_text("INSTALLED_APPS = []\n", encoding="utf-8")
    (root / "config" / "urls.py").write_text("urlpatterns = []\n", encoding="utf-8")
    if tenancy_files:
        (root / "apps" / "core").mkdir()
        (root / "apps" / "core" / "tenancy.py").write_text("", encoding="utf-8")
    return root


def _marker(**overrides: object) -> Marker:
    values: dict[str, object] = {
        "schema": SCHEMA,
        "generator_version": "0.3.0",
        "database": "sqlite",
        "docker": False,
        "multitenancy": False,
        "frontend": False,
        "register": False,
        "crud": False,
        "celery": False,
    }
    values.update(overrides)
    return Marker(**values)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def running_version(monkeypatch: pytest.MonkeyPatch) -> str:
    """Pin the running version so the tests do not depend on the package version."""
    monkeypatch.setattr(marker_module, "current_version", lambda: "0.3.0")
    return "0.3.0"


def test_detect_project_without_a_marker_has_none(tmp_path: Path) -> None:
    project = detect_project(_fake_project(tmp_path))

    assert project.marker is None
    assert not (tmp_path / FILENAME).exists()


@pytest.mark.parametrize(
    "generated", ["0.3.0", "0.2.9", "0.3", "0.3.0.dev1", "unknown"]
)
def test_detect_project_returns_the_marker_when_it_is_equal_or_older(
    tmp_path: Path, generated: str
) -> None:
    root = _fake_project(tmp_path)
    marker = _marker(generator_version=generated, database="postgres", docker=True)
    write_marker(root, marker)

    assert detect_project(root).marker == marker


@pytest.mark.parametrize(
    "generated", ["0.3.1", "0.4.0", "1.0.0", "0.10.0", "0.4.0.dev1"]
)
def test_detect_project_refuses_a_marker_from_a_newer_version(
    tmp_path: Path, generated: str
) -> None:
    root = _fake_project(tmp_path)
    write_marker(root, _marker(generator_version=generated))

    with pytest.raises(MarkerError) as raised:
        detect_project(root)

    assert generated in str(raised.value)
    assert "0.3.0" in str(raised.value)


def test_detect_project_refuses_a_newer_marker_schema(tmp_path: Path) -> None:
    root = _fake_project(tmp_path)
    write_marker(root, _marker(schema=SCHEMA + 1))

    with pytest.raises(MarkerError, match="newer django-octave"):
        detect_project(root)


def test_detect_project_with_an_invalid_marker_names_the_file(tmp_path: Path) -> None:
    root = _fake_project(tmp_path)
    (root / FILENAME).write_text("schema = [", encoding="utf-8")

    with pytest.raises(MarkerError, match=r"\.octave\.toml.*fix or delete"):
        detect_project(root)


def test_detect_project_still_reports_a_directory_that_is_not_a_project(
    tmp_path: Path,
) -> None:
    # The structure check comes first, so a stray marker does not change that answer.
    write_marker(tmp_path, _marker(generator_version="9.9.9"))

    with pytest.raises(NotOctaveProjectError):
        detect_project(tmp_path)


def test_detect_project_takes_multitenancy_from_the_files_not_the_marker(
    tmp_path: Path,
) -> None:
    root = _fake_project(tmp_path / "plain")
    write_marker(root, _marker(multitenancy=True))
    tenant_root = _fake_project(tmp_path / "tenant", tenancy_files=True)
    write_marker(tenant_root, _marker(multitenancy=False))

    assert detect_project(root).use_multitenancy is False
    assert detect_project(tenant_root).use_multitenancy is True
