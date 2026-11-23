"""Shared types for frontend CRUD generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

CrudFieldKind = Literal[
    "string",
    "text",
    "number",
    "boolean",
    "decimal",
    "date",
    "datetime",
    "email",
    "slug",
    "fk",
    "readonly",
]


@dataclass(frozen=True, slots=True)
class CrudField:
    """One form/table field for generated CRUD pages."""

    name: str
    kind: CrudFieldKind
    required: bool = True
    related_plural: str | None = None
    related_label_field: str | None = None
    related_app: str | None = None
    related_model: str | None = None


@dataclass(frozen=True, slots=True)
class ResourceSpec:
    """A ModelViewSet-backed API resource discoverable for CRUD pages."""

    app_name: str
    model_name: str
    model_snake: str
    model_plural: str
    api_collection: str
    viewset_name: str
    label_field: str = "id"
    fields: tuple[CrudField, ...] = field(default_factory=tuple)
    skip_reason: str | None = None
    """If set, resource was found but should be soft-skipped for generation."""

    owner_field: str | None = None
    """Owner attribute of an owner-scoped viewset (``owner_field = "..."``); read-only in the SPA."""
