from __future__ import annotations

from pathlib import Path
import pytest

from core.tools.files import register_file_tools
from core.tools.registry import ToolRegistry


@pytest.fixture
def file_registry(tmp_path: Path) -> ToolRegistry:
    reg = ToolRegistry()
    register_file_tools(reg)
    return reg


def test_files_crud_lifecycle(file_registry: ToolRegistry, tmp_path: Path) -> None:
    test_file = tmp_path / "test_doc.txt"

    # 1. Create file
    res_create = file_registry.execute("files.create", path=str(test_file), content="Hello Friday V2!", confirmed=True)
    assert res_create.success is True
    assert test_file.exists()

    # 2. Exists tool
    res_exists = file_registry.execute("files.exists", path=str(test_file))
    assert res_exists.success is True
    assert res_exists.data["exists"] is True

    # 3. Read file
    res_read = file_registry.execute("files.read", path=str(test_file))
    assert res_read.success is True
    assert "Hello Friday V2!" in res_read.data["content"]

    # 4. List directory
    res_list = file_registry.execute("files.list", directory=str(tmp_path))
    assert res_list.success is True
    assert res_list.data["count"] >= 1

    # 5. Search files
    res_search = file_registry.execute("files.search", query="test_doc", directory=str(tmp_path))
    assert res_search.success is True
    assert res_search.data["count"] >= 1

    # 6. Delete file
    res_delete = file_registry.execute("files.delete", path=str(test_file), confirmed=True)
    assert res_delete.success is True
    assert not test_file.exists()
