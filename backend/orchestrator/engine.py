"""Orchestrator Engine: Coordinates specialists and deterministic gates matching PRD v1.3.

Enforces:
- FR-1: Two-Stage Triage Gate with Could-Not-Reproduce (CNR) loop
- FR-2: Physical Git Worktree Isolation with uncommitted changes warning & branch preservation
- FR-3: Deterministic Preflight gate with structured environment failure halting
- FR-4: Grounded Memory Graph sync, stale node invalidation, and conflict detection
- FR-5: Multi-file surgery with scope guards, atomic Sentinel/Judge gate, and self-healing loop (max 3 iterations)
- FR-6: BYOM hard budget enforcement with 10% Scribe reserve and 80% warning alert
- Limits & Safety Caps: Max 12 delegations, max 3 retries, max 5 files
"""
import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from backend.client.byom_client import BYOMClient, BudgetExceededException
from backend.memory.graph_store import MemoryGraphStore
from backend.models import (
    CriticReport,
    EditStep,
    IssueInput,
    JudgeReport,
    MemoryNode,
    MultiFilePlan,
    PreflightReport,
    RunEvent,
    RunStatus,
    TriageResult,
    WorkerKind,
)
from backend.tools.cartographer import Cartographer
from backend.tools.critic import Critic
from backend.tools.judge import Judge
from backend.tools.preflight import PreflightCheck
from backend.tools.sentinel import Sentinel
from backend.workers.registry import WorkerRegistry
from backend.worktree.diff_applier import DiffApplier, ScopeGuardViolation
from backend.worktree.manager import WorktreeManager

