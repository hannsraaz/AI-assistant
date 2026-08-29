from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Any

from core.tools.base import BaseTool, RiskLevel, ToolError, ToolResult


class FileHelper:
    """Safe filesystem operations with strict path traversal, symlink, and system directory protection."""

    # Absolute protected root system directories on Windows
    PROTECTED_DIRS = {
        Path(os.environ.get("WINDIR", r"C:\Windows")).resolve(),
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")).resolve(),
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")).resolve(),
        Path(r"C:\ProgramData\Microsoft").resolve(),
    }

    @classmethod
    def resolve_safe_path(cls, path_str: str, base_dir: Path | None = None) -> tuple[Path | None, ToolError | None]:
        """Resolve and canonicalize path with path traversal and symlink boundary verification."""
        if not path_str or not path_str.strip():
            return None, ToolError(code="INVALID_PATH", message="Path string cannot be empty.")

        clean_str = path_str.strip()

        # Expand user and environment variables
        expanded = os.path.expandvars(os.path.expanduser(clean_str))
        raw_path = Path(expanded)

        if not raw_path.is_absolute():
            # If relative, resolve against base_dir or User Home
            anchor = base_dir or Path.home()
            target = (anchor / raw_path).resolve()
        else:
            target = raw_path.resolve()

        # Check for system directory access
        for protected in cls.PROTECTED_DIRS:
            if target == protected or protected in target.parents:
                return None, ToolError(
                    code="PROTECTED_DIRECTORY",
                    message=f"Access to protected system directory '{target}' is prohibited.",
                    details={"path": str(target), "protected_root": str(protected)},
                )

        return target, None


# --- File Tools ---

class FilesSearchTool(BaseTool):
    name = "files.search"
    description = "Search for files by name, pattern, or extension across user directories or a specific folder."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Filename, substring, or wildcard pattern (e.g. '*.pdf', 'project', 'report')."},
            "directory": {"type": "string", "description": "Optional directory path to search in (e.g. 'Downloads', 'Documents').", "default": ""},
            "max_results": {"type": "integer", "description": "Maximum number of results to return.", "default": 20},
        },
        "required": ["query"],
    }

    def execute(self, query: str, directory: str = "", max_results: int = 20, **kwargs: Any) -> ToolResult:
        search_dirs: list[Path] = []
        if directory:
            p, err = FileHelper.resolve_safe_path(directory)
            if err:
                return ToolResult(success=False, error=err)
            if p and p.exists() and p.is_dir():
                search_dirs.append(p)
            else:
                return ToolResult(
                    success=False,
                    error=ToolError(code="DIRECTORY_NOT_FOUND", message=f"Search directory '{directory}' does not exist."),
                )
        else:
            home = Path.home()
            search_dirs = [home / "Downloads", home / "Desktop", home / "Documents", Path.cwd()]

        matches: list[dict[str, Any]] = []
        clean_query = query.strip().lower()

        for base_dir in search_dirs:
            if not base_dir.exists():
                continue
            try:
                for root, dirs, files in os.walk(base_dir, followlinks=False):
                    # Skip heavy / hidden / build folders
                    dirs[:] = [
                        d for d in dirs
                        if not d.startswith((".", "$")) and d not in ("node_modules", ".git", "venv", ".venv", "__pycache__", "build", "dist")
                    ]
                    for fname in files:
                        if clean_query in fname.lower() or (clean_query.startswith("*") and fname.lower().endswith(clean_query[1:])):
                            full_path = Path(root) / fname
                            try:
                                stat = full_path.stat()
                                matches.append({
                                    "name": fname,
                                    "path": str(full_path),
                                    "size_bytes": stat.st_size,
                                    "size_kb": round(stat.st_size / 1024, 1),
                                    "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)),
                                })
                            except Exception:
                                pass
                            if len(matches) >= max_results:
                                break
                    if len(matches) >= max_results:
                        break
            except Exception:
                continue

        return ToolResult(
            success=True,
            message=f"Found {len(matches)} files matching '{query}'.",
            data={"query": query, "count": len(matches), "files": matches},
        )


