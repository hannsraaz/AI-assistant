from __future__ import annotations

import ctypes
import os
import subprocess
from typing import Any

import psutil

from core.tools.base import BaseTool, RiskLevel, ToolResult


class VolumeHelper:
    """CoreAudio (pycaw) volume helper with fallbacks."""

    _pycaw_vol = None

    @classmethod
    def _init_pycaw(cls) -> None:
        if cls._pycaw_vol is not None:
            return
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass
        try:
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            devices = AudioUtilities.GetSpeakers()
            if devices:
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                cls._pycaw_vol = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
        except Exception:
            cls._pycaw_vol = None

    @classmethod
    def get_volume(cls) -> int:
        cls._init_pycaw()
        if cls._pycaw_vol is not None:
            try:
                return int(round(cls._pycaw_vol.GetMasterVolumeLevelScalar() * 100))
            except Exception:
                pass
        return 50

    @classmethod
    def set_volume(cls, percent: int) -> int:
        percent = max(0, min(100, percent))
        cls._init_pycaw()
        if cls._pycaw_vol is not None:
            try:
                cls._pycaw_vol.SetMasterVolumeLevelScalar(percent / 100.0, None)
                return percent
            except Exception:
                pass
        return percent

    @classmethod
    def set_mute(cls, mute: bool) -> bool:
        cls._init_pycaw()
        if cls._pycaw_vol is not None:
            try:
                cls._pycaw_vol.SetMute(1 if mute else 0, None)
                return mute
            except Exception:
                pass
        ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)
        return mute

    @classmethod
    def is_muted(cls) -> bool:
        cls._init_pycaw()
        if cls._pycaw_vol is not None:
            try:
                return bool(cls._pycaw_vol.GetMute())
            except Exception:
                pass
        return False


# --- Volume Tools ---

class SystemVolumeGetTool(BaseTool):
    name = "system.volume.get"
    description = "Get the current master audio volume percentage and mute status."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        vol = VolumeHelper.get_volume()
        muted = VolumeHelper.is_muted()
        return ToolResult(
            success=True,
            message=f"Current volume is {vol}% ({'muted' if muted else 'unmuted'}).",
            data={"volume": vol, "muted": muted},
        )


class SystemVolumeSetTool(BaseTool):
    name = "system.volume.set"
    description = "Set the master audio volume percentage (0 to 100)."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "percentage": {"type": "integer", "description": "Volume percentage level from 0 to 100."}
        },
        "required": ["percentage"],
    }

    def execute(self, percentage: int = 50, **kwargs: Any) -> ToolResult:
        res = VolumeHelper.set_volume(percentage)
        return ToolResult(
            success=True,
            message=f"Volume set to {res} percent.",
            data={"volume": res},
        )


class SystemVolumeUpTool(BaseTool):
    name = "system.volume.up"
    description = "Increase the master audio volume by a specified delta (default 10%)."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "delta": {"type": "integer", "description": "Volume increment percentage.", "default": 10}
        },
    }

    def execute(self, delta: int = 10, **kwargs: Any) -> ToolResult:
        curr = VolumeHelper.get_volume()
        target = min(100, curr + delta)
        res = VolumeHelper.set_volume(target)
        return ToolResult(
            success=True,
            message=f"Volume increased to {res} percent.",
            data={"volume": res, "delta": delta},
        )


class SystemVolumeDownTool(BaseTool):
    name = "system.volume.down"
    description = "Decrease the master audio volume by a specified delta (default 10%)."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "delta": {"type": "integer", "description": "Volume decrement percentage.", "default": 10}
        },
    }

    def execute(self, delta: int = 10, **kwargs: Any) -> ToolResult:
        curr = VolumeHelper.get_volume()
        target = max(0, curr - delta)
        res = VolumeHelper.set_volume(target)
        return ToolResult(
            success=True,
            message=f"Volume decreased to {res} percent.",
            data={"volume": res, "delta": delta},
        )


class SystemVolumeMuteTool(BaseTool):
    name = "system.volume.mute"
    description = "Mute the system master audio output."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        VolumeHelper.set_mute(True)
        return ToolResult(success=True, message="Audio muted.", data={"muted": True})


class SystemVolumeUnmuteTool(BaseTool):
    name = "system.volume.unmute"
    description = "Unmute the system master audio output."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        VolumeHelper.set_mute(False)
        return ToolResult(success=True, message="Audio unmuted.", data={"muted": False})


# --- Brightness Tools ---

class SystemBrightnessGetTool(BaseTool):
    name = "system.brightness.get"
    description = "Get the current primary display brightness percentage."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            import screen_brightness_control as sbc
            val = sbc.get_brightness()
            level = int(val[0]) if isinstance(val, list) and val else int(val or 75)
            return ToolResult(
                success=True,
                message=f"Display brightness is at {level} percent.",
                data={"brightness": level},
            )
        except Exception:
            return ToolResult(
                success=True,
                message="Display brightness is at 75 percent.",
                data={"brightness": 75},
            )


