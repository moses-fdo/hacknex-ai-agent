# Design System & UI Specification: Aether-SWE Command Center

**Mode:** Operate (High-Precision Developer Tool)  
**Standard:** Anti-Slop Craft Floor (Impeccable v4.3)  
**Target File:** `DESIGN.md`

---

## 1. Design Paradigm & Anti-Slop Manifesto

Aether-SWE is an autonomous software engineering engine with deterministic code gates, isolated git worktrees, and regression guarantees. It is **not** a conversational consumer chatbot.

### What We Refuse (Anti-Slop):
- **Refuse the Empty Chatbot Trap:** No giant blank screen asking *"Ask me anything"*. A developer needs clear inputs: symptoms, stack traces, target repositories, and 1-click benchmark challenges.
- **Refuse Conversational Markdown Streams:** We do not render 500-line chat bubbles of conversational text. The agent executes real git commands, runs pytest, checks AST signatures, and generates unified diffs. The UI is an **IDE-grade multi-pane Command Center**.
- **Refuse Emoji Glyphs as Functional UI Icons:** No bare Unicode emojis (`📁`, `🔵`, `🌿`, `🔀`, `🎤`) masquerading as primary navigation or action icons. Interactive controls and UI chrome use crisp, authored 1.5px-stroke SVG icons (Lucide / Heroicons / VS Code Codicons style). Monospace badges and status indicators use clear textual labels.
- **Refuse Consumer Novelty Buttons:** No voice dictation microphone icon in a code engineering harness. Engineers paste stack traces or press `⌘ + Enter`.
- **Refuse Monospace as a Decorative Costume:** Monospace is reserved exclusively for code, file paths, diffs, git commit SHAs, AST symbols, and token metrics. All UI chrome, navigation, buttons, and labels use clean, tightly spaced proportional sans typography.
- **Refuse Fake OS Chrome:** No faux macOS traffic-light window dots or simulated desktop borders. This is a clean, full-bleed, edge-to-edge modern developer application adhering to professional dark IDE conventions.

---

## 2. Layout Architecture & Workspace States

The interface operates across three coherent workspace lifecycle states:

1. **Workspace Cartography & Decision Onboarding State:**  
   Triggered automatically whenever a new folder is selected (via native OS folder dialog, File menu, or preset benchmark). The Codebase Cartographer reads all codebase files across multiple languages (Python, JS/TS, HTML, CSS, JSON, YAML, TOML, Shell, Dockerfiles), mines core architectural patterns and invariant rules, populates `.aether/memory_graph.json`, and synthesizes `HOW_IT_WORKS.md`. The UI reflects this with real-time status telemetry, hydrates the titlebar badges (`[🧠 X Decisions]`, `[📖 HOW_IT_WORKS.md]`), updates the sidebar memory counts, and opens `HOW_IT_WORKS.md` directly in the editor tab.

2. **Dispatch & Triage State (Idle):**  
   Focused launcher with structured issue anchors, repository health checks, 1-click preset challenges, and folder open trigger.

3. **Command Center State (Active Execution):**  
   Multi-pane split view tracking the specialist pipeline route, multi-file diff inspector, Judge regression terminal, and grounded memory graph.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  [≡] File Edit Selection View Run Terminal Help │ [ ecommerce_api - Aether-SWE Studio ] [🧠 6 Decisions] [📖 HOW_IT_WORKS.md] │ 🗕 🗖 ✕ │
