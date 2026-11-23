"""Unit tests for compose service injection."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.celery_gen.compose import (
    COMPOSE_MARKER_BEGIN,
    COMPOSE_MARKER_END,
    ComposeInjectError,
    build_compose_services,
    inject_compose_services,
)

SAMPLE = """services:
  web:
    build: .
    ports:
      - "8000:8000"

  db:
    image: postgres:16-alpine

volumes:
  pgdata:
"""


def test_build_compose_services_deps() -> None:
    block = build_compose_services(has_db=True, has_web=True)
    assert "redis:" in block
    assert "worker:" in block
    assert "beat:" in block
    assert "- redis" in block
    assert "- web" in block
    assert "- db" in block


def test_build_compose_services_binds_redis_to_localhost() -> None:
    block = build_compose_services(has_db=False, has_web=True)

    assert '"127.0.0.1:6379:6379"' in block
    assert '- "6379:6379"' not in block


def test_inject_compose_insert_and_force(tmp_path: Path) -> None:
    path = tmp_path / "docker-compose.yml"
    path.write_text(SAMPLE, encoding="utf-8")
    assert inject_compose_services(path) is True
    text = path.read_text(encoding="utf-8")
    assert COMPOSE_MARKER_BEGIN in text
    assert "\nvolumes:" in text
    # celery block ends before top-level volumes
    assert text.index(COMPOSE_MARKER_END) < text.index("\nvolumes:")

    assert inject_compose_services(path) is False  # no force, markers present
    assert inject_compose_services(path, force=True) is True


def test_inject_refuses_unmarked_services(tmp_path: Path) -> None:
    path = tmp_path / "docker-compose.yml"
    path.write_text(
        "services:\n  web:\n    build: .\n  redis:\n    image: redis\n",
        encoding="utf-8",
    )
    with pytest.raises(ComposeInjectError):
        inject_compose_services(path)


def test_inject_missing_file(tmp_path: Path) -> None:
    assert inject_compose_services(tmp_path / "missing.yml") is False


def test_celery_services_build_the_dev_target() -> None:
    block = build_compose_services(has_db=True, has_web=True)

    assert block.count("build:\n      context: .\n      target: dev\n") == 2  # worker + beat
    assert "build: ." not in block