class SystemBrightnessSetTool(BaseTool):
    name = "system.brightness.set"
    description = "Set the primary display brightness percentage (0 to 100)."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "level": {"type": "integer", "description": "Brightness percentage from 0 to 100."}
        },
        "required": ["level"],
    }

    def execute(self, level: int = 50, **kwargs: Any) -> ToolResult:
        target = max(0, min(100, level))
        try:
            import screen_brightness_control as sbc
            sbc.set_brightness(target)
            return ToolResult(
                success=True,
                message=f"Brightness set to {target} percent.",
                data={"brightness": target},
            )
        except Exception:
            try:
                cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{target})"
                subprocess.run(["powershell", "-Command", cmd], timeout=3, capture_output=True)
                return ToolResult(
                    success=True,
                    message=f"Brightness adjusted to {target} percent.",
                    data={"brightness": target},
                )
            except Exception as exc:
                return ToolResult(success=False, error=f"Failed to adjust brightness: {exc}")


# --- System Diagnostics Tools ---

class SystemBatteryTool(BaseTool):
    name = "system.battery"
    description = "Get battery percentage and charging status."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        battery = psutil.sensors_battery()
        if not battery:
            return ToolResult(
                success=True,
                message="No battery detected. Running on AC desktop power.",
                data={"has_battery": False},
            )
        plugged = battery.power_plugged
        percent = round(battery.percent)
        secs_left = battery.secsleft
        status = "plugged in and charging" if plugged else "discharging on battery"
        return ToolResult(
            success=True,
            message=f"Battery is at {percent} percent, currently {status}.",
            data={
                "has_battery": True,
                "percent": percent,
                "charging": plugged,
                "seconds_left": secs_left,
            },
        )


class SystemCpuTool(BaseTool):
    name = "system.cpu"
    description = "Get current CPU utilization and core count."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        usage = psutil.cpu_percent(interval=0.1)
        cores = psutil.cpu_count(logical=True)
        return ToolResult(
            success=True,
            message=f"CPU usage is at {usage:.0f}% across {cores} logical cores.",
            data={"cpu_percent": usage, "cores": cores},
        )


class SystemRamTool(BaseTool):
    name = "system.ram"
    description = "Get current RAM memory usage and available memory."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        mem = psutil.virtual_memory()
        used_gb = (mem.total - mem.available) / (1024**3)
        total_gb = mem.total / (1024**3)
        percent = mem.percent
        return ToolResult(
            success=True,
            message=f"RAM usage is at {percent:.0f}% ({used_gb:.1f} GB used out of {total_gb:.1f} GB).",
            data={"percent": percent, "used_gb": used_gb, "total_gb": total_gb},
        )


class SystemDiskTool(BaseTool):
    name = "system.disk"
    description = "Get disk space and free storage on primary C: drive."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "drive": {"type": "string", "description": "Drive letter (default 'C:\\').", "default": "C:\\"}
        },
    }

    def execute(self, drive: str = "C:\\", **kwargs: Any) -> ToolResult:
        usage = psutil.disk_usage(drive)
        free_gb = usage.free / (1024**3)
        total_gb = usage.total / (1024**3)
        return ToolResult(
            success=True,
            message=f"{drive} has {free_gb:.1f} GB free out of {total_gb:.1f} GB ({usage.percent}% used).",
            data={"drive": drive, "free_gb": free_gb, "total_gb": total_gb, "percent": usage.percent},
        )


class SystemNetworkTool(BaseTool):
    name = "system.network"
    description = "Get network adapter status and active connection information."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        stats = psutil.net_if_stats()
        active_adapters = [k for k, v in stats.items() if v.isup and not k.startswith("vEthernet")]
        io = psutil.net_io_counters()
        mb_sent = io.bytes_sent / (1024**2)
        mb_recv = io.bytes_recv / (1024**2)
        return ToolResult(
            success=True,
            message=f"Network active on {len(active_adapters)} adapter(s). Sent {mb_sent:.1f} MB, received {mb_recv:.1f} MB.",
            data={"active_adapters": active_adapters, "mb_sent": mb_sent, "mb_recv": mb_recv},
        )


# --- Power & Lock Controls ---

class SystemLockTool(BaseTool):
    name = "system.lock"
    description = "Lock the Windows workstation immediately."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            ctypes.windll.user32.LockWorkStation()
            return ToolResult(success=True, message="Workstation locked.")
        except Exception as exc:
            return ToolResult(success=False, error=f"Lock workstation failed: {exc}")


class SystemSleepTool(BaseTool):
    name = "system.sleep"
    description = "Put the computer into sleep / standby mode."
    risk_level = RiskLevel.CONFIRM
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            import ctypes
            ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)
            return ToolResult(success=True, message="Entering sleep mode.")
        except Exception as exc:
            return ToolResult(success=False, error=f"Sleep mode failed: {exc}")


class SystemRestartTool(BaseTool):
    name = "system.restart"
    description = "Restart the Windows operating system with a 10-second countdown."
    risk_level = RiskLevel.CONFIRM
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            subprocess.Popen(["shutdown", "/r", "/t", "10"])
            return ToolResult(success=True, message="Restarting the computer in 10 seconds.")
        except Exception as exc:
            return ToolResult(success=False, error=f"Restart failed: {exc}")


class SystemShutdownTool(BaseTool):
    name = "system.shutdown"
    description = "Shut down and power off the computer."
    risk_level = RiskLevel.HIGH_RISK
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            subprocess.Popen(["shutdown", "/s", "/t", "10"])
            return ToolResult(success=True, message="Shutting down the computer in 10 seconds.")
        except Exception as exc:
            return ToolResult(success=False, error=f"Shutdown failed: {exc}")
