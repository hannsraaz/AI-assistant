from __future__ import annotations

import json
import logging
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from core.tools.base import BaseTool, RiskLevel, ToolError, ToolResult

logger = logging.getLogger("memory")


@dataclass
class MemoryEntry:
    memory_id: str
    key: str
    value: str
    type: str = "fact"  # fact, project_alias, preference, workflow
    source: str = "user"
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MemoryManager:
    """Memory 2.0 persistent facts, project knowledge, preferences, and credential filtering."""

    # Sensitive patterns to reject from long-term memory
    SENSITIVE_PATTERNS = (
        r"\bpassword\s*[:=]\s*\S+",
        r"\bpasswd\s*[:=]\s*\S+",
        r"\bapi[_-]?key\s*[:=]\s*\S+",
        r"\bsecret[_-]?token\s*[:=]\s*\S+",
        r"\bghp_[0-9a-zA-Z]{30,}",
        r"\bBearer\s+[0-9a-zA-Z._-]+",
        r"\bprivate[_-]?key\b",
    )

    def __init__(self, memory_file: str | Path = "data/memory.json") -> None:
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, MemoryEntry] = self._load()

    def _load(self) -> dict[str, MemoryEntry]:
        if self.memory_file.exists():
            try:
                with self.memory_file.open("r", encoding="utf-8") as f:
                    raw = json.load(f)
                    entries = {}
                    # Handle V2 legacy structure or V3 MemoryEntry structure
                    for k, v in raw.items():
                        if isinstance(v, dict) and "memory_id" in v:
                            entries[k] = MemoryEntry(**v)
                        elif isinstance(v, dict):
                            # Legacy dict
                            for subk, subv in v.items():
                                entries[subk] = MemoryEntry(
                                    memory_id=f"mem_{uuid.uuid4().hex[:6]}",
                                    key=subk,
                                    value=str(subv),
                                    type=k,
                                )
                        else:
                            entries[k] = MemoryEntry(
                                memory_id=f"mem_{uuid.uuid4().hex[:6]}",
                                key=k,
                                value=str(v),
                            )
                    return entries
            except Exception as exc:
                logger.warning("Failed to load memory file: %s", exc)
        return {}

    def _save(self) -> None:
        try:
            with self.memory_file.open("w", encoding="utf-8") as f:
                json.dump({k: e.to_dict() for k, e in self._entries.items()}, f, indent=2)
        except Exception as exc:
            logger.error("Failed to save memory: %s", exc)

    def remember(
        self,
        key: str,
        value: str,
        category: str = "fact",
        confidence: float = 1.0,
        source: str = "user",
    ) -> tuple[bool, str]:
        # Reject sensitive credentials
        full_text = f"{key} {value}"
        for pat in self.SENSITIVE_PATTERNS:
            if re.search(pat, full_text, re.IGNORECASE):
                logger.warning("Rejected sensitive credential storage in memory: %s", key)
                return False, "Security block: Cannot store sensitive passwords, secrets, or API tokens in memory."

        clean_key = key.strip().lower()
        if clean_key in self._entries:
            entry = self._entries[clean_key]
            entry.value = value.strip()
            entry.type = category
            entry.confidence = confidence
            entry.updated_at = time.time()
        else:
            entry = MemoryEntry(
                memory_id=f"mem_{uuid.uuid4().hex[:6]}",
                key=clean_key,
                value=value.strip(),
                type=category,
                source=source,
                confidence=confidence,
            )
            self._entries[clean_key] = entry

        self._save()
        return True, f"Remembered {key} ({category})."

    def recall(self, query: str) -> list[dict[str, Any]]:
        clean_q = query.strip().lower()
        matches = []
        for entry in self._entries.values():
            if clean_q in entry.key or clean_q in entry.value.lower():
                matches.append(entry.to_dict())
        return matches

    def forget(self, key: str) -> bool:
        clean_key = key.strip().lower()
        if clean_key in self._entries:
            del self._entries[clean_key]
            self._save()
            return True
        return False

    def list_all(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._entries.values()]

    def list_memories(self, category: str = "all", limit: int = 100) -> list[dict[str, Any]]:
        entries = self.list_all()
        if category and category != "all":
            entries = [e for e in entries if e.get("type", "").lower() == category.lower() or e.get("category", "").lower() == category.lower()]
        return entries[:limit]

    def delete_memory(self, memory_id_or_key: str) -> bool:
        if self.forget(memory_id_or_key):
            return True
        for key, entry in list(self._entries.items()):
            if entry.memory_id == memory_id_or_key:
                del self._entries[key]
                self._save()
                return True
        return False


