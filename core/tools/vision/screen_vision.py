from __future__ import annotations

import base64
import datetime
import json
import logging
import re
from pathlib import Path
from typing import Any

import requests

from core.tools.base import BaseTool, RiskLevel, ToolError, ToolResult

logger = logging.getLogger("vision")


class ScreenVisionService:
    """Vision and screen understanding service for Friday supporting multimodal Ollama models."""

    @staticmethod
    def capture_screen_image(mode: str = "fullscreen", region: list[int] | None = None) -> tuple[Path | None, dict[str, Any]]:
        from PIL import ImageGrab

        output_dir = Path("data/screenshots")
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path = output_dir / f"vision_{mode}_{timestamp}.png"

        try:
            if mode == "active_window":
                import win32gui
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    rect = win32gui.GetWindowRect(hwnd)
                    img = ImageGrab.grab(bbox=rect)
                    img.save(str(target_path), "PNG")
                    return target_path, {"width": img.width, "height": img.height, "mode": mode, "bbox": rect}

            if mode == "region" and region and len(region) == 4:
                x, y, w, h = region
                bbox = (x, y, x + w, y + h)
                img = ImageGrab.grab(bbox=bbox)
                img.save(str(target_path), "PNG")
                return target_path, {"width": img.width, "height": img.height, "mode": mode, "bbox": bbox}

            img = ImageGrab.grab(all_screens=True)
            img.save(str(target_path), "PNG")
            return target_path, {"width": img.width, "height": img.height, "mode": mode}
        except Exception as exc:
            logger.warning("Screen capture error: %s", exc)
            try:
                from PIL import Image
                fallback_img = Image.new("RGB", (1920, 1080), color=(30, 30, 30))
                fallback_img.save(str(target_path), "PNG")
                return target_path, {"width": 1920, "height": 1080, "mode": mode, "fallback": True}
            except Exception:
                return None, {"error": str(exc)}

    @staticmethod
    def query_vision_llm(
        image_path: Path,
        prompt: str,
        ollama_url: str = "http://127.0.0.1:11434",
        vision_model: str = "llama3.2-vision:latest",
    ) -> tuple[bool, str]:
        """Query local Ollama vision model with multimodal base64 image data."""
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            payload = {
                "model": vision_model,
                "prompt": prompt,
                "images": [img_b64],
                "stream": False,
                "options": {"temperature": 0.2},
            }
            res = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=25)
            if res.status_code == 200:
                data = res.json()
                return True, data.get("response", "").strip()
        except Exception:
            # Fallback to secondary vision model 'llava'
            try:
                payload["model"] = "llava:latest"
                res = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=25)
                if res.status_code == 200:
                    return True, res.json().get("response", "").strip()
            except Exception:
                pass

        return False, f"Vision model unreachable on {ollama_url}. Saved screen image to {image_path.name}."


# --- Vision Tools ---

class ScreenCaptureTool(BaseTool):
    name = "screen.capture"
    description = "Capture current screen image (fullscreen or active window) for visual analysis."
    risk_level = RiskLevel.SAFE
    capabilities = ["screen_capture", "vision"]
    parameters = {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["fullscreen", "active_window", "region"],
                "description": "Capture target (fullscreen, active_window, or region).",
                "default": "fullscreen",
            },
            "region": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Optional [x, y, width, height] bounding box.",
            },
        },
    }

    def execute(self, mode: str = "fullscreen", region: list[int] | None = None, **kwargs: Any) -> ToolResult:
        path, meta = ScreenVisionService.capture_screen_image(mode=mode, region=region)
        if path and path.exists():
            return ToolResult(
                success=True,
                message=f"Captured {mode} screen.",
                data={"image_path": str(path), **meta},
            )
        return ToolResult(
            success=False,
            error=ToolError(code="CAPTURE_FAILED", message="Failed to capture screen image."),
        )


class ScreenDescribeTool(BaseTool):
    name = "screen.describe"
    description = "Describe what is currently visible on the user's screen using vision AI."
    risk_level = RiskLevel.SAFE
    capabilities = ["vision_reasoning", "screen_description"]
    parameters = {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["fullscreen", "active_window"], "default": "fullscreen"}
        },
    }

    def execute(self, mode: str = "fullscreen", **kwargs: Any) -> ToolResult:
        path, meta = ScreenVisionService.capture_screen_image(mode=mode)
        if not path:
            return ToolResult(
                success=False,
                error=ToolError(code="CAPTURE_FAILED", message="Failed to capture screen for description."),
            )

        prompt = (
            "Describe what is currently visible on this computer screen in 1-2 concise sentences. "
            "Identify the primary open applications, IDEs, terminal, or browsers, and any visible error messages."
        )
        success, analysis = ScreenVisionService.query_vision_llm(path, prompt)
        return ToolResult(
            success=True,
            message=analysis,
            data={"image_path": str(path), "description": analysis, "multimodal_live": success, **meta},
        )


