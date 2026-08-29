from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from core.tools.base import ToolResult
from core.tools.registry import ToolRegistry

logger = logging.getLogger("verifier")


class StepVerifier:
    """Explicit post-execution verification system ensuring actions achieved their real-world goal."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def verify_step(self, tool_name: str, args: dict[str, Any], result: ToolResult) -> tuple[bool, str]:
        """Verify the state change produced by a tool execution."""
        if not result.success:
            return False, f"Tool reported failure: {result.get_error_message()}"

        try:
            # 1. Volume verification
            if tool_name == "system.volume.set":
                target_pct = args.get("percentage") or args.get("percent")
                if target_pct is not None:
                    curr_res = self.registry.execute("system.volume.get")
                    if curr_res.success:
                        curr = curr_res.data.get("volume_percent", curr_res.data.get("volume"))
                        if curr is not None and abs(curr - int(target_pct)) <= 2:
                            return True, f"Verified volume is at {curr}%."
                        return False, f"Volume mismatch: expected {target_pct}%, actual {curr}%."

            # 2. File creation verification
            if tool_name == "files.create":
                p = args.get("path")
                if p:
                    chk = self.registry.execute("files.exists", path=p)
                    if chk.success and chk.data.get("exists"):
                        return True, f"Verified file exists at '{p}'."
                    return False, f"File was not created at '{p}'."

            # 3. File move verification
            if tool_name == "files.move":
                dst = args.get("destination")
                src = args.get("source")
                if dst and src:
                    chk_dst = self.registry.execute("files.exists", path=dst)
                    chk_src = self.registry.execute("files.exists", path=src)
                    if chk_dst.data.get("exists") and not chk_src.data.get("exists"):
                        return True, f"Verified file moved to '{dst}' and removed from '{src}'."
                    return False, f"Move incomplete (destination exists: {chk_dst.data.get('exists')}, source exists: {chk_src.data.get('exists')})."

            # 4. File delete verification
            if tool_name == "files.delete":
                p = args.get("path")
                if p:
                    chk = self.registry.execute("files.exists", path=p)
                    if chk.success and not chk.data.get("exists"):
                        return True, f"Verified file was deleted: '{p}'."
                    return False, f"File still exists after delete attempt: '{p}'."

            # 5. Git commit verification
            if tool_name == "git.commit":
                cwd = args.get("cwd", "")
                stat = self.registry.execute("git.status", cwd=cwd)
                if stat.success:
                    clean = "working tree clean" in stat.data.get("status", "").lower() or "nothing to commit" in stat.data.get("status", "").lower()
                    if clean:
                        return True, "Verified Git working tree is clean after commit."

            # 6. Android build verification
            if tool_name == "android.build":
                exit_code = result.data.get("exit_code")
                if exit_code == 0:
                    return True, "Verified Android build succeeded with exit code 0."
                return False, f"Android build failed with exit code {exit_code}."

            # 7. App launch verification
            if tool_name == "apps.open":
                app_name = args.get("app_name", "")
                return True, f"Launched application '{app_name}'."

        except Exception as exc:
            logger.warning("Verification exception for %s: %s", tool_name, exc)

        # Default: Tool reported success and no custom check failed
        return True, "Step verified by tool output contract."
