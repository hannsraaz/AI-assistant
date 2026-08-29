from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from core.tools.base import BaseTool, RiskLevel, ToolResult


class AndroidHelper:
    @staticmethod
    def find_adb() -> str:
        # 1. System PATH
        in_path = shutil.which("adb")
        if in_path:
            return in_path
        # 2. LocalAppData Android SDK
        sdk_adb = Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools" / "adb.exe"
        if sdk_adb.exists():
            return str(sdk_adb)
        # 3. ANDROID_HOME / ANDROID_SDK_ROOT
        for env_var in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
            home = os.environ.get(env_var, "")
            if home:
                cand = Path(home) / "platform-tools" / "adb.exe"
                if cand.exists():
                    return str(cand)
        return "adb"

    @staticmethod
    def find_gradlew(project_dir: Path) -> Path | None:
        cand_bat = project_dir / "gradlew.bat"
        if cand_bat.exists():
            return cand_bat
        cand_sh = project_dir / "gradlew"
        if cand_sh.exists():
            return cand_sh
        return None


class AndroidDevicesTool(BaseTool):
    name = "android.devices"
    description = "List all connected Android physical devices and active emulators via ADB."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        adb_bin = AndroidHelper.find_adb()
        try:
            res = subprocess.run([adb_bin, "devices", "-l"], capture_output=True, text=True, timeout=10)
            lines = res.stdout.strip().splitlines()
            devices = []
            if len(lines) > 1:
                for line in lines[1:]:
                    line = line.strip()
                    if line:
                        parts = line.split()
                        serial = parts[0]
                        state = parts[1] if len(parts) > 1 else "unknown"
                        model = next((p.split(":")[1] for p in parts if p.startswith("model:")), serial)
                        devices.append({"serial": serial, "state": state, "model": model, "raw": line})

            return ToolResult(
                success=True,
                message=f"Found {len(devices)} connected Android device(s).",
                data={"count": len(devices), "devices": devices},
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"ADB error: {exc}")


class AndroidBuildTool(BaseTool):
    name = "android.build"
    description = "Execute Gradle build (e.g. assembleDebug or bundleRelease) in an Android project."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "project_dir": {"type": "string", "description": "Android project directory containing gradlew.", "default": "."},
            "task": {"type": "string", "description": "Gradle task to run (default 'assembleDebug').", "default": "assembleDebug"},
        },
    }

    def execute(self, project_dir: str = ".", task: str = "assembleDebug", **kwargs: Any) -> ToolResult:
        target_path = kwargs.get("project_path") or project_dir
        p_dir = Path(target_path).resolve()
        gradlew = AndroidHelper.find_gradlew(p_dir)
        if not gradlew:
            return ToolResult(
                success=False,
                error=f"No gradlew wrapper found in '{target_path}'. Is this an Android/Gradle project?",
            )

        try:
            cmd = [str(gradlew), task]
            res = subprocess.run(cmd, cwd=str(p_dir), capture_output=True, text=True, timeout=180)
            success = (res.returncode == 0)
            return ToolResult(
                success=success,
                message=f"Gradle {task} {'succeeded' if success else 'failed'}.",
                data={
                    "task": task,
                    "exit_code": res.returncode,
                    "stdout": res.stdout[-2500:],
                    "stderr": res.stderr[-2500:],
                },
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="Gradle build timed out after 3 minutes.")
        except Exception as exc:
            return ToolResult(success=False, error=f"Gradle build error: {exc}")


class AndroidTestTool(BaseTool):
    name = "android.test"
    description = "Run unit tests or connected instrumentation tests in an Android project."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "project_dir": {"type": "string", "description": "Android project directory.", "default": "."},
            "test_task": {"type": "string", "description": "Gradle test task (default 'testDebugUnitTest').", "default": "testDebugUnitTest"},
        },
    }

    def execute(self, project_dir: str = ".", test_task: str = "testDebugUnitTest", **kwargs: Any) -> ToolResult:
        p_dir = Path(project_dir).resolve()
        gradlew = AndroidHelper.find_gradlew(p_dir)
        if not gradlew:
            return ToolResult(success=False, error=f"No gradlew found in '{project_dir}'.")

        try:
            res = subprocess.run([str(gradlew), test_task], cwd=str(p_dir), capture_output=True, text=True, timeout=180)
            success = (res.returncode == 0)
            return ToolResult(
                success=success,
                message=f"Android tests {'passed' if success else 'failed'}.",
                data={"task": test_task, "exit_code": res.returncode, "output": res.stdout[-2500:]},
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Android test run error: {exc}")


class AndroidLogcatTool(BaseTool):
    name = "android.logcat"
    description = "Capture recent error logs and exceptions from connected Android device via Logcat."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "filter_tag": {"type": "string", "description": "Optional log tag filter or package.", "default": ""},
            "max_lines": {"type": "integer", "description": "Maximum log lines to return.", "default": 50},
        },
    }

    def execute(self, filter_tag: str = "", max_lines: int = 50, **kwargs: Any) -> ToolResult:
        adb_bin = AndroidHelper.find_adb()
        try:
            cmd = [adb_bin, "logcat", "-d", "*:E"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            lines = res.stdout.strip().splitlines()
            if filter_tag:
                lines = [l for l in lines if filter_tag.lower() in l.lower()]
            selected = lines[-max_lines:] if lines else []
            return ToolResult(
                success=True,
                message=f"Retrieved {len(selected)} error log lines from Logcat.",
                data={"count": len(selected), "logs": selected, "raw": "\n".join(selected)},
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Logcat error: {exc}")
