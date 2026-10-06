from typing import Dict, Any
from backend.personas.base import BasePersona
from backend.models.schema import PersonaType, SquadType, ArchitectBlueprint
from backend.engine.llm_client import UniversalLLMClient

class ArchitectPersona(BasePersona):
    """Drafts surgical blueprints, interface contracts, and blast-radius safety bounds."""

    def __init__(self, llm: UniversalLLMClient):
        super().__init__(
            name=PersonaType.ARCHITECT,
            squad=SquadType.DISCOVERY,
            role="System Architecture & Surgical Mutation Planning",
            avatar="📐",
            allowed_tools=["read_interface_contract", "draft_blueprint"],
            forbidden_tools=["write_file", "apply_diff", "run_tests"]
        )
        self.llm = llm

    async def execute(self, state: Dict[str, Any], event_bus) -> Dict[str, Any]:
        diagnostic = state["diagnostic"]
        issue = state["issue_description"]

        await self.emit_thought(event_bus, f"Formulating surgical blueprint for {', '.join(diagnostic.target_files)}::{diagnostic.target_symbol}. Establishing zero-regression boundaries...")

        await self.emit_tool_call(event_bus, "read_interface_contract", {"files": diagnostic.target_files, "symbol": diagnostic.target_symbol})

        system_prompt = (
            "You are The Architect. Create a surgical execution blueprint for the code patch. "
            "Ensure existing interfaces are preserved, external dependencies are not invented, and regression risk is minimized.\n"
            "Return JSON with: 'plan_title', 'summary', 'target_files', 'proposed_mutation', 'safety_constraints', 'affected_components'."
        )
        user_prompt = (
            f"ISSUE: {issue}\n"
            f"TARGET FILES: {diagnostic.target_files}\n"
            f"TARGET SYMBOL: {diagnostic.target_symbol}\n"
            f"ROOT CAUSE: {diagnostic.root_cause}"
        )

        raw_response = await self.llm.complete(system_prompt, user_prompt)
        data = self.llm.parse_json(raw_response)

        blueprint = ArchitectBlueprint(
            plan_title=data.get("plan_title", "Surgical Patch Specification"),
            summary=data.get("summary", "Surgical modification to align timezone handling."),
            target_files=data.get("target_files", diagnostic.target_files),
            proposed_mutation=data.get("proposed_mutation", "Update timestamp calculation to use timezone.utc."),
            safety_constraints=data.get("safety_constraints", ["Preserve function signature", "Zero regression on existing tests"]),
            affected_components=data.get("affected_components", diagnostic.target_files)
        )

        await self.emit_tool_result(
            event_bus,
            "draft_blueprint",
            f"Architect Blueprint defined: '{blueprint.plan_title}'. Enforcing {len(blueprint.safety_constraints)} safety constraints.",
            metadata=blueprint.model_dump()
        )

        state["blueprint"] = blueprint
        await self.emit_thought(event_bus, "Blueprint ratified. Handing off to Test Crafter for Test-Driven Development (TDD) reproduction.")
        return state
