"""The generated OwnerScopedMixin, executed for real with small fakes (no Django needed)."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from django_octave.options import DatabaseChoice
from django_octave.prompts.new_project import NewProjectOptions
from django_octave.rendering.context import ProjectContext
from django_octave.rendering.writer import render_project


def _render(tmp_path: Path, *, multitenancy: bool) -> Path:
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
    return render_project(ProjectContext.from_options(options)) / "apps" / "core" / "ownership.py"


@pytest.fixture
def Mixin(tmp_path: Path):  # noqa: N802
    source = _render(tmp_path, multitenancy=False).read_text(encoding="utf-8")
    namespace: dict[str, object] = {}
    exec(compile(source, "ownership.py", "exec"), namespace)  # noqa: S102
    return namespace["OwnerScopedMixin"]


class FakeQuerySet:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def filter(self, **conditions: object) -> FakeQuerySet:
        return FakeQuerySet([r for r in self.rows if all(r.get(k) == v for k, v in conditions.items())])

    def none(self) -> FakeQuerySet:
        return FakeQuerySet([])


class FakeSerializer:
    def __init__(self) -> None:
        self.saved: dict[str, object] | None = None

    def save(self, **extra: object) -> None:
        self.saved = extra


def _user(authenticated: bool = True) -> SimpleNamespace:
    return SimpleNamespace(is_authenticated=authenticated)


ROWS = [
    {"id": 1, "owner": "alice", "tenant": "a"},
    {"id": 2, "owner": "bob", "tenant": "a"},
    {"id": 3, "owner": "alice", "tenant": "b"},
]


def test_ownership_module_is_generated_for_every_project(tmp_path: Path) -> None:
    for multitenancy in (False, True):
        path = _render(tmp_path / str(multitenancy), multitenancy=multitenancy)
        ast.parse(path.read_text(encoding="utf-8"))
        assert "class OwnerScopedMixin" in path.read_text(encoding="utf-8")


def test_queryset_is_limited_to_the_requesting_user(Mixin) -> None:
    class Base:
        def get_queryset(self) -> FakeQuerySet:
            return FakeQuerySet(ROWS)

    class View(Mixin, Base):
        pass

    view = View()
    view.request = SimpleNamespace(user="alice")
    view.request.user = type("U", (str,), {"is_authenticated": True})("alice")

    assert [r["id"] for r in view.get_queryset().rows] == [1, 3]


def test_the_owner_field_name_is_configurable(Mixin) -> None:
    class Base:
        def get_queryset(self) -> FakeQuerySet:
            return FakeQuerySet([{"id": 1, "created_by": "alice"}, {"id": 2, "created_by": "bob"}])

    class View(Mixin, Base):
        owner_field = "created_by"

    view = View()
    view.request = SimpleNamespace(user=type("U", (str,), {"is_authenticated": True})("bob"))

    assert [r["id"] for r in view.get_queryset().rows] == [2]


def test_anonymous_users_get_an_empty_queryset(Mixin) -> None:
    class Base:
        def get_queryset(self) -> FakeQuerySet:
            return FakeQuerySet(ROWS)

    class View(Mixin, Base):
        pass

    view = View()
    view.request = SimpleNamespace(user=_user(authenticated=False))

    assert view.get_queryset().rows == []


@pytest.mark.parametrize("hook", ["perform_create", "perform_update"])
def test_the_server_sets_the_owner_on_create_and_update(Mixin, hook: str) -> None:
    class View(Mixin):
        pass

    view = View()
    view.request = SimpleNamespace(user="alice")
    serializer = FakeSerializer()

    getattr(view, hook)(serializer)

    assert serializer.saved == {"owner": "alice"}


def test_owner_mixin_first_composes_with_a_tenant_style_mixin(Mixin) -> None:
    class TenantLike:
        """Like TenantScopedMixin: builds its queryset without calling super()."""

        def get_queryset(self) -> FakeQuerySet:
            return FakeQuerySet([r for r in ROWS if r["tenant"] == "a"])

    class Right(Mixin, TenantLike):
        pass

    class Wrong(TenantLike, Mixin):
        pass

    user = type("U", (str,), {"is_authenticated": True})("alice")
    right, wrong = Right(), Wrong()
    right.request = wrong.request = SimpleNamespace(user=user)

    assert [r["id"] for r in right.get_queryset().rows] == [1]  # tenant a AND owner alice
    assert [r["id"] for r in wrong.get_queryset().rows] == [1, 2]  # owner scoping silently lost
