"""Tests for models.py writer."""

from __future__ import annotations

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
