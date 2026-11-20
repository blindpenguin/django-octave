"""Unit tests for frontend compose injection."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.frontend_gen.compose import (
    COMPOSE_MARKER_BEGIN,
    COMPOSE_MARKER_END,
    ComposeInjectError,
    build_dev_frontend_service,
    build_prod_frontend_service,
    inject_compose_frontend,
    inject_project_compose,
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


def test_build_dev_and_prod_blocks() -> None:
    dev = build_dev_frontend_service(has_web=True)
    assert "5173:5173" in dev
    assert "pnpm dev" in dev
    assert "- web" in dev
    prod = build_prod_frontend_service(has_web=True)
    assert "8080:80" in prod
    assert "context: ./frontend" in prod


def test_inject_dev_compose(tmp_path: Path) -> None:
    path = tmp_path / "docker-compose.yml"
    path.write_text(SAMPLE, encoding="utf-8")
    assert inject_compose_frontend(path, prod=False) is True
    text = path.read_text(encoding="utf-8")
    assert COMPOSE_MARKER_BEGIN in text
    assert "frontend:" in text
    assert text.index(COMPOSE_MARKER_END) < text.index("\nvolumes:")
    assert inject_compose_frontend(path, prod=False) is False
    assert inject_compose_frontend(path, prod=False, force=True) is True


def test_inject_prod_compose(tmp_path: Path) -> None:
    path = tmp_path / "docker-compose.prod.yml"
    path.write_text(SAMPLE, encoding="utf-8")
    assert inject_compose_frontend(path, prod=True) is True
    text = path.read_text(encoding="utf-8")
    assert "8080:80" in text
    assert "context: ./frontend" in text


def test_inject_refuses_unmarked_frontend(tmp_path: Path) -> None:
    path = tmp_path / "docker-compose.yml"
    path.write_text(
        "services:\n  web:\n    build: .\n  frontend:\n    image: node\n",
        encoding="utf-8",
    )
    with pytest.raises(ComposeInjectError):
        inject_compose_frontend(path)


def test_inject_project_both(tmp_path: Path) -> None:
    (tmp_path / "docker-compose.yml").write_text(SAMPLE, encoding="utf-8")
    (tmp_path / "docker-compose.prod.yml").write_text(SAMPLE, encoding="utf-8")
    written = inject_project_compose(tmp_path)
    assert len(written) == 2


def test_inject_missing_file(tmp_path: Path) -> None:
    assert inject_compose_frontend(tmp_path / "missing.yml") is False
