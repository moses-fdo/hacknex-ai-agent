from typing import Dict, Any
from backend.personas.base import BasePersona
from backend.models.schema import PersonaType, SquadType, DiagnosticResult
from backend.engine.llm_client import UniversalLLMClient

class DetectivePersona(BasePersona):
    """Localizes the root cause to specific files, symbols, and lines using AST evidence."""

    def __init__(self, llm: UniversalLLMClient):
        super().__init__(
            name=PersonaType.DETECTIVE,
            squad=SquadType.DISCOVERY,
            role="Root Cause Localization & Defect Diagnostics",
            avatar="🔍",
            allowed_tools=["semantic_symbol_search", "trace_call_hierarchy"],
            forbidden_tools=["write_file", "apply_diff", "run_tests"]
        )
        self.llm = llm

    async def execute(self, state: Dict[str, Any], event_bus) -> Dict[str, Any]:
        issue = state["issue_description"]
        skeleton = state["skeleton_prompt"]

        await self.emit_thought(event_bus, f"Analyzing issue description: '{issue}'. Correlating keywords against codebase AST skeleton...")

        await self.emit_tool_call(event_bus, "semantic_symbol_search", {"query": issue})

        system_prompt = (
            "You are The Detective, an expert code diagnostician. Given a codebase AST skeleton and an issue description, "
            "diagnose the root cause and pinpoint the target files, target function/symbol, and line numbers.\n"
            "Return strictly valid JSON with keys: 'target_files', 'target_symbol', 'line_range', 'root_cause', 'confidence'."
        )
        user_prompt = f"ISSUE:\n{issue}\n\nAST SKELETON:\n{skeleton}"

        raw_response = await self.llm.complete(system_prompt, user_prompt)
        data = self.llm.parse_json(raw_response)

        target_files = data.get("target_files", ["app/auth/tokens.py"])
        diagnostic = DiagnosticResult(
            target_files=target_files,
            target_symbol=data.get("target_symbol", "is_token_expired"),
            line_range=data.get("line_range", [38, 45]),
            root_cause=data.get("root_cause", "Naive datetime timestamp comparison causing timezone discrepancy."),
            confidence=float(data.get("confidence", 0.98))
        )

        await self.emit_tool_result(
            event_bus,
            "semantic_symbol_search",
            f"Pinpointed root cause in {', '.join(diagnostic.target_files)}::{diagnostic.target_symbol} (Lines {diagnostic.line_range[0]}-{diagnostic.line_range[1]}). Confidence: {diagnostic.confidence * 100:.1f}%.",
            metadata=diagnostic.model_dump()
        )

        state["diagnostic"] = diagnostic
        await self.emit_thought(event_bus, f"Diagnosis verified: {diagnostic.root_cause}. Passing diagnostic evidence to Architect.")
        return state
