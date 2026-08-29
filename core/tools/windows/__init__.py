"""Windows Automation Tools for Friday."""
from core.tools.registry import ToolRegistry
from core.tools.windows.apps import (
    AppsCloseTool,
    AppsFindTool,
    AppsFocusTool,
    AppsListTool,
    AppsOpenTool,
)
from core.tools.windows.clipboard import (
    ClipboardClearTool,
    ClipboardReadTool,
    ClipboardWriteTool,
)
from core.tools.windows.media import (
    MediaNextTool,
    MediaPauseTool,
    MediaPlayPauseTool,
    MediaPlayTool,
    MediaPreviousTool,
    MediaStopTool,
)
from core.tools.windows.screenshot import ScreenshotTakeTool
from core.tools.windows.system import (
    SystemBatteryTool,
    SystemBrightnessGetTool,
    SystemBrightnessSetTool,
    SystemCpuTool,
    SystemDiskTool,
    SystemLockTool,
    SystemNetworkTool,
    SystemRamTool,
    SystemRestartTool,
    SystemShutdownTool,
    SystemSleepTool,
    SystemVolumeDownTool,
    SystemVolumeGetTool,
    SystemVolumeMuteTool,
    SystemVolumeSetTool,
    SystemVolumeUnmuteTool,
    SystemVolumeUpTool,
)
from core.tools.windows.windows_mgr import (
    WindowsCloseTool,
    WindowsFocusTool,
    WindowsListTool,
    WindowsMaximizeTool,
    WindowsMinimizeTool,
    WindowsRestoreTool,
    WindowsShowDesktopTool,
)


def register_windows_tools(registry: ToolRegistry, screenshot_dir: str = "data/screenshots") -> None:
    """Register all Windows automation tools into the given registry."""
    tools = [
        # Apps
        AppsListTool(),
        AppsFindTool(),
        AppsOpenTool(),
        AppsCloseTool(),
        AppsFocusTool(),
        # Windows
        WindowsListTool(),
        WindowsFocusTool(),
        WindowsMinimizeTool(),
        WindowsMaximizeTool(),
        WindowsRestoreTool(),
        WindowsCloseTool(),
        WindowsShowDesktopTool(),
        # System - Volume
        SystemVolumeGetTool(),
        SystemVolumeSetTool(),
        SystemVolumeUpTool(),
        SystemVolumeDownTool(),
        SystemVolumeMuteTool(),
        SystemVolumeUnmuteTool(),
        # System - Brightness
        SystemBrightnessGetTool(),
        SystemBrightnessSetTool(),
        # System - Stats & Diagnostics
        SystemBatteryTool(),
        SystemCpuTool(),
        SystemRamTool(),
        SystemDiskTool(),
        SystemNetworkTool(),
        # System - Power
        SystemLockTool(),
        SystemSleepTool(),
        SystemRestartTool(),
        SystemShutdownTool(),
        # Media
        MediaPlayPauseTool(),
        MediaPlayTool(),
        MediaPauseTool(),
        MediaNextTool(),
        MediaPreviousTool(),
        MediaStopTool(),
        # Clipboard
        ClipboardReadTool(),
        ClipboardWriteTool(),
        ClipboardClearTool(),
        # Screenshot
        ScreenshotTakeTool(output_directory=screenshot_dir),
    ]
    registry.register_many(tools)


__all__ = [
    "register_windows_tools",
    "AppsListTool",
    "AppsFindTool",
    "AppsOpenTool",
    "AppsCloseTool",
    "AppsFocusTool",
    "WindowsListTool",
    "WindowsFocusTool",
    "WindowsMinimizeTool",
    "WindowsMaximizeTool",
    "WindowsRestoreTool",
    "WindowsCloseTool",
    "WindowsShowDesktopTool",
    "SystemVolumeGetTool",
    "SystemVolumeSetTool",
    "SystemVolumeUpTool",
    "SystemVolumeDownTool",
    "SystemVolumeMuteTool",
    "SystemVolumeUnmuteTool",
    "SystemBrightnessGetTool",
    "SystemBrightnessSetTool",
    "SystemBatteryTool",
    "SystemCpuTool",
    "SystemRamTool",
    "SystemDiskTool",
    "SystemNetworkTool",
    "SystemLockTool",
    "SystemSleepTool",
    "SystemRestartTool",
    "SystemShutdownTool",
    "MediaPlayPauseTool",
    "MediaPlayTool",
    "MediaPauseTool",
    "MediaNextTool",
    "MediaPreviousTool",
    "MediaStopTool",
    "ClipboardReadTool",
    "ClipboardWriteTool",
    "ClipboardClearTool",
    "ScreenshotTakeTool",
]
