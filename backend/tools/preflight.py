"""Deterministic Preflight Tool (owned by Judge side). Checks environment readiness."""
import os
import shutil
import subprocess
from typing import Dict, Any, Tuple

class PreflightCheck:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def run_check(self) -> Tuple[bool, str, Dict[str, Any]]:
        details = {
            "python_executable": shutil.which("python3") or shutil.which("python"),
            "pytest_available": False,
            "docker_compose_present": os.path.exists(os.path.join(self.repo_path, "docker-compose.yml")),
            "env_example_present": os.path.exists(os.path.join(self.repo_path, ".env.example")),
        }

        # Check pytest in venv or environment
        venv_pytest = os.path.abspath(".venv/bin/pytest")
        if os.path.exists(venv_pytest):
            details["pytest_available"] = True
            details["pytest_path"] = venv_pytest
        elif shutil.which("pytest"):
            details["pytest_available"] = True
            details["pytest_path"] = shutil.which("pytest")
        else:
            return False, "ENVIRONMENT_NOT_READY: pytest runner not found in environment or .venv", details

        return True, "Preflight passed: Environment ready", details
