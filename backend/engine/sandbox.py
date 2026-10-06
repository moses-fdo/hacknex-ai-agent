import subprocess
import time
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from backend.models.schema import TestRunResult, TestCaseResult

class SandboxTestRunner:
    """Isolated subprocess test execution harness with mathematical zero-regression detection."""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.baseline_results: Optional[TestRunResult] = None
        self._file_backups: Dict[str, str] = {}

    def backup_file(self, rel_path: str) -> None:
        full_path = self.repo_path / rel_path
        if full_path.exists() and rel_path not in self._file_backups:
            self._file_backups[rel_path] = full_path.read_text(encoding="utf-8")

    def rollback_file(self, rel_path: str) -> bool:
        if rel_path in self._file_backups:
            full_path = self.repo_path / rel_path
            full_path.write_text(self._file_backups[rel_path], encoding="utf-8")
            return True
        return False

    def rollback_all(self) -> None:
        for rel_path, content in self._file_backups.items():
            full_path = self.repo_path / rel_path
            if full_path.exists():
                full_path.write_text(content, encoding="utf-8")
        self._file_backups.clear()

    def run_pytest(self, test_subpath: Optional[str] = None) -> TestRunResult:
        """Executes pytest in target repo and parses test outcomes."""
        start_time = time.time()
        
        # Use active venv python
        python_bin = sys.executable
        cmd = [python_bin, "-m", "pytest", "-v"]
        if test_subpath:
            cmd.append(test_subpath)
        else:
            cmd.append("tests")

        env = {
            "PYTHONPATH": str(self.repo_path),
            "PATH": subprocess.os.environ.get("PATH", "")
        }

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.repo_path),
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )
            raw_output = proc.stdout + "\n" + proc.stderr
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            raw_output = "ERROR: Pytest execution timed out after 30 seconds."
            exit_code = 124
        except Exception as e:
            raw_output = f"ERROR: Subprocess execution failed: {str(e)}"
            exit_code = 1

        duration = time.time() - start_time
        tests, passed_count, failed_count = self._parse_pytest_output(raw_output)

        # Mathematical regression calculation: R = BaselinePassSet \ PostPatchPassSet
        regressions = 0
        broken_tests: List[str] = []
        if self.baseline_results:
            baseline_passed = {t.nodeid for t in self.baseline_results.tests if t.passed}
            current_passed = {t.nodeid for t in tests if t.passed}
            broken_set = baseline_passed - current_passed
            regressions = len(broken_set)
            broken_tests = sorted(list(broken_set))

        all_passed = (exit_code == 0) and (failed_count == 0) and (regressions == 0)

        result = TestRunResult(
            passed=all_passed,
            total_tests=len(tests),
            passed_tests=passed_count,
            failed_tests=failed_count,
            regressions=regressions,
            broken_tests=broken_tests,
            tests=tests,
            raw_output=raw_output,
            duration_seconds=round(duration, 3)
        )
        return result

    def establish_baseline(self) -> TestRunResult:
        """Executes current repo tests before modifications to establish baseline truth."""
        result = self.run_pytest()
        self.baseline_results = result
        return result

    def _parse_pytest_output(self, output: str) -> Tuple[List[TestCaseResult], int, int]:
        tests: List[TestCaseResult] = []
        passed_count = 0
        failed_count = 0

        # Pattern: path/to/test.py::test_name PASSED / FAILED
        regex = r"^([^\s:]+\.py::[^\s]+)\s+(PASSED|FAILED|ERROR)"
        for line in output.splitlines():
            line_clean = line.strip()
            match = re.match(regex, line_clean)
            if match:
                nodeid = match.group(1)
                status = match.group(2)
                is_pass = status == "PASSED"
                if is_pass:
                    passed_count += 1
                else:
                    failed_count += 1
                tests.append(TestCaseResult(
                    nodeid=nodeid,
                    passed=is_pass,
                    duration=0.01,
                    error_message=None if is_pass else f"Test failed with {status}"
                ))

        return tests, passed_count, failed_count
