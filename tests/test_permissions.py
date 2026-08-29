from __future__ import annotations

import pytest

from core.tools.base import BaseTool, RiskLevel, ToolResult
from core.tools.permissions import PermissionManager
from core.tools.registry import ToolRegistry


class DummySafeTool(BaseTool):
    name = "dummy.safe"
    risk_level = RiskLevel.SAFE

    def execute(self, **kwargs: None) -> ToolResult:
        return ToolResult(success=True, message="Safe executed.")


class DummyConfirmTool(BaseTool):
    name = "dummy.confirm"
    risk_level = RiskLevel.CONFIRM

    def execute(self, target: str = "", **kwargs: None) -> ToolResult:
        return ToolResult(success=True, message=f"Confirmed executed for {target}.")


class DummyHighRiskTool(BaseTool):
    name = "dummy.high_risk"
    risk_level = RiskLevel.HIGH_RISK

    def execute(self, **kwargs: None) -> ToolResult:
        return ToolResult(success=True, message="High risk executed.")


def test_permission_safe_execution() -> None:
    pm = PermissionManager()
    reg = ToolRegistry(permission_manager=pm)
    reg.register(DummySafeTool())

    res = reg.execute("dummy.safe")
    assert res.success is True
    assert res.needs_confirmation is False
    assert res.message == "Safe executed."


def test_permission_confirm_requires_token_or_confirmation() -> None:
    pm = PermissionManager()
    reg = ToolRegistry(permission_manager=pm)
    reg.register(DummyConfirmTool())

    # 1. Unconfirmed attempt
    res = reg.execute("dummy.confirm", target="something")
    assert res.success is False
    assert res.needs_confirmation is True
    assert "confirmation_token" in res.data
    token = res.data["confirmation_token"]

    # 2. Confirm via token
    confirm_res = pm.confirm_token(token)
    assert confirm_res.success is True
    assert "something" in confirm_res.message

    # 3. Direct confirmed execution
    direct_res = reg.execute("dummy.confirm", confirmed=True, target="direct")
    assert direct_res.success is True
    assert "direct" in direct_res.message


def test_permission_override_whitelist() -> None:
    pm = PermissionManager()
    reg = ToolRegistry(permission_manager=pm)
    reg.register(DummyHighRiskTool())

    # Blocked initially
    res1 = reg.execute("dummy.high_risk")
    assert res1.needs_confirmation is True

    # Allow override
    pm.set_override("dummy.high_risk", True)
    res2 = reg.execute("dummy.high_risk")
    assert res2.success is True
    assert res2.message == "High risk executed."
