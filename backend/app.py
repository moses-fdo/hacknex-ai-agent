import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import config
from backend.models.schema import RunRequest, ModelSettings, AgentEvent
from backend.engine.orchestrator import MasterOrchestrator
from backend.engine.ast_parser import CodebaseCartographer
from backend.engine.llm_client import UniversalLLMClient
from backend.engine.sandbox import SandboxTestRunner

app = FastAPI(title="Aether-SWE Agent Command Center", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
orchestrator = MasterOrchestrator()
active_state: Dict[str, Any] = {}

PRESET_CHALLENGES = [
    {
        "id": "challenge_1",
        "title": "Fix UTC Token Expiry Bug (Zero Regression Guarantee)",
        "difficulty": "Core Benchmark",
        "tags": ["Bugfix", "Timezone", "Auth", "Zero-Regression"],
        "description": "In app/auth/tokens.py, token expiration validation uses naive local time instead of timezone-aware UTC, causing tokens to prematurely expire. Fix this to use timezone.utc, ensuring all 24 existing tests pass and adding a test for cross-timezone validation."
    },
    {
        "id": "challenge_2",
        "title": "Add API Rate-Limiting to Service Layer without Breaking RBAC",
        "difficulty": "Feature Addition",
        "tags": ["Feature", "Security", "OrderService"],
        "description": "Add in-memory rate limiting (max 10 requests per minute per user) to OrderService.create_order without mutating existing Order models or breaking role-based permission tests."
    },
    {
        "id": "challenge_3",
        "title": "Multi-File Refactoring of Database Session & Config Singleton",
        "difficulty": "Advanced Multi-File",
        "tags": ["Refactoring", "Multi-File", "Architecture"],
        "description": "Refactor app/config.py and app/services/order_service.py to support dynamic secret rotation while preserving backward compatibility across all 24 existing test cases."
    }
]

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "agent": "Aether-SWE", "version": "1.0.0"}

@app.get("/api/challenges")
async def get_challenges():
    return {"challenges": PRESET_CHALLENGES}

@app.get("/api/repo/tree")
async def get_repo_tree(repo_path: Optional[str] = None):
    target = repo_path or config.DEFAULT_REPO_PATH
    cartographer = CodebaseCartographer(target)
    repo_map = cartographer.scan(force_refresh=True)
    return {
        "repo_path": repo_map.repo_path,
        "total_files": repo_map.total_files,
        "files": repo_map.files,
        "import_graph": repo_map.import_graph
    }

@app.get("/api/repo/file")
async def get_file_content(path: str, repo_path: Optional[str] = None):
    base = Path(repo_path or config.DEFAULT_REPO_PATH)
    target = (base / path).resolve()
    if not target.exists() or not str(target).startswith(str(base)):
        raise HTTPException(status_code=404, detail="File not found")
    return {"path": path, "content": target.read_text(encoding="utf-8")}

@app.post("/api/model/test")
async def test_model_connection(settings: ModelSettings):
    client = UniversalLLMClient(settings)
    result = await client.test_connection()
    return result

@app.post("/api/run")
async def start_agent_run(request: RunRequest, background_tasks: BackgroundTasks):
    global active_state

    async def run_pipeline():
        global active_state
        try:
            active_state = await orchestrator.run(request)
        except Exception as e:
            print(f"[App] Pipeline execution error: {e}")

    background_tasks.add_task(run_pipeline)
    return {"status": "started", "message": "Aether-SWE autonomous run launched."}

@app.get("/api/events")
async def stream_events(request: Request):
    """Server-Sent Events (SSE) streaming real-time thoughts and persona events."""
    queue = orchestrator.event_bus.subscribe()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                event: AgentEvent = await queue.get()
                yield f"data: {event.model_dump_json()}\n\n"
        finally:
            orchestrator.event_bus.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

class HiddenTestRequest(BaseModel):
    test_code: str
    test_name: Optional[str] = "test_hidden_eval.py"

@app.post("/api/evaluate/hidden")
async def run_hidden_tests(payload: HiddenTestRequest):
    """Judges can drop their secret hidden tests to verify against the patched repo."""
    repo = Path(config.DEFAULT_REPO_PATH)
    hidden_file = repo / "tests" / payload.test_name
    hidden_file.write_text(payload.test_code, encoding="utf-8")

    sandbox = SandboxTestRunner(str(repo))
    result = sandbox.run_pytest(f"tests/{payload.test_name}")

    # Clean up hidden test file after execution
    if hidden_file.exists():
        hidden_file.unlink()

    return {
        "status": "evaluated",
        "passed": result.passed,
        "passed_tests": result.passed_tests,
        "failed_tests": result.failed_tests,
        "raw_output": result.raw_output
    }

# Mount static frontend
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
