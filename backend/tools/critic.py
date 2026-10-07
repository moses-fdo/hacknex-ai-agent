"""Critic: Deterministic code cleanliness and total diff size scoring."""
from typing import Dict, Any

class Critic:
    @staticmethod
    def evaluate_diff(unified_diff: str, max_expected_lines: int = 20) -> Dict[str, Any]:
        """Score cleanliness 0-100 based on diff size, readability, and targeted scope."""
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
        
        # Penalize excessive diff size progressively
        if total_lines_changed > max_expected_lines:
            excess = total_lines_changed - max_expected_lines
            penalty = min(40, excess * 2)
            score -= penalty

        # Penalize empty diff
        if total_lines_changed == 0:
            score = 0

        return {
            "score": score,
            "added_lines": added_lines,
            "deleted_lines": deleted_lines,
            "total_lines_changed": total_lines_changed,
            "summary": f"Critic Score: {score}/100 ({added_lines} additions, {deleted_lines} deletions)"
        }
