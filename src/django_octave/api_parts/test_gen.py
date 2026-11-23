"""Generate factory-boy factories and pytest stubs for a model."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from django_octave.api_parts.ownership_gen import viewset_owner_field
from django_octave.formatting import format_written_python
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
        if rel_app and rel_model:
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
    if info.has_tenant_aware:
        lines.insert(0, '    tenant = factory.SubFactory("tests.factories.tenant.TenantFactory")')
    if lines:
        body.extend(lines)
    else:
        body.append("    pass")
    body.append("")
    return "\n".join(imports + body)


def build_tenant_factory_source() -> str:
    return '''"""Tenant factory for multitenancy API tests."""

from __future__ import annotations

import factory

from apps.core.models import Tenant


class TenantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tenant

    name = factory.Sequence(lambda n: f"Tenant {n}")
    slug = factory.Sequence(lambda n: f"tenant-{n}")
'''


def build_user_factory_source() -> str:
    return '''"""User factory for API tests."""

from __future__ import annotations

import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    is_active = True
    # Hash at create time (no post-generation hook / extra save).
    password = factory.django.Password("password")
'''


def detect_viewset_allows_anonymous(views_source: str, viewset_class: str) -> bool:
    """Return True if ``viewset_class`` looks like it uses AllowAny."""
    if viewset_class not in views_source or "AllowAny" not in views_source:
        return False
    # Narrow to the class body: from class line until next top-level class or EOF.
    pattern = rf"class {re.escape(viewset_class)}\b[\s\S]*?(?=\nclass |\Z)"
    match = re.search(pattern, views_source)
    if not match:
        return False
    body = match.group(0)
    return "permission_classes" in body and "AllowAny" in body


def _owner_factory_kw(info: ModelFieldInfo) -> str:
    """Return ``author=user``-style kwargs when a User FK is present."""
    for name, rel in info.relations.items():
        if rel.kind == "m2m":
            continue
        to = rel.to or ""
        _, rel_model = resolve_related_app_and_model(to if to else name, default_app="")
        is_user = (
            rel_model in {"User", "AbstractUser"}
            or to.endswith(".User")
            or to in {"settings.AUTH_USER_MODEL", "AUTH_USER_MODEL"}
            or "AUTH_USER_MODEL" in to
        )
        if is_user:
            return f"{name}=user"
    return ""


def _build_api_test_source(
    *,
    app_name: str,
    model_name: str,
    tenant_aware: bool = False,
    anonymous_list_ok: bool = False,
    owner_kw: str = "",
    owner_field: str | None = None,
) -> str:
    """API test module for one model's viewset.

    With ``owner_field`` (an owner-scoped viewset) the smoke tests create rows owned by the
    requester and four isolation tests are appended.
    """
    if owner_field:
        owner_kw = f"{owner_field}=user"
    snake = pascal_to_snake(model_name)
    stem = factory_module_stem(app_name, model_name)
    factory_name = factory_class_name(model_name)
    kwargs = ", ".join(k for k in ("tenant=tenant" if tenant_aware else "", owner_kw) if k)
    factory_call = f"{factory_name}({kwargs})"
    if anonymous_list_ok:
        list_anon = f'''@pytest.mark.django_db
def test_list_anonymous_ok(api_client) -> None:
    {factory_name}()
    url = reverse("{snake}-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
'''
    else:
        list_anon = f'''@pytest.mark.django_db
def test_list_requires_auth(api_client) -> None:
    url = reverse("{snake}-list")
    response = api_client.get(url)
    assert response.status_code in {{status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}}
'''
    if tenant_aware:
        owner_fixture = ", user" if owner_kw else ""
        return f'''"""API tests for {app_name}.{model_name} (tenant-scoped)."""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status

from tests.factories.{stem} import {factory_name}
from tests.factories.tenant import TenantFactory


def _items(data):  # type: ignore[no-untyped-def]
    return data["results"] if isinstance(data, dict) else data


{list_anon}

@pytest.mark.django_db
def test_list_without_tenant_header_forbidden(auth_client) -> None:
    response = auth_client.get(reverse("{snake}-list"))
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_list_authenticated(tenant_client, tenant{owner_fixture}) -> None:
    {factory_call}
    response = tenant_client.get(reverse("{snake}-list"))
    assert response.status_code == status.HTTP_200_OK
    assert len(_items(response.json())) == 1


@pytest.mark.django_db
def test_retrieve_authenticated(tenant_client, tenant{owner_fixture}) -> None:
    obj = {factory_call}
    response = tenant_client.get(reverse("{snake}-detail", kwargs={{"pk": obj.pk}}))
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_list_excludes_other_tenants(tenant_client, tenant{owner_fixture}) -> None:
    {factory_call}
    {factory_name}(tenant=TenantFactory(){", " + owner_kw if owner_kw else ""})
    response = tenant_client.get(reverse("{snake}-list"))
    assert response.status_code == status.HTTP_200_OK
    assert len(_items(response.json())) == 1


@pytest.mark.django_db
def test_retrieve_other_tenant_not_found(tenant_client, tenant{owner_fixture}) -> None:
    other = {factory_name}(tenant=TenantFactory(){", " + owner_kw if owner_kw else ""})
    response = tenant_client.get(reverse("{snake}-detail", kwargs={{"pk": other.pk}}))
    assert response.status_code == status.HTTP_404_NOT_FOUND
'''
    auth_args = "auth_client, user" if owner_kw else "auth_client"
    return f'''"""API smoke tests for {app_name}.{model_name}."""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status

from tests.factories.{stem} import {factory_name}


{list_anon}

@pytest.mark.django_db
def test_list_authenticated({auth_args}) -> None:
    {factory_call}
    response = auth_client.get(reverse("{snake}-list"))
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list) or "results" in data


@pytest.mark.django_db
def test_retrieve_authenticated({auth_args}) -> None:
    obj = {factory_call}
    response = auth_client.get(reverse("{snake}-detail", kwargs={{"pk": obj.pk}}))
    assert response.status_code == status.HTTP_200_OK
'''


def build_api_test_source(
    *,
    app_name: str,
    model_name: str,
    tenant_aware: bool = False,
    anonymous_list_ok: bool = False,
    owner_kw: str = "",
    owner_field: str | None = None,
) -> str:
    source = _build_api_test_source(
        app_name=app_name,
        model_name=model_name,
        tenant_aware=tenant_aware,
        anonymous_list_ok=anonymous_list_ok,
        owner_kw=owner_kw,
        owner_field=owner_field,
    )
    if not owner_field:
        return source
    stem = factory_module_stem(app_name, model_name)
    factory_name = factory_class_name(model_name)
    marker = f"from tests.factories.{stem} import {factory_name}\n"
    assert marker in source
    source = source.replace("import pytest\n", "import factory\nimport pytest\n", 1)
    source = source.replace(
        "from django.urls import reverse\n",
        "from django.db.models import Model\nfrom django.urls import reverse\n",
        1,
    )
    source = source.replace(
        marker,
        f"from apps.{app_name}.models import {model_name}\n"
        + marker
        + "from tests.factories.user import UserFactory\n",
        1,
    )
    return source.rstrip("\n") + "\n" + _owner_tests_source(
        model_name=model_name,
        factory_name=factory_name,
        owner_field=owner_field,
        tenant_aware=tenant_aware,
    )


def _owner_tests_source(
    *, model_name: str, factory_name: str, owner_field: str, tenant_aware: bool
) -> str:
    snake = pascal_to_snake(model_name)
    if tenant_aware:
        client, args, manager = "tenant_client", "tenant_client, tenant, user", "all_objects"
        mine = f"{factory_name}(tenant=tenant, {owner_field}=user)"
        theirs = f"{factory_name}(tenant=tenant, {owner_field}=UserFactory())"
        other_args = "tenant_client, tenant"
    else:
        client, args, manager = "auth_client", "auth_client, user", "objects"
        mine = f"{factory_name}({owner_field}=user)"
        theirs = f"{factory_name}({owner_field}=UserFactory())"
        other_args = "auth_client"
    return f'''

def _rows(data):  # type: ignore[no-untyped-def]
    return data["results"] if isinstance(data, dict) else data


def _create_payload() -> dict:
    data = factory.build(dict, FACTORY_CLASS={factory_name})
    for key in ("{owner_field}", "tenant"):
        data.pop(key, None)
    if any(isinstance(value, Model) for value in data.values()):
        pytest.skip("needs a hand-written payload: the factory builds related objects")
    return data


@pytest.mark.django_db
def test_list_only_returns_own_rows({args}) -> None:
    own = {mine}
    {theirs}
    response = {client}.get(reverse("{snake}-list"))
    assert response.status_code == status.HTTP_200_OK
    assert [row["id"] for row in _rows(response.json())] == [own.pk]


@pytest.mark.django_db
def test_other_users_row_is_not_found({other_args}) -> None:
    other = {theirs}
    response = {client}.get(reverse("{snake}-detail", kwargs={{"pk": other.pk}}))
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_create_sets_the_owner_to_the_requester_and_ignores_the_payload({args}) -> None:
    payload = {{**_create_payload(), "{owner_field}": UserFactory().pk}}
    response = {client}.post(reverse("{snake}-list"), payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.content
    created = {model_name}.{manager}.get(pk=response.json()["id"])
    assert created.{owner_field} == user


@pytest.mark.django_db
def test_update_cannot_change_the_owner({args}) -> None:
    own = {mine}
    response = {client}.patch(
        reverse("{snake}-detail", kwargs={{"pk": own.pk}}),
        {{"{owner_field}": UserFactory().pk}},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    own.refresh_from_db()
    assert own.{owner_field} == user
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


_TENANT_FIXTURE_BLOCK = """
@pytest.fixture
def tenant(user):
    from apps.core.models import Membership, Tenant

    tenant = Tenant.objects.create(name="Test Tenant", slug="test-tenant")
    Membership.objects.create(user=user, tenant=tenant)
    return tenant


