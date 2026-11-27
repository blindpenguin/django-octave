"""Shared rules for tenant-scoped viewsets in multitenancy projects.

Kept free of other ``django_octave`` imports so every viewset emitter can use it.
"""

from __future__ import annotations

from pathlib import Path

from django_octave.errors import OctaveError

TENANCY_IMPORT = "from apps.core.tenancy import TenantScopedMixin\n"


class TenancyModuleMissingError(OctaveError, ValueError):
    """Raised when a multitenancy project lacks ``apps/core/tenancy.py``."""


def is_tenant_scoped(*, use_multitenancy: bool, tenant_aware: bool) -> bool:
    """True when a generated viewset must inherit ``TenantScopedMixin``."""
    return use_multitenancy and tenant_aware


def viewset_bases(*, scoped: bool, owned: bool = False) -> str:
    """Base-class list for a generated ``ModelViewSet``.

    Order matters: ``OwnerScopedMixin`` calls ``super().get_queryset()`` and filters, while
    ``TenantScopedMixin.get_queryset`` does not call ``super()``, so the owner mixin goes
    first and the tenant mixin second.
    """
    parts = []
    if owned:
        parts.append("OwnerScopedMixin")
    if scoped:
        parts.append("TenantScopedMixin")
    parts.append("viewsets.ModelViewSet")
    return ", ".join(parts)


def ensure_tenancy_module(apps_dir: Path) -> None:
    """Fail early for projects generated before ``TenantScopedMixin`` existed."""
    if not (apps_dir / "core" / "tenancy.py").is_file():
        msg = (
            "This multitenancy project has no apps/core/tenancy.py (it was generated "
            "before tenants were bound in DRF). Add it first; see "
            "docs/concepts/multitenancy.md#upgrading-an-existing-project."
        )
        raise TenancyModuleMissingError(msg)
