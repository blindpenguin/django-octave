"""Unit tests for test/factory generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.api_parts.test_gen import (
    StubExistsError,
    StubOptions,
    build_api_test_source,
    build_model_factory_source,
    build_model_test_source,
    ensure_test_fixtures,
    write_tests,
)
from django_octave.inspect.model_fields import inspect_model_fields

SAMPLE = '''
from django.db import models
from apps.core.models import TimeStampedModel

class Post(TimeStampedModel):
    title = models.CharField(max_length=100)
    body = models.TextField()
    published = models.BooleanField(default=False)
'''

TENANT = '''
from django.db import models
from apps.core.models import TenantAwareModel

class Item(TenantAwareModel):
    name = models.CharField(max_length=50)
'''


def test_build_model_factory_source() -> None:
    info = inspect_model_fields(SAMPLE, "Post")
    src = build_model_factory_source(app_name="blog", model_name="Post", info=info)
    assert "class PostFactory" in src
    assert "title = factory.Sequence" in src
    assert "published = True" in src
    assert "body = factory.Faker" in src
    assert "created_at" not in src.split("class PostFactory")[1] or "TODO" in src


def test_build_api_and_model_tests() -> None:
    api = build_api_test_source(app_name="blog", model_name="Post", skip_tenant=False)
    assert 'reverse("post-list")' in api
    assert "PostFactory" in api
    assert "skip" not in api.lower() or "pytest.mark.skip" not in api

    skipped = build_api_test_source(
        app_name="blog", model_name="Post", skip_tenant=True
    )
    assert "pytest.mark.skip" in skipped

    model = build_model_test_source(app_name="blog", model_name="Post")
    assert "PostFactory" in model
    assert "obj.pk" in model


def test_ensure_fixtures_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "conftest.py"
    path.write_text("import pytest\n", encoding="utf-8")
    assert ensure_test_fixtures(path) is True
    text = path.read_text(encoding="utf-8")
    assert "def api_client" in text
    assert ensure_test_fixtures(path) is False


def test_write_tests_api_and_force(tmp_path: Path) -> None:
    app_dir = tmp_path / "apps" / "blog"
    app_dir.mkdir(parents=True)
    (app_dir / "models.py").write_text(SAMPLE, encoding="utf-8")
    (app_dir / "views.py").write_text(
        "class PostViewSet:\n    pass\n",
        encoding="utf-8",
    )
    opts = StubOptions(app_name="blog", model_name="Post")
    paths = write_tests(
        tmp_path, app_dir, options=opts, use_multitenancy=False
    )
    assert any("blog_post.py" in str(p) for p in paths)
    assert any("test_blog_post_api.py" in str(p) for p in paths)
    assert (tmp_path / "tests" / "factories" / "user.py").exists()
    assert "def auth_client" in (tmp_path / "tests" / "conftest.py").read_text(
        encoding="utf-8"
    )

    with pytest.raises(StubExistsError):
        write_tests(tmp_path, app_dir, options=opts, use_multitenancy=False)

    write_tests(
        tmp_path,
        app_dir,
        options=StubOptions(app_name="blog", model_name="Post", force=True),
        use_multitenancy=False,
    )


def test_write_tests_model_only(tmp_path: Path) -> None:
    app_dir = tmp_path / "apps" / "blog"
    app_dir.mkdir(parents=True)
    (app_dir / "models.py").write_text(SAMPLE, encoding="utf-8")
    (app_dir / "views.py").write_text("# empty\n", encoding="utf-8")
    paths = write_tests(
        tmp_path,
        app_dir,
        options=StubOptions(app_name="blog", model_name="Post"),
        use_multitenancy=False,
    )
    assert any("test_blog_post_model.py" in str(p) for p in paths)


def test_tenant_aware_flag() -> None:
    info = inspect_model_fields(TENANT, "Item")
    assert info.has_tenant_aware is True
    assert info.has_timestamps is True
