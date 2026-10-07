# PRD: Aether-SWE v1.3 (Production Orchestrator Edition)

Oct 7, 2026 · @Moses

## Executive summary

Aether-SWE is an autonomous software engineering agent that fixes bugs and ships features in multi-file Python repos. A boss Orchestrator hands each job to a narrow specialist, so no single context fills up with clutter.

**The problem.** In long sessions a single agent drowns. It carries 20+ tools and a growing pile of files, then calls the wrong tool, forgets earlier findings, invents APIs, and patches code without checking what else broke. Furthermore, naive agents suffer from six fatal failure modes: guessing on vague bug reports, contaminating user git branches, crashing on unconfigured databases, poisoning memory graphs with hallucinated rules, botching multi-file edits, and running up unlimited API bills.

**The approach.** The Orchestrator routes each task through a skill registry to narrow workers with 2–3 tools each. Hard rules are enforced by deterministic tools in plain code. This edition bakes in six battle-hardened production guardrails:
1. **Two-stage Triage Gate:** Deterministic anchor check followed by bounded clarification questions, with "Could Not Reproduce" (CNR) as a first-class outcome.
2. **Physical Git Worktree Isolation:** All modifications, tests, and rollbacks execute in an isolated worktree (`../aether-<run-id>`), making it physically impossible to touch the user's working tree or active uncommitted files.
3. **Deterministic Preflight Tool:** Dedicated environment pre-flight (owned by the Judge) that initializes `.env.example` and `docker-compose`, checks service health, and halts on environment failures without blaming code.
4. **Grounded Fact Memory:** A persistent repository graph storing only deterministically verified facts (AST relationships, test commands, commit provenance). Provisional entries act as hints, never constraints, and invalidate automatically when referenced files change.
5. **Multi-File Staging with Scope Guards:** Architect drafts an ordered edit plan (max 5 files); Surgeon executes step-by-step; Sentinel and Judge verify atomically post-patch.
6. **Hard Client-Side Budget Enforcement:** BYOM client tracks token costs per model, refuses calls that breach limits, and reserves 10% of the budget to ensure the Scribe can always produce a final post-mortem report.

---

## Orchestrator and skill registry

The Orchestrator coordinates specialists through a structured skill registry. The boss reads only worker metadata, task briefs, and compact structured outputs. Full transcripts and execution logs stay on disk.

**The Execution Loop**

```
[Issue Description]
       │
       ▼
[Stage 1 & 2 Triage Gate] ──(Missing anchors / CNR)──▶ [Clarify or State Assumption]
       │
       ▼
[Git Worktree Setup (`../aether-<run-id>`)]
       │
       ▼
[Preflight Check (Judge/Preflight)] ──(Env Fail)──▶ [Halt: "Environment Not Ready"]
       │
       ▼
[Cartographer (AST Index & Grounded Memory Scan)]
       │
       ▼
[Detective (Localize Root Cause)]
       │
       ▼
[Architect (Multi-File Edit Plan, max 5 files)]
       │
       ▼
[Test Crafter (Failing Reproduction Test)] ──(Passes or fails syntax 2x)──▶ [Loop to Triage: CNR]
       │
       ▼
[Surgeon (Applies Diff Plan Step-by-Step in Worktree)]
       │
       ▼
[Sentinel (Atomic AST & Type Check across all touched files)]
       │
       ▼
[Judge (Run Baseline + Post-Patch Test Suite)] ──(Regressions > 0)──▶ [Atomic Worktree Rollback & Retry]
       │
       ▼
[Critic (Cleanliness & Total Diff Size Score)]
       │
       ▼
[Scribe (Final Report, Commit Grounded Memory, Export Diff)]
```

**Limits & Safety Caps**
- Max **12 delegations** per run.
- Max **3 retries** per worker.
- Max **3 self-healing iterations** after a Judge veto.
- Max **5 files** per multi-file patch plan.
- Hard **dollar/token budget cap** with 10% reserved for Scribe.
- Single level of delegation (no recursive worker spawning).

