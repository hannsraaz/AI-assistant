from __future__ import annotations

import ctypes
import difflib
import os
import subprocess
import time
import winreg
from pathlib import Path
from typing import Any

import psutil

from core.tools.base import BaseTool, RiskLevel, ToolResult


class AppDiscovery:
    """Scans and caches installed and running Windows applications."""

    _cache: dict[str, str] = {}
    _cache_time: float = 0.0
    _CACHE_TTL = 300.0  # 5 minutes

    @classmethod
    def get_installed_apps(cls, force_refresh: bool = False) -> dict[str, str]:
        if cls._cache and not force_refresh and (time.time() - cls._cache_time < cls._CACHE_TTL):
            return cls._cache

        apps: dict[str, str] = {}

        # 1. Standard Start Menu Paths
        start_paths = [
            Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft/Windows/Start Menu/Programs",
            Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        ]

        for base_path in start_paths:
            if not base_path.exists():
                continue
            for ext in ("*.lnk", "*.url"):
                for file_path in base_path.rglob(ext):
                    name = file_path.stem.lower()
                    # Filter out uninstallers and helpers
                    if any(bad in name for bad in ("uninstall", "readme", "help", "setup", "update", "manual")):
                        continue
                    clean_name = name.replace("-", " ").replace("_", " ").strip()
                    apps[clean_name] = str(file_path)

        # 2. Registry App Paths
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                key_path = r"Software\Microsoft\Windows\CurrentVersion\App Paths"
                with winreg.OpenKey(root, key_path) as app_key:
                    num_subkeys = winreg.QueryInfoKey(app_key)[0]
                    for i in range(num_subkeys):
                        try:
                            sub_name = winreg.EnumKey(app_key, i)
                            with winreg.OpenKey(app_key, sub_name) as sub_key:
                                val, _ = winreg.QueryValueEx(sub_key, "")
                                if val and os.path.exists(val):
                                    clean = sub_name.replace(".exe", "").lower()
                                    apps[clean] = str(val)
                        except Exception:
                            continue
            except Exception:
                continue

        # 3. Windows Store / UWP Packaged Apps (via Get-StartApps)
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-StartApps | ConvertTo-Json"],
                capture_output=True,
                text=True,
                timeout=4,
            )
            if res.returncode == 0 and res.stdout.strip():
                import json
                start_apps = json.loads(res.stdout)
                if isinstance(start_apps, dict):
                    start_apps = [start_apps]
                for item in start_apps:
                    name = item.get("Name", "").strip().lower()
                    app_id = item.get("AppID", "").strip()
                    if name and app_id:
                        clean_name = name.replace("-", " ").replace("_", " ").strip()
                        apps[clean_name] = f"shell:AppsFolder\\{app_id}"
                        raw_clean = "".join(c for c in clean_name if c.isalnum() or c.isspace()).strip()
                        if raw_clean:
                            apps[raw_clean] = f"shell:AppsFolder\\{app_id}"
        except Exception:
            pass

        # 4. Known system tools and URI protocols
        system_tools = {
            "whatsapp": "whatsapp:",
            "telegram": "tg:",
            "spotify": "spotify:",
            "netflix": "netflix:",
            "instagram": "instagram:",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "powershell": "powershell.exe",
            "terminal": "wt.exe",
            "windows terminal": "wt.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "notepad": "notepad.exe",
            "task manager": "taskmgr.exe",
            "taskmgr": "taskmgr.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "settings": "ms-settings:",
            "control panel": "control.exe",
            "paint": "mspaint.exe",
            "vs code": "code.cmd",
            "vscode": "code.cmd",
            "visual studio code": "code.cmd",
            "chrome": "chrome.exe",
            "google chrome": "chrome.exe",
            "edge": "msedge.exe",
            "microsoft edge": "msedge.exe",
            "firefox": "firefox.exe",
            "discord": "discord.exe",
            "camera": "microsoft.windows.camera:",
            "photos": "ms-photos:",
            "store": "ms-windows-store:",
            "microsoft store": "ms-windows-store:",
        }
        for k, v in system_tools.items():
            if k not in apps:
                apps[k] = v

        cls._cache = apps
        cls._cache_time = time.time()
        return apps

    @classmethod
    def find_app_path(cls, app_name: str) -> str | None:
        clean = app_name.strip().lower()
        apps = cls.get_installed_apps()

        # Exact match
        if clean in apps:
            return apps[clean]

        # Substring / fuzzy match
        for key, path in apps.items():
            if clean in key or key in clean:
                return path

        matches = difflib.get_close_matches(clean, apps.keys(), n=1, cutoff=0.6)
        if matches:
            return apps[matches[0]]

        return None


