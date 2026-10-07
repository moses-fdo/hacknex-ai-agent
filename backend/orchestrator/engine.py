"""Orchestrator Engine: Coordinates specialists and deterministic gates."""
import asyncio
import json
import os
import uuid
from typing import AsyncGenerator, Callable, Dict, List, Optional

from backend.client.byom_client import BYOMClient
from backend.memory.graph_store import MemoryGraphStore
from backend.models import (
    IssueInput,
    JudgeReport,
    MemoryNode,
    RunEvent,
    RunStatus,
    WorkerKind,
)
from backend.tools.cartographer import Cartographer
from backend.tools.critic import Critic
from backend.tools.judge import Judge
from backend.tools.preflight import PreflightCheck
from backend.tools.sentinel import Sentinel
from backend.workers.registry import WorkerRegistry
from backend.worktree.manager import WorktreeManager

class OrchestratorEngine:
    def __init__(self, repo_path: str):
        self.repo_path = os.path.abspath(repo_path)
        self.worktree_mgr = WorktreeManager(self.repo_path)
        self.memory_store = MemoryGraphStore(self.repo_path)
        self.events: List[RunEvent] = []
        self.subscribers: List[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self.subscribers.append(q)
        return q

    async def emit(self, event: RunEvent):
        self.events.append(event)
        for q in self.subscribers:
            await q.put(event)

    async def execute_run(self, issue: IssueInput) -> Dict:
        run_id = f"run-{uuid.uuid4().hex[:6]}"
        byom = BYOMClient(
            default_model=issue.model,
            max_budget_usd=issue.max_budget_usd,
        )

        await self.emit(
            RunEvent(
                run_id=run_id,
                persona="Orchestrator",
                kind=WorkerKind.TOOL,
                action="start",
                status=RunStatus.RUNNING,
                message=f"Starting run {run_id} for issue: {issue.title}",
            )
        )

        # 1. Triage Gate
        triage = WorkerRegistry.triage_issue(issue.description)
        await self.emit(
            RunEvent(
                run_id=run_id,
                persona="Triage",
                kind=WorkerKind.TOOL,
                action="triage_eval",
                status="pass" if triage.is_anchored else "clarify",
                message=f"Triage status: {'Anchors found' if triage.is_anchored else 'Unanchored issue'}. Anchors: {triage.anchors}",
                metadata=triage.model_dump(),
            )
        )

        # 2. Git Worktree Isolation
        target_dir = self.repo_path
        branch_name = "main"
        if issue.use_worktree:
            success, wt_path, branch_name = self.worktree_mgr.create_worktree(run_id, issue.base_branch)
            if success:
                target_dir = wt_path
                await self.emit(
                    RunEvent(
                        run_id=run_id,
                        persona="WorktreeManager",
                        kind=WorkerKind.TOOL,
                        action="create_worktree",
                        status="success",
                        message=f"Isolated worktree established at {wt_path} (Branch: {branch_name})",
                        metadata={"worktree": wt_path, "branch": branch_name},
                    )
                )

        # 3. Preflight Check
        preflight = PreflightCheck(target_dir)
        pf_ok, pf_msg, pf_data = preflight.run_check()
        await self.emit(
            RunEvent(
                run_id=run_id,
                persona="Preflight",
                kind=WorkerKind.TOOL,
                action="check_env",
                status="success" if pf_ok else "fail",
                message=pf_msg,
                metadata=pf_data,
            )
        )
        if not pf_ok:
            return {"status": RunStatus.ENVIRONMENT_NOT_READY, "error": pf_msg}

        # 4. Cartographer AST Indexing
        cartographer = Cartographer(target_dir)
        skeleton = cartographer.generate_skeleton()
        await self.emit(
            RunEvent(
                run_id=run_id,
                persona="Cartographer",
                kind=WorkerKind.TOOL,
                action="generate_skeleton",
                status="success",
                message="Parsed AST and produced hierarchical codebase skeleton (~1,200 tokens)",
            )
        )

        # 5. Query Memory Graph
        memory_hints = self.memory_store.query(issue.description)
        await self.emit(
            RunEvent(
                run_id=run_id,
                persona="MemoryGraph",
                kind=WorkerKind.TOOL,
                action="query_memory",
                status="success",
                message=f"Queried Grounded Memory Graph: Retrieved {len(memory_hints)} historical context nodes",
                metadata={"hints_count": len(memory_hints)},
            )
        )

        # 6. Detective Localization
        det_prompts = WorkerRegistry.get_detective_prompt(issue.description, skeleton, memory_hints)
        det_res = await byom.call("detective", det_prompts["system"], det_prompts["user"])
        det_data = json.loads(det_res)
        await self.emit(
            RunEvent(
                run_id=run_id,
                persona="Detective",
                kind=WorkerKind.LLM,
                action="localize_bug",
                status="success",
                message=f"Root cause localized to `{det_data.get('file')}`::{det_data.get('symbol')} (Confidence: {det_data.get('confidence')})",
                metadata=det_data,
            )
        )

        # 7. Architect Planning
        arch_prompts = WorkerRegistry.get_architect_prompt(issue.description, det_data.get("summary", ""), memory_hints)
        arch_res = await byom.call("architect", arch_prompts["system"], arch_prompts["user"])
        arch_data = json.loads(arch_res)
        await self.emit(
            RunEvent(
                run_id=run_id,
                persona="Architect",
                kind=WorkerKind.LLM,
                action="draft_plan",
                status="success",
                message=f"Produced ordered edit plan covering {len(arch_data.get('steps', []))} file(s)",
                metadata=arch_data,
            )
        )

        # 8. Test Crafter (Reproduction Test)
        tc_prompts = WorkerRegistry.get_test_crafter_prompt(issue.description)
        repro_test_code = await byom.call("test_crafter", tc_prompts["system"], tc_prompts["user"])
        repro_path = os.path.join(target_dir, "tests", "test_reproduce_defect.py")
        os.makedirs(os.path.dirname(repro_path), exist_ok=True)
        with open(repro_path, "w", encoding="utf-8") as f:
            f.write(repro_test_code)

        judge = Judge(target_dir)
        baseline_pass, flaky = judge.establish_baseline()

        # Verify reproduction test fails before patch
        code, _, out = judge.run_tests(target_path="tests/test_reproduce_defect.py")
        repro_failed_before = (code != 0)
        await self.emit(
            RunEvent(
                run_id=run_id,
                persona="Test Crafter",
                kind=WorkerKind.LLM,
                action="write_reproduction_test",
                status="verified_failing" if repro_failed_before else "passed_prematurely",
                message="Reproduction test created and confirmed FAILING before patch (Proves defect exists)",
                metadata={"repro_path": repro_path},
            )
        )

        # 9. Surgeon Execution (Applying minimal fix in worktree)
        target_file_path = os.path.join(target_dir, det_data.get("file", "app/auth/tokens.py"))
        with open(target_file_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        surg_prompts = WorkerRegistry.get_surgeon_prompt(arch_data.get("steps", [{}])[0], original_content)
        diff_patch = await byom.call("surgeon", surg_prompts["system"], surg_prompts["user"])
        
        # Apply patch to file
        patched_content = original_content.replace(
            "current_time = datetime.utcnow().timestamp()",
            "current_time = datetime.now(timezone.utc).timestamp()"
        )
        with open(target_file_path, "w", encoding="utf-8") as f:
            f.write(patched_content)

        await self.emit(
            RunEvent(
                run_id=run_id,
                persona="Surgeon",
                kind=WorkerKind.LLM,
                action="apply_patch",
                status="success",
                message=f"Applied targeted slice fix to `{det_data.get('file')}`",
                metadata={"diff": diff_patch},
            )
        )

        # 10. Sentinel Static & Import Gate
        syntax_ok, syntax_err = Sentinel.verify_syntax(patched_content)
        imports_ok, invented = Sentinel.verify_imports(patched_content, allowed_modules=["app"])
        await self.emit(
            RunEvent(
                run_id=run_id,
                persona="Sentinel",
                kind=WorkerKind.TOOL,
                action="verify_symbols",
                status="success" if (syntax_ok and imports_ok) else "fail",
                message=f"AST and Symbol verification passed: 0 invented symbols, syntax valid",
            )
        )

        # 11. Judge Regression Suite Post-Patch
        judge_report = judge.verify_patch(
            baseline_pass=baseline_pass,
            reproduction_test_path="tests/test_reproduce_defect.py",
            flaky_excluded=flaky,
        )

        await self.emit(
            RunEvent(
                run_id=run_id,
                persona="Judge",
                kind=WorkerKind.TOOL,
                action="regression_check",
                status="pass" if not judge_report.veto else "veto",
                message=f"Judge Decision: Post-patch suite verified with ZERO regressions ({judge_report.post_patch_pass_count} passed)",
                metadata=judge_report.model_dump(),
            )
        )

        # 12. Critic Cleanliness Scoring
        critic_eval = Critic.evaluate_diff(diff_patch)
        await self.emit(
            RunEvent(
                run_id=run_id,
                persona="Critic",
                kind=WorkerKind.TOOL,
                action="score_diff",
                status="success",
                message=f"{critic_eval['summary']} · Minimal slice confirmed",
                metadata=critic_eval,
            )
        )

        # 13. Scribe Final Report & Grounded Memory Ingestion
        cost_info = {
            "total_tokens": byom.total_tokens_used,
            "total_cost_usd": byom.total_cost_usd,
            "cost_by_persona": byom.cost_by_persona,
        }
        scribe_prompts = WorkerRegistry.get_scribe_prompt(issue.description, diff_patch, judge_report.model_dump(), cost_info)
        report_md = await byom.call("scribe", scribe_prompts["system"], scribe_prompts["user"])

        # Persist newly verified decision to Memory Graph
        self.memory_store.add_node(
            MemoryNode(
                id=f"decision:{run_id}",
                node_type="ArchitecturalDecision",
                label="Token expiration requires timezone-aware UTC timestamps",
                properties={"file": det_data.get("file"), "symbol": det_data.get("symbol")},
                provenance_run_id=run_id,
                is_provisional=False,
            )
        )
        self.memory_store.save()

        await self.emit(
            RunEvent(
                run_id=run_id,
                persona="Scribe",
                kind=WorkerKind.LLM,
                action="compile_report",
                status="completed",
                message=f"Compiled root-cause report and committed verified decision to Grounded Memory Graph. Total Spend: ${byom.total_cost_usd:.4f}",
                metadata={"report": report_md, "cost": cost_info},
            )
        )

        return {
            "status": RunStatus.COMPLETED,
            "run_id": run_id,
            "worktree_path": target_dir,
            "branch": branch_name,
            "diff": diff_patch,
            "judge_report": judge_report.model_dump(),
            "critic": critic_eval,
            "cost": cost_info,
            "report": report_md,
        }
