"""Append or replace model classes in apps/*/models.py using libcst."""

from __future__ import annotations

import libcst as cst
from libcst import matchers as m

from django_octave.errors import OctaveError
from django_octave.fields.codegen import field_source, needs_uuid_import, str_field_name
from django_octave.fields.parser import FieldSpec
from django_octave.formatting import format_written_python


class ModelExistsError(OctaveError, FileExistsError):
    """Raised when the model class already exists without force."""


class ModelWriteError(OctaveError, ValueError):
    """Raised when models.py cannot be updated safely."""


def _build_class_source(
    *,
    model_name: str,
    use_multitenancy: bool,
    fields: list[FieldSpec],
) -> str:
    base = "TenantAwareModel" if use_multitenancy else "TimeStampedModel"
    lines = [f"class {model_name}({base}):"]
    for spec in fields:
        lines.append(f"    {field_source(spec)}")
    str_name = str_field_name(fields)
    if str_name:
        lines.append("")
        lines.append("    class Meta:")
        lines.append(f'        ordering = ("{str_name}",)')
        lines.append("")
        lines.append("    def __str__(self) -> str:")
        lines.append(f"        return str(self.{str_name})")
    else:
        lines.append("")
        lines.append("    def __str__(self) -> str:")
        lines.append("        return str(self.pk)")
    lines.append("")
    return "\n".join(lines)


def _ensure_imports(
    module: cst.Module,
    *,
    use_multitenancy: bool,
    need_uuid: bool,
) -> cst.Module:
    body = list(module.body)
    existing = module.code

    def has_import(snippet: str) -> bool:
        return snippet in existing

    inserts: list[cst.SimpleStatementLine] = []
    if need_uuid and "import uuid" not in existing:
        inserts.append(cst.parse_statement("import uuid"))
    if "from django.db import models" not in existing and "import models" not in existing:
        inserts.append(cst.parse_statement("from django.db import models"))
    base = "TenantAwareModel" if use_multitenancy else "TimeStampedModel"
    import_line = f"from apps.core.models import {base}"
    if import_line not in existing and f"import {base}" not in existing:
        # If the other base is imported, still add this one.
        inserts.append(cst.parse_statement(import_line))

    if not inserts:
        return module

    # Place after future import if present.
    insert_at = 0
    for i, stmt in enumerate(body):
        if m.matches(
            stmt,
            m.SimpleStatementLine(
                body=[m.ImportFrom(module=m.Name("__future__"))]
            ),
        ):
            insert_at = i + 1
        elif m.matches(stmt, m.SimpleStatementLine(body=[m.ImportFrom() | m.Import()])):
            insert_at = i + 1
        else:
            break
    new_body = body[:insert_at] + inserts + body[insert_at:]
    return module.with_changes(body=new_body)


class _RemoveClass(cst.CSTTransformer):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.removed = False

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef | cst.RemovalSentinel:
        if original_node.name.value == self.model_name:
            self.removed = True
            return cst.RemovalSentinel.REMOVE
        return updated_node


def model_exists(source: str, model_name: str) -> bool:
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        raise ModelWriteError(f"Could not parse models.py: {exc}") from exc
    for node in module.body:
        if isinstance(node, cst.ClassDef) and node.name.value == model_name:
            return True
    return False


def write_model(
    models_path,
    *,
    model_name: str,
    fields: list[FieldSpec],
    use_multitenancy: bool,
    force: bool,
) -> None:
    """Write or replace a model class in ``models_path``."""
    from pathlib import Path

    path = Path(models_path)
    if not path.is_file():
        raise ModelWriteError(f"models.py not found: {path}")

    source = path.read_text(encoding="utf-8")
    exists = model_exists(source, model_name)
    if exists and not force:
        raise ModelExistsError(
            f"Model {model_name} already exists in {path}. Use --force to replace it."
        )

    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        raise ModelWriteError(f"Could not parse models.py: {exc}") from exc

    if exists and force:
        remover = _RemoveClass(model_name)
        module = module.visit(remover)

    module = _ensure_imports(
        module,
        use_multitenancy=use_multitenancy,
        need_uuid=needs_uuid_import(fields),
    )

    class_src = _build_class_source(
        model_name=model_name,
        use_multitenancy=use_multitenancy,
        fields=fields,
    )
    class_module = cst.parse_module(class_src)
    addition = list(class_module.body)
    if module.body and addition:
        first = addition[0]
        if isinstance(first, cst.ClassDef):
            addition[0] = first.with_changes(
                leading_lines=[
                    *first.leading_lines,
                    cst.EmptyLine(),
                    cst.EmptyLine(),
                ]
            )
    updated = module.with_changes(body=[*module.body, *addition])
    path.write_text(updated.code, encoding="utf-8")
    format_written_python(path)
