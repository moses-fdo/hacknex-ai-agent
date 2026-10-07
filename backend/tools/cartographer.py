"""Cartographer: Indexes codebase using standard library Python ast with zero compiled deps."""
import ast
import os
from typing import Any, Dict, List

class Cartographer:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def index_repo(self) -> Dict[str, Any]:
        """Parse all Python files, extract classes, functions, arguments, docstrings, imports."""
        index: Dict[str, Any] = {
            "files": {},
            "symbol_table": {},
            "import_graph": {}
        }

        for root, _, files in os.walk(self.repo_path):
            if any(part.startswith(".") or part in ("__pycache__", ".venv", "tests") for part in root.split(os.sep)):
                continue
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.repo_path)
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            tree = ast.parse(f.read(), filename=rel_path)
                        file_info = self._parse_ast(tree, rel_path)
                        index["files"][rel_path] = file_info
                        for sym in file_info["symbols"]:
                            index["symbol_table"][sym["name"]] = {
                                "file": rel_path,
                                "type": sym["type"],
                                "lineno": sym["lineno"],
                                "args": sym.get("args", [])
                            }
                    except Exception:
                        continue
        return index

    def _parse_ast(self, tree: ast.AST, file_path: str) -> Dict[str, Any]:
        symbols = []
        imports = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                args = [arg.arg for arg in node.args.args]
                symbols.append({
                    "name": node.name,
                    "type": "function",
                    "lineno": node.lineno,
                    "args": args,
                    "docstring": ast.get_docstring(node) or ""
                })
            elif isinstance(node, ast.ClassDef):
                methods = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
                symbols.append({
                    "name": node.name,
                    "type": "class",
                    "lineno": node.lineno,
                    "methods": methods,
                    "docstring": ast.get_docstring(node) or ""
                })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return {
            "symbols": symbols,
            "imports": imports
        }

    def generate_skeleton(self) -> str:
        """Produce a hierarchical skeleton under the 1,500 token budget."""
        index = self.index_repo()
        lines = ["# Codebase Skeleton"]
        for file_path, data in sorted(index["files"].items()):
            lines.append(f"\n## File: {file_path}")
            if data["imports"]:
                lines.append(f"  Imports: {', '.join(data['imports'][:5])}")
            for sym in data["symbols"]:
                if sym["type"] == "class":
                    lines.append(f"  Class `{sym['name']}` (methods: {', '.join(sym['methods'])})")
                else:
                    lines.append(f"  Function `{sym['name']}({', '.join(sym['args'])})` [L{sym['lineno']}]")
        return "\n".join(lines)
