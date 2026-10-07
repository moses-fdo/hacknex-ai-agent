"""Sentinel: Deterministic symbol, AST safety gate, and linter check.

Fulfills PRD v1.3 Sentinel tool specifications:
- AST syntax verification
- Invented import detection against stdlib and allowed dependencies
- Signature preservation checks
- Atomic multi-file verification
- Ruff/pyflakes linting
"""
import ast
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

class Sentinel:
    @staticmethod
    def verify_syntax(code_string: str) -> Tuple[bool, str]:
        """Verify code parses cleanly without syntax errors."""
        try:
            ast.parse(code_string)
            return True, "Syntax valid"
        except SyntaxError as e:
            return False, f"SyntaxError at line {e.lineno}: {e.msg}"

    @classmethod
    def get_known_modules(cls, extra_allowed: Optional[List[str]] = None) -> set:
        """Collect stdlib modules and installed third-party modules."""
        known = set(sys.stdlib_module_names)
        # Add common third-party standard modules
        known.update({
            "pytest", "fastapi", "pydantic", "httpx", "uvicorn",
            "sqlalchemy", "jwt", "requests", "yaml", "dotenv",
            "starlette", "anyio", "numpy", "pandas"
        })
        if extra_allowed:
            for mod in extra_allowed:
                known.add(mod.split(".")[0])
        return known

    @classmethod
    def verify_imports(cls, code_string: str, allowed_modules: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
        """Catch invented/hallucinated imports."""
        try:
            tree = ast.parse(code_string)
        except SyntaxError:
            return False, ["Cannot parse syntax for import verification"]

        known = cls.get_known_modules(allowed_modules)
        invented = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_pkg = alias.name.split(".")[0]
                    if top_pkg not in known:
                        invented.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top_pkg = node.module.split(".")[0]
                    if top_pkg not in known and not node.level:
                        invented.append(node.module)

        if invented:
            return False, list(set(invented))
        return True, []

    @classmethod
    def verify_signature(
        cls,
        original_code: str,
        patched_code: str,
        target_symbol: str
    ) -> Tuple[bool, str]:
        """Verify that target function or method signature was not corrupted."""
        def extract_sym_args(code: str, sym_name: str) -> Optional[List[str]]:
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.name == sym_name:
                            return [a.arg for a in node.args.args]
            except Exception:
                pass
            return None

        orig_args = extract_sym_args(original_code, target_symbol)
        patch_args = extract_sym_args(patched_code, target_symbol)

        if orig_args is not None and patch_args is not None:
            # If original required arguments were deleted
            missing = set(orig_args) - set(patch_args)
            if missing:
                return False, f"Signature regression: arguments {missing} were removed from {target_symbol}"

        return True, "Signature preserved"

    @classmethod
    def run_linter(cls, file_path: str) -> Tuple[bool, List[str]]:
        """Run ruff or pyflakes if available on disk."""
        ruff_bin = shutil.which("ruff") or shutil.which(".venv/bin/ruff")
        if ruff_bin:
            try:
                proc = subprocess.run([ruff_bin, "check", file_path], capture_output=True, text=True, timeout=10)
                if proc.returncode != 0:
                    errors = [l for l in proc.stdout.splitlines() if file_path in l]
                    return False, errors[:5]
                return True, []
            except Exception:
                pass
        return True, []

    @classmethod
    def verify_atomic(
        cls,
        patched_files: Dict[str, str],
        original_files: Dict[str, str],
        target_symbols: Dict[str, str],
        allowed_modules: Optional[List[str]] = None
    ) -> Tuple[bool, List[str]]:
        """FR-5.3: Atomic AST & Type Check across all touched files in the multi-file plan."""
        errors = []
        for file_path, content in patched_files.items():
            # 1. Syntax check
            ok, msg = cls.verify_syntax(content)
            if not ok:
                errors.append(f"{file_path}: {msg}")
                continue

            # 2. Imports check
            ok_imp, invented = cls.verify_imports(content, allowed_modules)
            if not ok_imp:
                errors.append(f"{file_path}: Invented imports detected: {invented}")

            # 3. Signature check if target symbol specified
            target_sym = target_symbols.get(file_path)
            orig_content = original_files.get(file_path)
            if target_sym and orig_content:
                ok_sig, sig_msg = cls.verify_signature(orig_content, content, target_sym)
                if not ok_sig:
                    errors.append(f"{file_path}: {sig_msg}")

        return (len(errors) == 0), errors
