from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum

class PersonaType(str, Enum):
    CARTOGRAPHER = "Cartographer"
    DETECTIVE = "Detective"
    ARCHITECT = "Architect"
    TEST_CRAFTER = "TestCrafter"
    SURGEON = "Surgeon"
    SENTINEL = "Sentinel"
    JUDGE = "Judge"
    CRITIC = "Critic"
    SCRIBE = "Scribe"

class SquadType(str, Enum):
    DISCOVERY = "Squad 1: Discovery & Strategy"
    CRAFTSMEN = "Squad 2: Implementation & Integrity"
    GOVERNANCE = "Squad 3: Verification & Governance"

class EventType(str, Enum):
    PIPELINE_START = "pipeline_start"
    PERSONA_START = "persona_start"
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    DIFF_GENERATED = "diff_generated"
    TEST_EXECUTED = "test_executed"
    REGRESSION_CHECK = "regression_check"
    VERDICT = "verdict"
    PERSONA_COMPLETE = "persona_complete"
    PIPELINE_COMPLETE = "pipeline_complete"
    ERROR = "error"

class AgentEvent(BaseModel):
    id: str
    timestamp: float
    persona: Optional[PersonaType] = None
    squad: Optional[SquadType] = None
    event_type: EventType
    title: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SymbolInfo(BaseModel):
    name: str
    kind: str  # function, class, method
    line_start: int
    line_end: int
    docstring: Optional[str] = None
    args: List[str] = Field(default_factory=list)

class FileOutline(BaseModel):
    file_path: str
    imports: List[str] = Field(default_factory=list)
    symbols: List[SymbolInfo] = Field(default_factory=list)
    line_count: int

class RepoMap(BaseModel):
    repo_path: str
    total_files: int
    files: Dict[str, FileOutline] = Field(default_factory=dict)
    import_graph: Dict[str, List[str]] = Field(default_factory=dict)

class DiagnosticResult(BaseModel):
    target_files: List[str] = Field(default_factory=list)
    target_symbol: str
    line_range: List[int]
    root_cause: str
    confidence: float

class ArchitectBlueprint(BaseModel):
    plan_title: str
    summary: str
    target_files: List[str] = Field(default_factory=list)
    proposed_mutation: str
    safety_constraints: List[str]
    affected_components: List[str]

class ReproductionTest(BaseModel):
    test_file_path: str
    test_name: str
    test_code: str
    adversarial_vectors: List[str] = Field(default_factory=list)  # Boundary, null, timezone offsets
    rationale: str

class FilePatch(BaseModel):
    file_path: str
    original_code_slice: str
    new_code_slice: str
    unified_diff: str
    lines_added: int
    lines_removed: int

class AtomicChangeset(BaseModel):
    patches: List[FilePatch] = Field(default_factory=list)
    total_files_changed: int = 0
    total_lines_added: int = 0
    total_lines_removed: int = 0
    rationale: str = ""

class RejectedHypothesis(BaseModel):
    turn: int
    attempted_changeset_summary: str
    failing_tests: List[str]
    stack_trace: str
    why_it_failed: str

class SentinelCheck(BaseModel):
    is_valid: bool
    imported_modules: List[str]
    unknown_imports: List[str] = Field(default_factory=list)
    violations: List[str] = Field(default_factory=list)

class TestCaseResult(BaseModel):
    nodeid: str
    passed: bool
    duration: float
    error_message: Optional[str] = None

class TestRunResult(BaseModel):
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    regressions: int
    broken_tests: List[str] = Field(default_factory=list)
    tests: List[TestCaseResult] = Field(default_factory=list)
    raw_output: str
    duration_seconds: float

class CriticReview(BaseModel):
    cleanliness_score: int  # 0 to 100
    is_minimal: bool
    cyclomatic_complexity: str
    comments: List[str] = Field(default_factory=list)

class FinalArtifact(BaseModel):
    title: str
    issue_prompt: str
    root_cause_analysis: str
    solution_summary: str
    files_modified: List[str]
    unified_diff: str
    tests_summary: Dict[str, Any]
    zero_regression_verified: bool
    safety_audit: Dict[str, Any]
    scope_note: str  # MVP vs Stretch
    markdown_report: str

class ModelSettings(BaseModel):
    provider_type: str = "anthropic"  # "anthropic", "openai_compatible", "ollama", "simulation"
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None

class RunRequest(BaseModel):
    repo_path: Optional[str] = None
    issue_description: str
    model_settings: Optional[ModelSettings] = None
