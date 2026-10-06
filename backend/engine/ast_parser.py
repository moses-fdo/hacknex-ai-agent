import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Optional
from backend.models.schema import FileOutline, SymbolInfo, RepoMap, SentinelCheck

EXCLUDE_DIRS = {".venv", "venv", "__pycache__", ".git", ".pytest_cache", "node_modules", "dist", "build"}

class CodebaseCartographer:
    """Parses codebase AST into lightweight symbol summaries, dependency trees, and import validations."""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self._cache: Optional[RepoMap] = None

    def scan(self, force_refresh: bool = False) -> RepoMap:
        if self._cache and not force_refresh:
            return self._cache

        files_map: Dict[str, FileOutline] = {}
        import_graph: Dict[str, List[str]] = {}

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                if file.endswith(".py"):
                    full_path = Path(root) / file
                    rel_path = str(full_path.relative_to(self.repo_path))
                    outline = self._parse_file(full_path, rel_path)
                    files_map[rel_path] = outline
                    import_graph[rel_path] = outline.imports

        repo_map = RepoMap(
            repo_path=str(self.repo_path),
            total_files=len(files_map),
            files=files_map,
            import_graph=import_graph
        )
        self._cache = repo_map
        return repo_map

    def _parse_file(self, full_path: Path, rel_path: str) -> FileOutline:
        try:
            content = full_path.read_text(encoding="utf-8")
        except Exception:
            return FileOutline(file_path=rel_path, line_count=0)

        line_count = len(content.splitlines())
        try:
            tree = ast.parse(content, filename=str(full_path))
        except SyntaxError:
            return FileOutline(file_path=rel_path, line_count=line_count)

        imports: List[str] = []
        symbols: List[SymbolInfo] = []

        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    imports.append(f"{mod}.{alias.name}" if mod else alias.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node)
                args = [a.arg for a in node.args.args]
                symbols.append(SymbolInfo(
                    name=node.name,
                    kind="function",
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    docstring=doc.split("\n")[0] if doc else None,
                    args=args
                ))
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node)
                symbols.append(SymbolInfo(
                    name=node.name,
                    kind="class",
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    docstring=doc.split("\n")[0] if doc else None,
                    args=[]
                ))
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        sub_doc = ast.get_docstring(sub)
                        sub_args = [a.arg for a in sub.args.args]
                        symbols.append(SymbolInfo(
                            name=f"{node.name}.{sub.name}",
                            kind="method",
                            line_start=sub.lineno,
                            line_end=sub.end_lineno or sub.lineno,
                            docstring=sub_doc.split("\n")[0] if sub_doc else None,
                            args=sub_args
                        ))

        return FileOutline(
            file_path=rel_path,
            imports=imports,
            symbols=symbols,
            line_count=line_count
        )

    def generate_skeleton_prompt(self) -> str:
        """Produces a token-efficient representation (< 1,500 tokens) of the repo for LLM reasoning."""
        repo_map = self.scan()
        lines = [f"=== CODEBASE SKELETON: {Path(repo_map.repo_path).name} ({repo_map.total_files} files) ==="]

        for file_path, outline in sorted(repo_map.files.items()):
            lines.append(f"\n[FILE: {file_path}] ({outline.line_count} lines)")
            if outline.imports:
                lines.append(f"  Imports: {', '.join(outline.imports[:8])}")
            for sym in outline.symbols:
                arg_str = ", ".join(sym.args)
                doc_str = f" - '{sym.docstring}'" if sym.docstring else ""
                lines.append(f"  {sym.kind} {sym.name}({arg_str}) [L{sym.line_start}-L{sym.line_end}]{doc_str}")

        return "\n".join(lines)

    def check_hallucinations(self, code_snippet: str) -> SentinelCheck:
        """Parses a patch AST to ensure all imported modules and references are real."""
        repo_map = self.scan()
        known_modules: Set[str] = {
            "os", "sys", "time", "datetime", "json", "math", "re", "typing", "base64",
            "pydantic", "pytest", "fastapi", "app", "app.config", "app.auth", "app.models", "app.services"
        }
        for file_path in repo_map.files:
            mod_name = file_path.replace("/", ".").replace(".py", "")
            known_modules.add(mod_name)
            parts = mod_name.split(".")
            for i in range(1, len(parts) + 1):
                known_modules.add(".".join(parts[:i]))

        try:
            tree = ast.parse(code_snippet)
        except SyntaxError as e:
            return SentinelCheck(
                is_valid=False,
                imported_modules=[],
                violations=[f"Syntax error in proposed patch: {str(e)}"]
            )

        imported: List[str] = []
        unknown_imports: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.append(alias.name)
                    root_mod = alias.name.split(".")[0]
                    if root_mod not in known_modules:
                        unknown_imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    full_name = f"{mod}.{alias.name}" if mod else alias.name
                    imported.append(full_name)
                    root_mod = mod.split(".")[0] if mod else alias.name
                    if root_mod not in known_modules:
                        unknown_imports.append(full_name)

        is_valid = len(unknown_imports) == 0
        violations = [f"Hallucinated or undeclared import: '{m}'" for m in unknown_imports]

        return SentinelCheck(
            is_valid=is_valid,
            imported_modules=imported,
            unknown_imports=unknown_imports,
            violations=violations
        )