# --- Memory 2.0 Tools ---

class MemoryRememberTool(BaseTool):
    name = "memory.remember"
    description = "Store a personal fact, project alias, or user preference in persistent memory."
    risk_level = RiskLevel.SAFE
    capabilities = ["knowledge_storage", "memory"]
    parameters = {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Subject, topic, or alias (e.g. 'project_name', 'favorite_ide')."},
            "value": {"type": "string", "description": "Information or path to remember."},
            "category": {"type": "string", "enum": ["fact", "project_alias", "preference", "workflow"], "default": "fact"},
        },
        "required": ["key", "value"],
    }

    def __init__(self, memory_manager: MemoryManager) -> None:
        self.mm = memory_manager

    def execute(self, key: str, value: str, category: str = "fact", **kwargs: Any) -> ToolResult:
        success, msg = self.mm.remember(key, value, category=category)
        if success:
            return ToolResult(success=True, message=msg, data={"key": key, "value": value, "category": category})
        return ToolResult(success=False, error=ToolError(code="MEMORY_REJECTED", message=msg))


class MemoryRecallTool(BaseTool):
    name = "memory.recall"
    description = "Query long-term memory for relevant user facts, project aliases, and preferences."
    risk_level = RiskLevel.SAFE
    capabilities = ["knowledge_retrieval", "memory"]
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query or topic."}
        },
        "required": ["query"],
    }

    def __init__(self, memory_manager: MemoryManager) -> None:
        self.mm = memory_manager

    def execute(self, query: str, **kwargs: Any) -> ToolResult:
        results = self.mm.recall(query)
        if results:
            return ToolResult(
                success=True,
                message=f"Found {len(results)} memory entries for '{query}'.",
                data={"query": query, "results": results},
            )
        return ToolResult(
            success=True,
            message=f"No memories found matching '{query}'.",
            data={"query": query, "results": []},
        )


class MemoryForgetTool(BaseTool):
    name = "memory.forget"
    description = "Delete a specific memory entry."
    risk_level = RiskLevel.CONFIRM
    capabilities = ["knowledge_deletion", "memory"]
    has_side_effects = True
    parameters = {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Key or topic to forget."}
        },
        "required": ["key"],
    }

    def __init__(self, memory_manager: MemoryManager) -> None:
        self.mm = memory_manager

    def execute(self, key: str, **kwargs: Any) -> ToolResult:
        success = self.mm.forget(key)
        if success:
            return ToolResult(success=True, message=f"Forgot memory '{key}'.", data={"key": key})
        return ToolResult(success=False, error=ToolError(code="KEY_NOT_FOUND", message=f"Memory '{key}' not found."))


class MemoryListTool(BaseTool):
    name = "memory.list"
    description = "List all stored memory entries."
    risk_level = RiskLevel.SAFE
    capabilities = ["knowledge_listing", "memory"]
    parameters = {"type": "object", "properties": {}}

    def __init__(self, memory_manager: MemoryManager) -> None:
        self.mm = memory_manager

    def execute(self, **kwargs: Any) -> ToolResult:
        all_entries = self.mm.list_all()
        return ToolResult(
            success=True,
            message=f"Total {len(all_entries)} memory items stored.",
            data={"count": len(all_entries), "memories": all_entries},
        )
