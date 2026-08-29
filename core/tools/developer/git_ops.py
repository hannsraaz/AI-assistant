from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from core.tools.base import BaseTool, RiskLevel, ToolResult


class GitHelper:
    @staticmethod
    def run_git(args: list[str], cwd: str = "") -> tuple[int, str, str]:
        work_dir = Path(cwd).resolve() if cwd else Path.cwd()
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=25,
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except Exception as exc:
            return 1, "", str(exc)


class GitStatusTool(BaseTool):
    name = "git.status"
    description = "Check git working tree status and modified files in the repository."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "cwd": {"type": "string", "description": "Repository path (default current directory).", "default": ""}
        },
    }

    def execute(self, cwd: str = "", **kwargs: Any) -> ToolResult:
        code, out, err = GitHelper.run_git(["status", "--short", "--branch"], cwd=cwd)
        if code != 0:
            return ToolResult(success=False, error=f"Git status error: {err or out}")
        return ToolResult(
            success=True,
            message="Git status fetched.",
            data={"status": out, "has_changes": bool(out.count("\n") > 0)},
        )


class GitDiffTool(BaseTool):
    name = "git.diff"
    description = "Show git diff of unstaged or staged modifications."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "staged": {"type": "boolean", "description": "True to show staged changes.", "default": False},
            "cwd": {"type": "string", "description": "Repository directory.", "default": ""},
        },
    }

    def execute(self, staged: bool = False, cwd: str = "", **kwargs: Any) -> ToolResult:
        args = ["diff", "--cached"] if staged else ["diff"]
        code, out, err = GitHelper.run_git(args, cwd=cwd)
        if code != 0:
            return ToolResult(success=False, error=f"Git diff error: {err or out}")
        return ToolResult(
            success=True,
            message=f"Git diff ({len(out)} characters).",
            data={"diff": out[:3000], "is_empty": not bool(out)},
        )


class GitLogTool(BaseTool):
    name = "git.log"
    description = "View recent git commit history."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "max_count": {"type": "integer", "description": "Number of commits to show.", "default": 5},
            "cwd": {"type": "string", "description": "Repository directory.", "default": ""},
        },
    }

    def execute(self, max_count: int = 5, cwd: str = "", **kwargs: Any) -> ToolResult:
        args = ["log", f"-n{max_count}", "--oneline"]
        code, out, err = GitHelper.run_git(args, cwd=cwd)
        if code != 0:
            return ToolResult(success=False, error=f"Git log error: {err or out}")
        commits = out.splitlines()
        return ToolResult(
            success=True,
            message=f"Recent {len(commits)} commit(s).",
            data={"commits": commits, "raw": out},
        )


class GitBranchTool(BaseTool):
    name = "git.branch"
    description = "List local git branches."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "cwd": {"type": "string", "description": "Repository directory.", "default": ""}
        },
    }

    def execute(self, cwd: str = "", **kwargs: Any) -> ToolResult:
        code, out, err = GitHelper.run_git(["branch"], cwd=cwd)
        if code != 0:
            return ToolResult(success=False, error=f"Git branch error: {err or out}")
        branches = [b.strip() for b in out.splitlines()]
        return ToolResult(
            success=True,
            message="Git branches listed.",
            data={"branches": branches, "current": [b for b in branches if b.startswith("*")]},
        )


class GitAddTool(BaseTool):
    name = "git.add"
    description = "Stage files for commit."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "files": {"type": "string", "description": "File path(s) or '.' for all changes.", "default": "."},
            "cwd": {"type": "string", "description": "Repository directory.", "default": ""},
        },
    }

    def execute(self, files: str = ".", cwd: str = "", **kwargs: Any) -> ToolResult:
        code, out, err = GitHelper.run_git(["add", files], cwd=cwd)
        if code != 0:
            return ToolResult(success=False, error=f"Git add error: {err or out}")
        return ToolResult(success=True, message=f"Staged changes for '{files}'.")


class GitCommitTool(BaseTool):
    name = "git.commit"
    description = "Commit staged git changes with a descriptive message."
    risk_level = RiskLevel.CONFIRM
    parameters = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Commit message."},
            "cwd": {"type": "string", "description": "Repository directory.", "default": ""},
        },
        "required": ["message"],
    }

    def execute(self, message: str, cwd: str = "", **kwargs: Any) -> ToolResult:
        code, out, err = GitHelper.run_git(["commit", "-m", message], cwd=cwd)
        if code != 0:
            return ToolResult(success=False, error=f"Git commit error: {err or out}")
        return ToolResult(
            success=True,
            message=f"Committed changes: '{message}'.",
            data={"output": out},
        )


class GitPushTool(BaseTool):
    name = "git.push"
    description = "Push committed changes to the remote Git repository."
    risk_level = RiskLevel.CONFIRM
    parameters = {
        "type": "object",
        "properties": {
            "remote": {"type": "string", "description": "Remote name (default 'origin').", "default": "origin"},
            "branch": {"type": "string", "description": "Branch name (default current).", "default": ""},
            "cwd": {"type": "string", "description": "Repository directory.", "default": ""},
        },
    }

    def execute(self, remote: str = "origin", branch: str = "", cwd: str = "", **kwargs: Any) -> ToolResult:
        args = ["push", remote]
        if branch:
            args.append(branch)
        code, out, err = GitHelper.run_git(args, cwd=cwd)
        if code != 0:
            return ToolResult(success=False, error=f"Git push error: {err or out}")
        return ToolResult(success=True, message="Pushed commits to remote repository.", data={"output": out or err})


class GitPullTool(BaseTool):
    name = "git.pull"
    description = "Fetch and pull latest changes from the remote Git repository."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "remote": {"type": "string", "description": "Remote name.", "default": "origin"},
            "cwd": {"type": "string", "description": "Repository directory.", "default": ""},
        },
    }

    def execute(self, remote: str = "origin", cwd: str = "", **kwargs: Any) -> ToolResult:
        code, out, err = GitHelper.run_git(["pull", remote], cwd=cwd)
        if code != 0:
            return ToolResult(success=False, error=f"Git pull error: {err or out}")
        return ToolResult(success=True, message="Pulled latest remote changes.", data={"output": out or err})


class GitCreateBranchTool(BaseTool):
    name = "git.create_branch"
    description = "Create and checkout a new git branch."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "branch_name": {"type": "string", "description": "Name of new branch."},
            "cwd": {"type": "string", "description": "Repository directory.", "default": ""},
        },
        "required": ["branch_name"],
    }

    def execute(self, branch_name: str, cwd: str = "", **kwargs: Any) -> ToolResult:
        code, out, err = GitHelper.run_git(["checkout", "-b", branch_name], cwd=cwd)
        if code != 0:
            return ToolResult(success=False, error=f"Git create branch error: {err or out}")
        return ToolResult(success=True, message=f"Created and switched to branch '{branch_name}'.")


class GitCheckoutTool(BaseTool):
    name = "git.checkout"
    description = "Switch to an existing git branch or commit."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "branch_name": {"type": "string", "description": "Branch or commit reference."},
            "cwd": {"type": "string", "description": "Repository directory.", "default": ""},
        },
        "required": ["branch_name"],
    }

    def execute(self, branch_name: str, cwd: str = "", **kwargs: Any) -> ToolResult:
        code, out, err = GitHelper.run_git(["checkout", branch_name], cwd=cwd)
        if code != 0:
            return ToolResult(success=False, error=f"Git checkout error: {err or out}")
        return ToolResult(success=True, message=f"Switched to '{branch_name}'.")
