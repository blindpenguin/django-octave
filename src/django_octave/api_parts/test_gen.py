"""Generate factory-boy factories and pytest stubs for a model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django_octave.inspect.model_fields import (
    ModelFieldInfo,
    inspect_model_fields_path,
    resolve_related_app_and_model,
)
from django_octave.models_gen.cst_util import class_exists
from django_octave.naming import pascal_to_snake

_OMIT_TYPES = frozenset(
    {
        "ManyToManyField",
        "FileField",
        "ImageField",
        "JSONField",
        "BinaryField",
    }
)
_AUTO_SKIP = frozenset({"created_at", "updated_at", "id"})


class StubExistsError(FileExistsError):
    """Raised when factory/test files already exist without force."""


@dataclass
class StubOptions:
    app_name: str
    model_name: str
    force: bool = False


def factory_module_stem(app_name: str, model_name: str) -> str:
    return f"{app_name}_{pascal_to_snake(model_name)}"


def factory_class_name(model_name: str) -> str:
    return f"{model_name}Factory"


def _field_factory_line(
    name: str,
    ftype: str,
    *,
    app_name: str,
    info: ModelFieldInfo,
) -> str | None:
    if name in _AUTO_SKIP or ftype in _OMIT_TYPES:
        return None
    if name in info.relations:
        rel = info.relations[name]
        if rel.kind == "m2m":
            return None
        to = rel.to or ""
        rel_app, rel_model = resolve_related_app_and_model(
            to if to else name, default_app=app_name
        )
        # User / AUTH_USER_MODEL style
        if rel_model in {"User", "AbstractUser"} or to in {
            "settings.AUTH_USER_MODEL",
            "AUTH_USER_MODEL",
        }:
            return f"    {name} = factory.SubFactory(UserFactory)"
        if rel_app == app_name:
            stem = factory_module_stem(rel_app, rel_model)
            return (
                f"    {name} = factory.SubFactory("
                f'"tests.factories.{stem}.{rel_model}Factory")'
            )
        return (
            f"    # TODO: wire SubFactory for {name} → {to or rel_model}\n"
            f"    # {name} = factory.SubFactory(...)"
        )

    if ftype in {"CharField", "SlugField"}:
        if name in {"name", "title", "slug"}:
            return f'    {name} = factory.Sequence(lambda n: f"{name}-{{n}}")'
        return f'    {name} = factory.Sequence(lambda n: f"{name}-{{n}}")'
    if ftype == "TextField":
        return f'    {name} = factory.Faker("paragraph")'
    if ftype == "EmailField":
        return f'    {name} = factory.Sequence(lambda n: f"{name}{{n}}@example.com")'
    if ftype == "BooleanField":
        return f"    {name} = True"
    if ftype in {
        "IntegerField",
        "PositiveIntegerField",
        "SmallIntegerField",
        "BigIntegerField",
    }:
        return f"    {name} = factory.Sequence(lambda n: n)"
    if ftype == "UUIDField":
        return f'    {name} = factory.Faker("uuid4")'
    if ftype in {"DateField", "DateTimeField", "TimeField"}:
        return f'    {name} = factory.Faker("date_time")'
    if ftype == "DecimalField":
        return f'    {name} = "0.00"'
    if ftype == "FloatField":
        return f"    {name} = 0.0"
    # Unknown: skip with comment
    return f"    # TODO: factory default for {name} ({ftype})"


def build_model_factory_source(
    *,
    app_name: str,
    model_name: str,
    info: ModelFieldInfo,
) -> str:
    lines: list[str] = []
    needs_user = False
    for name, ftype in info.fields.items():
        line = _field_factory_line(name, ftype, app_name=app_name, info=info)
        if line and "UserFactory" in line and "SubFactory(UserFactory)" in line:
            needs_user = True
        if line:
            lines.append(line)

    imports = [
        '"""Factories for ' + f"{app_name}.{model_name}" + '."""',
        "",
        "from __future__ import annotations",
        "",
        "import factory",
        "",
        f"from apps.{app_name}.models import {model_name}",
    ]
    if needs_user:
        imports.append("from tests.factories.user import UserFactory")
    imports.append("")
    imports.append("")
    body = [
        f"class {factory_class_name(model_name)}(factory.django.DjangoModelFactory):",
        "    class Meta:",
        f"        model = {model_name}",
        "",
    ]
    if lines:
        body.extend(lines)
    else:
        body.append("    pass")
    body.append("")
    return "\n".join(imports + body)


def build_user_factory_source() -> str:
    return '''"""User factory for API tests."""

from __future__ import annotations

import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    is_active = True
    password = factory.PostGenerationMethodCall("set_password", "password")
'''


def build_api_test_source(
    *,
    app_name: str,
    model_name: str,
    skip_tenant: bool,
) -> str:
    snake = pascal_to_snake(model_name)
    stem = factory_module_stem(app_name, model_name)
    factory_name = factory_class_name(model_name)
    skip_deco = (
        '@pytest.mark.skip(reason="tenant setup required")\n' if skip_tenant else ""
    )
    return f'''"""API smoke tests for {app_name}.{model_name}."""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status

from tests.factories.{stem} import {factory_name}


{skip_deco}@pytest.mark.django_db
def test_list_requires_auth(api_client) -> None:
    url = reverse("{snake}-list")
    response = api_client.get(url)
    assert response.status_code in {{status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}}


{skip_deco}@pytest.mark.django_db
def test_list_authenticated(auth_client) -> None:
    {factory_name}()
    response = auth_client.get(reverse("{snake}-list"))
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list) or "results" in data


{skip_deco}@pytest.mark.django_db
def test_retrieve_authenticated(auth_client) -> None:
    obj = {factory_name}()
    response = auth_client.get(reverse("{snake}-detail", kwargs={{"pk": obj.pk}}))
    assert response.status_code == status.HTTP_200_OK
'''


def build_model_test_source(
    *,
    app_name: str,
    model_name: str,
) -> str:
    stem = factory_module_stem(app_name, model_name)
    factory_name = factory_class_name(model_name)
    return f'''"""Model smoke tests for {app_name}.{model_name}."""

from __future__ import annotations

import pytest

from tests.factories.{stem} import {factory_name}


@pytest.mark.django_db
def test_{pascal_to_snake(model_name)}_factory_creates_instance() -> None:
    obj = {factory_name}()
    assert obj.pk is not None
    assert str(obj)
'''


_FIXTURE_BLOCK = """
@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def user(db):
    from tests.factories.user import UserFactory

    return UserFactory()


