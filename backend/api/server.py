"""FastAPI Server exposing Command Center REST endpoints and SSE live event stream."""
import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.models import (
    IssueInput,
    MergeBranchInput,
    MemoryNode,
    MemoryEdge,
    RunStatus,
    TriageClarificationInput,
    VerifyMemoryInput,
)
from backend.client.byom_client import BYOMClient
from backend.orchestrator.engine import OrchestratorEngine
from backend.workers.registry import WorkerRegistry
from backend.worktree.manager import WorktreeManager

app = FastAPI(title="Aether-SWE Command Center API", version="1.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Engine instance pointed at the benchmark repo
REPO_PATH = os.path.abspath("benchmarks/ecommerce_api")
engine = OrchestratorEngine(repo_path=REPO_PATH)

@app.get("/api/status")
async def get_system_status():
    """Retrieve system health, active repo, and memory/worktree stats."""
    worktrees = engine.worktree_mgr.list_worktrees()
    return {
        "repo": REPO_PATH,
        "engine_active": True,
        "memory_nodes_count": len(engine.memory_store.nodes),
        "verified_rules_count": len(engine.memory_store.get_verified_rules()),
        "advisory_hints_count": len(engine.memory_store.get_advisory_hints()),
        "active_worktrees_count": len(worktrees),
        "worktrees": worktrees,
    }

@app.get("/api/presets")
async def get_presets():
    """FR-7.8: Preset Challenge Launcher benchmarks."""
    return [
        {
            "id": "ecommerce_tz_defect",
            "title": "Ecommerce API: Timezone Expiry Bug",
            "repo": "benchmarks/ecommerce_api",
            "description": (
                "Tokens expire early or late depending on timezone offset.\n"
                "In app/auth/tokens.py::is_token_expired(), datetime.utcnow().timestamp() "
                "treats naive UTC as local time, producing an offset equal to server UTC offset."
            ),
            "target_file": "app/auth/tokens.py",
            "target_symbol": "is_token_expired",
            "expected_test": "test_token_expiration_under_non_utc_timezone",
        },
        {
            "id": "ecommerce_permissions_defect",
            "title": "Ecommerce API: Role Access Check",
            "repo": "benchmarks/ecommerce_api",
            "description": (
                "Admin users are denied order delete access due to case-sensitivity check.\n"
                "In app/auth/permissions.py::has_permission(), role.lower() comparison is missing."
            ),
            "target_file": "app/auth/permissions.py",
            "target_symbol": "has_permission",
            "expected_test": "test_admin_has_order_delete",
        },
    ]

@app.get("/api/config/endpoints")
async def get_supported_endpoints():
    """Retrieve list of supported model endpoints and provider templates."""
    return {
        "providers": [
            {
                "id": "gemini_openai",
                "name": "Google Gemini (OpenAI-compatible)",
                "provider": "openai_compatible",
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
                "models": ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
                "default_model": "gemini-1.5-flash",
                "docs": "Use your Google AI Studio API key with the Gemini OpenAI-compatible base URL.",
            },
            {
                "id": "gemini_native",
                "name": "Google Gemini (Native REST)",
                "provider": "gemini_native",
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "models": ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
                "default_model": "gemini-1.5-flash",
                "docs": "Native Google AI Studio endpoint.",
            },
            {
                "id": "anthropic",
                "name": "Anthropic Claude",
                "provider": "anthropic",
                "base_url": "https://api.anthropic.com/v1/messages",
                "models": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
                "default_model": "claude-3-5-sonnet-20241022",
                "docs": "Direct Anthropic Messages API.",
            },
            {
                "id": "openai",
                "name": "OpenAI Official",
                "provider": "openai_compatible",
                "base_url": "https://api.openai.com/v1",
                "models": ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"],
                "default_model": "gpt-4o-mini",
            },
            {
                "id": "ollama",
                "name": "Ollama (Local)",
                "provider": "openai_compatible",
                "base_url": "http://localhost:11434/v1",
                "models": ["llama3.2", "qwen2.5-coder", "mistral", "deepseek-r1"],
                "default_model": "llama3.2",
            },
            {
                "id": "lm_studio",
                "name": "LM Studio (Local)",
                "provider": "openai_compatible",
                "base_url": "http://localhost:1234/v1",
                "models": ["local-model"],
                "default_model": "local-model",
            },
            {
                "id": "openrouter",
                "name": "OpenRouter",
                "provider": "openai_compatible",
                "base_url": "https://openrouter.ai/api/v1",
                "models": ["google/gemini-2.0-flash", "anthropic/claude-3.5-sonnet", "deepseek/deepseek-chat"],
                "default_model": "google/gemini-2.0-flash",
            },
            {
                "id": "groq",
                "name": "Groq",
                "provider": "openai_compatible",
                "base_url": "https://api.groq.com/openai/v1",
                "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
                "default_model": "llama-3.3-70b-versatile",
            },
            {
                "id": "custom",
                "name": "Custom OpenAI-compatible Endpoint",
                "provider": "openai_compatible",
                "base_url": "https://your-custom-proxy.com/v1",
                "models": ["custom-model"],
                "default_model": "custom-model",
                "docs": "Any endpoint implementing the /chat/completions specification.",
            }
        ]
    }

class EndpointTestRequest(BaseModel):
    endpoint: str
    api_key: Optional[str] = ""
    model: Optional[str] = "default"
    provider: Optional[str] = "openai_compatible"

@app.post("/api/config/test-endpoint")
async def test_endpoint(req: EndpointTestRequest):
    """Test connectivity to any custom endpoint with an API key."""
    result = await BYOMClient.test_endpoint_connection(
        endpoint=req.endpoint,
        api_key=req.api_key or "",
        model=req.model or "default",
        provider=req.provider or "openai_compatible"
    )
    return result

@app.post("/api/triage/eval")
async def evaluate_triage(req: Dict[str, str]):
    """FR-1.1: Fast Stage 1 deterministic triage evaluation for real-time UI feedback."""
    description = req.get("description", "")
    triage = WorkerRegistry.triage_issue(description)
    return triage.model_dump()

@app.post("/api/run")
async def start_run(issue: IssueInput, bg: BackgroundTasks):
    """Trigger an autonomous repair run in background."""
    bg.add_task(engine.execute_run, issue)
    return {
        "status": "started",
        "message": f"Run queued for issue: {issue.title}",
        "issue": issue.model_dump(),
    }

@app.post("/api/run/abort")
async def abort_run(req: Dict[str, str]):
    """Abort an active run."""
    run_id = req.get("run_id", "")
    ok = engine.abort_run(run_id)
    return {"success": ok, "run_id": run_id}

@app.get("/api/events")
async def stream_events(request: Request):
    """SSE endpoint for live telemetry stream (FR-7.2, FR-7.4)."""
    queue = engine.subscribe()

    async def event_generator():
        try:
            # Yield past events first
            for past in engine.events[-15:]:
                yield f"data: {json.dumps(past.model_dump())}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(event.model_dump())}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- Grounded Memory Graph Endpoints (FR-4) ---

@app.get("/api/memory")
async def get_memory_graph():
    """FR-4.1: Retrieve Grounded Memory Graph nodes and edges."""
    return {
        "repo": REPO_PATH,
        "nodes": list(engine.memory_store.nodes.values()),
        "edges": engine.memory_store.edges,
    }

@app.post("/api/memory/verify")
async def verify_memory_node(req: VerifyMemoryInput):
    """FR-4.3: Manually mark a provisional decision as verified."""
    success = engine.memory_store.verify_node(req.node_id, verified=req.verified)
    if not success:
        raise HTTPException(status_code=404, detail=f"Node '{req.node_id}' not found")
    return {"success": True, "node_id": req.node_id, "is_provisional": not req.verified}

@app.post("/api/memory/node")
async def add_memory_node(node: MemoryNode):
    """Add a new node to the grounded memory graph."""
    engine.memory_store.add_node(node)
    return {"success": True, "node": node.model_dump()}

@app.delete("/api/memory")
async def reset_memory(prune_stale_only: bool = False):
    """Reset or prune stale nodes from memory graph."""
    if prune_stale_only:
        stale_count = engine.memory_store.mark_stale_by_git()
        return {"success": True, "stale_pruned": stale_count}
    engine.memory_store.nodes = {}
    engine.memory_store.edges = []
    engine.memory_store._init_defaults()
    return {"success": True, "message": "Memory graph reset to defaults"}

# --- Git Worktree Endpoints (FR-2) ---

@app.get("/api/worktrees")
async def list_worktrees():
    """FR-2.1 & FR-2.3: List active isolated worktrees."""
    worktrees = engine.worktree_mgr.list_worktrees()
    return {
        "success": True,
        "worktrees": worktrees,
        "uncommitted_warning": engine.worktree_mgr.get_uncommitted_warning(),
    }

@app.get("/api/diff")
async def get_branch_diff(branch: str, base: str = "main"):
    """FR-2.4 & FR-7.5: Retrieve unified diff for manual branch review."""
    diff_text = engine.worktree_mgr.get_branch_diff(branch, base_branch=base)
    return {"success": True, "branch": branch, "base": base, "diff": diff_text}

@app.post("/api/worktree/merge")
async def merge_worktree_branch(req: MergeBranchInput):
    """FR-2.4: Merge tested branch on explicit user manual review only."""
    branch_name = f"aether/fix-{req.run_id}" if not req.run_id.startswith("aether/") else req.run_id
    success, msg = engine.worktree_mgr.merge_branch(branch_name, target_branch=req.target_branch)
    return {"success": success, "message": msg}

@app.delete("/api/worktree/{run_id}")
async def teardown_worktree(run_id: str, preserve_branch: bool = True):
    """FR-2.5: Teardown worktree while preserving branch."""
    branch_name = f"aether/fix-{run_id}"
    parent_dir = os.path.dirname(engine.worktree_mgr.git_root)
    wt_path = os.path.join(parent_dir, f"aether-{run_id}")
    ok = engine.worktree_mgr.remove_worktree(wt_path, branch_name, preserve_branch=preserve_branch)
    return {"success": ok, "worktree_path": wt_path, "branch_preserved": preserve_branch}

# --- File & Project Tree Endpoints ---

class FileSaveInput(BaseModel):
    path: str
    content: str

@app.get("/api/file")
async def get_file_content(path: str):
    """Read a code file from disk."""
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        rel_to_repo = os.path.join(REPO_PATH, path)
        if os.path.exists(rel_to_repo):
            abs_path = rel_to_repo
        else:
            return {"success": False, "error": f"File not found: {path}"}
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {
            "success": True,
            "path": abs_path,
            "name": os.path.basename(abs_path),
            "content": content,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/file")
async def save_file_content(req: FileSaveInput):
    """Write/save a code file to disk."""
    abs_path = os.path.abspath(req.path)
    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"success": True, "path": abs_path}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/tree")
async def get_directory_tree(path: str = "benchmarks/ecommerce_api"):
    """Scan and return tree structure of a directory."""
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        return {"success": False, "error": f"Directory not found: {path}"}

    def scan_dir(cur_dir, root_dir, depth=0):
        if depth > 4:
            return []
        items = []
        try:
            for entry in sorted(os.scandir(cur_dir), key=lambda e: (not e.is_dir(), e.name.lower())):
                if entry.name.startswith(".") or entry.name in ("__pycache__", "node_modules", ".venv"):
                    continue
                is_d = entry.is_dir()
                items.append({
                    "name": entry.name,
                    "relPath": os.path.relpath(entry.path, root_dir),
                    "fullPath": entry.path,
                    "isDirectory": is_d,
                    "children": scan_dir(entry.path, root_dir, depth + 1) if is_d else [],
                })
        except Exception:
            pass
        return items

    return {
        "success": True,
        "path": abs_path,
        "name": os.path.basename(abs_path),
        "tree": scan_dir(abs_path, abs_path),
    }

# --- Past Runs & Reports Endpoints ---

@app.get("/api/runs")
async def list_past_runs():
    """List past runs stored on disk."""
    runs = []
    if os.path.exists(engine.runs_dir):
        for run_id in sorted(os.listdir(engine.runs_dir), reverse=True):
            r_dir = os.path.join(engine.runs_dir, run_id)
            if os.path.isdir(r_dir):
                has_report = os.path.exists(os.path.join(r_dir, "logs", "report.md"))
                runs.append({
                    "run_id": run_id,
                    "has_report": has_report,
                })
    return {"runs": runs}

@app.get("/api/runs/{run_id}")
async def get_run_details(run_id: str):
    """Retrieve full logs and Scribe report for a run."""
    run_dir = os.path.join(engine.runs_dir, run_id)
    if not os.path.exists(run_dir):
        raise HTTPException(status_code=404, detail="Run not found")

    report_path = os.path.join(run_dir, "logs", "report.md")
    report_content = ""
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()

    return {
        "run_id": run_id,
        "report": report_content,
        "active_status": engine.active_runs.get(run_id, {}).get("status"),
    }

# Mount static frontend
frontend_dir = os.path.abspath("frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