class AppsListTool(BaseTool):
    name = "apps.list"
    description = "List all currently open applications and running GUI processes on Windows."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "filter": {"type": "string", "description": "Optional search term to filter running applications."}
        },
    }

    def execute(self, filter: str = "", **kwargs: Any) -> ToolResult:
        running_apps: list[dict[str, Any]] = []
        seen_names = set()

        for proc in psutil.process_iter(["pid", "name", "exe"]):
            try:
                name = proc.info["name"] or ""
                if not name or name.lower().startswith(("svchost", "system", "registry", "runtimebroker")):
                    continue
                # If filter provided
                if filter and filter.lower() not in name.lower():
                    continue
                if name.lower() not in seen_names:
                    seen_names.add(name.lower())
                    running_apps.append({
                        "pid": proc.info["pid"],
                        "name": name,
                        "exe": proc.info["exe"] or "",
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        app_names = [a["name"].replace(".exe", "") for a in running_apps[:15]]
        return ToolResult(
            success=True,
            message=f"Found {len(running_apps)} running processes.",
            data={"count": len(running_apps), "apps": running_apps, "summary_names": app_names},
        )


class AppsFindTool(BaseTool):
    name = "apps.find"
    description = "Find the install path or shortcut for a given application on Windows."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Application name to search for (e.g. 'Spotify', 'VS Code')."}
        },
        "required": ["query"],
    }

    def execute(self, query: str, **kwargs: Any) -> ToolResult:
        path = AppDiscovery.find_app_path(query)
        if path:
            return ToolResult(
                success=True,
                message=f"Found application path for '{query}'.",
                data={"query": query, "path": path},
            )
        return ToolResult(
            success=False,
            error=f"Could not locate application '{query}'.",
            data={"query": query},
        )


class AppsOpenTool(BaseTool):
    name = "apps.open"
    description = "Launch an application or file on Windows by name or path."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Name of the application or URI (e.g. 'notepad', 'chrome', 'Spotify')."}
        },
        "required": ["app_name"],
    }

    def execute(self, app_name: str, **kwargs: Any) -> ToolResult:
        target = app_name.strip()
        path = AppDiscovery.find_app_path(target)

        # 1. Try matched path or URI
        if path:
            try:
                if path.startswith("shell:AppsFolder") or path.startswith("ms-") or path.endswith((".lnk", ".url")) or ":" in path:
                    try:
                        os.startfile(path)
                    except Exception:
                        subprocess.Popen(f'explorer.exe "{path}"', shell=True)
                else:
                    subprocess.Popen(path, shell=True)
                return ToolResult(
                    success=True,
                    message=f"Opened {target}.",
                    data={"target": target, "path": path},
                )
            except Exception as exc:
                pass

        # 2. Try raw os.startfile
        try:
            os.startfile(target)
            return ToolResult(
                success=True,
                message=f"Opened {target}.",
                data={"target": target},
            )
        except Exception:
            pass

        # 3. Try subprocess popen directly
        try:
            subprocess.Popen([target], shell=True)
            return ToolResult(
                success=True,
                message=f"Launched {target}.",
                data={"target": target},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Could not open application '{target}': {exc}",
                data={"target": target},
            )


class AppsCloseTool(BaseTool):
    name = "apps.close"
    description = "Close or terminate an application by process name or PID."
    risk_level = RiskLevel.CONFIRM
    parameters = {
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Process name or title to close (e.g. 'notepad', 'chrome')."}
        },
        "required": ["app_name"],
    }

    def execute(self, app_name: str, **kwargs: Any) -> ToolResult:
        clean = app_name.strip().lower().replace(".exe", "")
        closed_pids = []

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pname = (proc.info["name"] or "").lower()
                if clean in pname or pname.startswith(clean):
                    proc.terminate()
                    closed_pids.append(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if closed_pids:
            return ToolResult(
                success=True,
                message=f"Closed {app_name} ({len(closed_pids)} process instances terminated).",
                data={"app_name": app_name, "pids": closed_pids},
            )

        return ToolResult(
            success=False,
            error=f"No running processes found for '{app_name}'.",
            data={"app_name": app_name},
        )


class AppsFocusTool(BaseTool):
    name = "apps.focus"
    description = "Bring an open application window to the foreground."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Application name or window title to focus."}
        },
        "required": ["app_name"],
    }

    def execute(self, app_name: str, **kwargs: Any) -> ToolResult:
        try:
            import win32gui
            import win32con

            clean = app_name.strip().lower()
            matched_hwnd = None

            def enum_window_callback(hwnd: int, extra: Any) -> bool:
                nonlocal matched_hwnd
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).lower()
                    if clean in title and title:
                        matched_hwnd = hwnd
                        return False
                return True

            try:
                win32gui.EnumWindows(enum_window_callback, None)
            except Exception:
                pass

            if matched_hwnd:
                # Restore if minimized
                if win32gui.IsIconic(matched_hwnd):
                    win32gui.ShowWindow(matched_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(matched_hwnd)
                return ToolResult(
                    success=True,
                    message=f"Brought {app_name} to the front.",
                    data={"app_name": app_name, "hwnd": matched_hwnd},
                )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Failed to focus '{app_name}': {exc}",
                data={"app_name": app_name},
            )

        return ToolResult(
            success=False,
            error=f"Window for '{app_name}' not found.",
            data={"app_name": app_name},
        )
