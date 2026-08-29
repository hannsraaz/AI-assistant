from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from core.tools.base import BaseTool, RiskLevel, ToolResult


class ScreenshotTakeTool(BaseTool):
    name = "screenshot.take"
    description = "Capture a screenshot of the entire screen, active window, or a specific screen region."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["fullscreen", "active_window", "region"],
                "description": "Capture target mode (fullscreen, active_window, or region).",
                "default": "fullscreen",
            },
            "name": {"type": "string", "description": "Optional name prefix for the saved file."},
            "region": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Optional [x, y, width, height] bounding box for region capture.",
            },
        },
    }

    def __init__(self, output_directory: str | Path = "data/screenshots") -> None:
        self.output_dir = Path(output_directory)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def execute(
        self,
        mode: str = "fullscreen",
        name: str | None = None,
        region: list[int] | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = (name or f"screenshot_{mode}").replace(" ", "_")
        filename = f"{prefix}_{timestamp}.png"
        target_path = self.output_dir / filename

        try:
            from PIL import ImageGrab

            # 1. Active window mode
            if mode == "active_window":
                try:
                    import win32gui
                    hwnd = win32gui.GetForegroundWindow()
                    if hwnd:
                        rect = win32gui.GetWindowRect(hwnd)  # (left, top, right, bottom)
                        img = ImageGrab.grab(bbox=rect)
                        img.save(str(target_path), "PNG")
                        return ToolResult(
                            success=True,
                            message=f"Active window screenshot saved as {filename}.",
                            data={"path": str(target_path), "filename": filename, "width": img.width, "height": img.height},
                        )
                except Exception:
                    pass

            # 2. Region mode
            if mode == "region" and region and len(region) == 4:
                x, y, w, h = region
                bbox = (x, y, x + w, y + h)
                img = ImageGrab.grab(bbox=bbox)
                img.save(str(target_path), "PNG")
                return ToolResult(
                    success=True,
                    message=f"Region screenshot saved as {filename}.",
                    data={"path": str(target_path), "filename": filename, "width": img.width, "height": img.height},
                )

            # 3. Fullscreen (mss preferred, ImageGrab fallback)
            try:
                import mss
                import mss.tools

                with mss.mss() as sct:
                    monitor = sct.monitors[0]
                    sct_img = sct.grab(monitor)
                    mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(target_path))
                    return ToolResult(
                        success=True,
                        message=f"Screenshot saved as {filename}.",
                        data={"path": str(target_path), "filename": filename, "width": sct_img.width, "height": sct_img.height},
                    )
            except Exception:
                img = ImageGrab.grab(all_screens=True)
                img.save(str(target_path), "PNG")
                return ToolResult(
                    success=True,
                    message=f"Screenshot saved as {filename}.",
                    data={"path": str(target_path), "filename": filename, "width": img.width, "height": img.height},
                )
        except Exception as exc:
            return ToolResult(success=False, error=f"Screenshot failed: {exc}")
