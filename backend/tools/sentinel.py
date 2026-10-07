"""Sentinel: Deterministic symbol and AST safety gate."""
import ast
import sys
from typing import List, Tuple

class Sentinel:
    @staticmethod
    def verify_syntax(code_string: str) -> Tuple[bool, str]:
        """Verify code parses cleanly without syntax errors."""
        try:
            ast.parse(code_string)
            return True, "Syntax valid"
        except SyntaxError as e:
            return False, f"SyntaxError at line {e.lineno}: {e.msg}"

    @staticmethod
    def verify_imports(code_string: str, allowed_modules: List[str]) -> Tuple[bool, List[str]]:
        """Catch invented imports."""
        try:
            tree = ast.parse(code_string)
        except SyntaxError:
            return False, ["Cannot parse syntax for import verification"]

        invented = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_pkg = alias.name.split(".")[0]
                    if top_pkg not in sys.stdlib_module_names and top_pkg not in allowed_modules:
                        invented.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top_pkg = node.module.split(".")[0]
                    if top_pkg not in sys.stdlib_module_names and top_pkg not in allowed_modules:
                        invented.append(node.module)

        if invented:
            return False, invented
        return True, []