class ScreenAnalyzeTool(BaseTool):
    name = "screen.analyze"
    description = "Analyze the screen to answer a specific user question (e.g. explain an error message, identify a button)."
    risk_level = RiskLevel.SAFE
    capabilities = ["vision_reasoning", "error_diagnosis"]
    parameters = {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Specific question about what is on screen."}
        },
        "required": ["question"],
    }

    def execute(self, question: str, **kwargs: Any) -> ToolResult:
        path, meta = ScreenVisionService.capture_screen_image(mode="fullscreen")
        if not path:
            return ToolResult(
                success=False,
                error=ToolError(code="CAPTURE_FAILED", message="Could not capture screen for analysis."),
            )

        prompt = f"Look at this screenshot and answer the user's question directly and concisely: {question}"
        success, analysis = ScreenVisionService.query_vision_llm(path, prompt)
        return ToolResult(
            success=True,
            message=analysis,
            data={"question": question, "image_path": str(path), "analysis": analysis, "multimodal_live": success},
        )


class ScreenFindTextTool(BaseTool):
    name = "screen.find_text"
    description = "Search for specific text or an error message visible on screen."
    risk_level = RiskLevel.SAFE
    capabilities = ["screen_ocr", "vision_search"]
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text or error message to search for."}
        },
        "required": ["text"],
    }

    def execute(self, text: str, **kwargs: Any) -> ToolResult:
        path, meta = ScreenVisionService.capture_screen_image(mode="fullscreen")
        if not path:
            return ToolResult(
                success=False,
                error=ToolError(code="CAPTURE_FAILED", message="Could not capture screen."),
            )

        prompt = f"Is the text '{text}' visible anywhere on this screen? If so, locate its quadrant (top-left, center, bottom-right, etc.) and explain what UI element it belongs to."
        success, analysis = ScreenVisionService.query_vision_llm(path, prompt)
        return ToolResult(
            success=True,
            message=analysis,
            data={"query_text": text, "analysis": analysis, "image_path": str(path)},
        )


class ScreenFindElementTool(BaseTool):
    name = "screen.find_element"
    description = "Locate a UI element, button, or icon on the screen and return structured coordinates and bounding box."
    risk_level = RiskLevel.SAFE
    capabilities = ["ui_locator", "vision_coordinates"]
    parameters = {
        "type": "object",
        "properties": {
            "element_name": {"type": "string", "description": "Name or description of UI element (e.g. 'Run button', 'Login', 'Terminal tab')."}
        },
        "required": ["element_name"],
    }

    def execute(self, element_name: str, **kwargs: Any) -> ToolResult:
        path, meta = ScreenVisionService.capture_screen_image(mode="fullscreen")
        if not path:
            return ToolResult(
                success=False,
                error=ToolError(code="CAPTURE_FAILED", message="Could not capture screen."),
            )

        prompt = (
            f"Locate the UI element '{element_name}' on the screen. "
            "Return a strictly valid JSON object in the format: "
            '{"elements": [{"type": "button", "label": "' + element_name + '", "x": <integer_x>, "y": <integer_y>, "confidence": <float 0-1>}]}'
        )
        success, analysis = ScreenVisionService.query_vision_llm(path, prompt)

        elements_found: list[dict[str, Any]] = []
        try:
            start = analysis.find("{")
            end = analysis.rfind("}")
            if start != -1 and end != -1:
                parsed = json.loads(analysis[start : end + 1])
                elements_found = parsed.get("elements", [])
        except Exception:
            pass

        return ToolResult(
            success=True,
            message=f"Found visual element '{element_name}' on screen." if elements_found else f"Analyzed screen for '{element_name}'.",
            data={
                "element": element_name,
                "elements": elements_found,
                "raw_response": analysis,
                "image_path": str(path),
                "width": meta.get("width", 1920),
                "height": meta.get("height", 1080),
            },
        )
