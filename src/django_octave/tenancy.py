"""Shared rules for tenant-scoped viewsets in multitenancy projects.

Kept free of other ``django_octave`` imports so every viewset emitter can use it.
"""

from __future__ import annotations

from pathlib import Path

TENANCY_IMPORT = "from apps.core.tenancy import TenantScopedMixin\n"


class TenancyModuleMissingError(ValueError):
    """Raised when a multitenancy project lacks ``apps/core/tenancy.py``."""


def is_tenant_scoped(*, use_multitenancy: bool, tenant_aware: bool) -> bool:
    """True when a generated viewset must inherit ``TenantScopedMixin``."""
    return use_multitenancy and tenant_aware


def viewset_bases(*, scoped: bool) -> str:
    """Base-class list for a generated ``ModelViewSet``."""
    return "TenantScopedMixin, viewsets.ModelViewSet" if scoped else "viewsets.ModelViewSet"


def ensure_tenancy_module(apps_dir: Path) -> None:
    """Fail early for projects generated before ``TenantScopedMixin`` existed."""
    if not (apps_dir / "core" / "tenancy.py").is_file():
        msg = (
            "This multitenancy project has no apps/core/tenancy.py (it was generated "
            "before tenants were bound in DRF). Add it first; see "
            "docs/concepts/multitenancy.md#upgrading-an-existing-project."
        )
        raise TenancyModuleMissingError(msg)
