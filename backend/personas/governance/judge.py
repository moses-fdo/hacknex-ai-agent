from typing import Dict, Any
from backend.personas.base import BasePersona
from backend.models.schema import PersonaType, SquadType, TestRunResult, EventType, AgentEvent, RejectedHypothesis
from backend.engine.sandbox import SandboxTestRunner
import time
import uuid

class RegressionOrTestFailureError(Exception):
    def __init__(self, test_result: TestRunResult, message: str):
        super().__init__(message)
        self.test_result = test_result

class JudgePersona(BasePersona):
    """Executes tests in sandbox, enforces zero regressions, and holds veto power."""

    def __init__(self):
        super().__init__(
            name=PersonaType.JUDGE,
            squad=SquadType.GOVERNANCE,
            role="Isolated Sandbox Executioner & Regression Arbiter",
            avatar="⚖️",
            allowed_tools=["run_sandbox_tests", "calculate_regression_delta", "git_rollback"],
            forbidden_tools=["modify_code", "bypass_failed_tests"]
        )

    async def execute(self, state: Dict[str, Any], event_bus) -> Dict[str, Any]:
        sandbox: SandboxTestRunner = state["sandbox"]
        changeset = state["changeset"]
        turn = state.get("turn", 1)

        await self.emit_thought(event_bus, "Judge executing test suite in isolated sandbox. Checking visible acceptance tests and regression delta...")

        await self.emit_tool_call(event_bus, "run_sandbox_tests", {"suite": "tests", "target": "all"})

        # Run full test suite including baseline tests + new TDD tests
        post_result: TestRunResult = sandbox.run_pytest()

        await self.emit_tool_result(
            event_bus,
            "run_sandbox_tests",
            f"Pytest run finished: {post_result.passed_tests}/{post_result.total_tests} passed. Broken baseline tests: {post_result.regressions}.",
            metadata=post_result.model_dump()
        )

        # Emit test event for UI Sandbox Matrix tab
        test_event = AgentEvent(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            persona=self.name,
            squad=self.squad,
            event_type=EventType.TEST_EXECUTED,
            title=f"Test Suite Results: {post_result.passed_tests}/{post_result.total_tests} Passing",
            content=post_result.raw_output,
            metadata=post_result.model_dump()
        )
        await event_bus.emit(test_event)

        # Regression Verification Gate: R = BaselinePassSet \ PostPatchPassSet
        if post_result.regressions > 0 or not post_result.passed:
            await self.emit_thought(event_bus, f"VETO! Tests failed or regressions detected ({post_result.regressions} broken baseline tests). Initiating immediate rollback...")
            sandbox.rollback_all()

            # Record in hypothesis ledger to prevent circular thrashing
            rejection = RejectedHypothesis(
                turn=turn,
                attempted_changeset_summary=changeset.rationale,
                failing_tests=[t.nodeid for t in post_result.tests if not t.passed],
                stack_trace=post_result.raw_output[-500:],
                why_it_failed=f"Caused {post_result.regressions} regressions or failed acceptance tests."
            )
            state.setdefault("rejected_hypotheses", []).append(rejection)

            raise RegressionOrTestFailureError(post_result, f"Judge veto: {post_result.failed_tests} failed, {post_result.regressions} regressions.")

        # If all tests pass with zero regressions
        verdict_event = AgentEvent(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            persona=self.name,
            squad=self.squad,
            event_type=EventType.VERDICT,
            title="VERDICT: APPROVED ✅ Zero Regressions Guaranteed",
            content=f"All {post_result.total_tests} tests PASSED. Existing workflows preserved with 100% integrity.",
            metadata={"status": "approved", "total_tests": post_result.total_tests, "regressions": 0}
        )
        await event_bus.emit(verdict_event)

        state["test_result"] = post_result
        await self.emit_thought(event_bus, f"Judge ratified changeset! {post_result.total_tests}/{post_result.total_tests} tests green. Handing off to Critic and Scribe for final audit and evidence generation.")
        return state
