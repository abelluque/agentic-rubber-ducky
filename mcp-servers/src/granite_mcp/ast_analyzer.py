"""Python AST analysis and source validation for the Code Agent."""

from __future__ import annotations

import ast
from typing import Any


def _walk_function(tree: ast.AST, function_name: str | None) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if function_name is None or node.name == function_name:
                return node
    return None


def _nested_loop_depth(node: ast.AST) -> int:
    max_depth = 0

    def visit(n: ast.AST, depth: int) -> None:
        nonlocal max_depth
        if isinstance(n, (ast.For, ast.AsyncFor, ast.While)):
            depth += 1
            max_depth = max(max_depth, depth)
        for child in ast.iter_child_nodes(n):
            visit(child, depth)

    visit(node, 0)
    return max_depth


def analyze_python_source(source: str, function_name: str | None = None) -> dict[str, Any]:
    """Parse source and report nested loops / size of a function."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {
            "ok": False,
            "error": f"syntax error: {exc.msg} (line {exc.lineno})",
            "lineno": exc.lineno,
        }

    target = _walk_function(tree, function_name)
    functions = [
        n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    if function_name and target is None:
        return {
            "ok": False,
            "error": f"function {function_name!r} not found",
            "functions": functions,
        }

    focus = target if target is not None else tree
    snippet = ast.get_source_segment(source, target) if target is not None else None
    return {
        "ok": True,
        "functions": functions,
        "target_function": getattr(target, "name", None),
        "lineno": getattr(target, "lineno", 1),
        "end_lineno": getattr(target, "end_lineno", None),
        "nested_loop_depth": _nested_loop_depth(focus),
        "hotspot": _nested_loop_depth(focus) >= 2,
        "source_segment": snippet,
        "hint": (
            "Nested loops detected; prefer a dict/Counter index over O(n²) scans."
            if _nested_loop_depth(focus) >= 2
            else "No nested loops in the target scope."
        ),
    }


def extract_function(source: str, function_name: str) -> dict[str, Any]:
    analysis = analyze_python_source(source, function_name)
    if not analysis.get("ok"):
        return analysis
    return {
        "ok": True,
        "function_name": function_name,
        "source_segment": analysis.get("source_segment"),
        "lineno": analysis.get("lineno"),
        "end_lineno": analysis.get("end_lineno"),
    }


def validate_python_source(source: str) -> dict[str, Any]:
    try:
        tree = ast.parse(source)
        compile(tree, "<agent>", "exec")
    except SyntaxError as exc:
        return {
            "ok": False,
            "error": f"syntax error: {exc.msg} (line {exc.lineno})",
            "lineno": exc.lineno,
        }
    except Exception as exc:  # noqa: BLE001 — surface any compile failure to the agent
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "message": "source compiled successfully"}
