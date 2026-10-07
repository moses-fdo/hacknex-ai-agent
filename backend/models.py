"""Shared Pydantic data schemas for Aether-SWE."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class WorkerKind(str, Enum):
    LLM = "llm"
    TOOL = "tool"

class RunStatus(str, Enum):
    PENDING = "pending"
    TRIAGE = "triage"
    RUNNING = "running"
    JUDGE_VETO = "judge_veto"
    COULD_NOT_REPRODUCE = "could_not_reproduce"
    ENVIRONMENT_NOT_READY = "environment_not_ready"
    COMPLETED = "completed"
    FAILED = "failed"
    BUDGET_EXCEEDED = "budget_exceeded"

class IssueInput(BaseModel):
    issue_id: str = "custom-issue"
    title: str = "Reported Defect"
    description: str
    repo_path: str = "benchmarks/ecommerce_api"
    model: str = "default"
    use_worktree: bool = True
    base_branch: str = "main"
    max_budget_usd: float = 1.00
    unattended: bool = True

class TriageResult(BaseModel):
    has_symptom: bool
    has_expected_vs_actual: bool
    anchors: List[str] = Field(default_factory=list)
    is_anchored: bool
    clarification_questions: List[str] = Field(default_factory=list)
    assumption_stated: Optional[str] = None

class EditStep(BaseModel):
    file_path: str
    target_symbol: str
    purpose: str
    patch_diff: Optional[str] = None

class MultiFilePlan(BaseModel):
    steps: List[EditStep] = Field(default_factory=list)
    rationale: str = ""
    regression_boundaries: List[str] = Field(default_factory=list)

class WorkerResult(BaseModel):
    worker_name: str
    success: bool
    summary: str
    data: Dict[str, Any] = Field(default_factory=dict)
    log_path: Optional[str] = None
    cost_usd: float = 0.0
    tokens_used: int = 0

class JudgeReport(BaseModel):
    baseline_pass_count: int = 0
    post_patch_pass_count: int = 0
    reproduction_test_failed_before: bool = False
    reproduction_test_passed_after: bool = False
    regressions_count: int = 0
    flaky_excluded: List[str] = Field(default_factory=list)
    veto: bool = False
    details: str = ""

class MemoryNode(BaseModel):
    id: str
    node_type: str  # 'File', 'Symbol', 'ArchitecturalDecision', 'HistoricalBug', 'VetoRecord'
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    provenance_run_id: Optional[str] = None
    provenance_commit_sha: Optional[str] = None
    is_provisional: bool = False
    is_stale: bool = False
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class MemoryEdge(BaseModel):
    source: str
    target: str
    relation: str  # 'DEFINES', 'CALLS', 'DEPENDS_ON', 'CONSTRAINED_BY', 'RESOLVED_BY', 'VETOED_BECAUSE'

class RunEvent(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    run_id: str
    persona: str
    kind: WorkerKind
    action: str
    status: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
