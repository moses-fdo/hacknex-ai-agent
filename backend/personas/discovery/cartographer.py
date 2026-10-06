from typing import Dict, Any
from backend.personas.base import BasePersona
from backend.models.schema import PersonaType, SquadType
from backend.engine.ast_parser import CodebaseCartographer

class CartographerPersona(BasePersona):
    """Parses AST, builds dependency trees and symbol outlines."""

    def __init__(self):
        super().__init__(
            name=PersonaType.CARTOGRAPHER,
            squad=SquadType.DISCOVERY,
            role="AST Symbol Cartography & Dependency Graph Mapping",
            avatar="🧭",
            allowed_tools=["build_ast_index", "get_import_graph", "generate_skeleton"],
            forbidden_tools=["write_file", "apply_diff", "run_tests"]
        )

    async def execute(self, state: Dict[str, Any], event_bus) -> Dict[str, Any]:
        await self.emit_thought(event_bus, "Beginning AST scan of repository. Constructing symbol table and import relationships...")
        repo_path = state["repo_path"]

        cartographer = CodebaseCartographer(repo_path)
        await self.emit_tool_call(event_bus, "build_ast_index", {"repo_path": repo_path})
        
        repo_map = cartographer.scan()
        skeleton = cartographer.generate_skeleton_prompt()

        await self.emit_tool_result(
            event_bus,
            "build_ast_index",
            f"Successfully mapped {repo_map.total_files} Python source files. Extracted functions, classes, and cross-file import graph.",
            metadata={
                "total_files": repo_map.total_files,
                "files": list(repo_map.files.keys()),
                "import_graph": repo_map.import_graph
            }
        )

        state["cartographer"] = cartographer
        state["repo_map"] = repo_map
        state["skeleton_prompt"] = skeleton

        await self.emit_thought(event_bus, f"Codebase skeleton ready ({repo_map.total_files} files indexed). Handing off to Detective for root-cause diagnosis.")
        return state
