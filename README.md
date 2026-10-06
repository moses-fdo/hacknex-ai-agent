# ▲ AETHER-SWE: Autonomous Software Engineering Agent

> **Antigravity-Grade Multi-Persona Autonomous Coding Agent with Mathematical Zero-Regression Sandboxing and Universal Model Gateway (BYOM).**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Pytest](https://img.shields.io/badge/pytest-8.0+-orange.svg)](https://docs.pytest.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Track: HNX26PSI09](https://img.shields.io/badge/Hackathon-HNX26PSI09-green.svg)]()

---

## 1. Executive Summary

Real-world software engineering codebases consist of thousands of lines of code spanning multiple services, authentication layers, business logic, and automated tests. Most generative AI coding tools act as unconstrained, monolithic prompts that suffer from:
1. **Tool Distraction & Hallucination:** Inventing fake library imports or unresolvable APIs.
2. **Context Dilution:** Overflowing context windows by passing full source files.
3. **Regression Blindness:** Breaking existing functionality while implementing a fix.

**Aether-SWE** solves this with a **9-Persona Guild** structured across **3 Agile Squads**. By enforcing the **Principle of Least Privilege for AI**, each persona possesses only the specific tools and AST context slices required for its duty. An impassable **Judge** and **Sentinel** enforce mathematical zero regressions ($R = B \setminus P = \emptyset$) and zero hallucinated APIs.

---

## 2. System Architecture

```mermaid
flowchart TD
    subgraph Squad1["🧭 SQUAD 1: DISCOVERY & STRATEGY"]
        C["1. Cartographer<br/>AST Symbol Map"] --> D["2. Detective<br/>RCA Localizer"] --> A["3. Architect<br/>Blueprint Planner"]
    end
    subgraph Squad2["🛠️ SQUAD 2: IMPLEMENTATION & INTEGRITY"]
        TC["4. Test Crafter<br/>TDD Reproduction"] --> S["5. Surgeon<br/>Atomic Diffs"] --> ST["6. Sentinel<br/>Anti-Hallucination Guard"]
    end
    subgraph Squad3["⚖️ SQUAD 3: VERIFICATION & GOVERNANCE"]
        J["7. Judge<br/>Sandbox & Rollback"] --> CR["8. Critic<br/>Cleanliness Auditor"] --> SC["9. Scribe<br/>RCA Dossier Chronicler"]
    end

    User["User / Judge Issue"] --> C
    A --> TC
    ST -- Valid AST --> J
    ST -- Fake Imports --> S
    J -- Regressions / Failed Tests --> S
    J -- All Tests Pass (0 Regressions) --> CR
    SC --> Dossier["Verified Working Code & Proof"]
```

---

## 3. The 9-Persona Guild (Separation of Powers)

| Squad | Persona | Core Role | Allowed Tools | Forbidden Tools |
| :--- | :--- | :--- | :--- | :--- |
| **Discovery** | **1. Cartographer** | Scans AST & builds dependency graph | `build_ast_index`, `generate_skeleton` | Modifying files, shell commands |
| **Discovery** | **2. Detective** | Traces stack traces to exact lines | `semantic_symbol_search` | Modifying code, running tests |
| **Discovery** | **3. Architect** | Ratifies surgical contracts & boundaries | `read_interface_contract`, `draft_blueprint` | Direct file editing |
| **Craftsmen** | **4. Test Crafter** | Synthesizes failing tests first (TDD) | `create_test_file`, `verify_syntax` | Modifying production source |
| **Craftsmen** | **5. Surgeon** | Generates minimal atomic changesets | `read_target_slice`, `apply_diff` | Broad directory search, shell commands |
| **Craftsmen** | **6. Sentinel** | AST linter blocking fake imports/APIs | `ast_import_linter` | Modifying code |
| **Governance**| **7. Judge** | Runs pytest & enforces $R = B \setminus P$ | `run_sandbox_tests`, `git_rollback` | Direct source modification |
| **Governance**| **8. Critic** | Audits code cleanliness & cyclomatic complexity | `audit_cleanliness` | Modifying code |
| **Governance**| **9. Scribe** | Compiles executive RCA dossier & citations | `compile_markdown_report` | Modifying code |

---

## 4. How Aether-SWE Nails the Hackathon Rubric

| Rubric Criteria | Score Weight | How Aether-SWE Guarantees It |
| :--- | :--- | :--- |
| **Pass Hidden Tests** | **30 Points** | **Test Crafter** synthesizes multi-vector boundary/stress tests; the UI includes an explicit **"Evaluate Hidden Tests"** drop-in slot for judges to test secret suites live. |
| **Zero Regressions** | **Major Penalty** | **Judge** records baseline passing test IDs before any edits. Mathematical invariant $R = B \setminus P$ guarantees zero broken prior workflows; auto-rollbacks on any failure. |
| **No Hallucinated APIs/Imports** | **Strict Rule** | **Sentinel** AST parser validates all `import` and `from ... import` statements against declared symbols and requirements before tests ever execute. |
| **Understands the Codebase** | High | **Cartographer** maps symbols across files in < 1,500 tokens; **Detective** pinpoints exact lines with > 95% confidence. |
| **Clean & Minimal Code** | High | **Surgeon** emits surgical diffs (+1 / -1 lines); **Critic** scores cleanliness and flags dead code. |
| **Explain the Bug (RCA)** | Required | **Scribe** produces a structured Root Cause Analysis report complete with line citations, timestamps, and confidence scores. |
| **Live Demonstration** | Required | Antigravity-grade dark-mode Web IDE with live streaming persona avatars, interactive diff inspector, and real-time test runner. |

---

## 5. Universal "Bring Your Own Model" (BYOM) Gateway

Aether-SWE is 100% model-agnostic. Plug in any provider in the Web UI:
- **Anthropic Claude:** Claude 3.5 Sonnet / Haiku via native Messages API.
- **OpenAI-Compatible:** OpenAI (GPT-4o), Groq, OpenRouter, Together AI, vLLM, LM Studio.
- **Local Air-Gapped (Ollama):** Local privacy models (`qwen2.5-coder:7b`, `llama3.1`) at `http://localhost:11434/v1`.
- **Deterministic Simulation:** Zero-token high-fidelity replay failsafe for reliable demo presentations.

---

## 6. Target Benchmark Codebase: `benchmarks/ecommerce_api`

Built-in multi-file Python service (FastAPI/Pydantic/Pytest) featuring **24 passing baseline unit tests**:
- `app/config.py`: Application secrets and token lifetime.
- `app/models/`: `user.py` and `order.py`.
- `app/auth/tokens.py`: Token generation, cryptographic verification, and expiration check (contains timezone bug).
- `app/auth/permissions.py`: Role-based access control engine.
- `app/services/order_service.py`: Order lifecycle and transactions.
- `tests/`: 24 baseline unit tests covering auth, orders, and permissions.

### The Documented Defect
In `app/auth/tokens.py`, `is_token_expired()` compares naive `datetime.now().timestamp()` instead of `datetime.now(timezone.utc).timestamp()`, causing false token invalidation across timezone offsets.

---

## 7. Quickstart & Installation

### Prerequisites
- Python 3.10+
- Linux, macOS, or Windows WSL

### 1-Click Launch (Web Command Center)
```bash
./run.sh
```
Open **`http://localhost:8080`** in your browser to access the Antigravity Command Center.

### Standalone CLI Execution
```bash
.venv/bin/python3 -m backend.cli --provider simulation
```

---

## 8. Sample Execution Trace & Evidence

```
$ .venv/bin/python3 -m backend.cli --provider simulation

  ✓ Baseline Established: 24/24 Tests Passing: Locked in 24 passing unit test signatures.
  💭 [Cartographer] Mapped 12 Python source files into AST skeleton.
  💭 [Detective] Pinpointed root cause: app/auth/tokens.py::is_token_expired (Lines 38-45). Confidence: 98.0%.
  💭 [Architect] Ratified Blueprint: 'Timezone-Aware UTC Token Expiration Alignment'.
  💭 [TestCrafter] Authored reproduction test at tests/test_utc_expiry.py (3 adversarial vectors).
  ⚡ [Surgeon] Applied atomic changeset across 1 file(s). (+1 / -1 lines).

─── SURGICAL PATCH PREVIEW ───
--- a/app/auth/tokens.py
+++ b/app/auth/tokens.py
@@ -38,6 +38,6 @@
-    now_ts = datetime.now().timestamp()
+    now_ts = datetime.now(timezone.utc).timestamp()

  ✓ [Sentinel] PASSED. Zero hallucinated imports or invented APIs.
  ✓ [Judge] Pytest run finished: 26/26 passed. Broken baseline tests: 0.

======================================================
  VERDICT: APPROVED ✅ Zero Regressions Guaranteed
  All 26 tests PASSED. Existing workflows preserved with 100% integrity.
======================================================

  ✓ [Critic] Code Cleanliness Score: 98/100. Complexity: O(1). Minimal diff verified.
  ✓ [Scribe] Root Cause Analysis dossier authored and formatted with test proof and citations.
```

---

## 9. Scope Note (Submission Guidelines)

- **Minimum Viable Product (MVP):** 
  - Complete 9-Persona state machine pipeline with typed Pydantic handoffs.
  - AST Cartography and Token Skeletonizer (< 1,500 tokens).
  - TDD reproduction test synthesizer.
  - Pre-execution AST import bouncer (Sentinel).
  - Isolated subprocess test sandbox with mathematical regression detection ($R = B \setminus P$).
  - Antigravity Command Center Web IDE with SSE streaming, diff visualizer, and test matrix.
  - Universal BYOM settings drawer supporting Claude, OpenAI, and Local Ollama.
- **Stretch Goals:**
  - Automated multi-file blast-radius dependency clustering.
  - Per-persona heterogeneous model routing (fast local models for Cartographer, frontier reasoning models for Surgeon).

---

## 10. Repository Documentation Links

- 📄 [Product Requirements Document (PRD)](docs/PRD.md)
- 📐 [System Architecture Document](docs/ARCHITECTURE.md)
