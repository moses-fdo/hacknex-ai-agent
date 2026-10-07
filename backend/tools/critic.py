"""Critic: Deterministic code cleanliness and total diff size scoring.

Fulfills PRD v1.3 FR-5.5:
- Cleanliness score (0-100)
- Progressive diff size penalties across all modified files
- Output structured CriticReport
"""
from backend.models import CriticReport

class Critic:
    @staticmethod
    def evaluate_diff(unified_diff: str, max_expected_lines: int = 20) -> CriticReport:
        """Score cleanliness 0-100 based on total diff size and targeted minimal scope."""
        added_lines = 0
        deleted_lines = 0

        for line in unified_diff.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added_lines += 1
            elif line.startswith("-") and not line.startswith("---"):
                deleted_lines += 1

        total_lines_changed = added_lines + deleted_lines

        # Base score 100
        score = 100
        penalty = 0

        # Penalize excessive diff size progressively
        if total_lines_changed > max_expected_lines:
            excess = total_lines_changed - max_expected_lines
            penalty = min(50, excess * 2)
            score -= penalty

        # Penalize empty diff
        if total_lines_changed == 0:
            score = 0
            penalty = 100

        summary = f"Critic Score: {score}/100 (+{added_lines}, -{deleted_lines} lines across slice)"
        if penalty > 0:
            summary += f" (Diff penalty: -{penalty} pts)"

        return CriticReport(
            score=score,
            added_lines=added_lines,
            deleted_lines=deleted_lines,
            total_lines_changed=total_lines_changed,
            penalty=penalty,
            summary=summary,
        )
