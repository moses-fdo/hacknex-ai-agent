from pathlib import Path
from typing import Dict, Any
from backend.personas.base import BasePersona
from backend.models.schema import PersonaType, SquadType, ReproductionTest
from backend.engine.llm_client import UniversalLLMClient

class TestCrafterPersona(BasePersona):
    """Synthesizes adversarial reproduction unit and integration tests (TDD Specialist)."""

    def __init__(self, llm: UniversalLLMClient):
        super().__init__(
            name=PersonaType.TEST_CRAFTER,
            squad=SquadType.CRAFTSMEN,
            role="TDD Reproduction Test Synthesis & Adversarial Edge Cases",
            avatar="🧪",
            allowed_tools=["create_test_file", "verify_test_syntax"],
            forbidden_tools=["modify_production_code", "bypass_linting"]
        )
        self.llm = llm

    async def execute(self, state: Dict[str, Any], event_bus) -> Dict[str, Any]:
        blueprint = state["blueprint"]
        repo_path = Path(state["repo_path"])

        await self.emit_thought(event_bus, f"Synthesizing adversarial reproduction test suite for: {blueprint.plan_title}. Following TDD principles...")

        system_prompt = (
            "You are The Test Crafter. Given an architectural blueprint, craft a clean, high-quality pytest file "
            "that tests the requested feature/bug fix. Generate adversarial vectors (boundary checks, timezone offset checks).\n"
            "Return JSON with: 'test_file_path', 'test_name', 'adversarial_vectors', 'test_code', 'rationale'."
        )
        user_prompt = (
            f"PLAN TITLE: {blueprint.plan_title}\n"
            f"TARGET FILES: {blueprint.target_files}\n"
            f"MUTATION: {blueprint.proposed_mutation}\n"
            f"CONSTRAINTS: {blueprint.safety_constraints}"
        )

        raw_response = await self.llm.complete(system_prompt, user_prompt)
        data = self.llm.parse_json(raw_response)

        repro_test = ReproductionTest(
            test_file_path=data.get("test_file_path", "tests/test_utc_expiry.py"),
            test_name=data.get("test_name", "test_token_expiration_utc_alignment"),
            adversarial_vectors=data.get("adversarial_vectors", [
                "Boundary check: Token expiring in +1 second UTC",
                "Offset check: System clock simulated with offset"
            ]),
            test_code=data.get("test_code", "# Generated Test Code"),
            rationale=data.get("rationale", "Proves token expiration handling across timezone offsets.")
        )

        await self.emit_tool_call(event_bus, "create_test_file", {"path": repro_test.test_file_path})

        # Write reproduction test file to repo
        target_path = repo_path / repro_test.test_file_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(repro_test.test_code, encoding="utf-8")

        await self.emit_tool_result(
            event_bus,
            "create_test_file",
            f"Authored reproduction test at {repro_test.test_file_path} with {len(repro_test.adversarial_vectors)} adversarial vectors.",
            metadata=repro_test.model_dump()
        )

        state["repro_test"] = repro_test
        await self.emit_thought(event_bus, "Reproduction test authored and mounted. Dispatching Surgeon to apply minimal atomic patch.")
        return state
