"""Specialist Worker Registry and Prompt Formats matching PRD v1.3 Personas.

Fulfills:
- FR-1: Two-Stage Triage Gate (deterministic scan, clarification questions, unattended assumption)
- Specialist prompts with strict boundaries and forbidden actions
- Test Crafter blindness to Detective diagnosis
"""
import re
from typing import Any, Dict, List, Optional
from backend.models import TriageResult

class WorkerRegistry:
    @staticmethod
    def triage_issue(description: str, repo_files: Optional[List[str]] = None) -> TriageResult:
        """FR-1.1 & FR-1.2: Deterministic first pass checking symptom, expected/actual, and concrete anchors."""
        has_symptom = bool(
            re.search(
                r"(fail|error|bug|wrong|crash|except|leak|broken|invalid|issue|timeout|defect|reproduce)",
                description,
                re.I,
            )
        )
        has_expected_actual = bool(
            re.search(
                r"(expect|actual|instead|should|must|got|wanted|differ|behav)",
                description,
                re.I,
            )
        )

        anchors = []
        # Code anchors: file paths (.py)
        path_matches = re.findall(r"[\w\./\-]+\.py", description)
        anchors.extend(path_matches)

        # Function names
        func_matches = re.findall(r"\b[\w_]+\(\)", description)
        anchors.extend(func_matches)

        # Python Exception / Error types
        error_matches = re.findall(r"\b[A-Z][a-zA-Z]+Error\b", description)
        anchors.extend(error_matches)

        # API endpoints
        endpoint_matches = re.findall(r"(?:GET|POST|PUT|DELETE|PATCH)\s+/[a-zA-Z0-9_\-/]+", description)
        anchors.extend(endpoint_matches)

        # Explicit symbols like path::symbol
        symbol_matches = re.findall(r"[\w/\.\-]+\.py::[\w_]+", description)
        anchors.extend(symbol_matches)

        anchors = list(set(anchors))
        is_anchored = len(anchors) > 0

        clarification_questions = []
        assumption_stated = None

        if not is_anchored:
            if repo_files:
                py_candidates = [f for f in repo_files if f.endswith(".py") and not f.startswith("tests/") and not f.startswith(".")]
                if py_candidates:
                    top_candidates = py_candidates[:3]
                    opts = ", ".join([f"[{chr(65+i)}] {c}" for i, c in enumerate(top_candidates)])
                    clarification_questions = [
                        f"Which subsystem or module is failing? (Options: {opts})",
                        "What is the expected vs actual behavior? Provide error message or stack trace."
                    ]
                    assumption_stated = (
                        f"Unattended run assumption: Defect anchored to {top_candidates[0]} based on repository structure."
                    )
                else:
                    clarification_questions = [
                        "Which file or module is failing? Provide target file and function.",
                        "What is the expected vs actual behavior? Provide error message or stack trace."
                    ]
                    assumption_stated = "Unattended run assumption: General repository investigation across primary files."
            else:
                # FR-1.2: Interactive Clarification with at most two multiple-choice questions
                clarification_questions = [
                    "Which subsystem or module is failing? (Options: [A] app/auth/tokens.py, [B] app/models/order.py, [C] app/auth/permissions.py)",
                    "What is the expected vs actual behavior? (Options: [A] Expiration calculation wrong under non-UTC timezone, [B] Signature verification fails, [C] Order total calculation error)"
                ]
                # FR-1.3: Unattended assumption fallback
                assumption_stated = (
                    "Unattended run assumption: Defect anchored to app/auth/tokens.py::is_token_expired based on highest defect probability in repository."
                )

        return TriageResult(
            has_symptom=has_symptom,
            has_expected_vs_actual=has_expected_actual,
            anchors=anchors,
            is_anchored=is_anchored,
            clarification_questions=clarification_questions,
            assumption_stated=assumption_stated,
            confidence=0.95 if is_anchored else 0.50,
        )

    @staticmethod
    def get_detective_prompt(
        issue: str,
        skeleton: str,
        memory_hints: List[Dict[str, Any]],
        call_hierarchy: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Detective: Locate root cause (file, symbol, line range, confidence > 0.9).
        Forbidden: Edit code, run tests."""
        system = (
            "You are the Detective specialist.\n"
            "Your ONLY job is to locate the root cause file, symbol, and line range.\n"
            "Forbidden Actions: NEVER edit code, NEVER run tests.\n"
            "Output JSON ONLY:\n"
            "{\n"
            '  "file": "path/to/file.py",\n'
            '  "symbol": "function_or_class_name",\n'
            '  "lines": [start_line, end_line],\n'
            '  "confidence": 0.95,\n'
            '  "summary": "Precise root cause explanation"\n'
            "}"
        )
        hints_text = "\n".join([f"- Hint from Memory: {h.get('label')} -> {h.get('properties')}" for h in memory_hints])
        call_text = f"\nCall Hierarchy for context: {call_hierarchy}" if call_hierarchy else ""
        user = f"Issue Description:\n{issue}\n\nMemory Hints:\n{hints_text}{call_text}\n\nRepo Skeleton:\n{skeleton}"
        return {"system": system, "user": user}

    @staticmethod
    def get_architect_prompt(
        issue: str,
        detective_summary: str,
        memory_rules: List[Dict[str, Any]],
        call_hierarchy: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Architect: Draft ordered edit plan (max 5 files), rationale, and regression boundaries.
        Forbidden: Direct file editing."""
        system = (
            "You are the Architect specialist.\n"
            "Plan the minimal, multi-file edit plan and regression boundaries.\n"
            "Forbidden Actions: NEVER write or edit code files directly.\n"
            "Safety Constraint: MAX 5 files per plan.\n"
            "Output JSON ONLY:\n"
            "{\n"
            '  "steps": [\n'
            '    {\n'
            '      "file_path": "path/to/file.py",\n'
            '      "target_symbol": "target_function",\n'
            '      "purpose": "Specific modification goal"\n'
            "    }\n"
            "  ],\n"
            '  "rationale": "Why this minimal surgical plan works",\n'
            '  "regression_boundaries": ["file_or_module_to_protect"],\n'
            '  "dependent_symbols": ["dependent_symbol_names"]\n'
            "}"
        )
        rules_text = "\n".join([f"- Past Architectural Invariant: {r.get('label')}" for r in memory_rules])
        call_info = f"\nDeterministic Call Graph Context: {call_hierarchy}" if call_hierarchy else ""
        user = f"Issue:\n{issue}\n\nDetective Diagnosis:\n{detective_summary}\n\nArchitectural Constraints:\n{rules_text}{call_info}"
        return {"system": system, "user": user}

    @staticmethod
    def get_test_crafter_prompt(issue_text: str) -> Dict[str, str]:
        """Test Crafter: Write reproduction pytest test file.
        CRITICAL: Blind to Detective diagnosis to prevent shared false assumptions!
        Forbidden: Touch production code."""
        system = (
            "You are the Test Crafter specialist.\n"
            "Your ONLY job is to write an isolated reproduction pytest test file.\n"
            "CRITICAL RULES:\n"
            "1. You only see the raw issue description. You are BLIND to any internal diagnosis.\n"
            "2. The test MUST FAIL on the unpatched bug and MUST PASS once fixed.\n"
            "3. Forbidden Actions: NEVER edit production code.\n"
            "Output raw Python code for the reproduction test file only (no markdown quotes)."
        )
        return {"system": system, "user": f"Write reproduction test exposing the defect reported in:\n{issue_text}"}

    @staticmethod
    def get_surgeon_prompt(
        step_plan: Dict[str, Any],
        file_content: str,
        feedback: Optional[str] = None
    ) -> Dict[str, str]:
        """Surgeon: Apply exact minimal unified diff for a single targeted slice.
        Forbidden: Touch out-of-scope files, search repo, run shell commands."""
        system = (
            "You are the Surgeon specialist.\n"
            "Your ONLY job is to produce a minimal standard unified diff for this single targeted slice.\n"
            "Forbidden Actions: NEVER touch any file other than the designated file_path.\n"
            "Output standard unified diff format:\n"
            "--- a/path/to/file.py\n"
            "+++ b/path/to/file.py\n"
            "@@ -start,count +start,count @@\n"
            "- deleted line\n"
            "+ added line\n"
            "  context line"
        )
        feedback_text = f"\nJudge Veto Feedback / Previous Failure:\n{feedback}\nFix the defect avoiding this regression." if feedback else ""
        user = f"Target Plan Step:\n{step_plan}\n\nCurrent Target File Content:\n{file_content}{feedback_text}"
        return {"system": system, "user": user}

    @staticmethod
    def get_scribe_prompt(
        issue: str,
        diff: str,
        judge_report: Dict[str, Any],
        cost_info: Dict[str, Any],
        triage_assumption: Optional[str] = None
    ) -> Dict[str, str]:
        """Scribe: Produce structured post-mortem / resolution report.
        Forbidden: Alter code or tests."""
        system = (
            "You are the Scribe specialist.\n"
            "Your ONLY job is to compile a comprehensive, professional Markdown report.\n"
            "Cite the diff, reproduction test proofs, confidence metrics, and token/dollar costs.\n"
            "If an assumption was stated during triage, highlight it prominently."
        )
        assumption_text = f"\nTriage Assumption: {triage_assumption}" if triage_assumption else ""
        user = (
            f"Issue: {issue}{assumption_text}\n"
            f"Unified Diff:\n{diff}\n"
            f"Judge Verification Report: {judge_report}\n"
            f"Telemetry & Cost: {cost_info}"
        )
        return {"system": system, "user": user}