@pytest.fixture
def tenant_client(user, tenant):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT_ID=str(tenant.id))
    return client
"""


def ensure_test_fixtures(conftest_path: Path, *, use_multitenancy: bool = False) -> bool:
    """Append missing api_client/user/auth_client (and tenant) fixtures.

    Return True if the file changed.
    """
    if not conftest_path.exists():
        source = (
            '"""Pytest configuration."""\n\nfrom __future__ import annotations\n\n'
            "import pytest\n"
        )
    else:
        source = conftest_path.read_text(encoding="utf-8")
    original = source
    if not (
        "def api_client" in source
        and "def auth_client" in source
        and "def user" in source
    ):
        if "import pytest" not in source:
            source = "import pytest\n" + source
        source = source.rstrip() + "\n" + _FIXTURE_BLOCK
    if use_multitenancy and "def tenant_client" not in source:
        source = source.rstrip() + "\n" + _TENANT_FIXTURE_BLOCK
    if source == original and conftest_path.exists():
        return False
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

    tenant_aware = use_multitenancy and info.has_tenant_aware
    if tenant_aware:
        tenant_factory = factories_dir / "tenant.py"
        if not tenant_factory.exists():
            tenant_factory.write_text(build_tenant_factory_source(), encoding="utf-8")
            written.append(tenant_factory)
    if has_viewset:
        views_src = views_path.read_text(encoding="utf-8")
        anonymous_ok = detect_viewset_allows_anonymous(
            views_src, f"{options.model_name}ViewSet"
        )
        api_path.write_text(
            build_api_test_source(
                app_name=options.app_name,
                model_name=options.model_name,
                tenant_aware=tenant_aware,
                anonymous_list_ok=anonymous_ok,
                owner_kw=_owner_factory_kw(info),
                owner_field=viewset_owner_field(views_src, f"{options.model_name}ViewSet"),
            ),
            encoding="utf-8",
        )
        format_written_python(api_path)
        written.append(api_path)
    else:
        model_path.write_text(
            build_model_test_source(
                app_name=options.app_name,
                model_name=options.model_name,
            ),
            encoding="utf-8",
        )
        format_written_python(model_path)
        written.append(model_path)

    format_written_python(factory_path)
    ensure_test_fixtures(tests_dir / "conftest.py", use_multitenancy=tenant_aware)
    return written
