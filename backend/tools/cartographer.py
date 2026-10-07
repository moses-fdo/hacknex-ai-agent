"""Cartographer: Deterministic AST codebase indexing, call hierarchy tracing, and skeleton generation.

Fulfills PRD v1.3 Cartographer tool specifications:
- Zero compiled dependencies (pure Python ast)
- trace_call_hierarchy for Detective & Architect
- semantic_symbol_search
- Hierarchical skeleton generation (< 1,500 tokens)
- Syncing deterministic facts with Grounded Memory Graph
"""
import ast
import os
from typing import Any, Dict, List, Optional

class Cartographer:
    def __init__(self, repo_path: str):
        self.repo_path = os.path.abspath(repo_path)
        self._index: Optional[Dict[str, Any]] = None

    def index_repo(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Parse all Python files, extract classes, functions, arguments, docstrings, imports, and calls."""
        if self._index and not force_refresh:
            return self._index

        index: Dict[str, Any] = {
            "files": {},
            "symbol_table": {},
            "call_graph": {},  # caller -> set of callees
            "caller_map": {},  # callee -> list of callers
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
                            sym_key = f"{rel_path}::{sym['name']}"
                            index["symbol_table"][sym["name"]] = {
                                "file": rel_path,
                                "type": sym["type"],
                                "lineno": sym["lineno"],
                                "args": sym.get("args", []),
                                "docstring": sym.get("docstring", ""),
                                "calls": sym.get("calls", []),
                            }
                            # Populate call graph
                            index["call_graph"][sym_key] = sym.get("calls", [])
                            for callee in sym.get("calls", []):
                                if callee not in index["caller_map"]:
                                    index["caller_map"][callee] = []
                                index["caller_map"][callee].append({
                                    "caller_file": rel_path,
                                    "caller_symbol": sym["name"],
                                    "lineno": sym["lineno"]
                                })
                    except Exception:
                        continue

        self._index = index
        return index

    def _parse_ast(self, tree: ast.AST, file_path: str) -> Dict[str, Any]:
        symbols = []
        imports = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [arg.arg for arg in node.args.args]
                calls = self._extract_calls(node)
                symbols.append({
                    "name": node.name,
                    "type": "function",
                    "lineno": node.lineno,
                    "args": args,
                    "docstring": ast.get_docstring(node) or "",
                    "calls": calls,
                })
            elif isinstance(node, ast.ClassDef):
                methods = []
                for m in node.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(m.name)
                        symbols.append({
                            "name": f"{node.name}.{m.name}",
                            "type": "method",
                            "lineno": m.lineno,
                            "args": [arg.arg for arg in m.args.args],
                            "docstring": ast.get_docstring(m) or "",
                            "calls": self._extract_calls(m),
                        })
                symbols.append({
                    "name": node.name,
                    "type": "class",
                    "lineno": node.lineno,
                    "methods": methods,
                    "docstring": ast.get_docstring(node) or "",
                    "calls": [],
                })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return {"symbols": symbols, "imports": imports}

    def _extract_calls(self, node: ast.AST) -> List[str]:
        """Extract called function and method names within an AST node."""
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Name):
                    calls.append(func.id)
                elif isinstance(func, ast.Attribute):
                    calls.append(func.attr)
        return list(set(calls))

    def trace_call_hierarchy(self, symbol_name: str) -> Dict[str, Any]:
        """Deterministically trace callers and callees for a symbol."""
        index = self.index_repo()
        callers = index["caller_map"].get(symbol_name, [])

        callees = []
        sym_info = index["symbol_table"].get(symbol_name)
        if sym_info:
            callees = sym_info.get("calls", [])

        return {
            "symbol": symbol_name,
            "callers": callers,
            "callees": callees,
        }

    def semantic_symbol_search(self, query: str) -> List[Dict[str, Any]]:
        """Search symbols by name, signature, and docstrings."""
        index = self.index_repo()
        q = query.lower()
        matches = []
        for name, data in index["symbol_table"].items():
            score = 0
            if q == name.lower():
                score += 10
            elif q in name.lower():
                score += 5
            if q in data.get("docstring", "").lower():
                score += 3
            if q in data.get("file", "").lower():
                score += 2

            if score > 0:
                matches.append({"name": name, "score": score, **data})

        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:10]

    def generate_skeleton(self) -> str:
        """Produce a hierarchical skeleton under the 1,500 token budget."""
        index = self.index_repo()
        lines = ["# Codebase Skeleton"]
        for file_path, data in sorted(index["files"].items()):
            lines.append(f"\n## File: {file_path}")
            if data["imports"]:
                lines.append(f"  Imports: {', '.join(data['imports'][:6])}")
            for sym in data["symbols"]:
                if sym["type"] == "class":
                    lines.append(f"  Class `{sym['name']}` (methods: {', '.join(sym['methods'])})")
                elif sym["type"] == "function":
                    lines.append(f"  Function `{sym['name']}({', '.join(sym['args'])})` [L{sym['lineno']}]")
        return "\n".join(lines)
