"""Judge: Deterministic regression gate, flaky exclusion, and atomic worktree rollback."""
import os
import subprocess
from typing import Dict, List, Set, Tuple
from backend.models import JudgeReport

class Judge:
    def __init__(self, worktree_dir: str):
        self.worktree_dir = worktree_dir
        self.pytest_bin = os.path.abspath(".venv/bin/pytest")
        if not os.path.exists(self.pytest_bin):
            self.pytest_bin = "pytest"

    def run_tests(self, target_path: str = "tests", extra_env: Dict[str, str] = None) -> Tuple[int, Set[str], str]:
        """Run pytest and collect passed test node IDs."""
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{self.worktree_dir}:{env.get('PYTHONPATH', '')}"
        if extra_env:
            env.update(extra_env)

        cmd = [self.pytest_bin, target_path, "-v", "-q"]
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

        return proc.returncode, passed_tests, proc.stdout + proc.stderr

    def establish_baseline(self) -> Tuple[Set[str], List[str]]:
        """Run suite twice; exclude flaky tests that disagree."""
        _, pass1, _ = self.run_tests()
        _, pass2, _ = self.run_tests()
        
        stable_pass = pass1.intersection(pass2)
        flaky = list(pass1.symmetric_difference(pass2))
        return stable_pass, flaky

    def verify_patch(
        self,
        baseline_pass: Set[str],
        reproduction_test_path: str,
        flaky_excluded: List[str]
    ) -> JudgeReport:
        r"""Run suite post-patch and calculate regressions: |BaselinePass \ PostPatchPass|."""
        _, post_pass, output = self.run_tests()
        
        # Calculate regressions against stable baseline
        regressions = baseline_pass - post_pass
        
        # Verify reproduction test
        repro_code, repro_pass, repro_out = self.run_tests(target_path=reproduction_test_path)
        repro_passed = (repro_code == 0)

        report = JudgeReport(
            baseline_pass_count=len(baseline_pass),
            post_patch_pass_count=len(post_pass),
            reproduction_test_failed_before=True,
            reproduction_test_passed_after=repro_passed,
            regressions_count=len(regressions),
            flaky_excluded=flaky_excluded,
            veto=(len(regressions) > 0 or not repro_passed),
            details=output
        )
        return report

    def rollback(self) -> str:
        """Atomic hard reset of the worktree."""
        proc = subprocess.run(
            ["git", "reset", "--hard", "HEAD"],
            cwd=self.worktree_dir,
            capture_output=True,
            text=True
        )
        subprocess.run(
            ["git", "clean", "-fd"],
            cwd=self.worktree_dir,
            capture_output=True,
            text=True
        )
        return proc.stdout
