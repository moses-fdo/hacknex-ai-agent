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
- **Refuse Emoji Glyphs as Icons:** No Unicode emojis (`📁`, `🔵`, `🌿`, `🔀`, `🎤`) acting as makeshift UI icons. Every icon is an authored, uniform 1.5px-stroke SVG icon (Lucide / Heroicons style).
- **Refuse Consumer Novelty Buttons:** No voice dictation microphone icon in a code engineering harness. Engineers paste stack traces or press `⌘ + Enter`.
- **Refuse Monospace as a Decorative Costume:** Monospace is reserved exclusively for code, file paths, diffs, git commit SHAs, and token metrics. All UI chrome, navigation, buttons, and labels use clean, tightly spaced proportional sans typography.
- **Refuse Fake OS Chrome:** No faux macOS traffic-light window dots or simulated desktop borders. This is a clean, full-bleed, edge-to-edge modern web application.

---

## 2. Layout Architecture & Workspace States

The interface operates in two primary states:
1. **Dispatch & Triage State (Idle):** Focused launcher with structured issue anchors, repository health checks, and 1-click preset challenges.
2. **Command Center State (Active Execution):** Multi-pane split view tracking the specialist pipeline route, multi-file diff inspector, Judge regression terminal, and grounded memory graph.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  AETHER-SWE  │  📁 benchmarks/ecommerce_api ⌄  │  🌿 main ⌄  │  🔀 aether/run-42  │  Budget: $0.14/$1.00│
├──────────────────────────────┬─────────────────────────────────────────────────────────────────────────┤
│  REPOSITORIES & WORKTREES    │  ISSUE & REPRODUCTION DISPATCHER                                        │
│                              │                                                                         │
│  ▼ ecommerce_api             │  [⚡ Preset: Ecommerce Timezone Bug]  [+ Paste Trace]  [🔗 GitHub Issue] │
│    ● fix-tz-offset (Active)  │  ┌────────────────────────────────────────────────────────────────────┐ │
│    ○ fix-role-alloc (Merged) │  │ Symptoms: Token expiry check fails in non-UTC timezone             │ │
│                              │  │ Anchors: app/auth/tokens.py::is_token_expired                      │ │
│  ▼ auth-service              │  │                                                                    │ │
│    ○ fix-jwt-signature       │  │                                                                    │ │
│                              │  │ ⚙️ Gemini 3.5 Flash ⌄   🔀 New Worktree ⌃   [ Run Agent  ⌘↵ ]      │ │
│  GROUNDED MEMORY             │  └──────────────────────────────────┬─────────────────────────────────┘ │
│  🧠 14 symbols, 2 rules      │                                     │ 🔀 Isolated Worktree [Safe]     │ │
│                              │                                     │ 💻 Local Working Tree [Unsafe]  │ │
│  PREFLIGHT HEALTH            │                                     └─────────────────────────────────┘ │
│  Docker: OK · Pytest: 24/24  │                                                                         │
└──────────────────────────────┴─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Specifications

### 3.1 The Dispatcher (Launcher Card)
Instead of a vague chat box, the launcher is a high-speed issue staging ground:

1. **One-Click Anchor Injectors (Top Pills):**
   - `[ ⚡ Preset: Ecommerce Timezone Bug ]` (Instantly loads benchmark issue, target file, and non-UTC test requirement).
   - `[ + Paste Stack Trace ]` (Opens auto-formatting modal that extracts file paths and line anchors).
   - `[ 🔗 GitHub Issue URL ]` (Imports description, labels, and issue title).

2. **Structured Issue Input Area:**
   - Multi-line editor with syntax highlighting for code snippets and stack traces.
   - Placeholder: *"Describe the defect or paste stack trace. Anchor to at least one file, function, or error message..."*
   - **Inline Stage 1 Triage Feedback:**
     - If the input contains a symptom + expected/actual + anchor: Displays green pill `✓ Triage: Anchors verified (app/auth/tokens.py)`.
     - If anchors are missing: Displays inline amber alert: `⚠️ Missing anchor. Select subsystem: [app/auth] [app/models] [app/services]` before running.

