import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
from backend.models.schema import (
    AgentEvent, EventType, RunRequest, PersonaType, SquadType
)
from backend.engine.sandbox import SandboxTestRunner
from backend.engine.llm_client import UniversalLLMClient
from backend.personas.discovery.cartographer import CartographerPersona
from backend.personas.discovery.detective import DetectivePersona
from backend.personas.discovery.architect import ArchitectPersona
from backend.personas.craftsmen.test_crafter import TestCrafterPersona
from backend.personas.craftsmen.surgeon import SurgeonPersona
from backend.personas.craftsmen.sentinel import SentinelPersona
from backend.personas.governance.judge import JudgePersona, RegressionOrTestFailureError
from backend.personas.governance.critic import CriticPersona
from backend.personas.governance.scribe import ScribePersona

class EventBus:
    """Asynchronous event bus supporting real-time SSE streaming for the UI."""

    def __init__(self):
        self.subscribers: List[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self.subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self.subscribers:
            self.subscribers.remove(q)

    async def emit(self, event: AgentEvent):
        for q in self.subscribers:
            await q.put(event)

class MasterOrchestrator:
    """Coordinates the 9-Persona Guild, self-healing loop, and event streaming."""

    def __init__(self, llm_client: Optional[UniversalLLMClient] = None):
        self.event_bus = EventBus()
        self.llm = llm_client or UniversalLLMClient()

    async def run(self, request: RunRequest) -> Dict[str, Any]:
        repo_path = request.repo_path or "benchmarks/ecommerce_api"
        issue = request.issue_description

        if request.model_settings:
            self.llm.update_settings(request.model_settings)

        # 1. Pipeline Start Event
        start_event = AgentEvent(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            event_type=EventType.PIPELINE_START,
            title="Aether-SWE Autonomous Pipeline Initialized",
            content=f"Target: {repo_path} | Task: {issue}",
            metadata={"repo_path": repo_path, "issue": issue}
        )
        await self.event_bus.emit(start_event)

        sandbox = SandboxTestRunner(repo_path)

        state: Dict[str, Any] = {
            "repo_path": repo_path,
            "issue_description": issue,
            "sandbox": sandbox,
            "rejected_hypotheses": [],
            "turn": 1
        }

        # Step 1: Establish baseline tests
        await self.event_bus.emit(AgentEvent(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            persona=PersonaType.JUDGE,
            squad=SquadType.GOVERNANCE,
            event_type=EventType.REGRESSION_CHECK,
            title="Establishing Baseline Tests Truth",
            content="Executing pre-patch test suite to establish non-regression baseline..."
        ))
        baseline = sandbox.establish_baseline()
        await self.event_bus.emit(AgentEvent(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            persona=PersonaType.JUDGE,
            squad=SquadType.GOVERNANCE,
            event_type=EventType.TOOL_RESULT,
            title=f"Baseline Established: {baseline.passed_tests}/{baseline.total_tests} Tests Passing",
            content=f"Locked in {baseline.passed_tests} passing unit test signatures. Zero broken workflows allowed.",
            metadata=baseline.model_dump()
        ))

        # Instantiate Personas
        cartographer = CartographerPersona()
        detective = DetectivePersona(self.llm)
        architect = ArchitectPersona(self.llm)
        test_crafter = TestCrafterPersona(self.llm)
        surgeon = SurgeonPersona(self.llm)
        sentinel = SentinelPersona()
        judge = JudgePersona()
        critic = CriticPersona(self.llm)
        scribe = ScribePersona(self.llm)

        # SQUAD 1: DISCOVERY & STRATEGY
        state = await cartographer.execute(state, self.event_bus)
        state = await detective.execute(state, self.event_bus)
        state = await architect.execute(state, self.event_bus)

        # SQUAD 2: CRAFTSMEN (TDD Test First)
        state = await test_crafter.execute(state, self.event_bus)

        # SELF-HEALING SURGICAL LOOP (Max 3 turns)
        max_turns = 3
        healing_success = False

        for turn in range(1, max_turns + 1):
            state["turn"] = turn
            try:
                state = await surgeon.execute(state, self.event_bus)
                state = await sentinel.execute(state, self.event_bus)
                state = await judge.execute(state, self.event_bus)
                healing_success = True
                break
            except (RegressionOrTestFailureError, ValueError) as err:
                if turn < max_turns:
                    await self.event_bus.emit(AgentEvent(
                        id=str(uuid.uuid4())[:8],
                        timestamp=time.time(),
                        persona=PersonaType.SURGEON,
                        squad=SquadType.CRAFTSMEN,
                        event_type=EventType.THOUGHT,
                        title=f"Self-Healing Turn {turn}/{max_turns} Activated",
                        content=f"Error encountered: {str(err)}. Reflecting on failure trace and adapting hypothesis..."
                    ))
                else:
                    await self.event_bus.emit(AgentEvent(
                        id=str(uuid.uuid4())[:8],
                        timestamp=time.time(),
                        event_type=EventType.ERROR,
                        title="Self-Healing Limit Exceeded",
                        content=f"Maximum {max_turns} turns reached without zero-regression sign-off."
                    ))
                    raise err

        # SQUAD 3: GOVERNANCE & EVIDENCE
        if healing_success:
            state = await critic.execute(state, self.event_bus)
            state = await scribe.execute(state, self.event_bus)

        # Pipeline Complete Event
        complete_event = AgentEvent(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            event_type=EventType.PIPELINE_COMPLETE,
            title="Aether-SWE Mission Accomplished",
            content="All visible and hidden criteria satisfied with 100% regression defense.",
            metadata={"status": "completed"}
        )
        await self.event_bus.emit(complete_event)

        return state
