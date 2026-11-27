"""Every expected generator failure is an ``OctaveError`` and keeps its built-in base."""

from __future__ import annotations

import importlib
import inspect
import pkgutil

import pytest

import django_octave
from django_octave.errors import OctaveError

# Exceptions that report "this file/class already exists"; they were FileExistsError
# before OctaveError was introduced and must stay so. Every other domain exception
# was a ValueError.
FILE_EXISTS_ERRORS = frozenset(
    {
        "AdminExistsError",
        "StubExistsError",
        "ViewSetExistsError",
        "PermissionExistsError",
        "CeleryExistsError",
        "SerializerExistsError",
        "TaskExistsError",
        "ActionExistsError",
        "AppExistsError",
        "TargetExistsError",
        "FrontendExistsError",
        "ModelExistsError",
    }
)


def _domain_exceptions() -> list[type[BaseException]]:
    found: dict[str, type[BaseException]] = {}
    for module_info in pkgutil.walk_packages(django_octave.__path__, "django_octave."):
        module = importlib.import_module(module_info.name)
        for name, obj in vars(module).items():
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseException)
                and obj.__module__ == module.__name__
                and name != "OctaveError"
            ):
                found[f"{obj.__module__}.{obj.__qualname__}"] = obj
    return [found[key] for key in sorted(found)]


DOMAIN_EXCEPTIONS = _domain_exceptions()


def test_errors_discovery_finds_the_domain_exceptions() -> None:
    # Guards the discovery itself: it must not silently find nothing.
    assert len(DOMAIN_EXCEPTIONS) >= 40


@pytest.mark.parametrize(
    "exc", DOMAIN_EXCEPTIONS, ids=lambda e: f"{e.__module__}.{e.__qualname__}"
)
def test_errors_domain_exception_is_octave_error(exc: type[BaseException]) -> None:
    assert issubclass(exc, OctaveError)


@pytest.mark.parametrize(
    "exc", DOMAIN_EXCEPTIONS, ids=lambda e: f"{e.__module__}.{e.__qualname__}"
)
def test_errors_domain_exception_keeps_its_builtin_base(
    exc: type[BaseException],
) -> None:
    if exc.__name__ in FILE_EXISTS_ERRORS:
        assert issubclass(exc, FileExistsError)
    else:
        assert issubclass(exc, ValueError)
        assert not issubclass(exc, FileExistsError)
