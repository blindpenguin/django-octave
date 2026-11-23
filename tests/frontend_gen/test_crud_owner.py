"""Owner-scoped viewsets: the SPA shows the owner but never lets the user edit it."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.frontend_gen.crud_discover import discover_app_resources
from django_octave.frontend_gen.crud_fields import enrich_resource
from django_octave.frontend_gen.crud_pages import render_crud_pages
from django_octave.frontend_gen.setup import render_frontend

MODELS = """\
from django.db import models


class Note(models.Model):
    title = models.CharField(max_length=200)
    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="+")
    assignee = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
"""

SCOPED = """\
class NoteViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    owner_field = "owner"
    queryset = Note.objects.all()
"""
PLAIN = """\
class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
"""


def _project(tmp_path: Path, views: str) -> Path:
    root = tmp_path / "proj"
    app = root / "apps" / "notes"
    app.mkdir(parents=True)
    (app / "models.py").write_text(MODELS, encoding="utf-8")
    (app / "views.py").write_text(views, encoding="utf-8")
    (app / "urls.py").write_text(
        'router.register("notes", NoteViewSet, basename="note")\n', encoding="utf-8"
    )
    render_frontend(root / "frontend", project_name="Proj", project_slug="proj", include_register=False)
    return root


def _page(root: Path, name: str) -> str:
    return (root / "frontend" / "src" / "pages" / "notes" / name).read_text(encoding="utf-8")


def test_discovery_reads_the_owner_field_of_a_scoped_viewset(tmp_path: Path) -> None:
    root = _project(tmp_path, SCOPED)

    (spec,) = discover_app_resources(root, "notes")

    assert spec.owner_field == "owner"


def test_discovery_uses_the_declared_attribute_and_defaults_to_owner(tmp_path: Path) -> None:
    custom = SCOPED.replace('owner_field = "owner"', "owner_field = 'assignee'")
    no_attr = SCOPED.replace('    owner_field = "owner"\n', "")

    assert discover_app_resources(_project(tmp_path / "a", custom), "notes")[0].owner_field == "assignee"
    assert discover_app_resources(_project(tmp_path / "b", no_attr), "notes")[0].owner_field == "owner"


def test_a_plain_viewset_has_no_owner_field(tmp_path: Path) -> None:
    root = _project(tmp_path, PLAIN)

    assert discover_app_resources(root, "notes")[0].owner_field is None


def test_the_owner_becomes_a_read_only_field_and_other_user_fks_stay_editable(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path, SCOPED)
    (spec,) = discover_app_resources(root, "notes")

    enriched, _ = enrich_resource(root, spec)

    kinds = {f.name: f.kind for f in enriched.fields}
    assert kinds["owner"] == "readonly"
    assert kinds["assignee"] in {"fk", "number"}  # still an editable input
    assert kinds["title"] == "string"
    assert enriched.owner_field == "owner"


def test_without_owner_scoping_the_owner_fk_stays_editable(tmp_path: Path) -> None:
    root = _project(tmp_path, PLAIN)
    (spec,) = discover_app_resources(root, "notes")

    enriched, _ = enrich_resource(root, spec)

    assert {f.name: f.kind for f in enriched.fields}["owner"] in {"fk", "number"}
    assert enriched.owner_field is None


def test_rendered_pages_show_the_owner_but_do_not_edit_it(tmp_path: Path) -> None:
    root = _project(tmp_path, SCOPED)
    (spec,) = discover_app_resources(root, "notes")
    enriched, _ = enrich_resource(root, spec)

    render_crud_pages(root / "frontend", enriched)

    detail = _page(root, "DetailView.vue")
    assert "item['owner']" in detail  # shown read-only
    for form in ("CreateView.vue", "EditView.vue"):
        text = _page(root, form)
        assert "'owner'" not in text and '"owner"' not in text, form
        assert "assignee" in text, form  # other user FKs remain in the form
    assert "owner" not in _page(root, "ListView.vue").replace("primaryLabel", "")


def test_without_owner_scoping_the_forms_still_contain_the_owner(tmp_path: Path) -> None:
    root = _project(tmp_path, PLAIN)
    (spec,) = discover_app_resources(root, "notes")
    enriched, _ = enrich_resource(root, spec)

    render_crud_pages(root / "frontend", enriched)

    assert "owner" in _page(root, "CreateView.vue")
    assert "owner" in _page(root, "EditView.vue")


@pytest.mark.parametrize("page", ["CreateView.vue", "EditView.vue", "DetailView.vue", "ListView.vue"])
def test_pages_for_owner_scoped_and_plain_resources_share_structure(
    tmp_path: Path, page: str
) -> None:
    scoped_root = _project(tmp_path / "s", SCOPED)
    plain_root = _project(tmp_path / "p", PLAIN)
    for root in (scoped_root, plain_root):
        (spec,) = discover_app_resources(root, "notes")
        render_crud_pages(root / "frontend", enrich_resource(root, spec)[0])

    scoped = _page(scoped_root, page)
    plain = _page(plain_root, page)

    # same template, only the owner field differs: nothing else is lost
    assert abs(len(scoped.splitlines()) - len(plain.splitlines())) <= 12
    assert "title" in scoped and "title" in plain
