"""Git Worktree Isolation Manager matching PRD v1.3 FR-2 specifications."""
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

class WorktreeManager:
    def __init__(self, base_repo: str):
        self.base_repo = os.path.abspath(base_repo)
        self.git_root = self._detect_git_root()
        self.rel_subpath = os.path.relpath(self.base_repo, self.git_root)

    def _detect_git_root(self) -> str:
        """Detect the git root directory containing .git."""
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self.base_repo,
                capture_output=True,
                text=True
            )
            if res.returncode == 0 and res.stdout.strip():
                return os.path.abspath(res.stdout.strip())
        except Exception:
            pass
        return self.base_repo

    def get_uncommitted_warning(self) -> str:
        """FR-2.3: Uncommitted changes notice."""
        return "Worktree created from HEAD. Uncommitted changes in your editor are not included in this run."

    def create_worktree(self, run_id: str, base_branch: str = "main") -> Tuple[bool, str, str, str]:
        """Create an isolated worktree at ../aether-<run_id> on branch aether/fix-<run_id>.
        
        Returns:
            Tuple of (success, effective_target_dir, branch_name, worktree_root_path)
        """
        branch_name = f"aether/fix-{run_id}"
        parent_dir = os.path.dirname(self.git_root)
        worktree_path = os.path.abspath(os.path.join(parent_dir, f"aether-{run_id}"))

        # Fallback if parent dir is not writable
        if not os.access(parent_dir, os.W_OK):
            worktree_path = os.path.abspath(os.path.join(self.git_root, ".aether", "worktrees", f"aether-{run_id}"))

        # Ensure directory does not exist beforehand
        if os.path.exists(worktree_path):
            self.remove_worktree(worktree_path, branch_name)

        # Delete branch if it lingered from previous run
        subprocess.run(["git", "branch", "-D", branch_name], cwd=self.git_root, capture_output=True)

        # FR-2.1: git worktree add ../aether-<run-id> -b aether/fix-<run-id> HEAD
        cmd = ["git", "worktree", "add", "-b", branch_name, worktree_path, "HEAD"]
        proc = subprocess.run(cmd, cwd=self.git_root, capture_output=True, text=True)

        if proc.returncode == 0:
            effective_dir = (
                os.path.join(worktree_path, self.rel_subpath)
                if self.rel_subpath and self.rel_subpath != "."
                else worktree_path
            )
            return True, effective_dir, branch_name, worktree_path

        # Fallback if git worktree fails (e.g. detached HEAD or non-git environment)
        try:
            fallback_dir = os.path.abspath(os.path.join(self.git_root, ".aether", "worktrees", f"aether-{run_id}"))
            os.makedirs(os.path.dirname(fallback_dir), exist_ok=True)
            if os.path.exists(fallback_dir):
                shutil.rmtree(fallback_dir, ignore_errors=True)
            shutil.copytree(
                self.base_repo,
                fallback_dir,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "node_modules")
            )
            return True, fallback_dir, branch_name, fallback_dir
        except Exception as e:
            return False, str(e), branch_name, ""

    def get_branch_diff(self, branch_name: str, base_branch: str = "main") -> str:
        """FR-2.4: Produce unified diff between tested branch and base."""
        # Check if base branch exists, otherwise use HEAD
        cmd = ["git", "diff", f"{base_branch}...{branch_name}"]
        proc = subprocess.run(cmd, cwd=self.git_root, capture_output=True, text=True)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout

        # Fallback: diff against HEAD
        cmd = ["git", "diff", f"HEAD...{branch_name}"]
        proc = subprocess.run(cmd, cwd=self.git_root, capture_output=True, text=True)
        return proc.stdout if proc.returncode == 0 else ""

    def merge_branch(self, branch_name: str, target_branch: str = "main") -> Tuple[bool, str]:
        """FR-2.4: Merge tested branch on explicit user manual review only."""
        # Check current branch
        curr = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.git_root,
            capture_output=True,
            text=True
        ).stdout.strip()

        proc = subprocess.run(
            ["git", "merge", "--no-ff", branch_name, "-m", f"Merge tested branch {branch_name} into {target_branch}"],
            cwd=self.git_root,
            capture_output=True,
            text=True
        )
        if proc.returncode == 0:
            return True, f"Successfully merged {branch_name} into {curr}"
        return False, f"Merge conflict or error:\n{proc.stderr}\n{proc.stdout}"

    def remove_worktree(self, worktree_path: str, branch_name: str, preserve_branch: bool = True) -> bool:
        """FR-2.5: Worktree Teardown while preserving the target branch."""
        try:
            wt_root = os.path.abspath(worktree_path)
            while wt_root and not os.path.basename(wt_root).startswith("aether-") and os.path.dirname(wt_root) != wt_root:
                wt_root = os.path.dirname(wt_root)

            # Clean up git worktree
            subprocess.run(
                ["git", "worktree", "remove", "--force", wt_root],
                cwd=self.git_root,
                capture_output=True,
                text=True
            )
            # Remove directory if still present
            if os.path.exists(wt_root):
                shutil.rmtree(wt_root, ignore_errors=True)

            if not preserve_branch and branch_name:
                subprocess.run(
                    ["git", "branch", "-D", branch_name],
                    cwd=self.git_root,
                    capture_output=True
                )
            return True
        except Exception:
            return False

    def list_worktrees(self) -> List[Dict[str, Any]]:
        """List active git worktrees and branches."""
        proc = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self.git_root,
            capture_output=True,
            text=True
        )
        if proc.returncode != 0:
            return []

        worktrees = []
        current_wt: Dict[str, Any] = {}

        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                if current_wt:
                    worktrees.append(current_wt)
                    current_wt = {}
                continue
            if line.startswith("worktree "):
                current_wt["path"] = line.split(" ", 1)[1]
            elif line.startswith("HEAD "):
                current_wt["commit"] = line.split(" ", 1)[1]
            elif line.startswith("branch "):
                current_wt["branch"] = line.split(" ", 1)[1].replace("refs/heads/", "")
            elif line == "bare":
                current_wt["bare"] = True

        if current_wt:
            worktrees.append(current_wt)

        return worktrees
