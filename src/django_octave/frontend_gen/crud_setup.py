"""Orchestrate frontend CRUD generation for one or all resources."""

from __future__ import annotations

from pathlib import Path

from django_octave.errors import OctaveError
from django_octave.frontend_gen.crud_discover import (
    discover_resources,
    require_resource,
)
from django_octave.frontend_gen.crud_fields import enrich_resource
from django_octave.frontend_gen.crud_pages import render_crud_pages
from django_octave.frontend_gen.crud_types import ResourceSpec
from django_octave.frontend_gen.crud_wire import (
    list_crud_plurals_on_disk,
    wire_crud,
)
from django_octave.frontend_gen.detect import frontend_configured
from django_octave.frontend_gen.django_patch import ensure_user_list_api


class CrudSetupError(OctaveError, ValueError):
    """Raised when CRUD setup cannot complete safely."""


def _frontend_dir(root: Path) -> Path:
    return root / "frontend"


def _ensure_user_fk_support(root: Path) -> None:
    """Wire ``/api/users/`` so User FK selects have a list endpoint."""
    if not (root / "apps" / "users").is_dir():
        return
    if not (root / "config" / "urls.py").is_file():
        return
    ensure_user_list_api(root)


def _specs_for_wiring(root: Path, newly: list[ResourceSpec]) -> list[ResourceSpec]:
    """Merge newly generated specs with other CRUD page dirs already on disk."""
    by_plural = {s.model_plural: s for s in newly}
    frontend = _frontend_dir(root)
    for plural in list_crud_plurals_on_disk(frontend):
        if plural in by_plural:
            continue
        # Minimal stub for wiring only
        by_plural[plural] = ResourceSpec(
            app_name="",
            model_name=plural.replace("_", " ").title().replace(" ", ""),
            model_snake=plural.rstrip("s") if plural.endswith("s") else plural,
            model_plural=plural,
            api_collection=f"/api/{plural}/",
            viewset_name="",
        )
    # Prefer enriched names from newly when present
    for s in newly:
        by_plural[s.model_plural] = s
    return sorted(by_plural.values(), key=lambda s: s.model_plural)


def generate_crud(
    root: Path,
    app_name: str,
    model_name: str,
    *,
    force: bool = False,
    fk_label_overrides: dict[str, str] | None = None,
) -> tuple[list[Path], list[str]]:
    """Generate CRUD pages for one model. Returns (written paths, warnings)."""
    root = root.resolve()
    if not frontend_configured(root):
        raise CrudSetupError("No frontend/ found. Run: django-octave add-frontend")

    _ensure_user_fk_support(root)
    spec = require_resource(root, app_name, model_name)
    enriched, warnings = enrich_resource(
        root, spec, fk_label_overrides=fk_label_overrides
    )
    if enriched.skip_reason:
        raise CrudSetupError(enriched.skip_reason)

    written = render_crud_pages(_frontend_dir(root), enriched, force=force)
    written.extend(wire_crud(_frontend_dir(root), _specs_for_wiring(root, [enriched])))
    return written, warnings


def generate_crud_all(
    root: Path,
    *,
    force: bool = False,
    fk_label_overrides: dict[str, str] | None = None,
) -> tuple[list[Path], list[str], list[str]]:
    """Generate CRUD for all discoverable resources.

    Returns (written paths, warnings, soft-skip messages).
    """
    root = root.resolve()
    if not frontend_configured(root):
        raise CrudSetupError("No frontend/ found. Run: django-octave add-frontend")

    _ensure_user_fk_support(root)
    written: list[Path] = []
    warnings: list[str] = []
    skips: list[str] = []
    generated: list[ResourceSpec] = []

    for spec in discover_resources(root):
        if spec.skip_reason:
            skips.append(f"{spec.app_name}.{spec.model_name}: {spec.skip_reason}")
            continue
        enriched, field_warnings = enrich_resource(
            root, spec, fk_label_overrides=fk_label_overrides
        )
        warnings.extend(field_warnings)
        if enriched.skip_reason:
            skips.append(f"{spec.app_name}.{spec.model_name}: {enriched.skip_reason}")
            continue
        try:
            written.extend(
                render_crud_pages(_frontend_dir(root), enriched, force=force)
            )
            generated.append(enriched)
        except FileExistsError:
            if force:
                raise
            skips.append(
                f"{spec.app_name}.{spec.model_name}: pages exist (use --force)"
            )
            # Still include existing for wiring
            generated.append(enriched)

    if generated:
        written.extend(
            wire_crud(_frontend_dir(root), _specs_for_wiring(root, generated))
        )
    return written, warnings, skips
