from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from backend.models.schema import PersonaType, SquadType, AgentEvent, EventType
import time
import uuid

class BasePersona(ABC):
    """Abstract base class for all specialized personas in the agent guild."""

    def __init__(
        self,
        name: PersonaType,
        squad: SquadType,
        role: str,
        avatar: str,
        allowed_tools: List[str],
        forbidden_tools: List[str]
    ):
        self.name = name
        self.squad = squad
        self.role = role
        self.avatar = avatar
        self.allowed_tools = allowed_tools
        self.forbidden_tools = forbidden_tools

    @abstractmethod
    async def execute(self, state: Dict[str, Any], event_bus) -> Dict[str, Any]:
        """Executes the persona's specialized task and emits events to the event bus."""
        pass

    async def emit_thought(self, event_bus, thought: str):
        event = AgentEvent(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            persona=self.name,
            squad=self.squad,
            event_type=EventType.THOUGHT,
            title=f"{self.name.value} Thought",
            content=thought
        )
        await event_bus.emit(event)

    async def emit_tool_call(self, event_bus, tool_name: str, args: Dict[str, Any]):
        event = AgentEvent(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            persona=self.name,
            squad=self.squad,
            event_type=EventType.TOOL_CALL,
            title=f"Invoking {tool_name}",
            content=f"Arguments: {args}",
            metadata={"tool": tool_name, "args": args}
        )
        await event_bus.emit(event)

    async def emit_tool_result(self, event_bus, tool_name: str, result_summary: str, metadata: Optional[Dict[str, Any]] = None):
        event = AgentEvent(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            persona=self.name,
            squad=self.squad,
            event_type=EventType.TOOL_RESULT,
            title=f"{tool_name} Result",
            content=result_summary,
            metadata=metadata or {}
        )
        await event_bus.emit(event)
