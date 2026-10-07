"""Git Worktree Isolation Manager."""
import os
import shutil
import subprocess
from typing import Tuple

class WorktreeManager:
    def __init__(self, base_repo: str):
        self.base_repo = os.path.abspath(base_repo)

    def create_worktree(self, run_id: str, base_branch: str = "main") -> Tuple[bool, str, str]:
        """Create an isolated worktree at ../aether-<run_id> on branch aether/fix-<run_id>."""
        branch_name = f"aether/fix-{run_id}"
        
        # Determine git root
        git_root = self.base_repo
        try:
            res = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=self.base_repo, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                git_root = res.stdout.strip()
        except Exception:
            pass

        rel_subpath = os.path.relpath(self.base_repo, git_root)
        parent_dir = os.path.dirname(git_root)
        worktree_path = os.path.abspath(os.path.join(parent_dir, f"aether-{run_id}"))

        # Create git worktree from git_root
        cmd = ["git", "worktree", "add", "-b", branch_name, worktree_path, "HEAD"]
        proc = subprocess.run(cmd, cwd=git_root, capture_output=True, text=True)

        if proc.returncode == 0:
            effective_target_dir = os.path.join(worktree_path, rel_subpath) if rel_subpath != "." else worktree_path
            return True, effective_target_dir, branch_name

        # Fallback: create isolated directory copy
        try:
            fallback_dir = os.path.abspath(os.path.join(os.path.dirname(self.base_repo), f"aether-{run_id}"))
            if os.path.exists(fallback_dir):
                shutil.rmtree(fallback_dir, ignore_errors=True)
            shutil.copytree(self.base_repo, fallback_dir, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__"))
            return True, fallback_dir, branch_name
        except Exception as e:
            return False, str(e), ""

    def remove_worktree(self, worktree_path: str, branch_name: str) -> bool:
        """Clean up the worktree path while preserving the branch for manual user review."""
        try:
            # If path is inside an aether- worktree
            wt_root = worktree_path
            while wt_root and not os.path.basename(wt_root).startswith("aether-") and os.path.dirname(wt_root) != wt_root:
                wt_root = os.path.dirname(wt_root)
            
            subprocess.run(["git", "worktree", "remove", "--force", wt_root], cwd=self.base_repo, capture_output=True, text=True)
            if os.path.exists(wt_root):
                shutil.rmtree(wt_root, ignore_errors=True)
        except Exception:
            pass
        return True
