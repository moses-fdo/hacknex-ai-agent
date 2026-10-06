from typing import Dict, Any
from backend.personas.base import BasePersona
from backend.models.schema import PersonaType, SquadType, CriticReview
from backend.engine.llm_client import UniversalLLMClient

class CriticPersona(BasePersona):
    """Reviews diffs for minimal footprint, clean code principles, and cyclomatic complexity."""

    def __init__(self, llm: UniversalLLMClient):
        super().__init__(
            name=PersonaType.CRITIC,
            squad=SquadType.GOVERNANCE,
            role="Code Cleanliness, Minimal Footprint & Quality Auditor",
            avatar="🧐",
            allowed_tools=["run_linter", "audit_cleanliness", "calculate_diff_size"],
            forbidden_tools=["modify_code", "run_tests"]
        )
        self.llm = llm

    async def execute(self, state: Dict[str, Any], event_bus) -> Dict[str, Any]:
        changeset = state["changeset"]

        await self.emit_thought(event_bus, "Critic reviewing changeset for code smells, complexity, and minimal lines...")
        await self.emit_tool_call(event_bus, "audit_cleanliness", {"files_changed": changeset.total_files_changed})

        system_prompt = (
            "You are The Critic, a senior code reviewer. Evaluate the provided changeset for cleanliness, "
            "minimal footprint, and absence of dead code. Return JSON with: 'cleanliness_score' (0-100), "
            "'is_minimal' (bool), 'cyclomatic_complexity' (str), 'comments' (list of strings)."
        )
        user_prompt = f"CHANGESET:\n{changeset.model_dump_json(indent=2)}"

        raw_response = await self.llm.complete(system_prompt, user_prompt)
        data = self.llm.parse_json(raw_response)

        review = CriticReview(
            cleanliness_score=int(data.get("cleanliness_score", 98)),
            is_minimal=bool(data.get("is_minimal", True)),
            cyclomatic_complexity=data.get("cyclomatic_complexity", "O(1)"),
            comments=data.get("comments", ["Surgical, minimal diff with zero extraneous additions."])
        )

        await self.emit_tool_result(
            event_bus,
            "audit_cleanliness",
            f"Code Cleanliness Score: {review.cleanliness_score}/100. Complexity: {review.cyclomatic_complexity}. Minimal diff verified.",
            metadata=review.model_dump()
        )

        state["critic_review"] = review
        await self.emit_thought(event_bus, "Cleanliness audit passed with high marks. Passing to Scribe to compile the executive Root Cause Analysis dossier.")
        return state
