# Aether-SWE v1.3: Autonomous Software Engineering Command Center

Aether-SWE is an autonomous software engineering agent that fixes bugs and ships features in multi-file Python repos using a team of narrow LLM specialists, deterministic code gates, isolated git worktrees, and grounded memory.

---

## Team Ownership & Directory Boundaries

The codebase is organized into isolated, decoupled folders so each sub-team can work independently without merge clashes:

```
hacknex-ai-agent/
├── backend/                  # 🤖 Backend & Agent Core Team
│   ├── api/                  # FastAPI server & Server-Sent Events (SSE) live telemetry
│   ├── client/               # Bring-Your-Own-Model (BYOM) client & budget enforcement
│   ├── memory/               # Grounded Fact Memory Graph (.aether/memory_graph.json)
│   ├── orchestrator/         # Execution loop, specialist sequencing, and event emitter
│   ├── tools/                # Deterministic Tools (Preflight, Cartographer, Sentinel, Judge, Critic)
│   ├── workers/              # Specialist Worker Prompts (Triage, Detective, Architect, TestCrafter, Surgeon, Scribe)
│   ├── worktree/             # Git Worktree isolation manager (../aether-<run-id>)
│   └── models.py             # Shared Pydantic data schemas
│
├── frontend/                 # 🎨 Frontend & Design Team (Impeccable Anti-Slop UI)
│   ├── index.html            # Web application shell & Command Center layout
│   ├── css/                  # Design tokens, layout, dispatcher card, diff viewer, terminal
│   └── js/                   # App state, SSE telemetry consumer, diff syntax highlighter
│
├── benchmarks/               # 🧪 Benchmarks & Evaluation Team
│   └── ecommerce_api/        # FastAPI microservice with 24 baseline tests & planted timezone defect
│       ├── app/              # Config, auth tokens, permissions, models, orders
│       └── tests/            # 24 baseline pytest suites (8 auth, 8 permissions, 8 orders)
│
├── docs/                     # 📚 Product & Specifications Team
│   └── PRD Aether-SWE v1.1 (Orchestrator Edition).md   # PRD v1.3
└── DESIGN.md                 # Impeccable Operate-mode UI design specification
```

---

## Quickstart (Running Desktop App or Web Server)

### 1. Launch Electron Desktop App (Recommended)
```bash
npm start
# OR
./run.sh
```
This automatically manages port 8000, starts the Python backend child process, and launches the Electron desktop app with native OS local folder picker support.

### 2. Launch Web Server Mode
```bash
./run.sh --web
```
Runs the server directly on `http://127.0.0.1:8000`.

### 3. Accessing Users' Local Folders
- In the desktop application, click **`📂 Open Local Folder...`** in the top navigation bar or sidebar.
- Electron's native dialog pops open (`dialog.showOpenDialog`) allowing you to select **any folder** on your machine.
- The app scans the directory, lists project files, and points Aether-SWE's Cartographer, Preflight, Detective, and Judge directly at that repository.

### 4. Verify Baseline Tests
```bash
PYTHONPATH=benchmarks/ecommerce_api .venv/bin/pytest benchmarks/ecommerce_api/tests -v
```
All **24 tests** will run and pass.

---

## Team Working Guidelines (Zero-Clash Rules)

1. **Backend Team (`backend/`):**
   - Keep API responses compliant with schemas in `backend/models.py`.
   - Never write code modifying `frontend/` files; expose features via clean `/api` routes and SSE events.

2. **Frontend Team (`frontend/`):**
   - Strictly follow tokens and guidelines in `DESIGN.md`.
   - All backend interaction happens via `fetch("/api/run")` and `EventSource("/api/events")`.
   - Can develop and test independently by opening `frontend/index.html` or running against the mock SSE events.

3. **Evaluation Team (`benchmarks/`):**
   - Add new target benchmark repositories directly under `benchmarks/<name>`.
   - Ensure target repos have a runnable test suite and a documented bug reproduction scenario.
