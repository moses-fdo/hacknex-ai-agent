from typing import Dict, Any
from backend.personas.base import BasePersona
from backend.models.schema import PersonaType, SquadType, SentinelCheck
from backend.engine.ast_parser import CodebaseCartographer

class SentinelPersona(BasePersona):
    """AST Linter that halts hallucinated APIs and undeclared imports before tests run."""

    def __init__(self):
        super().__init__(
            name=PersonaType.SENTINEL,
            squad=SquadType.CRAFTSMEN,
            role="AST Hallucination & API Integrity Bouncer",
            avatar="🛡️",
            allowed_tools=["verify_symbol_existence", "ast_import_linter"],
            forbidden_tools=["modify_code", "run_bash"]
        )

    async def execute(self, state: Dict[str, Any], event_bus) -> Dict[str, Any]:
        changeset = state["changeset"]
        cartographer: CodebaseCartographer = state["cartographer"]

        await self.emit_thought(event_bus, "Sentinel inspecting changeset AST. Verifying zero hallucinated imports or invented APIs...")

        all_valid = True
        all_violations = []
        all_imported = []

        for patch in changeset.patches:
            await self.emit_tool_call(event_bus, "ast_import_linter", {"file": patch.file_path})
            check: SentinelCheck = cartographer.check_hallucinations(patch.new_code_slice)
            all_imported.extend(check.imported_modules)
            if not check.is_valid:
                all_valid = False
                all_violations.extend(check.violations)

        sentinel_result = SentinelCheck(
            is_valid=all_valid,
            imported_modules=all_imported,
            violations=all_violations
        )

        if not all_valid:
            await self.emit_tool_result(
                event_bus,
                "ast_import_linter",
                f"VETO! Detected {len(all_violations)} hallucination violations: {', '.join(all_violations)}",
                metadata=sentinel_result.model_dump()
            )
            state["sentinel_check"] = sentinel_result
            raise ValueError(f"Sentinel veto: Hallucinated dependencies detected: {all_violations}")

        await self.emit_tool_result(
            event_bus,
            "ast_import_linter",
            f"PASSED. All imports ({', '.join(all_imported) if all_imported else 'internal only'}) verified against symbol table and environment dependencies.",
            metadata=sentinel_result.model_dump()
        )

        state["sentinel_check"] = sentinel_result
        await self.emit_thought(event_bus, "Changeset verified clean and grounded in real code. Handing off to Judge for isolated sandbox testing.")
        return state
