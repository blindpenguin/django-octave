"""Replace or insert a top-level class in a libcst module (no file I/O).

Kept free of other ``django_octave`` imports so ``cst_util`` and ``writer`` can both use
it without importing each other.
"""

from __future__ import annotations

from collections.abc import Sequence

import libcst as cst


def top_level_class_index(module: cst.Module, class_name: str) -> int | None:
    """Index of the top-level class ``class_name`` in ``module.body``, if any."""
    for i, node in enumerate(module.body):
        if isinstance(node, cst.ClassDef) and node.name.value == class_name:
            return i
    return None


def with_blank_leading(
    addition: Sequence[cst.BaseStatement],
) -> list[cst.BaseStatement]:
    """Put two blank lines above a class that is appended or inserted."""
    statements = list(addition)
    if statements and isinstance(statements[0], cst.ClassDef):
        first = statements[0]
        statements[0] = first.with_changes(
            leading_lines=[*first.leading_lines, cst.EmptyLine(), cst.EmptyLine()]
        )
    return statements


def replace_class_in_module(
    module: cst.Module,
    class_name: str,
    addition: Sequence[cst.BaseStatement],
    *,
    before: str | None = None,
) -> cst.Module:
    """Put ``addition`` (the new source of ``class_name``) into ``module``.

    - The class exists and is not after the ``before`` anchor (or there is no anchor):
      ``addition`` takes its place and the first new statement keeps the lines above
      the old class (blank lines and comments). Nothing else in the module changes.
    - The class exists after the anchor: it is removed and inserted before the anchor,
      so helpers stay defined before the class that uses them.
    - The class is missing: it is appended, or inserted before the anchor, with two
      blank lines above it.
    """
    old = top_level_class_index(module, class_name)
    anchor = top_level_class_index(module, before) if before else None
    body = list(module.body)
    new = list(addition)

    if old is not None and (anchor is None or old < anchor):
        if new:
            new[0] = new[0].with_changes(leading_lines=body[old].leading_lines)
        body[old : old + 1] = new
        return module.with_changes(body=body)

    if old is not None:
        del body[old]  # it was after the anchor, so the anchor's index is unchanged
    new = with_blank_leading(new)
    if anchor is None:
        body.extend(new)
    else:
        body[anchor:anchor] = new
    return module.with_changes(body=body)
