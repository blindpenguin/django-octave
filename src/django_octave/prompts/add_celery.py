"""Interactive prompts for ``django-octave add-celery``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AddCeleryPromptOptions:
    path: Path
    force: bool


def resolve_add_celery_options(
    *,
    path: Path,
    force: bool,
) -> AddCeleryPromptOptions:
    return AddCeleryPromptOptions(path=path, force=force)
