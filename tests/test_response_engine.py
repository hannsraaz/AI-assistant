from __future__ import annotations

from core.response_engine import ResponseEngine
from core.tools.base import ToolResult


def test_response_engine_formatting() -> None:
    # Volume formatting
    vol_res = ToolResult(success=True, data={"volume": 65})
    assert "65 percent" in ResponseEngine.format_tool_response("system.volume.set", vol_res)

    # Battery formatting
    bat_res = ToolResult(success=True, data={"has_battery": True, "percent": 88, "charging": True})
    bat_msg = ResponseEngine.format_tool_response("system.battery", bat_res)
    assert "88 percent" in bat_msg
    assert "charging" in bat_msg

    # AC Desktop formatting
    ac_res = ToolResult(success=True, data={"has_battery": False})
    assert "AC desktop power" in ResponseEngine.format_tool_response("system.battery", ac_res)

    # Error handling
    err_res = ToolResult(success=False, error="Process access denied")
    assert "couldn't do that" in ResponseEngine.format_tool_response("apps.close", err_res)


def test_response_classification_and_routing() -> None:
    from core.response_engine import ResponseClass

    # FAST
    assert ResponseEngine.classify_response("Muted.", tool_name="system.volume.mute") == ResponseClass.FAST
    assert ResponseEngine.classify_response("Done.") == ResponseClass.FAST

    # ALERT
    assert ResponseEngine.classify_response("Build failed with error 1", is_error=True) == ResponseClass.ALERT
    assert ResponseEngine.classify_response("Warning: Battery low.") == ResponseClass.ALERT

    # CINEMATIC
    long_text = " ".join(["word"] * 40)
    assert ResponseEngine.classify_response(long_text) == ResponseClass.CINEMATIC

    # NORMAL
    assert ResponseEngine.classify_response("I have opened Visual Studio Code for you.") == ResponseClass.NORMAL

    # TTS Backend Selection
    assert ResponseEngine.select_tts_backend(ResponseClass.FAST) == "piper"
    assert ResponseEngine.select_tts_backend(ResponseClass.NORMAL) == "piper"
    assert ResponseEngine.select_tts_backend(ResponseClass.ALERT) == "piper"

