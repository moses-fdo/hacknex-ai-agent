"""FastAPI Server exposing REST endpoints and SSE live event stream."""
import asyncio
import json
import os
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel
from backend.models import IssueInput
from backend.orchestrator.engine import OrchestratorEngine

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

@app.get("/api/presets")
async def get_presets():
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
        }
    ]

@app.post("/api/run")
async def start_run(issue: IssueInput, bg: BackgroundTasks):
    """Trigger an autonomous repair run in background."""
    bg.add_task(engine.execute_run, issue)
    return {"status": "started", "message": f"Run queued for issue: {issue.title}"}

@app.get("/api/events")
async def stream_events(request: Request):
    """SSE endpoint for live telemetry stream."""
    queue = engine.subscribe()

    async def event_generator():
        try:
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

@app.get("/api/memory")
async def get_memory_graph():
    """Retrieve Grounded Memory Graph nodes and edges."""
    return {
        "nodes": list(engine.memory_store.nodes.values()),
        "edges": engine.memory_store.edges,
    }

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
            "content": content
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
                    "children": scan_dir(entry.path, root_dir, depth + 1) if is_d else []
                })
        except Exception:
            pass
        return items

    return {
        "success": True,
        "path": abs_path,
        "name": os.path.basename(abs_path),
        "tree": scan_dir(abs_path, abs_path)
    }

@app.get("/api/status")
async def get_system_status():
    return {
        "repo": REPO_PATH,
        "engine_active": True,
        "memory_nodes_count": len(engine.memory_store.nodes),
    }

# Mount static frontend
frontend_dir = os.path.abspath("frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
