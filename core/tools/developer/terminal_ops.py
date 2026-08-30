from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

from core.tools.base import BaseTool, RiskLevel, ToolError, ToolResult


class TerminalExecuteTool(BaseTool):
    name = "terminal.execute"
    description = "Execute a controlled shell / terminal command within a project or working directory."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to run (e.g. 'git status', 'python --version', 'dir')."},
            "cwd": {"type": "string", "description": "Optional working directory path.", "default": ""},
            "timeout": {"type": "integer", "description": "Execution timeout in seconds.", "default": 30},
        },
        "required": ["command"],
    }

    # Safe read-only commands
    SAFE_COMMAND_PREFIXES = (
        "git status", "git diff", "git log", "git branch", "git show",
        "dir", "ls", "pwd", "echo", "type", "cat", "where", "which",
        "python --version", "python -V", "node -v", "npm -v", "java -version", "java --version",
        "gradle --version", "gradlew --version", "adb devices", "adb version",
        "pytest --version", "pip list", "cargo --version", "rustc --version",
    )

    # High-risk destructive command patterns
    HIGH_RISK_PATTERNS = (
        r"\brmdir\s+/[sS]",
        r"\bdel\s+/[fFsS]",
        r"\bformat\s+[a-zA-Z]:",
        r"\bdiskpart\b",
        r"\brm\s+-rf\b",
        r"\bmkfs\b",
        r"\bdrop\s+database\b",
        r"\bsudo\b",
        r"\breg\s+delete\b",
        r"\bpowershell\s+.*-enc\b",
        r"\bvssadmin\b",
        r"\bbcdedit\b",
        r"\bwbadmin\b",
        r"\bcertutil\s+.*-urlcache\b",
        r"\bnet\s+user\s+.*\/add\b",
    )

    def execute(self, command: str, cwd: str = "", timeout: int = 30, **kwargs: Any) -> ToolResult:
        clean_cmd = command.strip()
        if not clean_cmd:
            return ToolResult(
                success=False,
                error=ToolError(code="EMPTY_COMMAND", message="Command string cannot be empty."),
            )

        # Check high-risk destructive patterns
        for pattern in self.HIGH_RISK_PATTERNS:
            if re.search(pattern, clean_cmd, re.IGNORECASE):
                return ToolResult(
                    success=False,
                    error=ToolError(
                        code="HIGH_RISK_BLOCKED",
                        message="Blocked high-risk command. Destructive system operations are prohibited.",
                        details={"command": clean_cmd, "pattern": pattern},
                    ),
                    data={"command": clean_cmd},
                )

        work_dir = Path(cwd).resolve() if cwd else Path.cwd()
        if not work_dir.exists():
            return ToolResult(
                success=False,
                error=ToolError(code="DIRECTORY_NOT_FOUND", message=f"Working directory '{cwd}' does not exist."),
            )

        try:
            res = subprocess.run(
                clean_cmd,
                shell=True,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            stdout = res.stdout.strip()
            stderr = res.stderr.strip()
            success = (res.returncode == 0)

            output = stdout if stdout else stderr
            if not success:
                return ToolResult(
                    success=False,
                    error=ToolError(
                        code="COMMAND_FAILED",
                        message=f"Command exited with non-zero status code {res.returncode}.",
                        details={"exit_code": res.returncode, "stderr": stderr, "stdout": stdout},
                    ),
                    data={"command": clean_cmd, "exit_code": res.returncode, "output": output[:3000]},
                )

            return ToolResult(
                success=True,
                message=f"Command executed with exit code {res.returncode}.",
                data={
                    "command": clean_cmd,
                    "exit_code": res.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                    "output": output[:3000],
                },
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error=ToolError(code="COMMAND_TIMEOUT", message=f"Command timed out after {timeout} seconds."),
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=ToolError(code="EXECUTION_ERROR", message=f"Failed to execute command: {exc}"),
            )
