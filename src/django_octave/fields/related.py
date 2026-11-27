"""Give relations that would clash on the target model their own reverse names.

Django names the reverse accessor and query name of a relation after the model that
declares it (``User.note_set``, query name ``note``). Two relations from one model to
the same target therefore clash (``fields.E304``, ``fields.E305``). A foreign key, a
one-to-one and a many-to-many field all share that namespace on the target, so they
are grouped together.

``resolve_related_names`` is a pure function: it takes the parsed fields and returns
copies with a generated ``related_name`` where one is needed. Fields that already have
an explicit ``related_name`` (including ``"+"``) are never changed and never count as
a clash.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace

from django_octave.fields.parser import RELATION_TYPES, FieldSpec
from django_octave.naming import pascal_to_snake

_MULTI_UNDERSCORE_RE = re.compile(r"_{2,}")


@dataclass(frozen=True, slots=True)
class ResolvedFields:
    """The fields to write, and the reverse names that were generated for them."""

    fields: list[FieldSpec]
    """Same order as the input; ``related_name`` is filled in where one was generated."""

    generated: dict[str, str]
    """Field name -> generated ``related_name``, in declaration order."""


def _target(related_to: str, app: str) -> str:
    """Normalize a relation target; Django resolves a bare ``Model`` in the model's app."""
    return related_to if "." in related_to else f"{app}.{related_to}"


def _clean(name: str) -> str:
    """Make ``name`` acceptable as a reverse query name (no ``__``, no trailing ``_``)."""
    return _MULTI_UNDERSCORE_RE.sub("_", name).rstrip("_")


def resolve_related_names(
    fields: Sequence[FieldSpec], *, app: str, model: str
) -> ResolvedFields:
    """Name every unnamed relation that shares its target with another unnamed relation.

    A generated name is ``<model_snake>_<field>``, with ``_2``, ``_3``, ... appended if
    it equals an explicit name or an earlier generated one, so the result is distinct
    and the same input always gives the same output.
    """
    groups: dict[str, list[int]] = {}
    for index, spec in enumerate(fields):
        if spec.type_key in RELATION_TYPES and spec.related_name is None:
            assert spec.related_to is not None
            groups.setdefault(_target(spec.related_to, app), []).append(index)

    clashing = sorted(
        i for indexes in groups.values() if len(indexes) > 1 for i in indexes
    )
    if not clashing:
        return ResolvedFields(fields=list(fields), generated={})

    taken = {
        spec.related_name
        for spec in fields
        if spec.related_name is not None and spec.related_name != "+"
    }
    prefix = pascal_to_snake(model)
    chosen: dict[int, str] = {}
    for index in clashing:
        base = _clean(f"{prefix}_{fields[index].name}")
        name, suffix = base, 2
        while name in taken:
            name = f"{base}_{suffix}"
            suffix += 1
        taken.add(name)
        chosen[index] = name

    resolved = [
        replace(spec, related_name=chosen[index]) if index in chosen else spec
        for index, spec in enumerate(fields)
    ]
    generated = {fields[index].name: name for index, name in chosen.items()}
    return ResolvedFields(fields=resolved, generated=generated)
