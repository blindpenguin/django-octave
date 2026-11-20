"""Unit tests for permission generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.api_parts.permission_gen import (
    PermissionExistsError,
    PermissionOptions,
    PermissionPresetError,
    PermissionWireError,
    build_permission_class,
    resolve_viewset_class_name,
    validate_preset,
    wire_permission_to_viewset,
    write_permission,
)


def test_validate_preset() -> None:
    assert validate_preset("owner", use_multitenancy=False) == "owner"
    with pytest.raises(PermissionPresetError, match="Unknown"):
        validate_preset("nope", use_multitenancy=False)
    with pytest.raises(PermissionPresetError, match="multitenancy"):
        validate_preset("tenant_member", use_multitenancy=False)
    assert validate_preset("tenant_member", use_multitenancy=True) == "tenant_member"


@pytest.mark.parametrize(
    ("preset", "needle"),
    [
        ("owner", 'getattr(obj, "owner"'),
        ("staff_or_read", "SAFE_METHODS"),
        ("auth_or_read", "is_authenticated"),
        ("tenant_member", 'getattr(request, "tenant"'),
    ],
)
def test_build_permission_class(preset: str, needle: str) -> None:
    src = build_permission_class("IsThing", preset=preset, owner_attr="owner")
    assert "class IsThing(BasePermission)" in src
    assert needle in src


def test_build_owner_custom_attr() -> None:
    src = build_permission_class("IsAuthor", preset="owner", owner_attr="author")
    assert 'getattr(obj, "author"' in src


def test_write_permission_create_and_force(tmp_path: Path) -> None:
    opts = PermissionOptions(app_name="blog", class_name="IsOwner", preset="owner")
    path = write_permission(tmp_path, options=opts)
    text = path.read_text(encoding="utf-8")
    assert "class IsOwner(BasePermission)" in text
    assert "from rest_framework.permissions import BasePermission" in text

    with pytest.raises(PermissionExistsError):
        write_permission(tmp_path, options=opts)

    forced = PermissionOptions(
        app_name="blog",
        class_name="IsOwner",
        preset="staff_or_read",
        force=True,
    )
    write_permission(tmp_path, options=forced)
    text = path.read_text(encoding="utf-8")
    assert "SAFE_METHODS" in text
    assert "is_staff" in text


def test_write_second_class(tmp_path: Path) -> None:
    write_permission(
        tmp_path,
        options=PermissionOptions(app_name="blog", class_name="IsOwner", preset="owner"),
    )
    write_permission(
        tmp_path,
        options=PermissionOptions(
            app_name="blog", class_name="IsAuthOrRead", preset="auth_or_read"
        ),
    )
    text = (tmp_path / "permissions.py").read_text(encoding="utf-8")
    assert "class IsOwner" in text
    assert "class IsAuthOrRead" in text
    assert "SAFE_METHODS" in text


def test_resolve_viewset_class_name() -> None:
    assert resolve_viewset_class_name("Post") == "PostViewSet"
    assert resolve_viewset_class_name("PostViewSet") == "PostViewSet"


def test_wire_permission_replace_and_append(tmp_path: Path) -> None:
    views = tmp_path / "views.py"
    views.write_text(
        '''"""API views."""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
''',
        encoding="utf-8",
    )
    wire_permission_to_viewset(
        views,
        app_name="blog",
        viewset_class="PostViewSet",
        permission_class="IsOwner",
        append=False,
    )
    text = views.read_text(encoding="utf-8")
    assert "from apps.blog.permissions import IsOwner" in text
    assert "permission_classes = [IsOwner]" in text

    wire_permission_to_viewset(
        views,
        app_name="blog",
        viewset_class="PostViewSet",
        permission_class="IsAuthOrRead",
        append=True,
    )
    text = views.read_text(encoding="utf-8")
    assert "IsAuthOrRead" in text
    assert "permission_classes = [IsOwner, IsAuthOrRead]" in text


def test_wire_missing_viewset(tmp_path: Path) -> None:
    views = tmp_path / "views.py"
    views.write_text("from rest_framework import viewsets\n", encoding="utf-8")
    with pytest.raises(PermissionWireError, match="PostViewSet"):
        wire_permission_to_viewset(
            views,
            app_name="blog",
            viewset_class="PostViewSet",
            permission_class="IsOwner",
            append=False,
        )