@pytest.fixture
def auth_client(user):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=user)
    return client
"""


def ensure_test_fixtures(conftest_path: Path) -> bool:
    """Append api_client/user/auth_client fixtures if missing. Return True if changed."""
    if not conftest_path.exists():
        conftest_path.write_text(
            '"""Pytest configuration."""\n\nfrom __future__ import annotations\n\n'
            "import pytest\n" + _FIXTURE_BLOCK,
            encoding="utf-8",
        )
        return True
    source = conftest_path.read_text(encoding="utf-8")
    if (
        "def api_client" in source
        and "def auth_client" in source
        and "def user" in source
    ):
        return False
    if "import pytest" not in source:
        source = "import pytest\n" + source
    source = source.rstrip() + "\n" + _FIXTURE_BLOCK
    conftest_path.write_text(source, encoding="utf-8")
    return True


def _ensure_pkg(dir_path: Path) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    init = dir_path / "__init__.py"
    if not init.exists():
        init.write_text("", encoding="utf-8")


def write_tests(
    project_root: Path,
    app_dir: Path,
    *,
    options: StubOptions,
    use_multitenancy: bool,
) -> list[Path]:
    """Write factory + API/model tests. Returns list of paths written/updated."""
    models_path = app_dir / "models.py"
    info = inspect_model_fields_path(models_path, options.model_name)
    snake = pascal_to_snake(options.model_name)
    stem = factory_module_stem(options.app_name, options.model_name)

    tests_dir = project_root / "tests"
    factories_dir = tests_dir / "factories"
    _ensure_pkg(tests_dir)
    _ensure_pkg(factories_dir)

    factory_path = factories_dir / f"{stem}.py"
    user_path = factories_dir / "user.py"
    views_path = app_dir / "views.py"
    has_viewset = views_path.is_file() and class_exists(
        views_path.read_text(encoding="utf-8"), f"{options.model_name}ViewSet"
    )
    api_path = tests_dir / f"test_{options.app_name}_{snake}_api.py"
    model_path = tests_dir / f"test_{options.app_name}_{snake}_model.py"
    target_test = api_path if has_viewset else model_path

    if not options.force:
        if factory_path.exists() and class_exists(
            factory_path.read_text(encoding="utf-8"),
            factory_class_name(options.model_name),
        ):
            raise StubExistsError(
                f"{factory_class_name(options.model_name)} already exists in "
                f"{factory_path}. Use --force to replace it."
            )
        if target_test.exists():
            raise StubExistsError(
                f"{target_test} already exists. Use --force to replace it."
            )

    written: list[Path] = []

    if not user_path.exists() or options.force:
        # Only overwrite user factory on force if we created it empty? Prefer create-if-missing
        if not user_path.exists():
            user_path.write_text(build_user_factory_source(), encoding="utf-8")
            written.append(user_path)

    factory_path.write_text(
        build_model_factory_source(
            app_name=options.app_name,
            model_name=options.model_name,
            info=info,
        ),
        encoding="utf-8",
    )
    written.append(factory_path)

    skip_tenant = use_multitenancy and info.has_tenant_aware
    if has_viewset:
        api_path.write_text(
            build_api_test_source(
                app_name=options.app_name,
                model_name=options.model_name,
                skip_tenant=skip_tenant,
            ),
            encoding="utf-8",
        )
        written.append(api_path)
        if model_path.exists() and options.force:
            # leave model file alone
            pass
    else:
        model_path.write_text(
            build_model_test_source(
                app_name=options.app_name,
                model_name=options.model_name,
            ),
            encoding="utf-8",
        )
        written.append(model_path)

    ensure_test_fixtures(tests_dir / "conftest.py")
    return written