3. **Bottom Execution Toolbar:**
   - **Model Selector Pill:** Displays active model and token pricing (e.g. `Gemini 3.5 Flash ($0.15/1M) ⌄`, `Claude 3.5 Sonnet ($3.00/1M) ⌄`, `Ollama ($0.00/1M) ⌄`).
   - **Worktree Isolation Dropdown:**
     - Label: `🔀 New Worktree ⌃`
     - Popover options:
       - `🔀 Isolated Worktree: ../aether-<run-id> [Recommended]`
         *(Runs in clean worktree from HEAD. Active editor files and uncommitted changes are 100% safe).*
       - `💻 Local Working Tree [Unsafe]`
         *(Executes in place; triggers git reset --hard on rollback).*
   - **Target Branch Picker:** `🌿 main ⌄`
   - **Primary Action Button:** `[ Run Agent  ⌘↵ ]` (High-contrast, keyboard-first trigger with spinner when running).

---

### 3.2 Engineering Sidebar (Left Navigation, Width: 260px)
Grounded purely in repository truth and git state:

1. **Top Actions:**
   - `[ + New Task ]` (Primary shortcut button).
   - `[ ⚡ Benchmark Suite ]` (Runs full test suite across target challenge presets).

2. **Repositories & Worktrees Tree:**
   - Folders for active projects (e.g., `benchmarks/ecommerce_api`).
   - Child worktrees:
     - `● aether/fix-tz-offset` (Active run indicator: spinning SVG ring, active persona badge `Judge`).
     - `○ aether/fix-role-alloc` (Closed run: checkmark, duration `42s`, cost `$0.14`).

3. **Grounded Memory Panel:**
   - Displays persistent facts stored in `.aether/memory_graph.json`:
     - `14 code symbols indexed`
     - `2 verified architectural rules`
     - `1 past Judge veto logged`
   - Quick button: `[ Inspect Graph ]`.

4. **Preflight Environment Card (Bottom Sidebar):**
   - `Docker: Connected (2 containers running)`
   - `Python: 3.11.8 (virtualenv active)`
   - `Baseline Tests: 24/24 passing (0 flaky)`
   - Status: `Environment Ready ✅`

---

### 3.3 The Command Center (Active Execution Layout)
When a task begins, the central stage dynamically transforms into the multi-pane developer console:

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
   - Displays real-time progress across specialists.
   - Badges indicate specialist type: `[LLM]` in subtle blue pill, `[TOOL]` in neutral gray pill.
   - Active specialist displays a smooth pulsing border and elapsed time counter.

2. **Left Pane: Live Event Stream (Width: 320px):**
   - Server-Sent Events (SSE) feed of model thoughts, tool calls, and results.
   - Compact 3-line summaries up; full logs written to disk (`log_path` clickable link).

3. **Center Pane: Multi-File Diff Inspector (Fluid):**
   - Tabbed headers for each touched file (strictly scope-guarded $\le 5$ files).
   - Side-by-side or unified diff toggle.
   - Real syntax highlighting with distinct addition (`#34D399` on `rgba(16,185,129,0.12)`) and deletion (`#F87171` on `rgba(239,68,68,0.12)`) styling.
   - Critic cleanliness score badge (`Score: 96/100 · Minimal Slice`).

4. **Right Pane: Judge & Grounded Memory Terminal (Width: 360px):**
   - **Top Half (Judge):** Real-time test output, reproduction test status (`FAILED before patch` $\rightarrow$ `PASSED after patch`), and prominent **Regressions: 0** verification badge.
   - **Bottom Half (Memory Graph):** Subgraph showing active symbol contracts and verified past decisions.

5. **Bottom Telemetry & Action Bar (Height: 48px):**
   - **Active Worktree:** `🔀 ../aether-fix-tz (Branch: aether/fix-tz)`
   - **Cost Tracker:** Real-time dollar spent meter (`$0.16 / $1.00`) with visual fill bar (turns amber at 80%).
   - **Reserve Indicator:** Confirms 10% budget is held in reserve for Scribe post-mortem.
   - **Action Trigger:** `[ Review & Merge Diff ]` button (Opens git branch diff; **never auto-merges**).

---

## 4. Strict Design Tokens (Craft Floor)

### 4.1 Typography Scale
- **Proportional UI Face:** `-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif`
- **Monospace Code/Data Face:** `"JetBrains Mono", "SF Mono", "Fira Code", monospace`

