"""Base class for every expected, user-facing generator failure.

Commands turn an :class:`OctaveError` into a red message and exit code 1. Each domain
exception also keeps its built-in base (``ValueError`` or ``FileExistsError``), so code
and tests that catch those still work. Kept free of other ``django_octave`` imports so
every layer can use it without import cycles.
"""

from __future__ import annotations


class OctaveError(Exception):
    """An expected failure that is reported to the user without a traceback."""