---

## Personas & Responsibilities

The system divides labor into 5 LLM workers and 5 deterministic tools:

### LLM Workers

| Worker | Role | Allowed Tools | Forbidden Actions | Done Condition |
| :--- | :--- | :--- | :--- | :--- |
| **Triage Specialist** | Clarify vague issues | `analyze_anchors`, `ask_clarification` | Never touch code, never make architectural edits | Anchors identified or assumption stated |
| **Detective** | Locate root cause | `query_memory_graph`, `semantic_symbol_search`, `trace_call_hierarchy` | Edit code, run tests | File, symbol, and line range found (confidence > 0.9) |
| **Architect** | Multi-file plan & invariants | `query_memory_graph`, `read_interface_contract`, `draft_blueprint` | Direct file editing | Ordered edit plan (symbol, file, purpose) covering $\le 5$ files |
| **Test Crafter** | Write reproduction test | `create_test_file`, `verify_test_syntax` | Touch production code, see Detective diagnosis | Test fails on unpatched code and passes after fix |
| **Surgeon** | Apply targeted diff slices | `read_target_slice`, `apply_unified_diff` | Search repo, run shell commands, touch out-of-scope files | Unified diff applied matching Architect's plan |
| **Scribe** | Final report & memory commit | `compile_markdown_report`, `update_memory_graph`, `export_proof` | Alter code or tests | Report cites diff, tests, cost, and commits grounded facts |

### Deterministic Tools (No LLM Trust)

| Tool | Role | What It Runs | Done Condition |
| :--- | :--- | :--- | :--- |
| **Preflight** | Environment readiness | Detect test runner, parse `.env.example`, launch `docker-compose`, poll health checks | All services healthy, test runner executable |
| **Cartographer** | AST index & graph sync | `build_ast_index`, `get_import_graph`, `sync_graph_symbols` | Hierarchical skeleton and deterministic import facts synced |
| **Sentinel** | Atomic symbol gate | `ruff`/`pyflakes`, `pyright` diff, AST signature checks | Zero new lint/type errors and zero invented symbols across all patched files |
| **Judge** | Sandbox & regression gate | Flaky test exclusion, baseline run $\times 2$, post-patch test run, worktree `git reset --hard` | Zero regressions ($\text{BaselinePass} \setminus \text{PostPatchPass} = \emptyset$) |
| **Critic** | Cleanliness scoring | Linter, total diff size calculation, cyclomatic complexity | Cleanliness score 0–100 with total diff size penalty |

---

## Detailed Functional Requirements

### 1. Two-Stage Triage Gate
- **FR-1.1 (Deterministic First Pass):** Regex and heuristic scan verifying the bug report contains:
  1. A symptom description.
  2. Expected vs. actual behavior.
  3. At least one concrete anchor: an error message/stack trace, API endpoint, function name, or file path.
- **FR-1.2 (Interactive Clarification):** If anchors are missing, prompt the user with at most **two multiple-choice questions** to anchor the scope.
- **FR-1.3 (Unattended / Demo Fallback):** If running non-interactively, proceed using the highest-probability interpretation and prominently tag the assumption in the UI and final Scribe report.
- **FR-1.4 (Could Not Reproduce - CNR):** If the Test Crafter cannot produce a valid failing test after 2 attempts, the run halts with status `COULD_NOT_REPRODUCE` and loops back to Triage rather than guessing a patch.

### 2. Git Worktree Isolation
- **FR-2.1 (Isolated Worktree Creation):** Every run initializes an isolated git worktree:
  ```bash
  git worktree add ../aether-<run-id> -b aether/fix-<run-id>
  ```