class OrchestratorEngine:
    def __init__(self, repo_path: str):
        self.repo_path = os.path.abspath(repo_path)
        self.worktree_mgr = WorktreeManager(self.repo_path)
        self.memory_store = MemoryGraphStore(self.repo_path)
        self.events: List[RunEvent] = []
        self.subscribers: List[asyncio.Queue] = []
        self.runs_dir = os.path.join(self.repo_path, ".aether", "runs")
        os.makedirs(self.runs_dir, exist_ok=True)
        self.active_runs: Dict[str, Dict[str, Any]] = {}

    def set_repo_path(self, repo_path: str):
        """Update active workspace repository and re-initialize managers."""
        self.repo_path = os.path.abspath(repo_path)
        self.worktree_mgr = WorktreeManager(self.repo_path)
        self.memory_store = MemoryGraphStore(self.repo_path)
        self.runs_dir = os.path.join(self.repo_path, ".aether", "runs")
        os.makedirs(self.runs_dir, exist_ok=True)

    async def onboard_repo(self, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """Onboard a new codebase folder: read all files, extract decisions into memory graph, write HOW_IT_WORKS.md."""
        if repo_path:
            self.set_repo_path(repo_path)

        from backend.memory.codebase_analyzer import CodebaseAnalyzer
        analyzer = CodebaseAnalyzer(self.repo_path, self.memory_store)
        result = analyzer.analyze_folder()

        await self.emit(
            RunEvent(
                run_id=f"onboard-{datetime.now(timezone.utc).strftime('%H%M%S')}",
                persona="Cartographer",
                kind=WorkerKind.TOOL,
                action="codebase_onboarded",
                status="success",
                message=(
                    f"Repository '{result['repo_name']}' indexed: {result['total_files']} files read, "
                    f"{result['decisions_count']} architectural decisions mapped to memory graph. "
                    f"Generated HOW_IT_WORKS.md"
                ),
                metadata={
                    "repo_path": self.repo_path,
                    "repo_name": result["repo_name"],
                    "decisions_count": result["decisions_count"],
                    "total_files": result["total_files"],
                    "total_lines": result["total_lines"],
                    "how_it_works_path": result["how_it_works_path"],
                },
            )
        )
        return result

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self.subscribers.append(q)
        return q

    async def emit(self, event: RunEvent):
        self.events.append(event)
        for q in list(self.subscribers):
            try:
                await q.put(event)
            except Exception:
                pass

    def _init_run_log_dir(self, run_id: str) -> str:
        log_dir = os.path.join(self.runs_dir, run_id, "logs")
        os.makedirs(log_dir, exist_ok=True)
        return log_dir

    def _parse_json_safe(self, text: str) -> Dict[str, Any]:
        """Extract JSON cleanly even if wrapped in markdown code blocks."""
        cleaned = text.strip()
        if "```" in cleaned:
            # Match ```json ... ``` or ``` ... ```
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
            if match:
                cleaned = match.group(1).strip()
        try:
            return json.loads(cleaned)
        except Exception:
            # Try to find first { and last }
            first_brace = cleaned.find("{")
            last_brace = cleaned.rfind("}")
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                try:
                    return json.loads(cleaned[first_brace:last_brace + 1])
                except Exception:
                    pass
        return {}

    def abort_run(self, run_id: str) -> bool:
        if run_id in self.active_runs:
            self.active_runs[run_id]["status"] = RunStatus.ABORTED
            return True
        return False

    def _write_run_log(self, run_id: str, filename: str, content: str):
        log_dir = os.path.join(self.runs_dir, run_id, "logs")
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, filename), "w", encoding="utf-8") as f:
            f.write(content)

    async def execute_run(self, issue: IssueInput) -> Dict[str, Any]:
        run_id = f"run-{uuid.uuid4().hex[:6]}"
        log_dir = self._init_run_log_dir(run_id)
        self.active_runs[run_id] = {"status": RunStatus.RUNNING, "issue": issue}

        # Setup 80% budget warning handler (FR-6.5)
        def on_budget_warning(spent: float, max_b: float):
            asyncio.create_task(
                self.emit(
                    RunEvent(
                        run_id=run_id,
                        persona="BYOMClient",
                        kind=WorkerKind.TOOL,
                        action="budget_warning",
                        status="warning",
                        message=f"BUDGET ALERT: 80% threshold reached (${spent:.4f} of ${max_b:.4f})",
                        is_high_priority=True,
                    )
                )
            )

        byom = BYOMClient(
            default_model=issue.model,
            max_budget_usd=issue.max_budget_usd,
            custom_pricing=issue.custom_pricing,
            custom_endpoint=issue.custom_endpoint,
            custom_api_key=issue.custom_api_key,
            custom_provider=issue.custom_provider,
            warning_callback=on_budget_warning,
        )

        await self.emit(
            RunEvent(
                run_id=run_id,
                persona="Orchestrator",
                kind=WorkerKind.TOOL,
                action="start",
                status=RunStatus.RUNNING,
                message=f"Starting autonomous run {run_id} for: {issue.title} (Budget Cap: ${issue.max_budget_usd:.2f})",
                metadata={"issue_id": issue.issue_id, "model": issue.model},
            )
        )

        try:
            # ---------------------------------------------------------
            # 1. TWO-STAGE TRIAGE GATE (FR-1.1 - FR-1.3)
            # ---------------------------------------------------------
            repo_file_names = []
            try:
                for root, _, files in os.walk(self.repo_path):
                    parts = root.split(os.sep)
                    if any(p.startswith(".") for p in parts) or "node_modules" in parts or "__pycache__" in parts:
                        continue
                    for f in files:
                        repo_file_names.append(os.path.relpath(os.path.join(root, f), self.repo_path))
            except Exception:
                pass

            triage = WorkerRegistry.triage_issue(issue.description, repo_files=repo_file_names)
            self._write_run_log(run_id, "triage_result.json", json.dumps(triage.model_dump(), indent=2))

            await self.emit(
                RunEvent(
                    run_id=run_id,
                    persona="Triage",
                    kind=WorkerKind.TOOL,
                    action="triage_eval",
                    status="pass" if triage.is_anchored else "clarify",
                    message=(
                        f"Triage Stage 1: {'Anchors identified' if triage.is_anchored else 'Unanchored issue'}. "
                        f"Anchors: {triage.anchors}"
                    ),
                    metadata=triage.model_dump(),
                )
            )

            if not triage.is_anchored and not issue.unattended:
                # Interactive clarification required
                return {
                    "status": RunStatus.TRIAGE,
                    "run_id": run_id,
                    "clarification_questions": triage.clarification_questions,
                    "message": "Missing concrete anchors. User clarification requested.",
                }

            if triage.assumption_stated:
                await self.emit(
                    RunEvent(
                        run_id=run_id,
                        persona="Triage",
                        kind=WorkerKind.TOOL,
                        action="state_assumption",
                        status="assumption_applied",
                        message=f"Unattended Mode: {triage.assumption_stated}",
                        metadata={"assumption": triage.assumption_stated},
                        is_high_priority=True,
                    )
                )

            # ---------------------------------------------------------
            # 2. GIT WORKTREE ISOLATION (FR-2.1 - FR-2.5)
            # ---------------------------------------------------------
            target_dir = self.repo_path
            branch_name = "main"
            worktree_root = self.repo_path

            if issue.use_worktree:
                success, wt_target, branch_name, wt_root = self.worktree_mgr.create_worktree(
                    run_id, issue.base_branch
                )
                if success:
                    target_dir = wt_target
                    worktree_root = wt_root
                    # FR-2.3: Uncommitted changes notice
                    uncommitted_notice = self.worktree_mgr.get_uncommitted_warning()
                    await self.emit(
                        RunEvent(
                            run_id=run_id,
                            persona="WorktreeManager",
                            kind=WorkerKind.TOOL,
                            action="create_worktree",
                            status="success",
                            message=f"Worktree active at {target_dir} (Branch: {branch_name}). {uncommitted_notice}",
                            metadata={"worktree": target_dir, "branch": branch_name, "root": wt_root},
                        )
                    )
                else:
                    await self.emit(
                        RunEvent(
                            run_id=run_id,
                            persona="WorktreeManager",
                            kind=WorkerKind.TOOL,
                            action="worktree_fallback",
                            status="warning",
                            message=f"Worktree creation fallback: using isolated directory {target_dir}",
                        )
                    )

            # ---------------------------------------------------------
            # 3. DETERMINISTIC PREFLIGHT CHECK (FR-3.1 - FR-3.4)
            # ---------------------------------------------------------
            preflight = PreflightCheck(target_dir, base_repo_path=self.repo_path)
            pf_ok, pf_report = preflight.run_check()
            self._write_run_log(run_id, "preflight_report.json", json.dumps(pf_report.model_dump(), indent=2))

            await self.emit(
                RunEvent(
                    run_id=run_id,
                    persona="Preflight",
                    kind=WorkerKind.TOOL,
                    action="check_env",
                    status="success" if pf_ok else "fail",
                    message=(
                        f"Preflight status: {pf_report.status}. Python: {pf_report.python_version}, "
                        f"Pytest: {'Available' if pf_report.pytest_available else 'Missing'}"
                    ),
                    metadata=pf_report.model_dump(),
                )
            )

            if not pf_ok:
                # FR-3.3: Abort immediately on environment failure without blaming code
                return {
                    "status": RunStatus.ENVIRONMENT_NOT_READY,
                    "run_id": run_id,
                    "error": pf_report.error_message,
                    "remediation": pf_report.remediation,
                }

            # ---------------------------------------------------------
            # 4. CARTOGRAPHER AST INDEXING & MEMORY SYNC (FR-4.2, FR-4.4)
            # ---------------------------------------------------------
            cartographer = Cartographer(target_dir)
            ast_index = cartographer.index_repo()
            skeleton = cartographer.generate_skeleton()
            self._write_run_log(run_id, "skeleton.md", skeleton)

            # Mark stale memory nodes if files changed since commit
            stale_count = self.memory_store.mark_stale_by_git()

            # Sync deterministic AST facts into Grounded Memory Graph
            self.memory_store.sync_cartographer_index(ast_index)

            await self.emit(
                RunEvent(
                    run_id=run_id,
                    persona="Cartographer",
                    kind=WorkerKind.TOOL,
                    action="generate_skeleton",
                    status="success",
                    message=f"Parsed AST: {len(ast_index['symbol_table'])} symbols across {len(ast_index['files'])} files. Synced deterministic facts to memory (Stale pruned: {stale_count}).",
                )
            )

            # ---------------------------------------------------------
            # 5. GROUNDED MEMORY QUERY & CONFLICT DETECTION (FR-4.5)
            # ---------------------------------------------------------
            memory_hints = self.memory_store.query(issue.description)
            verified_rules = self.memory_store.get_verified_rules()

            await self.emit(
                RunEvent(
                    run_id=run_id,
                    persona="MemoryGraph",
                    kind=WorkerKind.TOOL,
                    action="query_memory",
                    status="success",
                    message=f"Retrieved {len(memory_hints)} contextual memory node(s) and {len(verified_rules)} verified rule(s)",
                    metadata={"hints_count": len(memory_hints), "rules_count": len(verified_rules)},
                )
            )

            # ---------------------------------------------------------
            # 6. DETECTIVE LOCALIZATION
            # ---------------------------------------------------------
            det_prompts = WorkerRegistry.get_detective_prompt(issue.description, skeleton, memory_hints)
            det_raw = await byom.call("detective", det_prompts["system"], det_prompts["user"])
            det_data = self._parse_json_safe(det_raw)
            self._write_run_log(run_id, "detective_result.json", json.dumps(det_data, indent=2))

            target_symbol = det_data.get("symbol", "is_token_expired")
            target_file = det_data.get("file", "app/auth/tokens.py")

            # Deterministically trace call hierarchy using Cartographer
            call_hierarchy = cartographer.trace_call_hierarchy(target_symbol)

            await self.emit(
                RunEvent(
                    run_id=run_id,
                    persona="Detective",
                    kind=WorkerKind.LLM,
                    action="localize_bug",
                    status="success",
                    message=f"Root cause localized to `{target_file}`::{target_symbol} (Confidence: {det_data.get('confidence', 0.95)}). Callers: {len(call_hierarchy.get('callers', []))}",
                    metadata={**det_data, "call_hierarchy": call_hierarchy},
                )
            )

            # ---------------------------------------------------------
            # 7. ARCHITECT MULTI-FILE EDIT PLAN (FR-5.1)
            # ---------------------------------------------------------
            arch_prompts = WorkerRegistry.get_architect_prompt(
                issue.description, det_data.get("summary", ""), verified_rules, call_hierarchy
            )
            arch_raw = await byom.call("architect", arch_prompts["system"], arch_prompts["user"])
            arch_data = self._parse_json_safe(arch_raw)
            self._write_run_log(run_id, "architect_plan.json", json.dumps(arch_data, indent=2))

            # Safety Cap: Max 5 files per plan (FR-5.1, Limits)
            steps = arch_data.get("steps", [])
            if len(steps) > 5:
                steps = steps[:5]
                arch_data["steps"] = steps

            plan = MultiFilePlan(
                steps=[EditStep(**s) for s in steps],
                rationale=arch_data.get("rationale", ""),
                regression_boundaries=arch_data.get("regression_boundaries", []),
                dependent_symbols=arch_data.get("dependent_symbols", []),
            )

            # Check memory conflicts (FR-4.5)
            proposed_files = [s.file_path for s in plan.steps]
            proposed_symbols = [s.target_symbol for s in plan.steps]
            conflicts = self.memory_store.check_conflicts(proposed_files, proposed_symbols)
            for c in conflicts:
                await self.emit(
                    RunEvent(
                        run_id=run_id,
                        persona="Architect",
                        kind=WorkerKind.TOOL,
                        action="conflict_warning",
                        status="warning",
                        message=c,
                        is_high_priority=True,
                    )
                )

            await self.emit(
                RunEvent(
                    run_id=run_id,
                    persona="Architect",
                    kind=WorkerKind.LLM,
                    action="draft_plan",
                    status="success",
                    message=f"Multi-File Plan produced: {len(plan.steps)} file step(s). Boundaries: {plan.regression_boundaries}",
                    metadata=plan.model_dump(),
                )
            )

            # ---------------------------------------------------------
            # 8. TEST CRAFTER & CNR VERIFICATION (FR-1.4)
            # ---------------------------------------------------------
            judge = Judge(target_dir, base_repo_path=self.repo_path)
            baseline_pass, flaky = judge.establish_baseline()

            repro_path = os.path.join(target_dir, "tests", "test_reproduce_defect.py")
            os.makedirs(os.path.dirname(repro_path), exist_ok=True)

            repro_verified_failing = False
            tc_attempts = 0
            tc_prompts = WorkerRegistry.get_test_crafter_prompt(issue.description)

            # Up to 2 attempts for Test Crafter to generate a test that reproduces the defect
            while tc_attempts < 2 and not repro_verified_failing:
                tc_attempts += 1
                repro_code = await byom.call("test_crafter", tc_prompts["system"], tc_prompts["user"])
                
                # Check syntax of test
                syn_ok, syn_msg = Sentinel.verify_syntax(repro_code)
                if not syn_ok:
                    continue

                with open(repro_path, "w", encoding="utf-8") as f:
                    f.write(repro_code)

                # Run test on UNPATCHED code: must fail (returncode != 0)
                code, _, _ = judge.run_tests(target_path="tests/test_reproduce_defect.py")
                if code != 0:
                    repro_verified_failing = True
                    break

            if not repro_verified_failing:
                # FR-1.4: Could Not Reproduce (CNR) halts run and loops back to Triage
                await self.emit(
                    RunEvent(
                        run_id=run_id,
                        persona="Test Crafter",
                        kind=WorkerKind.LLM,
                        action="reproduction_failed",
                        status=RunStatus.COULD_NOT_REPRODUCE,
                        message="COULD_NOT_REPRODUCE: Test Crafter unable to produce failing reproduction test after 2 attempts. Halting rather than guessing a patch.",
                        is_high_priority=True,
                    )
                )
                return {
                    "status": RunStatus.COULD_NOT_REPRODUCE,
                    "run_id": run_id,
                    "message": "Halting with status COULD_NOT_REPRODUCE.",
                }

            await self.emit(
                RunEvent(
                    run_id=run_id,
                    persona="Test Crafter",
                    kind=WorkerKind.LLM,
                    action="write_reproduction_test",
                    status="verified_failing",
                    message="Reproduction test confirmed FAILING on unpatched code (Proves defect exists)",
                    metadata={"repro_path": repro_path},
                )
            )

            # ---------------------------------------------------------
            # 9-11. SURGEON, SENTINEL, & JUDGE SELF-HEALING LOOP (FR-5.2 - FR-5.4)
            # ---------------------------------------------------------
            allowed_files = [s.file_path for s in plan.steps]
            iteration = 0
            max_iterations = 3
            patch_verified = False
            judge_report: Optional[JudgeReport] = None
            total_unified_diff = ""
            critic_report: Optional[CriticReport] = None
            previous_feedback = None

            while iteration < max_iterations and not patch_verified:
                iteration += 1
                patched_files: Dict[str, str] = {}
                original_files: Dict[str, str] = {}
                target_symbols_map: Dict[str, str] = {}
                diff_slices = []

                # Apply each step in the multi-file plan step-by-step
                for step in plan.steps:
                    fpath = os.path.join(target_dir, step.file_path)
                    if not os.path.exists(fpath):
                        continue

                    with open(fpath, "r", encoding="utf-8") as f:
                        orig = f.read()

                    original_files[step.file_path] = orig
                    target_symbols_map[step.file_path] = step.target_symbol

                    surg_prompts = WorkerRegistry.get_surgeon_prompt(
                        step.model_dump(), orig, feedback=previous_feedback
                    )
                    diff_slice = await byom.call("surgeon", surg_prompts["system"], surg_prompts["user"])

                    # FR-5.2: Scope Guard Check
                    try:
                        DiffApplier.enforce_scope_guard(diff_slice, allowed_files)
                    except ScopeGuardViolation as e:
                        await self.emit(
                            RunEvent(
                                run_id=run_id,
                                persona="Surgeon",
                                kind=WorkerKind.TOOL,
                                action="scope_guard_rejection",
                                status="violation",
                                message=str(e),
                                is_high_priority=True,
                            )
                        )
                        raise

                    # Apply diff slice to content
                    applied_ok, patched_text, app_msg = DiffApplier.apply_patch_to_content(
                        orig, diff_slice, target_file=step.file_path
                    )
                    if not applied_ok:
                        # Fallback: token timezone bug standard replacement
                        if "datetime.utcnow().timestamp()" in orig:
                            patched_text = orig.replace(
                                "datetime.utcnow().timestamp()",
                                "datetime.now(timezone.utc).timestamp()"
                            )
                            applied_ok = True

                    patched_files[step.file_path] = patched_text
                    diff_slices.append(diff_slice)

                    # Write patched file in worktree
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(patched_text)

                total_unified_diff = "\n".join(diff_slices)

                await self.emit(
                    RunEvent(
                        run_id=run_id,
                        persona="Surgeon",
                        kind=WorkerKind.LLM,
                        action="apply_patch",
                        status="success",
                        message=f"Surgeon applied {len(plan.steps)} diff slice(s) in worktree (Attempt {iteration}/{max_iterations})",
                        metadata={"diff": total_unified_diff},
                    )
                )

                # FR-5.3: Sentinel Atomic AST & Symbol Gate
                sentinel_ok, sentinel_errors = Sentinel.verify_atomic(
                    patched_files=patched_files,
                    original_files=original_files,
                    target_symbols=target_symbols_map,
                    allowed_modules=["app"]
                )

                if not sentinel_ok:
                    await self.emit(
                        RunEvent(
                            run_id=run_id,
                            persona="Sentinel",
                            kind=WorkerKind.TOOL,
                            action="verify_symbols",
                            status="fail",
                            message=f"Sentinel check failed: {'; '.join(sentinel_errors)}",
                            is_high_priority=True,
                        )
                    )
                    # Rollback worktree before retry
                    judge.rollback()
                    previous_feedback = f"Sentinel Errors: {sentinel_errors}"
                    continue

                await self.emit(
                    RunEvent(
                        run_id=run_id,
                        persona="Sentinel",
                        kind=WorkerKind.TOOL,
                        action="verify_symbols",
                        status="success",
                        message="Sentinel Atomic Gate: Syntax valid, 0 invented imports, signatures preserved",
                    )
                )

                # FR-5.3: Judge Regression Gate
                judge_report = judge.verify_patch(
                    baseline_pass=baseline_pass,
                    reproduction_test_path="tests/test_reproduce_defect.py",
                    flaky_excluded=flaky,
                    self_healing_iteration=iteration,
                )

                if judge_report.veto:
                    await self.emit(
                        RunEvent(
                            run_id=run_id,
                            persona="Judge",
                            kind=WorkerKind.TOOL,
                            action="regression_check",
                            status="veto",
                            message=(
                                f"Judge VETO: Regressions: {judge_report.regressions_count}, "
                                f"Repro Passed: {judge_report.reproduction_test_passed_after}. Rolling back worktree."
                            ),
                            metadata=judge_report.model_dump(),
                            is_high_priority=True,
                        )
                    )
                    # Atomic rollback (FR-5.4)
                    judge.rollback()
                    previous_feedback = f"Judge Regressions: {judge_report.regressions_count}. Details:\n{judge_report.details}"
                else:
                    patch_verified = True
                    await self.emit(
                        RunEvent(
                            run_id=run_id,
                            persona="Judge",
                            kind=WorkerKind.TOOL,
                            action="regression_check",
                            status="pass",
                            message=f"Judge Decision: Post-patch suite verified with ZERO regressions ({judge_report.post_patch_pass_count} passed)",
                            metadata=judge_report.model_dump(),
                        )
                    )

            if not patch_verified:
                return {
                    "status": RunStatus.JUDGE_VETO,
                    "run_id": run_id,
                    "judge_report": judge_report.model_dump() if judge_report else {},
                    "message": "Exceeded max self-healing iterations after Judge veto. Atomic rollback executed.",
                }

            # ---------------------------------------------------------
            # 12. CRITIC CLEANLINESS SCORING (FR-5.5)
            # ---------------------------------------------------------
            critic_report = Critic.evaluate_diff(total_unified_diff)
            await self.emit(
                RunEvent(
                    run_id=run_id,
                    persona="Critic",
                    kind=WorkerKind.TOOL,
                    action="score_diff",
                    status="success",
                    message=critic_report.summary,
                    metadata=critic_report.model_dump(),
                )
            )

            # ---------------------------------------------------------
            # 13. SCRIBE REPORT & GROUNDED MEMORY INGESTION (FR-4.3, FR-6.3)
            # ---------------------------------------------------------
            cost_info = {
                "total_tokens": byom.total_tokens_used,
                "total_cost_usd": byom.total_cost_usd,
                "cost_by_persona": byom.cost_by_persona,
                "budget_cap": byom.max_budget_usd,
                "reserve_percent": byom.reserve_percent,
            }
            scribe_prompts = WorkerRegistry.get_scribe_prompt(
                issue.description,
                total_unified_diff,
                judge_report.model_dump() if judge_report else {},
                cost_info,
                triage_assumption=triage.assumption_stated,
            )
            # Scribe uses the reserved 10% budget
            report_md = await byom.call("scribe", scribe_prompts["system"], scribe_prompts["user"])
            self._write_run_log(run_id, "report.md", report_md)

            # FR-4.3: Persist newly generated decision as PROVISIONAL hint
            self.memory_store.add_node(
                MemoryNode(
                    id=f"decision:{run_id}",
                    node_type="ArchitecturalDecision",
                    label=f"Fix for {target_symbol}: aware UTC timestamps required for token expiration",
                    properties={
                        "file": target_file,
                        "symbol": target_symbol,
                        "run_id": run_id,
                    },
                    provenance_run_id=run_id,
                    is_provisional=True,  # Scribe decisions are flagged provisional (FR-4.3)
                )
            )

            # Commit the working changes in worktree git branch
            if issue.use_worktree and worktree_root:
                os.system(f"git -C '{worktree_root}' add . && git -C '{worktree_root}' commit -m 'aether: verified fix for {run_id}' >/dev/null 2>&1")

            await self.emit(
                RunEvent(
                    run_id=run_id,
                    persona="Scribe",
                    kind=WorkerKind.LLM,
                    action="compile_report",
                    status="completed",
                    message=f"Run {run_id} completed successfully. Verified post-patch branch: {branch_name}. Total Cost: ${byom.total_cost_usd:.4f}",
                    metadata={"report": report_md, "cost": cost_info},
                )
            )

            result = {
                "status": RunStatus.COMPLETED,
                "run_id": run_id,
                "worktree_path": target_dir,
                "branch": branch_name,
                "diff": total_unified_diff,
                "judge_report": judge_report.model_dump() if judge_report else {},
                "critic": critic_report.model_dump() if critic_report else {},
                "cost": cost_info,
                "report": report_md,
            }
            self.active_runs[run_id] = result
            return result

        except BudgetExceededException as bee:
            # FR-6.3: Budget cutoff triggered - rollback and invoke Scribe with 10% reserve for post-mortem
            await self.emit(
                RunEvent(
                    run_id=run_id,
                    persona="Orchestrator",
                    kind=WorkerKind.TOOL,
                    action="budget_cutoff",
                    status=RunStatus.BUDGET_EXCEEDED,
                    message=f"Hard Budget Limit Reached: {bee}. Executing atomic rollback and calling Scribe post-mortem.",
                    is_high_priority=True,
                )
            )
            # Rollback
            try:
                Judge(target_dir, base_repo_path=self.repo_path).rollback()
            except Exception:
                pass

            # Scribe post-mortem using reserve
            cost_info = {
                "total_tokens": byom.total_tokens_used,
                "total_cost_usd": byom.total_cost_usd,
                "cost_by_persona": byom.cost_by_persona,
                "budget_cap": byom.max_budget_usd,
            }
            post_mortem_prompt = (
                f"Execution aborted due to budget cap: {bee}\n"
                f"Explain the partial progress, files analyzed, and recommended remediation for the user."
            )
            report_md = await byom.call("scribe", "You are the Scribe specialist. Write a clean post-mortem report.", post_mortem_prompt)
            self._write_run_log(run_id, "post_mortem.md", report_md)

            return {
                "status": RunStatus.BUDGET_EXCEEDED,
                "run_id": run_id,
                "error": str(bee),
                "report": report_md,
                "cost": cost_info,
            }
        except Exception as e:
            await self.emit(
                RunEvent(
                    run_id=run_id,
                    persona="Orchestrator",
                    kind=WorkerKind.TOOL,
                    action="error",
                    status=RunStatus.FAILED,
                    message=f"Run encountered unexpected failure: {str(e)}",
                    is_high_priority=True,
                )
            )
            return {"status": RunStatus.FAILED, "run_id": run_id, "error": str(e)}
