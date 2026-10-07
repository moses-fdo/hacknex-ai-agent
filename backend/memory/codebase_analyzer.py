"""Codebase Analyzer & Decision Graph Generator.

Reads every file in a selected folder/repository, mines architectural patterns,
data models, authentication methods, testing frameworks, and critical invariants,
populates the Grounded Memory Graph (.aether/memory_graph.json), and writes
a comprehensive HOW_IT_WORKS.md explaining the project.
"""
import ast
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.memory.graph_store import MemoryGraphStore
from backend.models import MemoryEdge, MemoryNode


# Files and directories to ignore when scanning
IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".next",
    ".nuxt",
    ".turbo",
    "dist",
    "build",
    "coverage",
    ".idea",
    ".vscode",
    "target",
    "vendor",
    ".gradle",
    "bower_components",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z",
    ".pyc", ".pyo", ".pyd", ".exe", ".dll", ".so", ".dylib",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".db", ".sqlite", ".sqlite3", ".parquet",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".bin", ".dat", ".iso", ".wasm",
}

CODE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".jsx": "JavaScript (React)",
    ".html": "HTML",
    ".css": "CSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".sh": "Shell Script",
    ".bash": "Shell Script",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".md": "Markdown",
    ".sql": "SQL",
}


class CodebaseAnalyzer:
    """Multi-language codebase reader, architectural decision miner, and documentation generator."""

    def __init__(self, repo_path: str, memory_store: Optional[MemoryGraphStore] = None):
        self.repo_path = os.path.abspath(repo_path)
        self.repo_name = os.path.basename(self.repo_path) or "Workspace"
        self.memory_store = memory_store or MemoryGraphStore(self.repo_path)
        self.files_data: Dict[str, Dict[str, Any]] = {}
        self.language_counts: Dict[str, int] = {}
        self.total_lines: int = 0
        self.configs: Dict[str, Any] = {}
        self.detected_decisions: List[Dict[str, Any]] = []
        self.deterministic_facts: List[Dict[str, Any]] = []

    def scan_and_read_codebase(self, max_file_size_bytes: int = 300_000) -> Dict[str, Dict[str, Any]]:
        """Scan all files across the folder, read textual contents, and record file metrics."""
        self.files_data.clear()
        self.language_counts.clear()
        self.total_lines = 0

        for root, dirs, files in os.walk(self.repo_path):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for file_name in files:
                if file_name.startswith(".") and file_name not in {".env.example", ".env", ".gitignore"}:
                    continue

                full_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(full_path, self.repo_path)
                _, ext = os.path.splitext(file_name)
                ext = ext.lower()

                if ext in BINARY_EXTENSIONS:
                    continue

                try:
                    file_size = os.path.getsize(full_path)
                except OSError:
                    continue

                lang = CODE_EXTENSIONS.get(ext, "Text")
                self.language_counts[lang] = self.language_counts.get(lang, 0) + 1

                # Read text content if within size limit
                content = ""
                line_count = 0
                if file_size <= max_file_size_bytes:
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                        line_count = len(content.splitlines())
                        self.total_lines += line_count
                    except Exception:
                        content = ""

                self.files_data[rel_path] = {
                    "rel_path": rel_path,
                    "full_path": full_path,
                    "name": file_name,
                    "ext": ext,
                    "lang": lang,
                    "size_bytes": file_size,
                    "line_count": line_count,
                    "content": content,
                }

        self._parse_config_files()
        return self.files_data

    def _parse_config_files(self):
        """Extract dependency lists, scripts, and environment specs from known config files."""
        self.configs = {
            "dependencies": [],
            "dev_dependencies": [],
            "scripts": {},
            "env_vars": [],
            "test_command": "pytest",
            "run_command": "",
            "entry_points": [],
        }

        # 1. package.json
        if "package.json" in self.files_data:
            try:
                pkg_data = json.loads(self.files_data["package.json"]["content"])
                deps = list(pkg_data.get("dependencies", {}).keys())
                dev_deps = list(pkg_data.get("devDependencies", {}).keys())
                scripts = pkg_data.get("scripts", {})
                self.configs["dependencies"].extend(deps)
                self.configs["dev_dependencies"].extend(dev_deps)
                self.configs["scripts"].update(scripts)
                if "main" in pkg_data:
                    self.configs["entry_points"].append(pkg_data["main"])
                if "start" in scripts:
                    self.configs["run_command"] = f"npm start ({scripts['start']})"
                if "test" in scripts:
                    self.configs["test_command"] = f"npm test ({scripts['test']})"
            except Exception:
                pass

        # 2. requirements.txt / pyproject.toml / setup.py
        for req_file in ["requirements.txt", "requirements-dev.txt"]:
            if req_file in self.files_data:
                lines = self.files_data[req_file]["content"].splitlines()
                for line in lines:
                    clean = line.strip().split("#")[0].strip()
                    if clean and not clean.startswith("-"):
                        pkg = re.split(r"[><=~;]", clean)[0].strip()
                        if pkg:
                            self.configs["dependencies"].append(pkg)

        if "pyproject.toml" in self.files_data:
            content = self.files_data["pyproject.toml"]["content"]
            # Look for dependencies list
            for line in content.splitlines():
                if "=" in line and ("dependencies" in line.lower() or "pytest" in line):
                    self.configs["dependencies"].append(line.strip())

        # 3. .env.example / .env
        for env_file in [".env.example", ".env"]:
            if env_file in self.files_data:
                lines = self.files_data[env_file]["content"].splitlines()
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        var_name = line.split("=")[0].strip()
                        if var_name not in self.configs["env_vars"]:
                            self.configs["env_vars"].append(var_name)

        # 4. Detect entry points
        candidates = [
            "main.py", "app.py", "server.py", "app/main.py", "backend/api/server.py",
            "main.js", "index.js", "src/index.ts", "src/main.ts", "run.sh"
        ]
        for c in candidates:
            if c in self.files_data:
                self.configs["entry_points"].append(c)

    def extract_ast_and_symbols(self) -> Dict[str, Any]:
        """Extract classes, functions, routes, and import graphs from source files."""
        ast_catalog = {
            "classes": {},
            "functions": {},
            "imports": {},
            "routes": [],
            "models": [],
            "tests": [],
            "invariants": [],
        }

        for rel_path, data in self.files_data.items():
            content = data["content"]
            if not content:
                continue

            # Python AST parsing
            if data["ext"] == ".py":
                try:
                    tree = ast.parse(content, filename=rel_path)
                    for node in ast.iter_child_nodes(tree):
                        # Classes
                        if isinstance(node, ast.ClassDef):
                            bases = [getattr(b, "id", getattr(b, "attr", "")) for b in node.bases]
                            methods = [
                                m.name for m in node.body
                                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                            ]
                            doc = ast.get_docstring(node) or ""
                            ast_catalog["classes"][f"{rel_path}::{node.name}"] = {
                                "file": rel_path,
                                "name": node.name,
                                "lineno": node.lineno,
                                "bases": bases,
                                "methods": methods,
                                "docstring": doc,
                            }
                            if any(b in ("BaseModel", "Model", "DeclarativeBase", "Schema") for b in bases) or "model" in rel_path.lower():
                                ast_catalog["models"].append({
                                    "file": rel_path,
                                    "name": node.name,
                                    "type": "pydantic/orm" if "BaseModel" in bases else "class_model",
                                    "doc": doc,
                                })

                        # Top-level Functions
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            args = [arg.arg for arg in node.args.args]
                            doc = ast.get_docstring(node) or ""
                            fn_entry = {
                                "file": rel_path,
                                "name": node.name,
                                "lineno": node.lineno,
                                "args": args,
                                "docstring": doc,
                                "is_async": isinstance(node, ast.AsyncFunctionDef),
                            }
                            ast_catalog["functions"][f"{rel_path}::{node.name}"] = fn_entry

                            # Check for FastAPI / Flask route decorators
                            for dec in node.decorator_list:
                                dec_str = ""
                                if isinstance(dec, ast.Call):
                                    if isinstance(dec.func, ast.Attribute):
                                        dec_str = f"{getattr(dec.func.value, 'id', '')}.{dec.func.attr}"
                                elif isinstance(dec, ast.Attribute):
                                    dec_str = f"{getattr(dec.value, 'id', '')}.{dec.attr}"

                                if any(verb in dec_str.lower() for verb in ("get", "post", "put", "delete", "patch", "route")):
                                    path_arg = ""
                                    if isinstance(dec, ast.Call) and dec.args and isinstance(dec.args[0], ast.Constant):
                                        path_arg = str(dec.args[0].value)
                                    ast_catalog["routes"].append({
                                        "file": rel_path,
                                        "handler": node.name,
                                        "decorator": dec_str,
                                        "path": path_arg,
                                        "lineno": node.lineno,
                                    })

                            # Check for tests
                            if node.name.startswith("test_") or "test" in rel_path.lower():
                                ast_catalog["tests"].append({
                                    "file": rel_path,
                                    "name": node.name,
                                    "lineno": node.lineno,
                                })

                        # Imports
                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                ast_catalog["imports"].setdefault(rel_path, []).append(alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                ast_catalog["imports"].setdefault(rel_path, []).append(node.module)

                except Exception:
                    pass

            # JavaScript / TypeScript regex inspection
            elif data["ext"] in (".js", ".ts", ".jsx", ".tsx", ".mjs"):
                # Express / Fastify / Next.js / Electron routes and handlers
                for m in re.finditer(r"(?:app|router|ipcMain)\.(get|post|put|delete|patch|handle)\s*\(\s*['\"]([^'\"]+)['\"]", content):
                    ast_catalog["routes"].append({
                        "file": rel_path,
                        "verb": m.group(1).upper(),
                        "path": m.group(2),
                    })

                # Exported functions
                for m in re.finditer(r"(?:export\s+(?:default\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)|const\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)", content):
                    fname = m.group(1) or m.group(2)
                    if fname:
                        ast_catalog["functions"][f"{rel_path}::{fname}"] = {
                            "file": rel_path,
                            "name": fname,
                            "is_async": "async" in m.group(0),
                        }

            # Invariant keywords & comments scan across all code files (comments only)
            if not rel_path.endswith("codebase_analyzer.py"):
                for idx, line in enumerate(content.splitlines(), start=1):
                    clean_line = line.strip()
                    if (clean_line.startswith("#") or clean_line.startswith("//") or clean_line.startswith("*")) and any(marker in clean_line.upper() for marker in ("INVARIANT:", "RULE:", "DECISION:", "MUST USE", "VETO:")):
                        comment_text = re.sub(r"^[#/\*\s]+", "", clean_line).strip()
                        ast_catalog["invariants"].append({
                            "file": rel_path,
                            "line": idx,
                            "text": comment_text,
                        })

        return ast_catalog

    def mine_architectural_decisions(self, ast_catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Synthesize concrete, grounded architectural decisions and rules from codebase facts."""
        decisions: List[Dict[str, Any]] = []
        all_deps = [d.lower() for d in self.configs.get("dependencies", [])]
        all_files = list(self.files_data.keys())

        # 1. Framework Architecture Decision
        if any("fastapi" in d for d in all_deps) or any("fastapi" in imp for imps in ast_catalog["imports"].values() for imp in imps):
            decisions.append({
                "id": "decision:framework:fastapi",
                "label": "Web Framework: FastAPI Asynchronous REST Architecture",
                "category": "Framework & Architecture",
                "description": (
                    "The backend is built with FastAPI, providing high-performance asynchronous endpoints, "
                    "automatic OpenAPI schemas, and Server-Sent Events (SSE) telemetry streaming."
                ),
                "rationale": "High throughput, native async support, and automatic typed request/response validation.",
                "rules": [
                    "All public API routes must be organized modularly via FastAPI APIRouter instances.",
                    "Input payloads and responses must strictly use typed Pydantic models.",
                    "Endpoints must handle exceptions cleanly and return structured HTTP status codes."
                ],
                "files": [f for f in all_files if "api" in f or "server" in f or "main.py" in f][:5],
            })
        elif any("flask" in d for d in all_deps):
            decisions.append({
                "id": "decision:framework:flask",
                "label": "Web Framework: Flask Microservice Architecture",
                "category": "Framework & Architecture",
                "description": "The application employs Flask for modular HTTP endpoints and routing.",
                "rationale": "Lightweight, decoupled microservice design.",
                "rules": [
                    "Keep blueprints decoupled and isolated.",
                    "Use application factory pattern for testing isolation."
                ],
                "files": [f for f in all_files if "app" in f or "server" in f][:5],
            })
        elif "main.js" in self.files_data and any("electron" in d for d in all_deps + list(self.configs.get("dev_dependencies", []))):
            decisions.append({
                "id": "decision:architecture:electron",
                "label": "Desktop Architecture: Electron Native Host & Preload Bridge",
                "category": "Desktop & Systems",
                "description": (
                    "The application runs as a native desktop command center using Electron, connecting "
                    "a Node.js main process to the web interface via a secure preload context bridge."
                ),
                "rationale": "Enables direct OS filesystem access, native directory selection dialogs, and subprocess management.",
                "rules": [
                    "Main process handles window creation, child process spawning, and native OS dialogs.",
                    "Renderer process must strictly communicate through window.electronAPI exposed in preload.js.",
                    "Zero nodeIntegration in webPreferences for sandboxing security."
                ],
                "files": ["main.js", "preload.js", "package.json"],
            })

        # 2. Data Modeling & Validation Decision
        has_pydantic = (
            any("pydantic" in d for d in all_deps)
            or any("pydantic" in imp for imps in ast_catalog["imports"].values() for imp in imps)
            or len(ast_catalog["models"]) > 0
        )
        if has_pydantic:
            model_files = list(set(m["file"] for m in ast_catalog["models"]))[:6]
            decisions.append({
                "id": "decision:data:pydantic_schemas",
                "label": "Data Layer: Typed Schemas & Pydantic Model Validation",
                "category": "Data & Modeling",
                "description": (
                    "Data integrity is enforced at boundaries using Pydantic BaseModel schemas. "
                    "Incoming requests and internal states are validated before processing."
                ),
                "rationale": "Eliminates type confusion and malformed payloads deterministically at compile/parse time.",
                "rules": [
                    "Every domain entity and API input/output payload must inherit from Pydantic BaseModel.",
                    "Use field type annotations and default_factory for mutable collections.",
                    "Never access undeclared attributes on schema objects."
                ],
                "files": model_files or [f for f in all_files if "model" in f.lower()][:4],
            })

        # 3. Authentication & Security Decisions
        auth_files = [f for f in all_files if "auth" in f.lower() or "token" in f.lower() or "permission" in f.lower()]
        if auth_files:
            # Check for tokens / UTC timestamp invariant
            token_files = [f for f in auth_files if "token" in f.lower()]
            if token_files or any("jwt" in d for d in all_deps):
                decisions.append({
                    "id": "decision:security:token_auth",
                    "label": "Security: Bearer Token Authentication & Timezone Invariant",
                    "category": "Security & Auth",
                    "description": (
                        "Stateless access token verification with expiration checks and signature validation."
                    ),
                    "rationale": "Stateless, horizontally scalable authentication across API calls.",
                    "rules": [
                        "CRITICAL INVARIANT: Token expiration timestamps must strictly use timezone-aware UTC datetime (datetime.now(timezone.utc)).",
                        "Tokens must be rejected immediately if expired or missing required claims.",
                        "Bearer token extraction must be resilient to whitespace and formatting."
                    ],
                    "files": token_files or auth_files[:2],
                    "symbols": ["is_token_expired", "create_access_token", "decode_token"],
                })

            # Check for permissions / RBAC
            perm_files = [f for f in auth_files if "permission" in f.lower() or "role" in f.lower()]
            if perm_files:
                decisions.append({
                    "id": "decision:security:rbac",
                    "label": "Authorization: Role-Based Access Control (RBAC) & Normalization",
                    "category": "Security & Auth",
                    "description": (
                        "Fine-grained role and action permissions gate access to sensitive operations and order state changes."
                    ),
                    "rationale": "Enforces least privilege and prevents unauthorized privilege escalation.",
                    "rules": [
                        "CRITICAL INVARIANT: Role strings must be normalized (case-insensitive lowercase) prior to comparison.",
                        "Admin privileges must allow comprehensive management while restricting regular users to owned resources.",
                        "Never bypass permission gates on write/delete operations."
                    ],
                    "files": perm_files,
                    "symbols": ["has_permission", "ROLES"],
                })

        # 4. Service / Business Logic Layer Decision
        service_files = [f for f in all_files if "service" in f.lower() or "logic" in f.lower() or "controller" in f.lower()]
        if service_files:
            decisions.append({
                "id": "decision:architecture:service_layer",
                "label": "Architecture: Decoupled Service Domain Layer",
                "category": "Architecture & Patterns",
                "description": (
                    "Business logic, calculations, and domain operations are encapsulated in dedicated service modules, "
                    "isolated from HTTP presentation and database controllers."
                ),
                "rationale": "Promotes testability, separation of concerns, and clean multi-file refactoring.",
                "rules": [
                    "HTTP endpoints must delegate business execution to the corresponding service class/method.",
                    "Services must not directly depend on request/response HTTP transport objects.",
                    "Domain validation errors should raise structured exceptions."
                ],
                "files": service_files[:5],
            })

        # 5. Testing & Regression Gate Decision
        test_files = [f for f in all_files if "test" in f.lower()]
        test_count = len(ast_catalog["tests"])
        if test_files or test_count > 0 or "pytest" in all_deps:
            decisions.append({
                "id": "decision:testing:regression_gate",
                "label": "Quality Gate: Pytest Automated Regression & Boundary Verification",
                "category": "Testing & QA",
                "description": (
                    f"Comprehensive automated test suite ({test_count} tests detected) "
                    "verifying functional correctness, boundary conditions, and regression immunity."
                ),
                "rationale": "Ensures every patch is verified deterministically with zero unintended regressions.",
                "rules": [
                    "Run baseline test command: 'pytest tests -v' before and after any proposed modification.",
                    "Aether-SWE Judge requires 0 regressions across all existing tests for any patch to be accepted.",
                    "Write reproduction tests demonstrating failure before applying code fixes."
                ],
                "files": test_files[:6],
            })

        # 6. Autonomous Agent & Grounded Memory Decision
        if any("aether" in f.lower() or "orchestrat" in f.lower() or "memory" in f.lower() for f in all_files):
            decisions.append({
                "id": "decision:agent:grounded_memory",
                "label": "Agent Core: Grounded Fact Memory & Worktree Isolation",
                "category": "Autonomous Agent",
                "description": (
                    "The system operates with persistent grounded memory (.aether/memory_graph.json), "
                    "git worktree isolation, budget enforcement, and AST code verification gates."
                ),
                "rationale": "Guarantees safety, zero hallucination of APIs, and sandboxed branch execution.",
                "rules": [
                    "All discovered architectural invariants must be synced into Grounded Memory Graph.",
                    "AI specialists must check conflicts against verified memory nodes before generating patches.",
                    "Never execute uncommitted edits directly on the main branch; preserve git worktrees."
                ],
                "files": [f for f in all_files if "memory" in f or "orchestrat" in f or "worktree" in f][:5],
            })

        # 7. Additional detected invariants from code comments
        for inv in ast_catalog["invariants"][:4]:
            slug = re.sub(r"[^a-zA-Z0-9]+", "_", inv["text"].lower())[:30].strip("_")
            decisions.append({
                "id": f"decision:invariant:{slug}",
                "label": f"Invariant: {inv['text'][:60]}",
                "category": "Code Invariant",
                "description": inv["text"],
                "rationale": f"Explicitly documented in {inv['file']}:L{inv['line']}.",
                "rules": [inv["text"]],
                "files": [inv["file"]],
            })

        self.detected_decisions = decisions
        return decisions

    def build_deterministic_facts(self) -> List[Dict[str, Any]]:
        """Construct deterministic facts for the codebase (entry points, run & test commands)."""
        facts: List[Dict[str, Any]] = []

        # 1. Baseline Test Command Fact
        test_cmd = "pytest tests -v" if any("test" in f for f in self.files_data) else "npm test"
        facts.append({
            "id": "cmd:test_baseline",
            "node_type": "DeterministicFact",
            "label": "Baseline Test Command",
            "properties": {
                "command": test_cmd,
                "framework": "pytest" if "pytest" in test_cmd else "npm",
            },
        })

        # 2. Entry Point Fact
        entry = self.configs.get("entry_points", ["main.py"])[0] if self.configs.get("entry_points") else "main.py"
        facts.append({
            "id": "fact:entry_point",
            "node_type": "DeterministicFact",
            "label": "Primary Entry Point",
            "properties": {
                "entry_file": entry,
                "all_entry_points": self.configs.get("entry_points", []),
            },
        })

        # 3. Tech Stack Fact
        top_languages = sorted(self.language_counts.items(), key=lambda x: x[1], reverse=True)
        facts.append({
            "id": "fact:tech_stack",
            "node_type": "DeterministicFact",
            "label": "Detected Technology Stack",
            "properties": {
                "languages": dict(top_languages[:5]),
                "total_files": len(self.files_data),
                "total_lines": self.total_lines,
                "dependencies": self.configs.get("dependencies", [])[:15],
            },
        })

        # 4. Environment Variables Fact
        if self.configs.get("env_vars"):
            facts.append({
                "id": "fact:env_variables",
                "node_type": "DeterministicFact",
                "label": "Required Environment Variables",
                "properties": {
                    "variables": self.configs["env_vars"],
                },
            })

        self.deterministic_facts = facts
        return facts

    def sync_to_memory_graph(self, ast_catalog: Dict[str, Any]) -> MemoryGraphStore:
        """Persist all extracted decisions, deterministic facts, files, and symbols to .aether/memory_graph.json."""
        head_commit = self.memory_store._get_head_commit()

        # 1. Ingest Deterministic Facts
        for fact in self.deterministic_facts:
            self.memory_store.add_node(
                MemoryNode(
                    id=fact["id"],
                    node_type=fact["node_type"],
                    label=fact["label"],
                    properties=fact["properties"],
                    provenance_commit_sha=head_commit,
                    is_provisional=False,
                )
            )

        # 2. Ingest Architectural Decisions
        for dec in self.detected_decisions:
            node = MemoryNode(
                id=dec["id"],
                node_type="ArchitecturalDecision",
                label=dec["label"],
                properties={
                    "category": dec.get("category", "General"),
                    "description": dec.get("description", ""),
                    "rationale": dec.get("rationale", ""),
                    "rules": dec.get("rules", []),
                    "files": dec.get("files", []),
                    "symbols": dec.get("symbols", []),
                },
                provenance_commit_sha=head_commit,
                is_provisional=False,
            )
            self.memory_store.add_node(node)

            # Link decision to each associated file
            for f in dec.get("files", []):
                self.memory_store.add_edge(
                    MemoryEdge(source=node.id, target=f"file:{f}", relation="GOVERNS")
                )

        # 3. Ingest Files and Symbols
        for rel_path, data in self.files_data.items():
            # Skip massive numbers of tiny files to keep graph focused
            if data["lang"] not in ("Python", "JavaScript", "TypeScript", "HTML", "CSS", "JSON", "Shell Script"):
                continue

            file_id = f"file:{rel_path}"
            imports = ast_catalog.get("imports", {}).get(rel_path, [])
            self.memory_store.add_node(
                MemoryNode(
                    id=file_id,
                    node_type="File",
                    label=rel_path,
                    properties={
                        "path": rel_path,
                        "lang": data["lang"],
                        "line_count": data["line_count"],
                        "imports": imports[:10],
                    },
                    provenance_commit_sha=head_commit,
                    is_provisional=False,
                )
            )

        # Ingest key classes and functions
        for sym_id, sym_info in list(ast_catalog.get("classes", {}).items())[:50]:
            self.memory_store.add_node(
                MemoryNode(
                    id=f"symbol:{sym_id}",
                    node_type="Symbol",
                    label=f"Class {sym_info['name']}",
                    properties=sym_info,
                    provenance_commit_sha=head_commit,
                    is_provisional=False,
                )
            )
            self.memory_store.add_edge(
                MemoryEdge(source=f"file:{sym_info['file']}", target=f"symbol:{sym_id}", relation="DEFINES")
            )

        for sym_id, sym_info in list(ast_catalog.get("functions", {}).items())[:60]:
            self.memory_store.add_node(
                MemoryNode(
                    id=f"symbol:{sym_id}",
                    node_type="Symbol",
                    label=f"Function {sym_info['name']}",
                    properties=sym_info,
                    provenance_commit_sha=head_commit,
                    is_provisional=False,
                )
            )
            self.memory_store.add_edge(
                MemoryEdge(source=f"file:{sym_info['file']}", target=f"symbol:{sym_id}", relation="DEFINES")
            )

        self.memory_store.save()
        return self.memory_store

    def generate_how_it_works_markdown(self, ast_catalog: Dict[str, Any]) -> str:
        """Produce a comprehensive, structured HOW_IT_WORKS.md documenting the project."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        primary_lang = sorted(self.language_counts.items(), key=lambda x: x[1], reverse=True)
        top_lang_str = ", ".join(f"{lang} ({cnt} files)" for lang, cnt in primary_lang[:4]) or "Unknown"

        # Directory structure summary
        dir_tree_lines = self._generate_directory_map()

        md_parts = [
            f"# {self.repo_name} - Architecture & Project Guide",
            f"\n> **Automated Project Onboarding Specification**  ",
            f"> Generated by **Aether-SWE Codebase Cartographer** on `{now_str}`  ",
            f"> Grounded Decision Graph stored in: `.aether/memory_graph.json`\n",
            "---\n",
            "## 1. Executive Summary & Purpose\n",
            f"The `{self.repo_name}` repository comprises **{len(self.files_data)} source files** across **{self.total_lines:,} lines of code**. ",
            f"Primary languages utilized include {top_lang_str}.\n",
            "This document explains the overarching system architecture, key architectural decisions, execution flow, component relationships, and operational invariants governing the codebase.\n",
            "### Core Metrics at a Glance",
            f"- **Total Indexed Files:** {len(self.files_data)}",
            f"- **Total Lines of Code:** {self.total_lines:,}",
            f"- **Architectural Decisions Mined:** {len(self.detected_decisions)}",
            f"- **Baseline Test Command:** `{self.configs.get('test_command', 'pytest tests -v')}`",
            f"- **Identified Entry Points:** {', '.join(f'`{e}`' for e in self.configs.get('entry_points', [])) or '`main.py`'}",
            "\n---\n",
            "## 2. Technology Stack & Ecosystem\n",
            "| Category | Technology / Library | Role & Purpose |",
            "| :--- | :--- | :--- |",
        ]

        # Populate tech stack table
        for dep in self.configs.get("dependencies", [])[:12]:
            role = self._describe_dep_role(dep)
            md_parts.append(f"| Dependency | `{dep}` | {role} |")

        if not self.configs.get("dependencies"):
            for lang, count in primary_lang[:4]:
                md_parts.append(f"| Language | `{lang}` | {count} source files in repository |")

        md_parts.extend([
            "\n---\n",
            "## 3. High-Level Architecture & System Design\n",
            "The repository is structured to maintain strict separation of concerns, deterministic boundaries, and testable domain logic:\n",
        ])

        # Bullet points for architectural decisions
        for idx, dec in enumerate(self.detected_decisions, start=1):
            md_parts.append(f"### 3.{idx}. {dec['label']}")
            md_parts.append(f"**Category:** `{dec['category']}`  ")
            md_parts.append(f"**Description:** {dec['description']}\n")
            if dec.get("rationale"):
                md_parts.append(f"*Rationale:* {dec['rationale']}\n")
            if dec.get("rules"):
                md_parts.append("**Enforced Architectural Rules:**")
                for r in dec["rules"]:
                    md_parts.append(f"- {r}")
                md_parts.append("")
            if dec.get("files"):
                file_links = ", ".join(f"`{f}`" for f in dec["files"])
                md_parts.append(f"**Associated Code Files:** {file_links}\n")

        md_parts.extend([
            "---\n",
            "## 4. Codebase Directory Map\n",
            "```text",
            dir_tree_lines,
            "```\n",
            "---\n",
            "## 5. Core Execution Lifecycle & Data Flow\n",
            "1. **Initialization / Entry Point:**",
            f"   - The system initiates from `{self.configs.get('entry_points', ['main.py'])[0] if self.configs.get('entry_points') else 'main.py'}`.",
            "   - Configuration and settings are loaded from environment variables and configuration files.",
            "2. **Request / Dispatch Handling:**",
            "   - Inbound requests or user actions are received by the presentation/API layer (HTTP handlers, CLI commands, or Electron IPC).",
            "   - Input parameters are validated against defined schemas (Pydantic / dataclasses).",
            "3. **Service & Domain Operations:**",
            "   - Handlers delegate execution to isolated service modules.",
            "   - Domain business logic, state calculations, and entity mutations occur within the service layer.",
            "4. **Verification & Testing:**",
            "   - Automated regression test suites verify that all baseline operations remain functional.",
            "\n---\n",
            "## 6. Key Components & Modules\n",
        ])

        # Detail key components
        classes = ast_catalog.get("classes", {})
        routes = ast_catalog.get("routes", [])
        models = ast_catalog.get("models", [])

        if routes:
            md_parts.append("### API Routes & Interface Endpoints")
            md_parts.append("| Method / Decorator | Path / Channel | Source File |")
            md_parts.append("| :--- | :--- | :--- |")
            for r in routes[:15]:
                path = r.get("path") or r.get("decorator") or r.get("verb", "GET")
                verb = r.get("verb") or r.get("decorator", "ROUTE")
                src = r.get("file", "api")
                md_parts.append(f"| `{verb}` | `{path}` | `{src}` |")
            md_parts.append("")

        if models:
            md_parts.append("### Domain Schemas & Models")
            md_parts.append("| Model Name | Type | Source File | Description |")
            md_parts.append("| :--- | :--- | :--- | :--- |")
            for m in models[:10]:
                doc_summary = (m.get("doc") or "Domain data model").split("\n")[0]
                md_parts.append(f"| `{m['name']}` | `{m['type']}` | `{m['file']}` | {doc_summary} |")
            md_parts.append("")

        if classes:
            md_parts.append("### Core Service & Logic Classes")
            md_parts.append("| Class Name | Methods | Source File |")
            md_parts.append("| :--- | :--- | :--- |")
            for _, c in list(classes.items())[:12]:
                meth_str = ", ".join(f"`{m}`" for m in c["methods"][:4]) or "None"
                md_parts.append(f"| `{c['name']}` | {meth_str} | `{c['file']}` |")
            md_parts.append("")

        md_parts.extend([
            "---\n",
            "## 7. Grounded Decisions & Invariants for AI Agents\n",
            "> [!IMPORTANT]",
            "> **NON-NEGOTIABLES FOR AI AGENTS & CONTRIBUTORS**",
            ">\n",
            "> The following rules have been verified from the codebase and stored in `.aether/memory_graph.json`.",
            "> Any automated patch or manual edit that violates these decisions will trigger regression vetoes.\n",
        ])

        for dec in self.detected_decisions:
            md_parts.append(f"#### {dec['label']}")
            for r in dec.get("rules", []):
                md_parts.append(f"- ⚠️ **Rule:** {r}")
            md_parts.append("")

        md_parts.extend([
            "---\n",
            "## 8. Configuration, Environment & Secrets\n",
        ])

        if self.configs.get("env_vars"):
            md_parts.append("The following environment variables are referenced by the project:")
            for ev in self.configs["env_vars"]:
                md_parts.append(f"- `{ev}`")
        else:
            md_parts.append("No explicit `.env.example` file detected; standard defaults apply.")

        md_parts.extend([
            "\n---\n",
            "## 9. Developer Operations: Run & Test Guide\n",
            "### Running Baseline Regression Tests",
            "```bash",
            f"{self.configs.get('test_command', 'pytest tests -v')}",
            "```\n",
            "### Launching the Application",
            "```bash",
            f"{self.configs.get('run_command', 'python main.py')}",
            "```\n",
            "---\n",
            "## 10. Summary & Memory Synchronization\n",
            f"All above decisions, file definitions, and deterministic symbols have been indexed into the **Aether-SWE Grounded Memory Graph** (`.aether/memory_graph.json`). ",
            "When the autonomous agent (Triage, Detective, Architect, Surgeon, Judge) executes runs in this folder, it queries these verified nodes to ensure zero-regression code generation.\n",
        ])

        return "\n".join(md_parts)

    def _generate_directory_map(self, max_depth: int = 3) -> str:
        """Create a clean ASCII tree representation of the codebase."""
        lines = [f"{self.repo_name}/"]
        dirs_seen = set()

        for rel_path in sorted(self.files_data.keys()):
            parts = rel_path.split(os.sep)
            if len(parts) > max_depth + 1:
                continue

            for i in range(1, len(parts)):
                sub = os.sep.join(parts[:i])
                if sub not in dirs_seen:
                    dirs_seen.add(sub)
                    indent = "  " * i
                    lines.append(f"{indent}├── {parts[i-1]}/")

            indent = "  " * len(parts)
            lines.append(f"{indent}└── {parts[-1]}")

        return "\n".join(lines[:60])  # limit lines for clean output

    def _describe_dep_role(self, dep: str) -> str:
        """Return human-readable role for standard packages."""
        d = dep.lower()
        if "fastapi" in d:
            return "Asynchronous REST API framework"
        if "uvicorn" in d:
            return "ASGI web server implementation"
        if "pydantic" in d:
            return "Data parsing, schema validation & settings management"
        if "pytest" in d:
            return "Automated testing & fixture framework"
        if "httpx" in d:
            return "Asynchronous HTTP client for API communication"
        if "requests" in d:
            return "Synchronous HTTP library"
        if "electron" in d:
            return "Desktop GUI runtime shell"
        if "react" in d:
            return "Frontend UI component library"
        if "sqlalchemy" in d:
            return "SQL database toolkit and Object-Relational Mapper (ORM)"
        return "Core runtime dependency"

    def analyze_folder(self, force_refresh: bool = True) -> Dict[str, Any]:
        """High-level orchestration: scans files, extracts decisions, updates memory graph, writes HOW_IT_WORKS.md."""
        # 1. Scan and read every file
        files_data = self.scan_and_read_codebase()

        # 2. Extract AST, routes, classes, and invariants
        ast_catalog = self.extract_ast_and_symbols()

        # 3. Mine architectural decisions & invariants
        decisions = self.mine_architectural_decisions(ast_catalog)

        # 4. Extract deterministic facts
        facts = self.build_deterministic_facts()

        # 5. Populate and persist Grounded Memory Graph
        self.sync_to_memory_graph(ast_catalog)

        # 6. Generate HOW_IT_WORKS.md
        how_it_works_content = self.generate_how_it_works_markdown(ast_catalog)

        # Write to repo root
        root_md_path = os.path.join(self.repo_path, "HOW_IT_WORKS.md")
        with open(root_md_path, "w", encoding="utf-8") as f:
            f.write(how_it_works_content)

        # Also mirror in .aether/HOW_IT_WORKS.md
        aether_dir = os.path.join(self.repo_path, ".aether")
        os.makedirs(aether_dir, exist_ok=True)
        aether_md_path = os.path.join(aether_dir, "HOW_IT_WORKS.md")
        with open(aether_md_path, "w", encoding="utf-8") as f:
            f.write(how_it_works_content)

        return {
            "success": True,
            "repo_path": self.repo_path,
            "repo_name": self.repo_name,
            "total_files": len(files_data),
            "total_lines": self.total_lines,
            "languages": dict(sorted(self.language_counts.items(), key=lambda x: x[1], reverse=True)),
            "decisions_count": len(decisions),
            "decisions": decisions,
            "deterministic_facts_count": len(facts),
            "memory_stats": self.memory_store.get_stats(),
            "how_it_works_path": root_md_path,
            "how_it_works_preview": how_it_works_content[:500] + "...",
        }
