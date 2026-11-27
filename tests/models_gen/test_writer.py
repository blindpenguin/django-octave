"""Tests for models.py writer."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from django_octave.fields.parser import parse_fields
from django_octave.models_gen.writer import ModelExistsError, write_model


def test_append_model(tmp_path: Path) -> None:
    models = tmp_path / "models.py"
    models.write_text(
        "from django.db import models\nfrom apps.core.models import TimeStampedModel\n",
        encoding="utf-8",
    )
    write_model(
        models,
        model_name="Post",
        fields=parse_fields(["title:char:max=100"]),
        use_multitenancy=False,
        force=False,
    )
    text = models.read_text(encoding="utf-8")
    assert "class Post(TimeStampedModel)" in text
    assert "title = models.CharField" in text

    with pytest.raises(ModelExistsError):
        write_model(
            models,
            model_name="Post",
            fields=parse_fields(["title:char"]),
            use_multitenancy=False,
            force=False,
        )

    write_model(
        models,
        model_name="Post",
        fields=parse_fields(["title:char:max=50", "published:bool:default=false"]),
        use_multitenancy=False,
        force=True,
    )
    text = models.read_text(encoding="utf-8")
    assert text.count("class Post(") == 1
    assert "published" in text


def test_blank_line_between_models(tmp_path: Path) -> None:
    models = tmp_path / "models.py"
    models.write_text(
        "from django.db import models\nfrom apps.core.models import TimeStampedModel\n",
        encoding="utf-8",
    )
    write_model(
        models,
        model_name="Category",
        fields=parse_fields(["name:char"]),
        use_multitenancy=False,
        force=False,
    )
    write_model(
        models,
        model_name="Post",
        fields=parse_fields(["title:char"]),
        use_multitenancy=False,
        force=False,
    )
    text = models.read_text(encoding="utf-8")
    assert "class Category(" in text
    assert "class Post(" in text
    # At least one blank line between top-level classes
    assert "\n\nclass Post(" in text or "\n\n\nclass Post(" in text


def _write(models: Path, name: str, field: str, *, force: bool = False) -> None:
    write_model(
        models,
        model_name=name,
        fields=parse_fields([field]),
        use_multitenancy=False,
        force=force,
    )


def _class_sources(text: str) -> dict[str, str]:
    tree = ast.parse(text)
    return {
        n.name: ast.get_source_segment(text, n) or ""
        for n in tree.body
        if isinstance(n, ast.ClassDef)
    }


def test_force_keeps_the_model_where_it_is_and_the_others_unchanged(
    tmp_path: Path,
) -> None:
    models = tmp_path / "models.py"
    models.write_text(
        "from django.db import models\nfrom apps.core.models import TimeStampedModel\n",
        encoding="utf-8",
    )
    for name, field in (
        ("Category", "name:char"),
        ("Post", "title:char"),
        ("Tag", "label:char"),
    ):
        _write(models, name, field)
    before = _class_sources(models.read_text(encoding="utf-8"))

    _write(models, "Post", "headline:char", force=True)

    after = _class_sources(models.read_text(encoding="utf-8"))
    assert list(after) == ["Category", "Post", "Tag"]
    assert "headline = models.CharField" in after["Post"]
    assert "title" not in after["Post"]
    assert after["Category"] == before["Category"]
    assert after["Tag"] == before["Tag"]


def test_force_on_the_last_model_leaves_the_order_alone(tmp_path: Path) -> None:
    models = tmp_path / "models.py"
    models.write_text(
        "from django.db import models\nfrom apps.core.models import TimeStampedModel\n",
        encoding="utf-8",
    )
    _write(models, "Category", "name:char")
    _write(models, "Post", "title:char")

    _write(models, "Post", "headline:char", force=True)

    assert list(_class_sources(models.read_text(encoding="utf-8"))) == [
        "Category",
        "Post",
    ]
