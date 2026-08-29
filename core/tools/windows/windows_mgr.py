from __future__ import annotations

import ctypes
import os
from typing import Any

from core.tools.base import BaseTool, RiskLevel, ToolResult


class WindowHelper:
    """Helper utilities using pywin32 and user32 for window management."""

    @staticmethod
    def list_visible_windows() -> list[dict[str, Any]]:
        windows: list[dict[str, Any]] = []
        try:
            import win32gui
            import win32process
            import psutil

            def enum_cb(hwnd: int, extra: Any) -> bool:
                if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd).strip():
                    title = win32gui.GetWindowText(hwnd).strip()
                    # Filter out common shell tooltips or 0-size hidden overlays
                    rect = win32gui.GetWindowRect(hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    if width > 100 and height > 100:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        proc_name = ""
                        try:
                            proc_name = psutil.Process(pid).name()
                        except Exception:
                            pass
                        
                        import ctypes
                        is_minimized = bool(win32gui.IsIconic(hwnd))
                        is_maximized = bool(ctypes.windll.user32.IsZoomed(hwnd))

                        windows.append({
                            "hwnd": hwnd,
                            "title": title,
                            "pid": pid,
                            "process": proc_name,
                            "is_minimized": is_minimized,
                            "is_maximized": is_maximized,
                        })
                return True

            win32gui.EnumWindows(enum_cb, None)
        except Exception:
            pass
        return windows

    @staticmethod
    def get_active_window() -> dict[str, Any] | None:
        try:
            import win32gui
            import win32process
            import psutil

            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                title = win32gui.GetWindowText(hwnd).strip()
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc_name = ""
                try:
                    proc_name = psutil.Process(pid).name()
                except Exception:
                    pass
                return {
                    "hwnd": hwnd,
                    "title": title,
                    "pid": pid,
                    "process": proc_name,
                }
        except Exception:
            pass
        return None


class WindowsListTool(BaseTool):
    name = "windows.list"
    description = "List all visible top-level windows with title, PID, and process name."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {},
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        windows = WindowHelper.list_visible_windows()
        titles = [w["title"] for w in windows[:10]]
        return ToolResult(
            success=True,
            message=f"Found {len(windows)} visible windows.",
            data={"count": len(windows), "windows": windows, "titles": titles},
        )


class WindowsFocusTool(BaseTool):
    name = "windows.focus"
    description = "Bring a specific window to the foreground by title or HWND."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Title substring of the window to focus."},
            "hwnd": {"type": "integer", "description": "HWND handle of the window."},
        },
    }

    def execute(self, title: str = "", hwnd: int | None = None, **kwargs: Any) -> ToolResult:
        try:
            import win32gui
            import win32con

            target_hwnd = hwnd
            target_title = title

            if not target_hwnd:
                clean = title.lower().strip()
                for w in WindowHelper.list_visible_windows():
                    if clean in w["title"].lower():
                        target_hwnd = w["hwnd"]
                        target_title = w["title"]
                        break

            if target_hwnd and win32gui.IsWindow(target_hwnd):
                if win32gui.IsIconic(target_hwnd):
                    win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(target_hwnd)
                return ToolResult(
                    success=True,
                    message=f"Focused window: {target_title or target_hwnd}",
                    data={"hwnd": target_hwnd, "title": target_title},
                )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Could not focus window: {exc}",
            )

        return ToolResult(
            success=False,
            error=f"No matching window found for '{title}'.",
        )


class WindowsMinimizeTool(BaseTool):
    name = "windows.minimize"
    description = "Minimize a specific window or the active window."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Optional title of window to minimize. If omitted, minimizes active window."}
        },
    }

    def execute(self, title: str = "", **kwargs: Any) -> ToolResult:
        try:
            import win32gui
            import win32con

            target_hwnd = None
            if title:
                clean = title.lower().strip()
                for w in WindowHelper.list_visible_windows():
                    if clean in w["title"].lower():
                        target_hwnd = w["hwnd"]
                        break
            else:
                target_hwnd = win32gui.GetForegroundWindow()

            if target_hwnd and win32gui.IsWindow(target_hwnd):
                win32gui.ShowWindow(target_hwnd, win32con.SW_MINIMIZE)
                return ToolResult(
                    success=True,
                    message="Minimized window.",
                    data={"hwnd": target_hwnd},
                )
        except Exception as exc:
            return ToolResult(success=False, error=f"Minimize failed: {exc}")

        return ToolResult(success=False, error="Window not found.")


