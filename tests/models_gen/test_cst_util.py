"""Unit tests for cst_util method upsert helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.models_gen.cst_util import (
    method_exists,
    upsert_method,
)
from django_octave.models_gen.writer import ModelWriteError

SAMPLE = '''"""API views."""

from rest_framework import viewsets

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def list(self, request):
        return super().list(request)
'''

METHOD = '''
@action(detail=True, methods=["post"])
def publish(self, request, pk=None):
    obj = self.get_object()
    return Response({"id": obj.pk})
'''


def test_method_exists() -> None:
    assert method_exists(SAMPLE, "PostViewSet", "list")
    assert not method_exists(SAMPLE, "PostViewSet", "publish")
    assert not method_exists(SAMPLE, "OtherViewSet", "list")


def test_upsert_method_append_and_force(tmp_path: Path) -> None:
    path = tmp_path / "views.py"
    path.write_text(SAMPLE, encoding="utf-8")
    upsert_method(
        path,
        "PostViewSet",
        "publish",
        METHOD,
        force=False,
        header_imports=[
            "from rest_framework.decorators import action\n",
            "from rest_framework.response import Response\n",
        ],
    )
    text = path.read_text(encoding="utf-8")
    assert "def publish" in text
    assert "from rest_framework.decorators import action" in text
    assert method_exists(text, "PostViewSet", "publish")

    # Without force: leave existing method body
    upsert_method(
        path,
        "PostViewSet",
        "publish",
        METHOD.replace("obj.pk", '"skip"'),
        force=False,
        header_imports=[],
    )
    assert '"skip"' not in path.read_text(encoding="utf-8")

    upsert_method(
        path,
        "PostViewSet",
        "publish",
        METHOD.replace("obj.pk", '"forced"'),
        force=True,
        header_imports=[],
    )
    text = path.read_text(encoding="utf-8")
    assert text.count("def publish") == 1
    assert '"forced"' in text


def test_upsert_method_missing_class(tmp_path: Path) -> None:
    path = tmp_path / "views.py"
    path.write_text("from rest_framework import viewsets\n", encoding="utf-8")
    with pytest.raises(ModelWriteError, match="PostViewSet"):
        upsert_method(
            path,
            "PostViewSet",
            "publish",
            METHOD,
            force=False,
            header_imports=[],
        )


def test_upsert_class_with_unparsable_generated_source_names_the_file(tmp_path: Path) -> None:
    from django_octave.models_gen.cst_util import upsert_class

    target = tmp_path / "views.py"
    target.write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(ModelWriteError, match=r"Could not generate Broken for .*views\.py"):
        upsert_class(target, "Broken", "class Broken(:\n    pass\n", force=False, header_imports=[])

    assert target.read_text(encoding="utf-8") == "x = 1\n"


def test_upsert_method_with_unparsable_generated_source_names_the_file(tmp_path: Path) -> None:
    from django_octave.models_gen.cst_util import upsert_method

    target = tmp_path / "views.py"
    target.write_text("class A:\n    pass\n", encoding="utf-8")

    with pytest.raises(ModelWriteError, match=r"Could not generate method go for .*views\.py"):
        upsert_method(
            target, "A", "go", "def go(self:\n    pass\n", force=False, header_imports=[]
        )