class FilesListTool(BaseTool):
    name = "files.list"
    description = "List files and subfolders within a given directory."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Path of directory to list (e.g. 'Downloads', 'Desktop', 'C:/Projects')."}
        },
        "required": ["directory"],
    }

    def execute(self, directory: str, **kwargs: Any) -> ToolResult:
        dir_path, err = FileHelper.resolve_safe_path(directory)
        if err:
            return ToolResult(success=False, error=err)
        if not dir_path or not dir_path.exists():
            return ToolResult(
                success=False,
                error=ToolError(code="DIRECTORY_NOT_FOUND", message=f"Directory '{directory}' does not exist."),
            )
        if not dir_path.is_dir():
            return ToolResult(
                success=False,
                error=ToolError(code="NOT_A_DIRECTORY", message=f"Path '{directory}' is a file, not a directory."),
            )

        items: list[dict[str, Any]] = []
        try:
            for item in sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if item.name.startswith((".", "$")):
                    continue
                try:
                    stat = item.stat()
                    items.append({
                        "name": item.name,
                        "is_dir": item.is_dir(),
                        "size_kb": round(stat.st_size / 1024, 1) if item.is_file() else 0,
                        "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)),
                    })
                except Exception:
                    pass
                if len(items) >= 50:
                    break
        except Exception as exc:
            return ToolResult(
                success=False,
                error=ToolError(code="IO_ERROR", message=f"Failed to list directory: {exc}"),
            )

        return ToolResult(
            success=True,
            message=f"Directory '{dir_path.name}' contains {len(items)} items.",
            data={"directory": str(dir_path), "count": len(items), "items": items},
        )


class FilesOpenTool(BaseTool):
    name = "files.open"
    description = "Open a file or folder with its default associated application or File Explorer."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to file or folder to open."}
        },
        "required": ["path"],
    }

    def execute(self, path: str, **kwargs: Any) -> ToolResult:
        target, err = FileHelper.resolve_safe_path(path)
        if err:
            return ToolResult(success=False, error=err)
        if not target or not target.exists():
            return ToolResult(
                success=False,
                error=ToolError(code="FILE_NOT_FOUND", message=f"Path '{path}' does not exist."),
            )

        try:
            os.startfile(str(target))
            return ToolResult(
                success=True,
                message=f"Opened {target.name}.",
                data={"path": str(target), "name": target.name},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=ToolError(code="OPEN_FAILED", message=f"Failed to open '{path}': {exc}"),
            )


class FilesReadTool(BaseTool):
    name = "files.read"
    description = "Read text content from a specified file (supports text, logs, markdown, json, python, etc.)."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to file to read."},
            "max_lines": {"type": "integer", "description": "Maximum lines to read.", "default": 200},
        },
        "required": ["path"],
    }

    def execute(self, path: str, max_lines: int = 200, **kwargs: Any) -> ToolResult:
        target, err = FileHelper.resolve_safe_path(path)
        if err:
            return ToolResult(success=False, error=err)
        if not target or not target.exists() or not target.is_file():
            return ToolResult(
                success=False,
                error=ToolError(code="FILE_NOT_FOUND", message=f"File '{path}' does not exist or is not a file."),
            )

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            read_slice = "\n".join(lines[:max_lines])
            return ToolResult(
                success=True,
                message=f"Read {len(lines[:max_lines])} lines from {target.name}.",
                data={"path": str(target), "total_lines": len(lines), "content": read_slice},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=ToolError(code="READ_ERROR", message=f"Failed to read file: {exc}"),
            )


class FilesCreateTool(BaseTool):
    name = "files.create"
    description = "Create a new text file or directory."
    risk_level = RiskLevel.CONFIRM
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path for the new file or directory."},
            "content": {"type": "string", "description": "Text content if creating a file.", "default": ""},
            "is_dir": {"type": "boolean", "description": "True to create a folder, False for file.", "default": False},
        },
        "required": ["path"],
    }

    def execute(self, path: str, content: str = "", is_dir: bool = False, **kwargs: Any) -> ToolResult:
        target, err = FileHelper.resolve_safe_path(path)
        if err:
            return ToolResult(success=False, error=err)
        if not target:
            return ToolResult(success=False, error=ToolError(code="INVALID_PATH", message="Invalid target path."))

        try:
            if is_dir:
                target.mkdir(parents=True, exist_ok=True)
                return ToolResult(success=True, message=f"Created directory {target.name}.", data={"path": str(target)})
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return ToolResult(
                    success=True,
                    message=f"Created file {target.name}.",
                    data={"path": str(target), "bytes": len(content.encode())},
                )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=ToolError(code="CREATE_FAILED", message=f"Failed to create: {exc}"),
            )


