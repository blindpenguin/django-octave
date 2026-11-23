"""Tests for project detection and patching."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.options import DatabaseChoice
from django_octave.project.detect import NotOctaveProjectError, detect_project
from django_octave.project.patch import patch_installed_apps, patch_urls
from django_octave.prompts.new_project import NewProjectOptions
from django_octave.rendering.context import ProjectContext
from django_octave.rendering.writer import render_project


def _make_project(tmp_path: Path, *, multitenancy: bool = False) -> Path:
    options = NewProjectOptions(
        name="Sample",
        path=tmp_path,
        database=DatabaseChoice.SQLITE,
        docker=False,
        multitenancy=multitenancy,
        frontend=False,
        register=False,
        crud=False,
        force=False,
    )
    return render_project(ProjectContext.from_options(options))


def test_detect_project(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    project = detect_project(root)
    assert project.root == root
    assert project.use_multitenancy is False


def test_detect_multitenancy(tmp_path: Path) -> None:
    root = _make_project(tmp_path, multitenancy=True)
    assert detect_project(root).use_multitenancy is True


def test_detect_invalid(tmp_path: Path) -> None:
    with pytest.raises(NotOctaveProjectError):
        detect_project(tmp_path)


def test_patch_idempotent(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    settings = root / "config" / "settings" / "base.py"
    urls = root / "config" / "urls.py"
    assert patch_installed_apps(settings, "apps.blog") is True
    assert patch_installed_apps(settings, "apps.blog") is False
    assert 'apps.blog' in settings.read_text(encoding="utf-8")
    assert patch_urls(urls, "blog") is True
    assert patch_urls(urls, "blog") is False
    text = urls.read_text(encoding="utf-8")
    assert "include" in text
    assert 'path("api/", include("apps.blog.urls"))' in text
    assert 'api/blog/' not in text

    # Legacy api/<app>/ mount still counts as wired (no double-add).
    urls.write_text(
        'from django.urls import include, path\n'
        "urlpatterns = [\n"
        '    path("api/shop/", include("apps.shop.urls")),\n'
        "]\n",
        encoding="utf-8",
    )
    assert patch_urls(urls, "shop") is False
    assert 'path("api/shop/", include("apps.shop.urls"))' in urls.read_text(
        encoding="utf-8"
    )


def test_detect_multitenancy_via_tenancy_module_only(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    (root / "apps" / "core" / "tenancy.py").write_text("", encoding="utf-8")
    assert detect_project(root).use_multitenancy is True


def test_detect_multitenancy_legacy_middleware_layout(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    (root / "apps" / "core" / "middleware.py").write_text(
        "class TenantMiddleware: ...\n", encoding="utf-8"
    )
    assert detect_project(root).use_multitenancy is True
