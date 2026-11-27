"""Make a viewset owner-scoped: ``OwnerScopedMixin``, ``owner_field`` and a read-only owner.

The contract is explicit. A generated owner permission class declares
``owner_attr = "<attr>"``; a scoped viewset declares ``owner_field = "<attr>"``.
Nothing is inferred from field names.
"""

from __future__ import annotations

import re
from pathlib import Path

from django_octave.errors import OctaveError
from django_octave.models_gen.cst_util import (
    class_exists,
    ensure_class_base,
    ensure_import_lines,
    ensure_read_only_field,
    set_class_attribute,
)
from django_octave.safe_names import validate_owner_attr

OWNER_IMPORT = "from apps.core.ownership import OwnerScopedMixin\n"

_OWNER_ATTR_RE = re.compile(
    r'^\s*owner_attr\s*=\s*["\']([A-Za-z_][A-Za-z0-9_]*)["\']', re.M
)
_OWNER_FIELD_RE = re.compile(
    r'^\s*owner_field\s*=\s*["\']([A-Za-z_][A-Za-z0-9_]*)["\']', re.M
)
_QUERYSET_MODEL_RE = re.compile(
    r"queryset\s*=\s*(\w+)\.(?:objects|all_objects|_default_manager)"
)


class OwnershipModuleMissingError(OctaveError, ValueError):
    """Raised when a project lacks ``apps/core/ownership.py``."""


class OwnershipWireError(OctaveError, ValueError):
    """Raised when a viewset cannot be made owner-scoped."""


def ensure_ownership_module(apps_dir: Path) -> None:
    """Fail early for projects generated before ``OwnerScopedMixin`` existed."""
    if not (apps_dir / "core" / "ownership.py").is_file():
        msg = (
            "This project has no apps/core/ownership.py (it was generated before owner "
            "scoping existed). Copy it from a freshly generated project first; see "
            "docs/concepts/security.md#upgrading-an-existing-project."
        )
        raise OwnershipModuleMissingError(msg)


def _class_chunk(source: str, class_name: str) -> str:
    """Source of one top-level class, up to the next top-level statement."""
    found = re.search(rf"^class\s+{re.escape(class_name)}\b", source, re.M)
    if found is None:
        return ""
    rest = source[found.start() :]
    header_end = rest.find("\n")
    if header_end < 0:
        return rest
    tail = re.search(r"\n(?=\S)", rest[header_end + 1 :])
    return rest if tail is None else rest[: header_end + 1 + tail.start()]


def owner_attr_of_permission(permissions_path: Path, class_name: str) -> str | None:
    """The ``owner_attr`` a generated owner permission class declares, else None."""
    if not permissions_path.is_file():
        return None
    chunk = _class_chunk(permissions_path.read_text(encoding="utf-8"), class_name)
    match = _OWNER_ATTR_RE.search(chunk)
    return match.group(1) if match else None


def viewset_owner_field(views_source: str, viewset_class: str) -> str | None:
    """The ``owner_field`` of a viewset that uses ``OwnerScopedMixin``, else None."""
    chunk = _class_chunk(views_source, viewset_class)
    header = chunk.split("\n", 1)[0]
    if "OwnerScopedMixin" not in header:
        return None
    match = _OWNER_FIELD_RE.search(chunk)
    return match.group(1) if match else "owner"


def model_of_viewset(views_source: str, viewset_class: str) -> str:
    """Model class of a viewset: from ``queryset = Model.objects...``, else the class name."""
    match = _QUERYSET_MODEL_RE.search(_class_chunk(views_source, viewset_class))
    if match:
        return match.group(1)
    return viewset_class.removesuffix("ViewSet")


def apply_owner_scoping(
    app_dir: Path, *, viewset_class: str, owner_attr: str
) -> list[str]:
    """Make ``viewset_class`` owner-scoped and its serializer's owner field read-only.

    Idempotent. Returns human-readable notes describing what was (not) changed.
    """
    owner_attr = validate_owner_attr(owner_attr)
    ensure_ownership_module(app_dir.parent)

    views = app_dir / "views.py"
    if not views.is_file():
        raise OwnershipWireError(f"views.py not found in {app_dir}")
    source = views.read_text(encoding="utf-8")
    if not class_exists(source, viewset_class):
        raise OwnershipWireError(f"{viewset_class} not found in {views}")

    notes: list[str] = []
    views.write_text(ensure_import_lines(source, [OWNER_IMPORT]), encoding="utf-8")
    base_added = ensure_class_base(views, viewset_class, "OwnerScopedMixin", first=True)
    field_set = set_class_attribute(
        views, viewset_class, "owner_field", f'"{owner_attr}"'
    )
    if base_added or field_set:
        notes.append(
            f"{viewset_class}: scoped to the requesting user via {owner_attr!r} "
            "(OwnerScopedMixin, owner_field)"
        )
    else:
        notes.append(f"{viewset_class}: already scoped via {owner_attr!r}")

    model = model_of_viewset(views.read_text(encoding="utf-8"), viewset_class)
    serializer_class = f"{model}Serializer"
    serializers = app_dir / "serializers.py"
    if not serializers.is_file() or not class_exists(
        serializers.read_text(encoding="utf-8"), serializer_class
    ):
        notes.append(
            f"{serializer_class} not found: make {owner_attr!r} read-only in your serializer"
        )
        return notes
    outcome = ensure_read_only_field(serializers, serializer_class, owner_attr)
    notes.append(
        {
            "added": f"{serializer_class}: {owner_attr!r} is now read-only",
            "present": f"{serializer_class}: {owner_attr!r} was already read-only",
            "not-a-field": f"{serializer_class}: {owner_attr!r} is not one of its fields; unchanged",
        }[outcome]
    )
    return notes
