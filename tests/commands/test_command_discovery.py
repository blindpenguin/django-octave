"""Commands register themselves: dropping a module into ``commands/`` is enough."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from django_octave.cli import import_command_modules


def _make_package(tmp_path: Path, name: str, modules: dict[str, str]) -> Path:
    package = tmp_path / name
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    for module, source in modules.items():
        (package / f"{module}.py").write_text(source, encoding="utf-8")
    return package


@pytest.fixture
def load_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Create a throwaway package on ``sys.path`` and import it."""
    created: list[str] = []

    def load(name: str, modules: dict[str, str]):
        _make_package(tmp_path, name, modules)
        monkeypatch.syspath_prepend(str(tmp_path))
        created.append(name)
        return importlib.import_module(name)

    yield load
    for name in list(sys.modules):
        if name in created or any(name.startswith(f"{c}.") for c in created):
            del sys.modules[name]


def test_discovery_imports_public_modules_in_alphabetical_order(load_package) -> None:
    package = load_package(
        "octave_fake_ok",
        {"zeta": "LOADED = True", "alpha": "LOADED = True"},
    )

    imported = import_command_modules(package)

    assert imported == ["alpha", "zeta"]
    assert "octave_fake_ok.alpha" in sys.modules
    assert "octave_fake_ok.zeta" in sys.modules


def test_discovery_skips_modules_that_start_with_an_underscore(load_package) -> None:
    package = load_package(
        "octave_fake_private",
        {"public": "LOADED = True", "_common": "raise RuntimeError('must not import')"},
    )

    imported = import_command_modules(package)

    assert imported == ["public"]
    assert "octave_fake_private._common" not in sys.modules


def test_discovery_lets_an_import_error_through(load_package) -> None:
    package = load_package(
        "octave_fake_broken",
        {"broken": "import module_that_does_not_exist_anywhere"},
    )

    with pytest.raises(ModuleNotFoundError, match="module_that_does_not_exist"):
        import_command_modules(package)


def test_discovery_registers_every_real_command() -> None:
    from django_octave import commands
    from django_octave.cli import app

    imported = import_command_modules(commands)

    assert "_common" not in imported
    assert len(imported) == len(app.registered_commands)