class WindowsMaximizeTool(BaseTool):
    name = "windows.maximize"
    description = "Maximize a specific window or the active window."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Optional title of window to maximize. If omitted, maximizes active window."}
        },
    }

    def execute(self, title: str = "", **kwargs: Any) -> ToolResult:
        try:
            import win32gui
            import win32con

            target_hwnd = None
            if title:
                clean = title.lower().strip()
                for w in WindowHelper.list_visible_windows():
                    if clean in w["title"].lower():
                        target_hwnd = w["hwnd"]
                        break
            else:
                target_hwnd = win32gui.GetForegroundWindow()

            if target_hwnd and win32gui.IsWindow(target_hwnd):
                win32gui.ShowWindow(target_hwnd, win32con.SW_MAXIMIZE)
                return ToolResult(
                    success=True,
                    message="Maximized window.",
                    data={"hwnd": target_hwnd},
                )
        except Exception as exc:
            return ToolResult(success=False, error=f"Maximize failed: {exc}")

        return ToolResult(success=False, error="Window not found.")


class WindowsRestoreTool(BaseTool):
    name = "windows.restore"
    description = "Restore a minimized or maximized window to normal state."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Optional title of window to restore."}
        },
    }

    def execute(self, title: str = "", **kwargs: Any) -> ToolResult:
        try:
            import win32gui
            import win32con

            target_hwnd = None
            if title:
                clean = title.lower().strip()
                for w in WindowHelper.list_visible_windows():
                    if clean in w["title"].lower():
                        target_hwnd = w["hwnd"]
                        break
            else:
                target_hwnd = win32gui.GetForegroundWindow()

            if target_hwnd and win32gui.IsWindow(target_hwnd):
                win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                return ToolResult(
                    success=True,
                    message="Restored window.",
                    data={"hwnd": target_hwnd},
                )
        except Exception as exc:
            return ToolResult(success=False, error=f"Restore failed: {exc}")

        return ToolResult(success=False, error="Window not found.")


class WindowsCloseTool(BaseTool):
    name = "windows.close"
    description = "Close a specific window or the currently active window."
    risk_level = RiskLevel.CONFIRM
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Optional title of window to close. If omitted, closes active window."}
        },
    }

    def execute(self, title: str = "", **kwargs: Any) -> ToolResult:
        try:
            import win32gui
            import win32con

            target_hwnd = None
            closed_title = ""
            if title:
                clean = title.lower().strip()
                for w in WindowHelper.list_visible_windows():
                    if clean in w["title"].lower():
                        target_hwnd = w["hwnd"]
                        closed_title = w["title"]
                        break
            else:
                target_hwnd = win32gui.GetForegroundWindow()
                if target_hwnd:
                    closed_title = win32gui.GetWindowText(target_hwnd)

            if target_hwnd and win32gui.IsWindow(target_hwnd):
                win32gui.PostMessage(target_hwnd, win32con.WM_CLOSE, 0, 0)
                return ToolResult(
                    success=True,
                    message=f"Closed window '{closed_title or target_hwnd}'.",
                    data={"hwnd": target_hwnd, "title": closed_title},
                )
        except Exception as exc:
            return ToolResult(success=False, error=f"Close window failed: {exc}")

        return ToolResult(success=False, error="Window not found.")


class WindowsShowDesktopTool(BaseTool):
    name = "windows.show_desktop"
    description = "Show the Windows desktop by minimizing all open windows."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            # Win + D
            ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x44, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x44, 0, 2, 0)
            ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)
            return ToolResult(
                success=True,
                message="Showing desktop.",
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Show desktop failed: {exc}")
