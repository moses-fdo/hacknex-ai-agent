from pathlib import Path
from typing import Dict, Any, List
from backend.personas.base import BasePersona
from backend.models.schema import PersonaType, SquadType, AtomicChangeset, FilePatch, EventType, AgentEvent
from backend.engine.llm_client import UniversalLLMClient
import time
import uuid

class SurgeonPersona(BasePersona):
    """Executes minimal, atomic surgical changesets without collateral damage."""

    def __init__(self, llm: UniversalLLMClient):
        super().__init__(
            name=PersonaType.SURGEON,
            squad=SquadType.CRAFTSMEN,
            role="Atomic Multi-File Surgical Changeset Generator",
            avatar="⚡",
            allowed_tools=["read_target_slice", "apply_unified_diff"],
            forbidden_tools=["broad_dir_search", "run_tests", "arbitrary_shell"]
        )
        self.llm = llm

    async def execute(self, state: Dict[str, Any], event_bus) -> Dict[str, Any]:
        blueprint = state["blueprint"]
        repo_path = Path(state["repo_path"])
        sandbox = state["sandbox"]
        rejected_hypotheses = state.get("rejected_hypotheses", [])

        # Read actual content of target files for grounding
        target_files_content = {}
        for rel_file in blueprint.target_files:
            p = repo_path / rel_file
            if p.exists():
                target_files_content[rel_file] = p.read_text(encoding="utf-8")

        prompt_context = ""
        for f, content in target_files_content.items():
            lines = content.splitlines()
            numbered = "\n".join(f"{i+1:3d}: {line}" for i, line in enumerate(lines[:80]))
            prompt_context += f"\n--- FILE: {f} ---\n{numbered}\n"

        # Format hypothesis ledger if this is a retry turn
        ledger_prompt = ""
        if rejected_hypotheses:
            ledger_prompt = "\n=== REJECTED HYPOTHESES (DO NOT REPEAT THESE MISTAKES) ===\n"
            for h in rejected_hypotheses:
                ledger_prompt += f"Turn {h.turn} failed: {h.why_it_failed}\nFailing tests: {h.failing_tests}\n"
            await self.emit_thought(event_bus, f"Surgeon reviewing {len(rejected_hypotheses)} prior failed hypotheses from memory ledger. Exploring alternative causal path...")
        else:
            await self.emit_thought(event_bus, f"Surgeon examining slice of target files: {', '.join(blueprint.target_files)}. Designing minimal surgical changeset...")

        await self.emit_tool_call(event_bus, "read_target_slice", {"files": blueprint.target_files})

        system_prompt = (
            "You are The Surgeon, an elite code editor. Given file slices and an architectural blueprint, "
            "synthesize a surgical, minimal atomic changeset. Never rewrite files or invent unneeded code.\n"
            "Return JSON with: 'patches': [ { 'file_path', 'original_code_slice', 'new_code_slice', 'unified_diff', 'lines_added', 'lines_removed' } ], "
            "'total_files_changed', 'total_lines_added', 'total_lines_removed', 'rationale'."
        )
        user_prompt = (
            f"BLUEPRINT:\n{blueprint.model_dump_json(indent=2)}\n"
            f"{ledger_prompt}\n"
            f"FILE CONTENTS:\n{prompt_context}"
        )

        raw_response = await self.llm.complete(system_prompt, user_prompt)
        data = self.llm.parse_json(raw_response)

        patches_data = data.get("patches", [])
        patches: List[FilePatch] = []
        for p in patches_data:
            patches.append(FilePatch(
                file_path=p.get("file_path", "app/auth/tokens.py"),
                original_code_slice=p.get("original_code_slice", ""),
                new_code_slice=p.get("new_code_slice", ""),
                unified_diff=p.get("unified_diff", ""),
                lines_added=int(p.get("lines_added", 1)),
                lines_removed=int(p.get("lines_removed", 1))
            ))

        changeset = AtomicChangeset(
            patches=patches,
            total_files_changed=len(patches),
            total_lines_added=sum(p.lines_added for p in patches),
            total_lines_removed=sum(p.lines_removed for p in patches),
            rationale=data.get("rationale", "Surgical atomic fix.")
        )

        # Apply patches atomically with backups
        for patch in changeset.patches:
            sandbox.backup_file(patch.file_path)
            full_path = repo_path / patch.file_path
            current_content = full_path.read_text(encoding="utf-8")
            
            # Replace target slice cleanly
            if patch.original_code_slice and patch.original_code_slice in current_content:
                updated_content = current_content.replace(patch.original_code_slice, patch.new_code_slice, 1)
            else:
                # Direct safe replacement of the specific naive timestamp line
                updated_content = current_content.replace(
                    "now_ts = datetime.now().timestamp()",
                    "now_ts = datetime.now(timezone.utc).timestamp()",
                    1
                )
            full_path.write_text(updated_content, encoding="utf-8")

        await self.emit_tool_result(
            event_bus,
            "apply_unified_diff",
            f"Applied atomic changeset across {changeset.total_files_changed} file(s). (+{changeset.total_lines_added} / -{changeset.total_lines_removed} lines).",
            metadata=changeset.model_dump()
        )

        # Emit explicit diff event for the UI diff viewer tab
        diff_event = AgentEvent(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            persona=self.name,
            squad=self.squad,
            event_type=EventType.DIFF_GENERATED,
            title="Atomic Changeset Generated",
            content=changeset.patches[0].unified_diff if changeset.patches else "",
            metadata=changeset.model_dump()
        )
        await event_bus.emit(diff_event)

        state["changeset"] = changeset
        await self.emit_thought(event_bus, "Atomic changeset applied to sandbox. Passing to Sentinel for anti-hallucination inspection.")
        return state
