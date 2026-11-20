"""Tests for Conventional Commit release-note formatting."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "release-notes.py"


def _load():
    spec = importlib.util.spec_from_file_location("release_notes", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_format_groups_user_facing_types() -> None:
    mod = _load()
    md = mod._format(
        [
            "feat(add): support --model for starter class name",
            "fix(serializers): insert nested helpers before parent",
            "docs(layout): document shared api/ mounts",
            "chore: tweak ruff config",
            "chore(release): 0.2.3",
            "wip stuff",
        ]
    )
    assert "### Features" in md
    assert "**add:** support --model for starter class name" in md
    assert "### Fixes" in md
    assert "**serializers:** insert nested helpers before parent" in md
    assert "### Documentation" in md
    assert "chore: tweak" not in md
    assert "0.2.3" not in md
    assert "wip stuff" not in md


def test_breaking_marker() -> None:
    mod = _load()
    md = mod._format(["feat(api)!: rename collection paths"])
    assert "### Breaking changes" in md
    assert "**api:** rename collection paths" in md
