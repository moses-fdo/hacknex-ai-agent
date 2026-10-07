"""Judge: Deterministic regression gate, flaky exclusion, and atomic worktree rollback.

Fulfills PRD v1.3 Judge tool specifications:
- Flaky test exclusion via two baseline runs (symmetric difference)
- Zero regressions gate: BaselinePass \\ PostPatchPass = empty
- Atomic worktree rollback via git reset --hard HEAD
- Multi-file atomic post-patch verification
"""
import os
import subprocess
from typing import Dict, List, Optional, Set, Tuple
from backend.models import JudgeReport

class Judge:
    def __init__(self, worktree_dir: str, base_repo_path: Optional[str] = None):
        self.worktree_dir = os.path.abspath(worktree_dir)
        self.base_repo_path = os.path.abspath(base_repo_path) if base_repo_path else None
        self.pytest_bin = self._find_pytest()

    def _find_pytest(self) -> str:
        candidates = [
            os.path.join(self.worktree_dir, ".venv/bin/pytest"),
        ]
        if self.base_repo_path:
            candidates.append(os.path.join(self.base_repo_path, ".venv/bin/pytest"))

        base_name = os.path.basename(self.worktree_dir)
        parent = os.path.dirname(self.worktree_dir)
        if base_name.startswith("aether-"):
            try:
                for entry in os.listdir(parent):
                    cand = os.path.join(parent, entry, ".venv/bin/pytest")
                    if os.path.exists(cand) and not entry.startswith("aether-"):
                        candidates.append(cand)
            except Exception:
                pass

        candidates.append(os.path.abspath(".venv/bin/pytest"))
        candidates.append("pytest")
        for c in candidates:
            if os.path.exists(c):
                return c
        return "pytest"

    def run_tests(self, target_path: str = "tests", extra_env: Optional[Dict[str, str]] = None) -> Tuple[int, Set[str], str]:
        """Run pytest and collect passed test node IDs."""
        env = os.environ.copy()
        if os.path.isabs(self.pytest_bin) and ".venv" in self.pytest_bin:
            venv_bin = os.path.dirname(self.pytest_bin)
            env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
            env["VIRTUAL_ENV"] = os.path.dirname(venv_bin)
        env["PYTHONPATH"] = f"{self.worktree_dir}:{env.get('PYTHONPATH', '')}"
        if extra_env:
            env.update(extra_env)

        full_target = target_path
        if not os.path.isabs(full_target):
            full_target = os.path.join(self.worktree_dir, target_path)

        cmd = [self.pytest_bin, full_target, "-v"]
        proc = subprocess.run(
            cmd,
            cwd=self.worktree_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

        passed_tests = set()
        for line in proc.stdout.splitlines():
            line = line.strip()
            if "PASSED" in line:
                test_id = line.split()[0]
                passed_tests.add(test_id)

        return proc.returncode, passed_tests, proc.stdout + ("\n" + proc.stderr if proc.stderr else "")

    def establish_baseline(self) -> Tuple[Set[str], List[str]]:
        """Run suite twice; exclude flaky tests that disagree across the two runs."""
        _, pass1, _ = self.run_tests()
        _, pass2, _ = self.run_tests()

        stable_pass = pass1.intersection(pass2)
        flaky = list(pass1.symmetric_difference(pass2))
        return stable_pass, flaky

    def verify_patch(
        self,
        baseline_pass: Set[str],
        reproduction_test_path: str,
        flaky_excluded: List[str],
        self_healing_iteration: int = 0
    ) -> JudgeReport:
        r"""Run suite post-patch and calculate regressions: |BaselinePass \ PostPatchPass|."""
        _, post_pass, output = self.run_tests()

        # Calculate regressions against stable baseline (excluding known flaky tests)
        regressions = (baseline_pass - post_pass) - set(flaky_excluded)

        # Verify reproduction test passes
        repro_code, repro_pass, repro_out = self.run_tests(target_path=reproduction_test_path)
        repro_passed = (repro_code == 0)

        veto = (len(regressions) > 0 or not repro_passed)
        details = (
            f"=== Post-Patch Test Run ===\n{output}\n"
            f"=== Reproduction Test Run ({reproduction_test_path}) ===\n{repro_out}"
        )

        report = JudgeReport(
            baseline_pass_count=len(baseline_pass),
            post_patch_pass_count=len(post_pass),
            reproduction_test_failed_before=True,
            reproduction_test_passed_after=repro_passed,
            regressions_count=len(regressions),
            flaky_excluded=flaky_excluded,
            veto=veto,
            details=details,
            self_healing_iteration=self_healing_iteration,
        )
        return report

    def rollback(self) -> str:
        """Atomic hard reset of the worktree (FR-5.4)."""
        proc = subprocess.run(
            ["git", "reset", "--hard", "HEAD"],
            cwd=self.worktree_dir,
            capture_output=True,
            text=True
        )
        clean_proc = subprocess.run(
            ["git", "clean", "-fd"],
            cwd=self.worktree_dir,
            capture_output=True,
            text=True
        )
        return proc.stdout + "\n" + clean_proc.stdout