- **FR-2.2 (Working Tree Immutability):** All edits, bash commands, tests, and rollbacks execute exclusively within `../aether-<run-id>`. The user's active branch and working directory are physically untouched.
- **FR-2.3 (Uncommitted Changes Notice):** Worktrees branch from `HEAD`. The UI displays a warning: *"Worktree created from HEAD. Uncommitted changes in your editor are not included in this run."*
- **FR-2.4 (Manual Review & Merge):** The system produces a tested branch and unified diff. It **never auto-merges** into the user's branch.
- **FR-2.5 (Worktree Teardown):** On completion or abort, the worktree is cleaned up via `git worktree remove` while preserving the target branch `aether/fix-<run-id>`.

### 3. Environment & Preflight Gate
- **FR-3.1 (Preflight Tool Ownership):** A deterministic Preflight tool (owned by the Judge) executes before any agent begins analysis.
- **FR-3.2 (Service Initialization):**
  - Parses `.env.example` or test configurations into temporary environment variables. Real `.env` files containing secrets are never read or copied.
  - If `docker-compose.yml` is present, starts dependencies (`docker-compose up -d`) and waits for health checks.
- **FR-3.3 (Failure Classification):**
  - `ConnectionRefusedError`, missing environment variables, and missing external binary packages are classified as **Environment Failures**.
  - On Environment Failure, the run aborts immediately with status `ENVIRONMENT_NOT_READY` and exact remediation instructions. Code is never blamed.
- **FR-3.4 (Supported MVP Matrix):** Explicitly supports Python $\ge$ 3.10 with SQLite, local mock services, or standard `docker-compose` setups. Other external database servers are marked unsupported up front.

### 4. Grounded Project Decision Memory
- **FR-4.1 (Storage & Location):** Persisted per repository in `.aether/memory_graph.json`.
- **FR-4.2 (Deterministic Fact Ingestion):**
  - Only stores facts verified by code: detected test commands, AST import graphs, file-symbol hierarchies, and exact git commit hashes.
  - LLM-concluded rules are **never** stored as definitive facts.
- **FR-4.3 (Provisional vs. Verified Entries):**
  - Fix decisions and root causes generated by Scribe are flagged `provisional`.
  - Workers view `provisional` entries strictly as **advisory hints**, never as constraints.
  - Users can manually mark decisions as `verified` via the UI.
- **FR-4.4 (Provenance & Stale Invalidation):**
  - Every graph node records `run_id` and `commit_sha`.
  - When Cartographer indexes the repository, any node referencing a file modified between `commit_sha` and `HEAD` is automatically marked `stale`.
- **FR-4.5 (Conflict Warnings):** If a worker's proposed blueprint contradicts an existing verified memory node, Orchestrator triggers an alert in the UI event stream.

### 5. Multi-File Surgery & Scope Guards
- **FR-5.1 (Ordered Edit Plan):** For issues requiring changes across multiple files, the Architect produces an ordered plan specifying:
  - File path, target symbol, and exact functional purpose for each step.
  - Dependent symbols and callers derived deterministically via `trace_call_hierarchy`.
- **FR-5.2 (Scope Guard Enforcement):** Surgeon receives one slice at a time and is physically barred from editing any file not explicitly listed in the Architect's approved plan. Total files capped at **5 files**.
- **FR-5.3 (Atomic Verification):** Sentinel (AST/type check) and Judge (regression test suite) run **once after all multi-file edit steps are applied**, accommodating broken intermediate states.
- **FR-5.4 (Atomic Rollback):** If post-patch verification fails, `git reset --hard` rolls back all files in the worktree simultaneously.
- **FR-5.5 (Total Diff Size Penalty):** Critic evaluates cleanliness on total diff size across all modified files, applying progressive penalties instead of rigid per-file line caps.

