"""Static code-quality checks used by the acceptance report.

This is deliberately conservative: it reports facts and locations, not claims
that a pattern is automatically a defect.  Dynamic bypass/authorization tests
live in ``tools/run_acceptance.py``.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("app", "core", "database", "security", "services", "ui", "scanners", "reports")
OUTPUT = ROOT / "docs" / "acceptance" / "code_quality.json"
STATUS_LITERAL_RE = re.compile(r"""["'](pending|confirmed|expired|revoked)["']""")
TODO_RE = re.compile(r"\b(TODO|FIXME)\b", re.IGNORECASE)
SQL_RE = re.compile(r"\b(SELECT|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b", re.IGNORECASE)


def product_files() -> list[Path]:
    files = list((ROOT / "main.py").parent.glob("main.py"))
    for package in PACKAGES:
        base = ROOT / package
        if base.exists():
            files.extend(
                path
                for path in base.rglob("*.py")
                if "__pycache__" not in path.parts
            )
    return sorted(set(files))


def parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def imports_for(tree: ast.AST) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def main() -> int:
    empty_functions: list[dict[str, Any]] = []
    pass_nodes: list[dict[str, Any]] = []
    todos: list[dict[str, Any]] = []
    ui_scanner_imports: list[dict[str, Any]] = []
    ui_sql: list[dict[str, Any]] = []
    status_literals: list[dict[str, Any]] = []
    sqlite_imports: list[str] = []

    for path in product_files():
        relative = path.relative_to(ROOT).as_posix()
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        parents = parent_map(tree)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = list(node.body)
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    body = body[1:]
                if body and all(isinstance(stmt, ast.Pass) for stmt in body):
                    empty_functions.append({"file": relative, "line": node.lineno, "name": node.name})
            if isinstance(node, ast.Pass):
                parent = parents.get(node)
                context = type(parent).__name__ if parent else "unknown"
                context_name = (
                    str(getattr(parent, "name", ""))
                    if isinstance(parent, ast.ClassDef)
                    else ""
                )
                pass_nodes.append(
                    {
                        "file": relative,
                        "line": node.lineno,
                        "parent": context,
                        "context_name": context_name,
                    }
                )

        for line_number, line in enumerate(source.splitlines(), start=1):
            if TODO_RE.search(line):
                todos.append({"file": relative, "line": line_number, "text": line.strip()})
            for match in STATUS_LITERAL_RE.finditer(line):
                status_literals.append(
                    {
                        "file": relative,
                        "line": line_number,
                        "status": match.group(1),
                        "text": line.strip(),
                    }
                )

        if relative.startswith("ui/"):
            for module in imports_for(tree):
                if module.split(".")[0] in {
                    "scanners",
                    "bandit",
                    "semgrep",
                    "pip_audit",
                    "socket",
                    "requests",
                    "httpx",
                    "urllib",
                    "http",
                }:
                    ui_scanner_imports.append({"file": relative, "module": module})
            for line_number, line in enumerate(source.splitlines(), start=1):
                if SQL_RE.search(line):
                    ui_sql.append({"file": relative, "line": line_number, "text": line.strip()})

        if "sqlite3" in imports_for(tree):
            sqlite_imports.append(relative)

    hardcoded_allow = [
        literal
        for literal in status_literals
        if literal["status"] == "confirmed"
        and literal["file"].startswith(("security/", "ui/"))
        and "AuthStatus" not in literal["text"]
    ]

    result = {
        "product_file_count": len(product_files()),
        "empty_functions": empty_functions,
        "empty_function_count": len(empty_functions),
        "pass_count": len(pass_nodes),
        "pass_locations": pass_nodes,
        "pass_outside_except_handlers": [
            item
            for item in pass_nodes
            if item["parent"] not in {"ExceptHandler", "ClassDef"}
        ],
        "pass_in_exception_classes": [
            item for item in pass_nodes if item["parent"] == "ClassDef"
        ],
        "todo_count": len(todos),
        "todos": todos,
        "ui_scanner_imports": ui_scanner_imports,
        "ui_sql_statements": ui_sql,
        "sqlite_import_files": sqlite_imports,
        "status_literal_count": len(status_literals),
        "status_literals": status_literals,
        "suspicious_hardcoded_confirmed_in_security_or_ui": hardcoded_allow,
        "verdicts": {
            "empty_functions": "PASS" if not empty_functions else "FAIL",
            "pass_usage": (
                "PASS"
                if all(
                    item["parent"] in {"ExceptHandler", "ClassDef"} for item in pass_nodes
                )
                else "REVIEW"
            ),
            "todo": "PASS" if not todos else "REVIEW",
            "ui_scanner_direct_calls": "PASS" if not ui_scanner_imports else "FAIL",
            "ui_sql_access": "PASS" if not ui_sql else "FAIL",
            "database_connection_centralized": (
                "PASS"
                if not any(path.startswith("ui/") for path in sqlite_imports)
                else "FAIL"
            ),
            "hardcoded_confirmed_allow": "PASS" if not hardcoded_allow else "REVIEW",
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["verdicts"], ensure_ascii=False, indent=2))
    print(f"PRODUCT_FILES={result['product_file_count']}")
    print(f"EMPTY_FUNCTIONS={result['empty_function_count']}")
    print(
        f"PASS_STATEMENTS={result['pass_count']} "
        f"EXCEPT_HANDLERS={result['pass_count'] - len(result['pass_in_exception_classes'])} "
        f"EXCEPTION_CLASSES={len(result['pass_in_exception_classes'])} "
        f"OUTSIDE={len(result['pass_outside_except_handlers'])}"
    )
    print(f"TODO={result['todo_count']}")
    print(f"UI_SCANNER_IMPORTS={len(ui_scanner_imports)}")
    print(f"UI_SQL_STATEMENTS={len(ui_sql)}")
    print(f"SQLITE_IMPORT_FILES={len(sqlite_imports)}")
    print(f"STATUS_LITERALS={len(status_literals)}")
    print(f"SUSPICIOUS_CONFIRMED_ALLOW={len(hardcoded_allow)}")
    print(f"REPORT={OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
