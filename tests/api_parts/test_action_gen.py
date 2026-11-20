"""Unit tests for action generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.api_parts.action_gen import (
    ActionExistsError,
    ActionMethodError,
    ActionNameError,
    ActionOptions,
    ActionTargetError,
    build_action_method,
    detect_viewset_tag,
    normalize_methods,
    parse_http_methods,
    validate_action_name,
    write_action,
)

VIEWS = '''"""API views for blog."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.blog.models import Post
from apps.blog.serializers import PostSerializer

@extend_schema_view(
    list=extend_schema(tags=["post"]),
    retrieve=extend_schema(tags=["post"]),
)
class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
'''


def test_validate_action_name() -> None:
    assert validate_action_name("publish") == "publish"
    assert validate_action_name("set_password") == "set_password"
    with pytest.raises(ActionNameError):
        validate_action_name("Publish")
    with pytest.raises(ActionNameError):
        validate_action_name("class")


def test_normalize_methods() -> None:
    assert normalize_methods(None, detail=True) == ["post"]
    assert normalize_methods(None, detail=False) == ["get"]
    assert parse_http_methods("POST,delete", detail=True) == ["post", "delete"]
    with pytest.raises(ActionMethodError):
        normalize_methods(["trace"], detail=True)


def test_build_detail_and_list() -> None:
    detail = build_action_method(
        "publish",
        detail=True,
        methods=["post"],
        tag="post",
        permission="IsOwner",
    )
    assert "detail=True" in detail
    assert "self.get_object()" in detail
    assert "permission_classes=[IsOwner]" in detail
    assert '@extend_schema(tags=["post"])' in detail

    listing = build_action_method(
        "recent",
        detail=False,
        methods=["get"],
        tag="post",
        url_path="recent-items",
    )
    assert "detail=False" in listing
    assert "paginate_queryset" in listing
    assert 'url_path="recent-items"' in listing


def test_detect_viewset_tag() -> None:
    assert detect_viewset_tag(VIEWS, "PostViewSet") == "post"


def test_write_action_force_and_options(tmp_path: Path) -> None:
    (tmp_path / "views.py").write_text(VIEWS, encoding="utf-8")
    (tmp_path / "permissions.py").write_text(
        "class IsOwner:\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "serializers.py").write_text(
        "class PostSerializer:\n    pass\nclass PublishSerializer:\n    pass\n",
        encoding="utf-8",
    )

    path = write_action(
        tmp_path,
        options=ActionOptions(
            app_name="blog",
            viewset="Post",
            action_name="publish",
            permission="IsOwner",
            serializer="PublishSerializer",
        ),
    )
    text = path.read_text(encoding="utf-8")
    assert "def publish" in text
    assert "from rest_framework.decorators import action" in text
    assert "from apps.blog.permissions import IsOwner" in text
    assert "PublishSerializer" in text
    assert "self.get_object()" in text

    with pytest.raises(ActionExistsError):
        write_action(
            tmp_path,
            options=ActionOptions(
                app_name="blog",
                viewset="PostViewSet",
                action_name="publish",
            ),
        )

    write_action(
        tmp_path,
        options=ActionOptions(
            app_name="blog",
            viewset="Post",
            action_name="publish",
            methods=["put"],
            force=True,
        ),
    )
    text = path.read_text(encoding="utf-8")
    assert text.count("def publish") == 1
    assert '"put"' in text

    write_action(
        tmp_path,
        options=ActionOptions(
            app_name="blog",
            viewset="Post",
            action_name="recent",
            detail=False,
        ),
    )
    assert "def recent" in path.read_text(encoding="utf-8")


def test_write_action_missing_viewset(tmp_path: Path) -> None:
    (tmp_path / "views.py").write_text(
        "from rest_framework import viewsets\n",
        encoding="utf-8",
    )
    with pytest.raises(ActionTargetError, match="PostViewSet"):
        write_action(
            tmp_path,
            options=ActionOptions(
                app_name="blog",
                viewset="Post",
                action_name="publish",
            ),
        )
