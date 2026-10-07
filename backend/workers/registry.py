"""Specialist Worker Registry and Prompt Formats."""
import re
from typing import Any, Dict, List
from backend.models import TriageResult

class WorkerRegistry:
    @staticmethod
    def triage_issue(description: str) -> TriageResult:
        """Stage 1: Deterministic regex/heuristic check for symptoms and anchors."""
        has_symptom = bool(re.search(r"(fail|error|bug|wrong|crash|except|leak|broken|invalid|issue)", description, re.I))
        has_expected_actual = bool(re.search(r"(expect|actual|instead|should|must)", description, re.I))
        
        # Look for code anchors: file paths (.py), function names (def or func()), or error types
        anchors = []
        path_matches = re.findall(r"[\w\./\-]+\.py", description)
        anchors.extend(path_matches)
        
        func_matches = re.findall(r"[\w_]+\(\)", description)
        anchors.extend(func_matches)

        error_matches = re.findall(r"\b[A-Z][a-zA-Z]+Error\b", description)
        anchors.extend(error_matches)

        is_anchored = len(anchors) > 0

        clarification_questions = []
        assumption_stated = None

        if not is_anchored:
            clarification_questions = [
                "Which subsystem or module is failing? (e.g. app/auth/tokens.py, permissions, or orders?)",
                "What is the exact observed error or unexpected behavior?"
            ]
            assumption_stated = "Unattended run assumed target module is app/auth/tokens.py based on highest defect probability."

        return TriageResult(
            has_symptom=has_symptom,
            has_expected_vs_actual=has_expected_actual,
            anchors=list(set(anchors)),
            is_anchored=is_anchored,
            clarification_questions=clarification_questions,
            assumption_stated=assumption_stated,
        )

    @staticmethod
    def get_detective_prompt(issue: str, skeleton: str, memory_hints: List[Dict[str, Any]]) -> Dict[str, str]:
        system = (
            "You are the Detective specialist. Your ONLY job is to locate the root cause file, symbol, and line range.\n"
            "Return JSON matching: {\"file\": str, \"symbol\": str, \"lines\": [int, int], \"confidence\": float, \"summary\": str}\n"
            "Never write patches or execute tests."
        )
        hints_text = "\n".join([f"- Hint from Memory: {h.get('label')} -> {h.get('properties')}" for h in memory_hints])
        user = f"Issue:\n{issue}\n\nMemory Hints:\n{hints_text}\n\nRepo Skeleton:\n{skeleton}"
        return {"system": system, "user": user}

    @staticmethod
    def get_architect_prompt(issue: str, detective_summary: str, memory_rules: List[Dict[str, Any]]) -> Dict[str, str]:
        system = (
            "You are the Architect specialist. Plan the minimal, multi-file edit plan and regression boundaries.\n"
            "Return JSON matching: {\"steps\": [{\"file_path\": str, \"target_symbol\": str, \"purpose\": str}], "
            "\"rationale\": str, \"regression_boundaries\": [str]}\n"
            "Max 5 files."
        )
        rules_text = "\n".join([f"- Past Decision: {r.get('label')}" for r in memory_rules])
        user = f"Issue:\n{issue}\n\nDetective Diagnosis:\n{detective_summary}\n\nPast Architectural Invariants:\n{rules_text}"
        return {"system": system, "user": user}

    @staticmethod
    def get_test_crafter_prompt(issue_text: str) -> Dict[str, str]:
        """CRITICAL: Blind to Detective diagnosis to prevent shared false assumptions."""
        system = (
            "You are the Test Crafter specialist. You write an isolated reproduction pytest test file.\n"
            "The test MUST fail on the unpatched bug and pass once fixed.\n"
            "You only see the raw issue text. Output raw Python code for the test file."
        )
        return {"system": system, "user": f"Write reproduction test for issue:\n{issue_text}"}

    @staticmethod
    def get_surgeon_prompt(step_plan: Dict[str, Any], file_content: str) -> Dict[str, str]:
        system = (
            "You are the Surgeon specialist. Apply the exact minimal unified diff for this single targeted slice.\n"
            "Do not touch any other symbols or files. Output a standard unified diff."
        )
        user = f"Target Plan Step:\n{step_plan}\n\nCurrent File Content:\n{file_content}"
        return {"system": system, "user": user}

    @staticmethod
    def get_scribe_prompt(issue: str, diff: str, judge_report: Dict[str, Any], cost_info: Dict[str, Any]) -> Dict[str, str]:
        system = (
            "You are the Scribe specialist. Write a clean root cause analysis markdown report.\n"
            "Cite the diff, the reproduction test proofs, confidence metrics, and token/dollar costs."
        )
        user = f"Issue: {issue}\nDiff:\n{diff}\nJudge Report: {judge_report}\nCost Telemetry: {cost_info}"
        return {"system": system, "user": user}
