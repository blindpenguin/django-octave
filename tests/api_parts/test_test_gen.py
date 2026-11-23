"""Unit tests for test/factory generation."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from django_octave.api_parts.test_gen import (
    StubExistsError,
    StubOptions,
    build_api_test_source,
    build_model_factory_source,
    build_model_test_source,
    build_user_factory_source,
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
    api = build_api_test_source(app_name="blog", model_name="Post")
    assert 'reverse("post-list")' in api
    assert "PostFactory" in api
    assert "skip" not in api.lower() or "pytest.mark.skip" not in api

    scoped = build_api_test_source(
        app_name="blog", model_name="Post", tenant_aware=True
    )
    assert "pytest.mark.skip" not in scoped
    assert "tenant_client" in scoped

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


def test_build_user_factory_uses_django_password() -> None:
    src = build_user_factory_source()
    assert 'password = factory.django.Password("password")' in src
    assert "skip_postgeneration_save = True" in src
    assert "PostGenerationMethodCall(" not in src


TENANT_SAMPLE = '''
from django.db import models
from apps.core.models import TenantAwareModel


class Note(TenantAwareModel):
    name = models.CharField(max_length=255)
'''


def test_factory_for_tenant_aware_model_has_tenant_subfactory() -> None:
    info = inspect_model_fields(TENANT_SAMPLE, "Note")
    src = build_model_factory_source(app_name="notes", model_name="Note", info=info)
    assert 'tenant = factory.SubFactory("tests.factories.tenant.TenantFactory")' in src


def test_factory_for_plain_model_has_no_tenant() -> None:
    info = inspect_model_fields(SAMPLE, "Post")
    src = build_model_factory_source(app_name="blog", model_name="Post", info=info)
    assert "tenant" not in src


def test_tenant_api_tests_cover_header_and_isolation() -> None:
    src = build_api_test_source(app_name="notes", model_name="Note", tenant_aware=True)
    assert "pytest.mark.skip" not in src
    assert "test_list_without_tenant_header_forbidden" in src
    assert "test_list_excludes_other_tenants" in src
    assert "test_retrieve_other_tenant_not_found" in src
    ast.parse(src)


def test_tenant_api_tests_pass_owner_kwarg_to_every_factory_call() -> None:
    src = build_api_test_source(
        app_name="notes", model_name="Note", tenant_aware=True, owner_kw="author=user"
    )
    assert src.count("author=user") >= 4
    ast.parse(src)


def test_ensure_test_fixtures_adds_tenant_fixtures_only_when_asked(tmp_path: Path) -> None:
    plain = tmp_path / "plain" / "conftest.py"
    scoped = tmp_path / "scoped" / "conftest.py"
    plain.parent.mkdir()
    scoped.parent.mkdir()

    ensure_test_fixtures(plain)
    ensure_test_fixtures(scoped, use_multitenancy=True)

    assert "def tenant_client" not in plain.read_text(encoding="utf-8")
    assert "def tenant_client" in scoped.read_text(encoding="utf-8")
    assert ensure_test_fixtures(scoped, use_multitenancy=True) is False  # idempotent


def test_ensure_test_fixtures_upgrades_existing_conftest(tmp_path: Path) -> None:
    conftest = tmp_path / "conftest.py"
    ensure_test_fixtures(conftest)

    changed = ensure_test_fixtures(conftest, use_multitenancy=True)

    assert changed is True
    assert "def tenant_client" in conftest.read_text(encoding="utf-8")
    assert conftest.read_text(encoding="utf-8").count("def auth_client") == 1
