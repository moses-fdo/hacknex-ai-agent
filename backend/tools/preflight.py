"""Deterministic Preflight Tool (owned by Judge). Checks environment readiness.

Fulfills PRD v1.3 FR-3:
- FR-3.1: Preflight Tool Ownership (owned by Judge)
- FR-3.2: Parse .env.example into temporary environment variables, docker-compose support
- FR-3.3: Failure classification into ENVIRONMENT_NOT_READY with exact remediation instructions
- FR-3.4: Python >= 3.10 support matrix
"""
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Tuple
from backend.models import PreflightReport

class PreflightCheck:
    def __init__(self, repo_path: str, base_repo_path: Optional[str] = None):
        self.repo_path = os.path.abspath(repo_path)
        self.base_repo_path = os.path.abspath(base_repo_path) if base_repo_path else None

    def _find_pytest(self) -> Optional[str]:
        candidates = [
            os.path.join(self.repo_path, ".venv/bin/pytest"),
        ]
        if self.base_repo_path:
            candidates.append(os.path.join(self.base_repo_path, ".venv/bin/pytest"))

        base_name = os.path.basename(self.repo_path)
        parent = os.path.dirname(self.repo_path)
        if base_name.startswith("aether-"):
            try:
                for entry in os.listdir(parent):
                    cand = os.path.join(parent, entry, ".venv/bin/pytest")
                    if os.path.exists(cand) and not entry.startswith("aether-"):
                        candidates.append(cand)
            except Exception:
                pass

        candidates.append(os.path.abspath(".venv/bin/pytest"))
        if shutil.which("pytest"):
            candidates.append(shutil.which("pytest"))

        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    def parse_env_example(self) -> Dict[str, str]:
        """FR-3.2: Parse .env.example into temporary environment variables. Real .env is never read."""
        env_example_path = os.path.join(self.repo_path, ".env.example")
        if not os.path.exists(env_example_path):
            # Check parent directory as well
            parent_example = os.path.join(os.path.dirname(self.repo_path), ".env.example")
            if os.path.exists(parent_example):
                env_example_path = parent_example
            else:
                return {}

        injected = {}
        try:
            with open(env_example_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        # Strip inline comments
                        val = val.split("#")[0].strip()
                        injected[key.strip()] = val.strip().strip("'\"")
        except Exception:
            pass
        return injected

    def check_docker_compose(self) -> Tuple[bool, str]:
        """FR-3.2: If docker-compose.yml is present, check readiness."""
        compose_file = os.path.join(self.repo_path, "docker-compose.yml")
        if not os.path.exists(compose_file):
            return True, "No docker-compose.yml found; using local mocks/SQLite."

        if not shutil.which("docker-compose") and not shutil.which("docker"):
            return False, "ENVIRONMENT_NOT_READY: docker-compose required by repository but docker binary is not installed."

        try:
            # Poll status
            cmd = ["docker", "compose", "ps"] if shutil.which("docker") else ["docker-compose", "ps"]
            res = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return True, "Docker compose services healthy"
        except Exception:
            pass

        return True, "Docker compose configured"

    def run_check(self) -> Tuple[bool, PreflightReport]:
        """Execute full deterministic preflight check before any agent begins analysis."""
        report = PreflightReport()

        # 1. Python version check (FR-3.4: Python >= 3.10)
        py_ver = sys.version_info
        report.python_version = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"
        if py_ver.major < 3 or (py_ver.major == 3 and py_ver.minor < 10):
            report.is_ready = False
            report.python_valid = False
            report.status = "ENVIRONMENT_NOT_READY"
            report.error_message = f"Python {report.python_version} is unsupported. Python >= 3.10 is required."
            report.remediation = "Upgrade Python runtime to >= 3.10 using pyenv or package manager."
            return False, report

        # 2. Test runner availability
        pytest_path = self._find_pytest()

        if not pytest_path:
            report.is_ready = False
            report.pytest_available = False
            report.status = "ENVIRONMENT_NOT_READY"
            report.error_message = "Test runner (pytest) not found in environment or .venv."
            report.remediation = "Install test runner via: pip install pytest (or run bash run.sh to create .venv)."
            return False, report

        report.pytest_available = True
        report.pytest_path = pytest_path

        # 3. Environment variables from .env.example
        injected_env = self.parse_env_example()
        report.env_example_present = len(injected_env) > 0
        report.env_vars_injected = list(injected_env.keys())

        # 4. Docker compose check
        docker_ok, docker_msg = self.check_docker_compose()
        report.docker_compose_present = os.path.exists(os.path.join(self.repo_path, "docker-compose.yml"))
        if not docker_ok:
            report.is_ready = False
            report.status = "ENVIRONMENT_NOT_READY"
            report.error_message = docker_msg
            report.remediation = "Start Docker daemon and run: docker compose up -d"
            return False, report

        # 5. Quick test collection check to verify baseline suite is executable
        tests_dir = os.path.join(self.repo_path, "tests")
        if os.path.exists(tests_dir):
            env = os.environ.copy()
            if os.path.isabs(pytest_path) and ".venv" in pytest_path:
                venv_bin = os.path.dirname(pytest_path)
                env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
                env["VIRTUAL_ENV"] = os.path.dirname(venv_bin)
            env["PYTHONPATH"] = f"{self.repo_path}:{env.get('PYTHONPATH', '')}"
            env.update(injected_env)

            proc = subprocess.run(
                [pytest_path, "--collect-only", "-q"],
                cwd=self.repo_path,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if proc.returncode != 0:
                # FR-3.3: Classify if environment failure
                err_text = proc.stderr + proc.stdout
                if "ModuleNotFoundError" in err_text or "ImportError" in err_text or "ConnectionRefused" in err_text:
                    report.is_ready = False
                    report.baseline_run_ok = False
                    report.status = "ENVIRONMENT_NOT_READY"
                    report.error_message = f"Environment dependency error during test collection:\n{err_text.strip()}"
                    report.remediation = "Install missing dependencies via: pip install -r requirements.txt"
                    return False, report

        report.is_ready = True
        report.status = "READY"
        return True, report
