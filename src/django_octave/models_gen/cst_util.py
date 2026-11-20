"""Shared libcst helpers for class upsert, imports, and router wiring."""

from __future__ import annotations

from pathlib import Path

import libcst as cst

from django_octave.models_gen.writer import ModelWriteError, _RemoveClass
from django_octave.naming import pascal_to_snake, pluralize


def ensure_import_lines(source: str, lines: list[str]) -> str:
    """Insert missing import lines after existing import block."""
    for line in lines:
        bare = line if line.endswith("\n") else line + "\n"
        if bare.strip() and bare.strip() not in {
            row.strip() for row in source.splitlines()
        }:
            parts = source.splitlines(keepends=True)
            idx = 0
            for i, row in enumerate(parts):
                if row.startswith("from __future__") or row.startswith(
                    ("import ", "from ")
                ):
                    idx = i + 1
            parts.insert(idx, bare)
            source = "".join(parts)
    return source


def add_to_import(source: str, module: str, symbol: str) -> str:
    """Ensure ``from module import ... symbol`` is present."""
    prefix = f"from {module} import "
    if symbol in source and prefix in source:
        for line in source.splitlines():
            if line.startswith(prefix) and symbol in line:
                return source
    if prefix in source:
        lines = source.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith(prefix) and symbol not in line:
                lines[i] = line.rstrip("\n").rstrip() + f", {symbol}\n"
                return "".join(lines)
    return ensure_import_lines(source, [f"{prefix}{symbol}\n"])


def class_exists(source: str, class_name: str) -> bool:
    """Return True if a top-level class named ``class_name`` exists."""
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError:
        return f"class {class_name}" in source
    return any(
        isinstance(n, cst.ClassDef) and n.name.value == class_name for n in module.body
    )


def method_exists(source: str, class_name: str, method_name: str) -> bool:
    """Return True if ``class_name`` has a method named ``method_name``."""
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError:
        return f"def {method_name}" in source
    for node in module.body:
        if not isinstance(node, cst.ClassDef) or node.name.value != class_name:
            continue
        for item in node.body.body:
            if isinstance(item, cst.FunctionDef) and item.name.value == method_name:
                return True
    return False


class _RemoveMethodInClass(cst.CSTTransformer):
    """Remove a FunctionDef from a named top-level class."""

    def __init__(self, class_name: str, method_name: str) -> None:
        self.class_name = class_name
        self.method_name = method_name

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        if original_node.name.value != self.class_name:
            return updated_node
        new_body = [
            item
            for item in updated_node.body.body
            if not (
                isinstance(item, cst.FunctionDef)
                and item.name.value == self.method_name
            )
        ]
        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=new_body)
        )


class _AppendMethodToClass(cst.CSTTransformer):
    """Append parsed statements (decorators + FunctionDef) to a class body."""

    def __init__(self, class_name: str, addition: list[cst.BaseStatement]) -> None:
        self.class_name = class_name
        self.addition = addition

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        if original_node.name.value != self.class_name:
            return updated_node
        spacer: list[cst.BaseStatement | cst.EmptyLine] = []
        if updated_node.body.body:
            spacer = [cst.EmptyLine()]
        new_body = [*updated_node.body.body, *spacer, *self.addition]
        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=new_body)
        )


def upsert_method(
    path: Path,
    class_name: str,
    method_name: str,
    method_src: str,
    *,
    force: bool,
    header_imports: list[str],
) -> None:
    """Create or replace a method on ``class_name`` in ``path``.

    When the method already exists and ``force`` is False, leave it unchanged
    (after ensuring header imports).
    """
    source = path.read_text(encoding="utf-8")
    source = ensure_import_lines(source, header_imports)
    path.write_text(source, encoding="utf-8")
    source = path.read_text(encoding="utf-8")
    if not class_exists(source, class_name):
        raise ModelWriteError(f"{class_name} not found in {path}")
    exists = method_exists(source, class_name, method_name)
    if exists and not force:
        return
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        raise ModelWriteError(f"Could not parse {path}: {exc}") from exc
    if exists and force:
        module = module.visit(_RemoveMethodInClass(class_name, method_name))
    try:
        addition_mod = cst.parse_module(method_src.lstrip("\n"))
    except cst.ParserSyntaxError as exc:
        raise ModelWriteError(f"Could not parse method source: {exc}") from exc
    addition = list(addition_mod.body)
    if not addition:
        raise ModelWriteError("method_src produced no statements")
    updated = module.visit(_AppendMethodToClass(class_name, addition))
    path.write_text(updated.code, encoding="utf-8")


def upsert_class(
    path: Path,
    class_name: str,
    class_src: str,
    *,
    force: bool,
    header_imports: list[str],
) -> None:
    """Create or replace a top-level class in ``path``.

    When the class already exists and ``force`` is False, leave it unchanged
    (after ensuring header imports).
    """
    source = path.read_text(encoding="utf-8")
    source = ensure_import_lines(source, header_imports)
    path.write_text(source, encoding="utf-8")
    source = path.read_text(encoding="utf-8")
    exists = class_exists(source, class_name)
    if exists and not force:
        return
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        raise ModelWriteError(f"Could not parse {path}: {exc}") from exc
    if exists and force:
        module = module.visit(_RemoveClass(class_name))
    addition = cst.parse_module(class_src.lstrip("\n"))
    updated = module.with_changes(body=[*module.body, *addition.body])
    path.write_text(updated.code, encoding="utf-8")


def ensure_router_registration(path: Path, app_name: str, model_name: str) -> None:
    """Ensure ``urls.py`` imports the viewset and registers it on the router."""
    source = path.read_text(encoding="utf-8")
    snake = pascal_to_snake(model_name)
    plural = pluralize(snake)
    register = f'router.register("{plural}", {model_name}ViewSet, basename="{snake}")'
    source = add_to_import(source, f"apps.{app_name}.views", f"{model_name}ViewSet")
    if register not in source and f"{model_name}ViewSet" not in [
        line for line in source.splitlines() if "router.register" in line
    ]:
        if not any(
            "router.register" in line and f"{model_name}ViewSet" in line
            for line in source.splitlines()
        ):
            ridx = source.rfind("router.register(")
            if ridx != -1:
                end = source.find("\n", ridx)
                source = source[: end + 1] + register + "\n" + source[end + 1 :]
            else:
                idx = source.find("urlpatterns")
                if idx == -1:
                    source = source.rstrip() + "\n" + register + "\n"
                else:
                    source = source[:idx] + register + "\n\n" + source[idx:]
    path.write_text(source, encoding="utf-8")