### 6. BYOM Client & Hard Cost Budgeting
- **FR-6.1 (Centralized Client Enforcement):** All LLM calls route through a single unified BYOM client interface (supporting Anthropic Messages API and any OpenAI-compatible endpoint).
- **FR-6.2 (Client-Side Pre-Flight Check):** The client counts tokens, tracks cumulative spend, and **refuses the next request** if estimated token usage exceeds the configured budget cap.
- **FR-6.3 (Scribe 10% Reserve):** The client reserves 10% of the maximum budget specifically for the Scribe. If a budget cutoff triggers, the worktree is rolled back and Scribe uses the reserve to generate an informative post-mortem report explaining where and why execution halted.
- **FR-6.4 (Custom Pricing Configuration):** Users can input custom input/output costs per 1M tokens per model. Local models (Ollama, LM Studio) default to `$0.00`.
- **FR-6.5 (Budget Warnings):** The client emits a high-priority warning event over SSE at 80% budget consumption. Default budget cap defaults to `$1.00`.

### 7. Command Center UI
- **FR-7.1 (Theme & Typography):** Sleek dark theme with monospace font hierarchy.
- **FR-7.2 (Real-Time Pipeline Route):** Interactive graph/stepper showing active persona, kind (`llm` vs `tool`), and real-time step status.
- **FR-7.3 (Worktree & Safety Status):** Prominent badge displaying active worktree path (`../aether-<run-id>`), target branch, and notice regarding uncommitted files.
- **FR-7.4 (Live Cost & Token Telemetry):** Real-time dollar and token counter broken down by persona, with visual progress toward the budget cap and an 80% warning bar.
- **FR-7.5 (Multi-File Diff Inspector):** Tabbed side-by-side and unified diff viewer supporting multi-file review with Critic score breakdown.
- **FR-7.6 (Judge Terminal):** Test counts (passed, failed, flaky, regressions) with clear green/red status indicators.
- **FR-7.7 (Interactive Memory Graph Explorer):** Visual node-link explorer displaying deterministic facts, verified decisions, and provisional hints with stale badges.
- **FR-7.8 (Preset Challenge Launcher):** One-click runner for benchmark suites (`ecommerce_api` and real-world SWE-bench cases).

---

## In-House Benchmark (`benchmarks/ecommerce_api`)

- **Repo:** FastAPI e-commerce microservice with 24 baseline pytest suites.
- **Planted Bug:** Timezone offset defect in `app/auth/tokens.py` using `datetime.utcnow().timestamp()`.
- **Reproducibility Test:** Test Crafter sets `TZ=Asia/Kolkata` using `time.tzset()`, proving failure on unpatched code and success post-patch.
- **Preflight Validation:** Preflight detects Python environment, verifies dependencies, and executes baseline suite twice to establish the zero-regression reference set.

---

## Evaluation Rubric Alignment

| Rubric Criterion | Weight | How Aether-SWE Satisfies It |
| :--- | :--- | :--- |
| **Pass Hidden Tests** | 30 pts | Test Crafter generates isolated reproduction tests; Judge requires fail-before and pass-after verification. |
| **Zero Regressions** | Major Penalty | Judge excludes flaky tests, computes $\text{BaselinePass} \setminus \text{PostPatchPass}$, and triggers atomic worktree rollback on any regression. |
| **Grounded Memory & History** | High | Persistent fact graph eliminates repeat scans, enforces provenance (`commit_sha`), and invalidates stale nodes. |
| **No Hallucinated APIs** | Strict | Sentinel enforces AST parsing, dependency import checks, and pyright static analysis before execution. |
| **Clean & Safe Git Practices** | High | Git worktree isolation ensures user working branch is never contaminated; changes delivered as clean reviewable branches. |
| **Cost & Budget Discipline** | High | Client-side hard budget caps with 10% reserve guarantee no surprise charges and complete reporting. |
| **Clear Root Cause Explanation** | Required | Scribe produces structured post-mortems citing exact diffs, test proofs, confidence metrics, and budget telemetry. |
| **Live Command Center Demo** | Required | Full UI with real-time SSE stream, multi-file diff viewer, cost breakdown, and memory graph visualizer. |
