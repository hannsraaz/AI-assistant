from __future__ import annotations

from pathlib import Path
import pytest

from core.memory import MemoryManager, register_memory_tools
from core.tools.registry import ToolRegistry


@pytest.fixture
def memory_system(tmp_path: Path) -> tuple[ToolRegistry, MemoryManager]:
    reg = ToolRegistry()
    mm = MemoryManager(memory_file=tmp_path / "test_mem.json")
    register_memory_tools(reg, memory_manager=mm)
    return reg, mm


def test_memory_lifecycle_and_recall(memory_system: tuple[ToolRegistry, MemoryManager]) -> None:
    reg, mm = memory_system

    # 1. Remember fact
    res1 = reg.execute("memory.remember", key="project_name", value="Friday V2 Assistant", category="facts")
    assert res1.success is True

    # 2. Remember project alias
    res2 = reg.execute("memory.remember", key="Nova", value="C:/Projects/NovaAndroid", category="project_aliases")
    assert res2.success is True

    # 3. Recall
    res3 = reg.execute("memory.recall", query="Nova")
    assert res3.success is True
    assert "Nova" in str(res3.data["results"])

    # 4. Privacy protection rejects raw passwords
    res_sec = reg.execute("memory.remember", key="my_secret_pw", value="password = SuperSecret123!", category="facts")
    assert res_sec.success is False
    assert "sensitive" in res_sec.get_error_message().lower()

    # 5. Forget
    res4 = reg.execute("memory.forget", key="project_name", confirmed=True)
    assert res4.success is True
