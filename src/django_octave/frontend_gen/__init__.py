"""Optional Vue + Nuxt UI frontend scaffolding."""

from __future__ import annotations

from django_octave.frontend_gen.compose import ComposeInjectError
from django_octave.frontend_gen.crud_setup import (
    CrudSetupError,
    generate_crud,
    generate_crud_all,
)
from django_octave.frontend_gen.detect import frontend_configured
from django_octave.frontend_gen.django_patch import (
    DjangoPatchError,
    patch_django_for_frontend,
)
from django_octave.frontend_gen.setup import (
    FrontendExistsError,
    FrontendSetupError,
    render_frontend,
    scaffold_frontend,
    setup_frontend,
)

__all__ = (
    "ComposeInjectError",
    "CrudSetupError",
    "DjangoPatchError",
    "FrontendExistsError",
    "FrontendSetupError",
    "frontend_configured",
    "generate_crud",
    "generate_crud_all",
    "patch_django_for_frontend",
    "render_frontend",
    "scaffold_frontend",
    "setup_frontend",
)