class FilesCopyTool(BaseTool):
    name = "files.copy"
    description = "Copy a file or directory to a destination path."
    risk_level = RiskLevel.CONFIRM
    parameters = {
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Source path."},
            "destination": {"type": "string", "description": "Destination path."},
        },
        "required": ["source", "destination"],
    }

    def execute(self, source: str, destination: str, **kwargs: Any) -> ToolResult:
        src, err_src = FileHelper.resolve_safe_path(source)
        if err_src:
            return ToolResult(success=False, error=err_src)
        dst, err_dst = FileHelper.resolve_safe_path(destination)
        if err_dst:
            return ToolResult(success=False, error=err_dst)

        if not src or not src.exists():
            return ToolResult(
                success=False,
                error=ToolError(code="FILE_NOT_FOUND", message=f"Source '{source}' does not exist."),
            )
        if not dst:
            return ToolResult(success=False, error=ToolError(code="INVALID_PATH", message="Invalid destination."))

        try:
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            return ToolResult(
                success=True,
                message=f"Copied '{src.name}' to '{dst}'.",
                data={"source": str(src), "destination": str(dst)},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=ToolError(code="COPY_FAILED", message=f"Failed to copy: {exc}"),
            )


class FilesMoveTool(BaseTool):
    name = "files.move"
    description = "Move a file or directory to a destination location."
    risk_level = RiskLevel.CONFIRM
    parameters = {
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Source path."},
            "destination": {"type": "string", "description": "Destination path."},
        },
        "required": ["source", "destination"],
    }

    def execute(self, source: str, destination: str, **kwargs: Any) -> ToolResult:
        src, err_src = FileHelper.resolve_safe_path(source)
        if err_src:
            return ToolResult(success=False, error=err_src)
        dst, err_dst = FileHelper.resolve_safe_path(destination)
        if err_dst:
            return ToolResult(success=False, error=err_dst)

        if not src or not src.exists():
            return ToolResult(
                success=False,
                error=ToolError(code="FILE_NOT_FOUND", message=f"Source '{source}' does not exist."),
            )
        if not dst:
            return ToolResult(success=False, error=ToolError(code="INVALID_PATH", message="Invalid destination."))

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return ToolResult(
                success=True,
                message=f"Moved '{src.name}' to '{dst}'.",
                data={"source": str(src), "destination": str(dst)},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=ToolError(code="MOVE_FAILED", message=f"Failed to move: {exc}"),
            )


class FilesRenameTool(BaseTool):
    name = "files.rename"
    description = "Rename a file or folder."
    risk_level = RiskLevel.CONFIRM
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Current file or folder path."},
            "new_name": {"type": "string", "description": "New filename or folder name."},
        },
        "required": ["path", "new_name"],
    }

    def execute(self, path: str, new_name: str, **kwargs: Any) -> ToolResult:
        src, err = FileHelper.resolve_safe_path(path)
        if err:
            return ToolResult(success=False, error=err)
        if not src or not src.exists():
            return ToolResult(
                success=False,
                error=ToolError(code="FILE_NOT_FOUND", message=f"Path '{path}' does not exist."),
            )

        target = src.parent / new_name
        try:
            src.rename(target)
            return ToolResult(
                success=True,
                message=f"Renamed '{src.name}' to '{new_name}'.",
                data={"old_path": str(src), "new_path": str(target), "new_name": new_name},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=ToolError(code="RENAME_FAILED", message=f"Failed to rename: {exc}"),
            )


class FilesDeleteTool(BaseTool):
    name = "files.delete"
    description = "Delete a file or folder (requires confirmation)."
    risk_level = RiskLevel.CONFIRM
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to file or folder to delete."}
        },
        "required": ["path"],
    }

    def execute(self, path: str, **kwargs: Any) -> ToolResult:
        target, err = FileHelper.resolve_safe_path(path)
        if err:
            return ToolResult(success=False, error=err)
        if not target or not target.exists():
            return ToolResult(
                success=False,
                error=ToolError(code="FILE_NOT_FOUND", message=f"Path '{path}' does not exist."),
            )

        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            return ToolResult(
                success=True,
                message=f"Deleted {target.name}.",
                data={"path": str(target)},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=ToolError(code="DELETE_FAILED", message=f"Failed to delete: {exc}"),
            )


class FilesExistsTool(BaseTool):
    name = "files.exists"
    description = "Check if a file or directory exists."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to check."}
        },
        "required": ["path"],
    }

    def execute(self, path: str, **kwargs: Any) -> ToolResult:
        target, err = FileHelper.resolve_safe_path(path)
        if err:
            return ToolResult(success=False, error=err)
        exists = target.exists() if target else False
        is_dir = target.is_dir() if exists and target else False
        return ToolResult(
            success=True,
            message=f"{'Found' if exists else 'Did not find'} '{target.name if target else path}'.",
            data={"exists": exists, "is_dir": is_dir, "path": str(target) if target else path},
        )
