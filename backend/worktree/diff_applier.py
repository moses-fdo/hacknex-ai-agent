"""Unified diff parser and robust hunk applier with Scope Guard enforcement."""
import re
from typing import Any, Dict, List, Optional, Tuple

class ScopeGuardViolation(Exception):
    pass

class DiffApplier:
    @staticmethod
    def parse_unified_diff(diff_text: str) -> List[Dict[str, Any]]:
        """Parse unified diff text into a structured list of per-file hunk sets."""
        files = []
        current_file = None
        current_hunk = None

        lines = diff_text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("--- "):
                # Start of file
                old_file = line[4:].strip()
                if old_file.startswith("a/"):
                    old_file = old_file[2:]
                i += 1
                if i < len(lines) and lines[i].startswith("+++ "):
                    new_file = lines[i][4:].strip()
                    if new_file.startswith("b/"):
                        new_file = new_file[2:]
                    current_file = {
                        "old_file": old_file,
                        "new_file": new_file,
                        "hunks": []
                    }
                    files.append(current_file)
                i += 1
                continue

            hunk_match = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if hunk_match and current_file is not None:
                current_hunk = {
                    "old_start": int(hunk_match.group(1)),
                    "old_count": int(hunk_match.group(2) or 1),
                    "new_start": int(hunk_match.group(3)),
                    "new_count": int(hunk_match.group(4) or 1),
                    "lines": []
                }
                current_file["hunks"].append(current_hunk)
                i += 1
                continue

            if current_hunk is not None:
                if line.startswith(("+", "-", " ")) or line == "":
                    current_hunk["lines"].append(line)
            i += 1

        return files

    @staticmethod
    def apply_hunk_to_lines(target_lines: List[str], hunk: Dict[str, Any]) -> Tuple[bool, List[str], str]:
        """Apply a single hunk to target lines with fuzzy offset tolerance."""
        hunk_lines = hunk["lines"]
        expected_old_lines = [l[1:] for l in hunk_lines if l.startswith(("-", " "))]

        if not expected_old_lines:
            return True, target_lines, "Empty hunk"

        # Try exact start position first (1-indexed in hunk)
        start_idx = max(0, hunk["old_start"] - 1)
        search_radius = max(20, len(target_lines))

        best_pos = -1
        # 1. Search around target start index
        for delta in range(0, search_radius):
            for candidate in [start_idx + delta, start_idx - delta]:
                if candidate < 0 or candidate + len(expected_old_lines) > len(target_lines):
                    continue
                match = True
                for j, exp_line in enumerate(expected_old_lines):
                    if target_lines[candidate + j] != exp_line:
                        match = False
                        break
                if match:
                    best_pos = candidate
                    break
            if best_pos != -1:
                break

        # 2. Fuzzy search (strip whitespace match)
        if best_pos == -1:
            for candidate in range(0, len(target_lines) - len(expected_old_lines) + 1):
                match = True
                for j, exp_line in enumerate(expected_old_lines):
                    if target_lines[candidate + j].strip() != exp_line.strip():
                        match = False
                        break
                if match:
                    best_pos = candidate
                    break

        if best_pos == -1:
            return False, target_lines, "Could not find matching hunk anchor lines in target file"

        # Apply changes at best_pos
        new_result = list(target_lines[:best_pos])
        cur_old_idx = best_pos

        for hl in hunk_lines:
            if hl.startswith("-"):
                cur_old_idx += 1
            elif hl.startswith("+"):
                new_result.append(hl[1:])
            elif hl.startswith(" "):
                new_result.append(hl[1:])
                cur_old_idx += 1
            else:
                # Blank context line
                new_result.append(hl)
                cur_old_idx += 1

        new_result.extend(target_lines[cur_old_idx:])
        return True, new_result, "Hunk applied"

    @classmethod
    def apply_patch_to_content(
        cls,
        original_content: str,
        diff_text: str,
        target_file: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        """Apply unified diff to single file content."""
        parsed_files = cls.parse_unified_diff(diff_text)
        
        # If standard diff format parsed
        if parsed_files:
            file_diff = parsed_files[0]
            target_lines = original_content.splitlines()
            for hunk in file_diff["hunks"]:
                success, target_lines, msg = cls.apply_hunk_to_lines(target_lines, hunk)
                if not success:
                    # Fallback to direct string hunk substitution
                    return cls._fallback_string_replacement(original_content, hunk)
            
            # Keep original newline format
            ending = "\n" if original_content.endswith("\n") else ""
            return True, "\n".join(target_lines) + ending, "Diff successfully applied"

        # If diff_text is a loose diff block without headers
        return cls._apply_loose_diff(original_content, diff_text)

    @classmethod
    def _fallback_string_replacement(cls, original_content: str, hunk: Dict[str, Any]) -> Tuple[bool, str, str]:
        """Fallback: match old block text directly and replace with new block text."""
        old_block = "\n".join([l[1:] for l in hunk["lines"] if l.startswith(("-", " "))])
        new_block = "\n".join([l[1:] for l in hunk["lines"] if l.startswith(("+", " "))])

        if old_block in original_content:
            return True, original_content.replace(old_block, new_block, 1), "Applied via exact block fallback"

        # Try stripped match
        old_stripped = "\n".join([l[1:].strip() for l in hunk["lines"] if l.startswith(("-", " ")) if l[1:].strip()])
        new_stripped = "\n".join([l[1:] for l in hunk["lines"] if l.startswith(("+", " "))])

        # If lines to remove can be found
        removed_lines = [l[1:].strip() for l in hunk["lines"] if l.startswith("-") if l[1:].strip()]
        added_lines = [l[1:] for l in hunk["lines"] if l.startswith("+")]

        if removed_lines and added_lines:
            target_text = original_content
            for r in removed_lines:
                for line in target_text.splitlines():
                    if r in line:
                        target_text = target_text.replace(line, "\n".join(added_lines), 1)
                        return True, target_text, "Applied via line match fallback"

        return False, original_content, "Hunk matching failed"

    @classmethod
    def _apply_loose_diff(cls, original_content: str, diff_text: str) -> Tuple[bool, str, str]:
        """Apply loose +/- diff lines without git diff header."""
        minus_lines = [l[1:].strip() for l in diff_text.splitlines() if l.startswith("-") and not l.startswith("---")]
        plus_lines = [l[1:] for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++")]

        if not minus_lines or not plus_lines:
            return False, original_content, "No replacement hunks identified in diff"

        content = original_content
        for m in minus_lines:
            for line in content.splitlines():
                if m in line:
                    replacement = "\n".join(plus_lines)
                    content = content.replace(line, replacement, 1)
                    return True, content, "Applied loose diff replacement"

        return False, original_content, "Could not locate target lines in content"

    @classmethod
    def enforce_scope_guard(cls, diff_text: str, allowed_files: List[str]) -> None:
        """Physical check: raise ScopeGuardViolation if diff tries to edit any file outside approved plan."""
        parsed = cls.parse_unified_diff(diff_text)
        for pf in parsed:
            target = pf.get("new_file") or pf.get("old_file")
            if target:
                clean_target = target.replace("\\", "/").strip()
                clean_allowed = [f.replace("\\", "/").strip() for f in allowed_files]
                if not any(clean_target.endswith(a) or a.endswith(clean_target) for a in clean_allowed):
                    raise ScopeGuardViolation(
                        f"Scope Guard Rejection: Diff attempts to modify '{target}' which is not in the approved Architect plan: {allowed_files}"
                    )
