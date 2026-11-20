"""Tests for from-import coalescing."""

from __future__ import annotations

from django_octave.models_gen.cst_util import coalesce_from_imports, ensure_import_lines


def test_coalesce_permission_imports() -> None:
    src = '''"""views."""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny

class X:
    pass
'''
    out = coalesce_from_imports(src)
    assert out.count("from rest_framework.permissions import") == 1
    assert "IsAuthenticated" in out
    assert "AllowAny" in out


def test_ensure_import_lines_merges_same_module() -> None:
    src = "from rest_framework.permissions import IsAuthenticated\n\n"
    out = ensure_import_lines(
        src, ["from rest_framework.permissions import AllowAny\n"]
    )
    assert out.count("from rest_framework.permissions import") == 1
    assert "IsAuthenticated" in out and "AllowAny" in out