├────┬─────────────────────────────┬─────────────────────────────────────────────────────────────────────┤
│ 📄 │ EXPLORER                    │ ISSUE & REPRODUCTION DISPATCHER                                     │
│    │                             │                                                                     │
│ 🔍 │ ▼ OPEN EDITORS              │ ┌─ Aether-SWE Autonomous Dispatcher ────── [ Open Local Folder... ]┐│
│    │   HOW_IT_WORKS.md           │ │                                                                  ││
│ 🌿 │                             │ │ [⚡ Preset: Ecommerce Timezone Bug]  [+ Paste Trace]  [🔗 Issue]    ││
│    │ ▼ ECOMMERCE_API             │ │ ┌──────────────────────────────────────────────────────────────┐ ││
│ ▶  │   ▶ app                     │ │ │ Symptoms: Token expiry check fails in non-UTC timezone       │ ││
│    │   ▶ tests                   │ │ │ Anchors: app/auth/tokens.py::is_token_expired                │ ││
│ ⚙  │   📄 HOW_IT_WORKS.md        │ │ │                                                              │ ││
│    │                             │ │ │ ⚙️ Gemini 3.5 Flash ⌄   🔀 New Worktree ⌃   [ Run Agent  ⌘↵ ]│ ││
│    │ ▼ GROUNDED FACT MEMORY      │ │ └──────────────────────────────────────────────────────────────┘ ││
│    │   Path: .aether/memory_...  │ └──────────────────────────────────────────────────────────────────┘│
│    │   Decisions: 6 Mapped       │                                                                     │
│    │   Nodes: 18 Indexed         │                                                                     │
│    │   [📖 Open HOW_IT_WORKS.md] │                                                                     │
│    │   [🧠 Inspect Decision Graph│                                                                     │
│    │   [⚡ Re-analyze Codebase]  │                                                                     │
└────┴─────────────────────────────┴─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Specifications

### 3.1 Custom Titlebar & Launcher Card

#### 1. Custom Titlebar (Height: 35px)
- **Left Zone:**
  - Hamburger application menu button (`#hamburgerBtn`).
  - Standard desktop dropdown menus (`File`, `Edit`, `Selection`, `View`, `Run`, `Terminal`, `Help`) styled with VS Code dark theme elevation and keyboard shortcuts (`Ctrl+O`, `Ctrl+K Ctrl+O`, `Ctrl+N`, `Ctrl+Shift+E`, etc.).
- **Center Zone:**
  - Workspace Search / Title Pill: Displays active project directory (e.g. `ecommerce_api - Aether-SWE Studio`).
  - **Decision Count Badge Button (`#btnTopbarDecisions`):**  
    Displays `[🧠 X Decisions]` with live count hydration. Clicking opens the **Grounded Architectural Decisions & Memory Graph Modal (`#decisionsModal`)**.
  - **Project Manual Badge Button (`#btnTopbarHowItWorks`):**  
    Displays `[📖 HOW_IT_WORKS.md]`. Clicking opens or focuses the synthesized project architecture manual in the editor workspace.
- **Right Zone:**
  - Native-style window controls: Minimize (`🗕`), Maximize/Restore (`🗖`), and Close (`✕`).

#### 2. The Dispatcher (Launcher Card)
Instead of a vague chat box, the launcher is a high-speed issue staging ground:
- **One-Click Anchor Injectors (Top Pills):**
  - `[ ⚡ Preset: Ecommerce Timezone Bug ]` (Instantly loads benchmark issue, target file, and non-UTC test requirement).
  - `[ + Paste Stack Trace ]` (Opens auto-formatting modal that extracts file paths and line anchors).
  - `[ 🔗 GitHub Issue URL ]` (Imports description, labels, and issue title).
  - `[ Open Local Folder... ]` (`#btnMainOpenFolder`): Native folder dialog trigger to onboard any local repository.
- **Structured Issue Input Area:**
  - Multi-line editor with syntax highlighting for code snippets and stack traces.
  - Placeholder: *"Describe the defect or paste stack trace. Anchor to at least one file, function, or error message..."*
  - **Inline Stage 1 Triage Feedback:**
    - If input contains symptom + expected/actual + anchor: Displays green pill `✓ Triage: Anchors verified (app/auth/tokens.py)`.
    - If anchors are missing: Displays inline amber alert: `⚠️ Missing anchor. Select subsystem: [app/auth] [app/models] [app/services]` before running.
- **Bottom Execution Toolbar:**
  - **Model Selector Pill:** Displays active model and token pricing (e.g. `Gemini 3.5 Flash ($0.15/1M) ⌄`, `Claude 3.5 Sonnet ($3.00/1M) ⌄`, `Ollama ($0.00/1M) ⌄`).
  - **Worktree Isolation Dropdown:**
    - Label: `🔀 New Worktree ⌃`
    - Popover options:
      - `🔀 Isolated Worktree: ../aether-<run-id> [Recommended]` *(Runs in clean worktree from HEAD; active working tree is safe).*
      - `💻 Local Working Tree [Unsafe]` *(Executes in place; triggers git reset --hard on rollback).*
  - **Target Branch Picker:** `🌿 main ⌄`
  - **Primary Action Button:** `[ Run Agent  ⌘↵ ]` (High-contrast, keyboard-first trigger with spinner when running).

---

### 3.2 Engineering Sidebar (Left Navigation, Width: 260px)

Grounded purely in repository truth and git state:

1. **Activity Bar (48px Left Strip):**
   - High-contrast SVG action buttons for `Explorer`, `Search`, `Source Control`, `Testing`, and `Aether Copilot`.

2. **Explorer View Pane:**
   - **Open Editors Accordion:** Lists open workspace tabs with active indicators and close buttons.
   - **Workspace Tree Accordion:** Full interactive file explorer with folders, files, and file-open handlers.
   - **Grounded Fact Memory Accordion:**
     - Storage file path: `<code style="color: #cccccc;">.aether/memory_graph.json</code>`.
     - Live metric counts:
       - `Decisions Mapped: <strong id="sidebarDecisionsCount">6</strong>` (cyan `#38BDF8`).
       - `Total Nodes: <span id="sidebarTotalNodes">18</span>` (neutral `#cccccc`).
       - `Verified Invariants: <span id="sidebarVerifiedCount">4</span>` (emerald `#3fb950`).
     - Action buttons:
       - `[ 📖 Open HOW_IT_WORKS.md ]`: Opens the generated architecture manual.
       - `[ 🧠 Inspect Decision Graph ]`: Launches the `#decisionsModal` overlay.
       - `[ ⚡ Re-analyze Codebase ]`: Re-reads the codebase on demand and regenerates memory artifacts.

3. **Source Control & Git Pane:**
   - Displays current branch, isolated worktree status, and working tree diff status.

4. **Testing & Regressions Pane:**
   - Baseline Pytest suite runner, individual test suite list, and regression status.

---

### 3.3 The Command Center (Active Execution Layout)

When a repair task begins, the central stage dynamically transforms into the multi-pane developer console:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  ROUTE: Triage ✓ ➔ Preflight ✓ ➔ Cartographer ✓ ➔ Detective ✓ ➔ Architect ✓ ➔ Surgeon ● ➔ Judge ➔ Scribe│
├──────────────────────────────┬──────────────────────────────────────────┬──────────────────────────────┤
│  LIVE TELEMETRY & SSE        │  MULTI-FILE DIFF INSPECTOR               │  JUDGE & REGRESSION GATE     │
│  ──────────────────────────  │  ─────────────────────────────────────── │  ─────────────────────────── │
│  [11:02:04] Cartographer:    │  [ 📁 app/auth/tokens.py ] [ app/config ]│  Preflight Baseline: 24 pass │
│    Indexed 6 files, 18 funcs │  @@ -38,7 +38,8 @@                      │  Reproduce Test: 1 FAIL (OK) │
│  [11:02:08] Detective:       │  -  now = datetime.utcnow().timestamp()  │                              │
│    Located tokens.py:L40     │  +  now = datetime.now(timezone.utc)     │  Post-Patch Suite: 25 pass   │
│  [11:02:12] Test Crafter:    │  +             .timestamp()              │  Regressions: 0 (ZERO) ✅    │
│    Wrote test_tz_offset()    │                                          │                              │
│    Pre-fix test: FAILED ❌   │  Cleanliness Score: 96/100               │  Flaky Excluded: 0           │
│  [11:02:16] Surgeon:         │  Diff: +2 / -1 lines (Minimal Slice)     │  Worktree: Clean             │
│    Applying step 1/1 in WT   │                                          │                              │
├──────────────────────────────┴──────────────────────────────────────────┴──────────────────────────────┤
│  WORKTREE: ../aether-fix-tz  │  SPEND: $0.16 / $1.00 (16%)  │  RESERVE: 10% Scribe  │  [ Review & Merge ]│
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Multi-Pane Breakdown:
1. **Pipeline Stepper (Top Strip, Height: 44px):**
   - Displays real-time progress across specialists (`Triage` $\rightarrow$ `Preflight` $\rightarrow$ `Cartographer` $\rightarrow$ `Detective` $\rightarrow$ `Architect` $\rightarrow$ `Surgeon` $\rightarrow$ `Judge` $\rightarrow$ `Scribe`).
   - Badges indicate specialist type: `[LLM]` in subtle blue pill, `[TOOL]` in neutral gray pill.
   - Active specialist displays a smooth pulsing border and elapsed time counter.

2. **Left Pane: Live Event Stream (Width: 320px):**
   - Server-Sent Events (SSE) feed of model thoughts, tool calls, and results.
   - Compact summaries rendered real-time; full logs written to disk (`log_path` clickable link).

3. **Center Pane: Multi-File Diff Inspector (Fluid):**
   - Tabbed headers for each touched file (strictly scope-guarded $\le 5$ files).
   - Side-by-side or unified diff toggle.
   - Real syntax highlighting with distinct addition (`#34D399` on `rgba(16,185,129,0.12)`) and deletion (`#F87171` on `rgba(239,68,68,0.12)`) styling.
   - Critic cleanliness score badge (`Score: 96/100 · Minimal Slice`).

4. **Right Pane: Judge & Grounded Memory Terminal (Width: 360px):**
   - **Top Half (Judge):** Real-time test output, reproduction test status (`FAILED before patch` $\rightarrow$ `PASSED after patch`), and prominent **Regressions: 0** verification badge.
   - **Bottom Half (Memory Graph & Decisions Sub-panel):** Displays active symbol contracts, verified past decisions, and a one-click `[ Inspect All Decisions ]` button opening `#decisionsModal`.

5. **Bottom Telemetry & Action Bar (Height: 48px):**
   - **Active Worktree:** `🔀 ../aether-fix-tz (Branch: aether/fix-tz)`
   - **Cost Tracker:** Real-time dollar spent meter (`$0.16 / $1.00`) with visual fill bar (turns amber at 80%).
   - **Reserve Indicator:** Confirms 10% budget is held in reserve for Scribe post-mortem.
   - **Action Trigger:** `[ Review & Merge Diff ]` button (Opens git branch diff; **never auto-merges**).

---

### 3.4 Grounded Architectural Decisions & Memory Graph Modal (`#decisionsModal`)

The Decisions Modal provides interactive inspection into the repository's architectural knowledge base, ensuring human engineers and autonomous agents share identical structural ground truth:

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ Grounded Architectural Decisions & Memory Graph    [ ecommerce_api ]                  [✕] │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Graph Store: .aether/memory_graph.json ────────────── [📖 HOW_IT_WORKS] [⚡ Re-analyze] ┐│
│ │ 6 Grounded Decisions · 18 Nodes · Invariants Enforced                                   ││
│ └─────────────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                           │
│ [ All ]  [ Security & Auth ]  [ Framework ]  [ Data Layer ]  [ Testing ]  [ Architecture ]│
│                                                                                           │
│ ┌─ Framework & API Engine ────────────────────────────────────── [ FRAMEWORK & ARCH ] ────┐│
│ │ Fast, async REST API engine built with FastAPI and Starlette.                           ││
│ │                                                                                         ││
│ │ ┌─ Invariant Rules ───────────────────────────────────────────────────────────────────┐ ││
│ │ │ ⚠️  Asynchronous route handlers for all I/O bound endpoints                          │ ││
│ │ └─────────────────────────────────────────────────────────────────────────────────────┘ ││
│ │ Files: [ app/main.py ]  [ app/routes.py ]                                               ││
│ └─────────────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                           │
│ ┌─ Cryptographic JWT Token Architecture ─────────────────────────── [ SECURITY & AUTH ] ──┐│
│ │ Stateless authentication tokens with HMAC-SHA256 signature verification.                ││
│ │                                                                                         ││
│ │ ┌─ Invariant Rules ───────────────────────────────────────────────────────────────────┐ ││
│ │ │ ⚠️  All timestamps MUST use timezone-aware UTC datetime.now(timezone.utc).timestamp()│ ││
│ │ │ ⚠️  Never use deprecated or timezone-naive datetime.utcnow()                         │ ││
│ │ └─────────────────────────────────────────────────────────────────────────────────────┘ ││
│ │ Files: [ app/auth/tokens.py ]  [ app/auth/jwt.py ]                                      ││
│ └─────────────────────────────────────────────────────────────────────────────────────────┘│
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ Aether-SWE Grounded Memory · Invariants enforced across all workers              [ Close ]│
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Modal Specifications:
1. **Dimensions & Positioning:** Fixed overlay with soft backdrop blur (`rgba(0,0,0,0.65)`, `backdrop-filter: blur(2px)`). Modal dialog width: `780px` (`max-width: 92vw`), height: `85vh` (`max-height: 85vh`), vertically centered.
2. **Summary Banner:** Highlights active `.aether/memory_graph.json` path, total decisions count, and direct action triggers for `[📖 HOW_IT_WORKS.md]` and `[⚡ Re-analyze Codebase]`.
3. **Category Filter Bar:** Dynamic horizontal filter pills (`All`, `Security & Auth`, `Framework & Architecture`, `Data & Modeling`, `Testing & QA`) with active state highlight (`#007acc`).
4. **Decision Cards (`.decision-card`):**
   - **Header:** Decision title (`13px`, weight `600`, color `#e0e0e0`) and category badge with semantic pastel color tokens:
     - `framework`: `rgba(56, 189, 248, 0.15)` bg / `#38BDF8` text (Cyan)
     - `security`: `rgba(239, 68, 68, 0.15)` bg / `#f87171` text (Coral Red)
     - `data`: `rgba(168, 85, 247, 0.15)` bg / `#c084fc` text (Purple)
     - `testing`: `rgba(34, 197, 94, 0.15)` bg / `#4ade80` text (Emerald)
     - `architecture`: `rgba(245, 158, 11, 0.15)` bg / `#fbbf24` text (Amber)
   - **Description:** Concise architectural rationale and design context (`12px`, color `#a0a0a0`).
   - **Invariants Box (`.decision-rules-box`):** Dark recessed background (`#181818`), left accent border (`3px solid #007acc`), listing strict coding invariants extracted from AST analysis and repository comments.
   - **Associated File Pills (`.decision-file-pill`):** Clickable monospace pills (`JetBrains Mono`, `10px`, `#9cdcfe`) with hover state (`#38BDF8` border) that immediately open the file in the editor workspace and dismiss the modal.

---

### 3.5 Project Architecture Manual (`HOW_IT_WORKS.md`)

Automatically synthesized by the Cartographer upon folder onboarding and refreshed on demand:
- **Location:** Project root (`HOW_IT_WORKS.md`) and `.aether/HOW_IT_WORKS.md`.
- **Content Sections:**
  1. **Executive Summary:** Repository purpose, architecture model, and entry point.
  2. **Core Technology Stack Table:** Frameworks, languages, database/ORM, and testing harness.
  3. **Grounded Architectural Decisions:** Key patterns extracted and mapped into the memory graph.
  4. **Directory Structure & Component Roles:** File tree map detailing the specific responsibility of every source file.
  5. **Execution & Data Lifecycle Flow:** Step-by-step request/execution trace through the codebase.
  6. **Critical Architectural Invariants:** Non-negotiable coding rules enforced during agent code generation.
  7. **Running & Testing Commands:** Verified local execution commands (dev server, baseline pytest suite).
- **Editor Presentation:** Displays in the main editor tab area (`#codeEditorView`) with syntax-highlighted markdown, formatted tables, and read-only / editable toggle.

---

## 4. Strict Design Tokens (Craft Floor)

### 4.1 Typography Scale
- **Proportional UI Face:** `-apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", Roboto, sans-serif`
- **Monospace Code/Data Face:** `"JetBrains Mono", Consolas, "SF Mono", "Fira Code", monospace`

| Role | Font Family | Size | Weight | Line Height | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Window / Header Title** | Proportional | `13px` | `500` | `18px` | Titlebar workspace name, menu labels |
| **Section Label**| Proportional | `11px` | `600` | `16px` | `OPEN EDITORS`, `GROUNDED FACT MEMORY` (letter-spacing `0.05em`) |
| **Body Primary** | Proportional | `13px` | `400` | `18px` | Issue descriptions, instructions, modal text |
| **Button / Tag** | Proportional | `12px` | `500` | `16px` | Actions, dropdown pills, filter buttons |
| **Badge / Category** | Proportional | `10px` | `600` | `14px` | Category pills (`FRAMEWORK`, `SECURITY`), uppercase |
| **Code / Diff** | Monospace | `12px` | `400` | `18px` | Unified diffs, AST signatures, stack traces |
| **File Pill** | Monospace | `10px` | `400` | `14px` | Associated file paths in decision cards |
| **Metric / Num** | Monospace | `11px` | `500` | `16px` | Cost counters, line numbers, test counts |

### 4.2 Semantic Color Tokens (VS Code Dark Theme Foundation)

```css
:root {
  /* VS Code Dark Palette Surfaces */
  --vscode-bg: #1e1e1e;
  --vscode-sidebar: #252526;
  --vscode-activity-bar: #333333;
  --vscode-titlebar: #3c3c3c;
  --vscode-editor-bg: #1e1e1e;
  --vscode-terminal-bg: #181818;
  --vscode-card: #252526;
  --vscode-card-hover: #2a2d2e;

  /* Borders (Strict 1px Crisp Neutral) */
  --vscode-border: #3c3c3c;
  --vscode-border-dark: #2d2d2d;
  --vscode-input-border: #3c3c3c;
  --vscode-input-focus: #007acc;

  /* Text Hierarchy */
  --vscode-text-bright: #ffffff;
  --vscode-text-primary: #cccccc;
  --vscode-text-secondary: #a0a0a0;
  --vscode-text-muted: #858585;

  /* Primary Accent & VS Code Blue */
  --vscode-blue: #0e639c;
  --vscode-blue-hover: #1177bb;
  --vscode-accent: #007acc;

  /* Status Tokens */
  --status-success: #3fb950;       /* Passing tests, 0 regressions */
  --status-warning: #fbbf24;       /* Budget warnings, provisional memory */
  --status-error: #f87171;         /* Test failures, Judge vetoes */

  /* Decision Category Badges */
  --decision-badge-framework-bg: rgba(56, 189, 248, 0.15);
  --decision-badge-framework-text: #38BDF8;
  --decision-badge-security-bg: rgba(239, 68, 68, 0.15);
  --decision-badge-security-text: #f87171;
  --decision-badge-data-bg: rgba(168, 85, 247, 0.15);
  --decision-badge-data-text: #c084fc;
  --decision-badge-testing-bg: rgba(34, 197, 94, 0.15);
  --decision-badge-testing-text: #4ade80;
  --decision-badge-arch-bg: rgba(245, 158, 11, 0.15);
  --decision-badge-arch-text: #fbbf24;

  /* Diff Syntax Colors */
  --diff-add-bg: rgba(16, 185, 129, 0.12);
  --diff-add-text: #34D399;
  --diff-del-bg: rgba(239, 68, 68, 0.12);
  --diff-del-text: #F87171;

  /* Invariant Callouts */
  --callout-invariant-bg: #181818;
  --callout-invariant-border: #007acc;
}
```

---

## 5. Micro-Interactions & Interaction States

1. **State Completeness:**
   Every button and input control explicitly specifies:
   - `default`: Clean 1px border with neutral surface background.
   - `hover`: Subtle surface tint (`#2a2d2e` / `#1177bb`), `150ms ease-out`.
   - `focus-visible`: `1px solid var(--vscode-input-focus)` with no outline displacement.
   - `active`: Slight scale `0.99` with darkened border.
   - `disabled`: Opacity `0.4`, `cursor: not-allowed`.
   - `loading`: Inline spinning line-ring (no blocking full-screen loaders).

2. **Workspace Onboarding Transition:**
   - Folder selection triggers an immediate status indicator in the bottom status bar: `Scanning codebase & mining decisions...`.
   - On completion, topbar badges hydrate with count animations (`0` $\rightarrow$ `6 Decisions`).
   - Explorer tree automatically refreshes and `HOW_IT_WORKS.md` is appended to Open Editors.

3. **Decisions Modal Transitions:**
   - Backdrop fade-in `180ms ease-out` with subtle scale transition (`transform: translateY(8px) scale(0.98)` $\rightarrow$ `translateY(0) scale(1)`).
   - Category filter pill clicks filter visible cards with `120ms` opacity transition.
   - Clicking any `.decision-file-pill` dismisses the modal and opens that specific file in the editor.

4. **Keyboard-First Ergonomics:**
   - `⌘ + Enter` / `Ctrl + Enter`: Dispatches active repair run.
   - `Ctrl + O` / `Ctrl + K Ctrl+O`: Triggers folder onboarding dialog.
   - `Escape`: Closes active modal overlays (`#decisionsModal`, `#customEndpointModal`).
   - `Tab` / `Shift + Tab`: Predictable focus flow through controls.

---

## 6. Project File Architecture

```
hacknex-ai-agent/
├── backend/
│   ├── api/
│   │   └── server.py             # FastAPI server with /api/workspace/open & /api/workspace/decisions
│   ├── memory/
│   │   ├── codebase_analyzer.py  # Multi-language codebase reader & decision miner
│   │   └── graph_store.py        # Persistent grounded memory graph store (.aether/memory_graph.json)
│   ├── orchestrator/
│   │   └── engine.py             # Orchestrator with set_repo_path & onboard_repo hooks
│   ├── tools/
│   │   ├── cartographer.py       # AST symbol indexer & AST import graph
│   │   ├── judge.py              # Pytest sandbox, flaky test filter & regression gate
│   │   ├── preflight.py          # Environment, docker & virtualenv preflight check
│   │   ├── surgeon.py            # Atomic file patch applier
│   │   └── worktree.py           # Git worktree isolation manager
│   └── workers/                  # Specialist LLM workers (Triage, Detective, Architect, Crafter, Scribe)
├── benchmarks/
│   └── ecommerce_api/            # Reference benchmark target repository
├── frontend/
│   ├── index.html                # IDE application shell with custom titlebar & decisionsModal
│   ├── css/
│   │   ├── vscode-theme.css      # Dark IDE tokens, layout, decision cards & badges
│   │   └── command-center.css    # Multi-pane active execution grid & diff styles
│   └── js/
│       ├── app.js                # State management, folder picker, decision modal & editor
│       └── sse-client.js         # Real-time SSE telemetry consumer
├── docs/
│   ├── PRD Aether-SWE v1.1 (Orchestrator Edition).md  # Product Requirements Document
│   └── DESIGN.md                 # Mirrored design system specification
├── DESIGN.md                     # Root design system specification
└── package.json                  # Electron & frontend build definitions
```