| Role | Font Family | Size | Weight | Line Height | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **View Title** | Proportional | `16px` | `600` | `22px` | Header labels, drawer titles |
| **Section Label**| Proportional | `11px` | `600` | `16px` | `REPOSITORIES`, `PREFLIGHT` (letter-spacing `0.06em`) |
| **Body Primary** | Proportional | `14px` | `400` | `20px` | Issue descriptions, instructions |
| **Button / Tag** | Proportional | `13px` | `500` | `18px` | Actions, dropdown pills, model names |
| **Code / Diff** | Monospace | `12px` | `400` | `18px` | Unified diffs, AST signatures, stack traces |
| **Metric / Num** | Monospace | `11px` | `500` | `16px` | Cost counters, line numbers, test counts |

### 4.2 Semantic Color Tokens

```css
:root {
  /* Surfaces */
  --surface-canvas: #FFFFFF;
  --surface-sidebar: #F9FAFB;
  --surface-card: #F3F4F6;
  --surface-card-hover: #E5E7EB;
  --surface-popover: #FFFFFF;
  --surface-terminal: #0F1117;
  --surface-terminal-header: #1A1D27;

  /* Borders (Strict 1px Crisp Neutral) */
  --border-subtle: #E5E7EB;
  --border-card: #E2E4E8;
  --border-terminal: #2A2F3D;

  /* Text */
  --text-primary: #111827;
  --text-secondary: #4B5563;
  --text-muted: #9CA3AF;
  --text-inverted: #FFFFFF;

  /* Accents & States */
  --accent-primary: #2563EB;       /* Focus rings, primary buttons */
  --accent-primary-hover: #1D4ED8;
  --status-success: #10B981;      /* Zero regressions, passing tests */
  --status-warning: #F59E0B;      /* 80% budget, provisional memory */
  --status-error: #EF4444;        /* Judge veto, environment failure */

  /* Diff Syntax Colors */
  --diff-add-bg: rgba(16, 185, 129, 0.12);
  --diff-add-text: #059669;
  --diff-del-bg: rgba(239, 68, 68, 0.12);
  --diff-del-text: #DC2626;

  /* Elevation (Soft Offset, Zero Halos) */
  --shadow-card: 0 1px 3px rgba(0, 0, 0, 0.04), 0 2px 8px rgba(0, 0, 0, 0.02);
  --shadow-popover: 0 8px 24px -4px rgba(0, 0, 0, 0.08), 0 2px 6px -1px rgba(0, 0, 0, 0.04);
}
```

---

## 5. Micro-Interactions & Interaction States

1. **State Completeness:**
   Every button and input control explicitly specifies:
   - `default`: Clean 1px border with soft neutral background.
   - `hover`: Subtle surface tint (`var(--surface-card-hover)`), `150ms ease-out`.
   - `focus-visible`: `2px solid var(--accent-primary)` with `2px` offset.
   - `active`: Slight scale `0.99` with darkened border.
   - `disabled`: Opacity `0.4`, `cursor: not-allowed`.
   - `loading`: Inline spinning line-ring (no blocking full-screen loaders).

2. **Keyboard First Ergonomics:**
   - `⌘ + Enter` / `Ctrl + Enter`: Dispatches active run from launcher.
   - `Escape`: Closes popovers, cancels active suggestion menus.
   - `Tab` / `Shift + Tab`: Predictable focus flow through controls.

---

## 6. Frontend File Architecture

```
frontend/
├── index.html              # Full-bleed application shell
├── css/
│   ├── design-tokens.css   # Strict craft floor color, type, and spacing tokens
│   ├── layout.css          # Responsive sidebar + split command center grid
│   ├── components.css      # Dispatcher card, preset pills, dropdown menus
│   ├── command-center.css  # Pipeline route stepper, telemetry bar, judge terminal
│   └── diff-viewer.css     # Unified & side-by-side syntax-highlighted diff engine
└── js/
    ├── app.js              # Application state, router, and keyboard handlers
    ├── sse-client.js       # Live SSE stream consumer & log dispatcher
    ├── worktree-manager.js # Git worktree selector & branch isolation manager
    ├── diff-viewer.js      # Unified/side-by-side diff renderer
    └── memory-graph.js     # Grounded memory graph explorer
```
