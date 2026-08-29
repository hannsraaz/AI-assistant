from __future__ import annotations

import ctypes
from typing import Any

from core.tools.base import BaseTool, RiskLevel, ToolResult


class MediaHelper:
    """Sends Windows virtual multimedia keystrokes."""

    @staticmethod
    def send_vk(vk_code: int) -> None:
        try:
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
        except Exception:
            pass


class MediaPlayPauseTool(BaseTool):
    name = "media.play_pause"
    description = "Toggle media playback (play or pause current media)."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        MediaHelper.send_vk(0xB3)  # VK_MEDIA_PLAY_PAUSE
        return ToolResult(success=True, message="Toggled media playback.")


class MediaPlayTool(BaseTool):
    name = "media.play"
    description = "Resume or start media playback."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        MediaHelper.send_vk(0xB3)  # VK_MEDIA_PLAY_PAUSE
        return ToolResult(success=True, message="Playing media.")


class MediaPauseTool(BaseTool):
    name = "media.pause"
    description = "Pause current media playback."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        MediaHelper.send_vk(0xB3)  # VK_MEDIA_PLAY_PAUSE
        return ToolResult(success=True, message="Paused media.")


class MediaNextTool(BaseTool):
    name = "media.next"
    description = "Skip to the next media track."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        MediaHelper.send_vk(0xB0)  # VK_MEDIA_NEXT_TRACK
        return ToolResult(success=True, message="Playing next track.")


class MediaPreviousTool(BaseTool):
    name = "media.previous"
    description = "Skip to the previous media track."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        MediaHelper.send_vk(0xB1)  # VK_MEDIA_PREV_TRACK
        return ToolResult(success=True, message="Playing previous track.")


class MediaStopTool(BaseTool):
    name = "media.stop"
    description = "Stop media playback."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        MediaHelper.send_vk(0xB2)  # VK_MEDIA_STOP
        return ToolResult(success=True, message="Stopped playback.")
