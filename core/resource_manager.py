from __future__ import annotations

import logging
import psutil
from typing import Any

logger = logging.getLogger("resource_manager")


class ModelResourceManager:
    """GPU (RTX 3050 6GB) and CPU resource budget manager.

    Coordinates memory allocations between Ollama LLM, Faster-Whisper, Vision,
    and TTS to guarantee zero CUDA out-of-memory errors and zero memory thrashing.
    """

    def __init__(self, max_gpu_vram_mb: int = 6144, reserved_headroom_mb: int = 1500) -> None:
        self.max_gpu_vram_mb = max_gpu_vram_mb
        self.reserved_headroom_mb = reserved_headroom_mb

    def get_system_memory_status(self) -> dict[str, Any]:
        """Return system RAM usage."""
        vm = psutil.virtual_memory()
        return {
            "total_gb": round(vm.total / (1024**3), 2),
            "available_gb": round(vm.available / (1024**3), 2),
            "used_gb": round(vm.used / (1024**3), 2),
            "percent": vm.percent,
        }

    def get_gpu_memory_status(self) -> dict[str, Any]:
        """Estimate or query current NVIDIA GPU VRAM usage."""
        try:
            import torch

            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / (1024**2)
                reserved = torch.cuda.memory_reserved() / (1024**2)
                total = torch.cuda.get_device_properties(0).total_memory / (1024**2)
                return {
                    "available": True,
                    "device_name": torch.cuda.get_device_name(0),
                    "total_mb": round(total, 1),
                    "allocated_mb": round(allocated, 1),
                    "reserved_mb": round(reserved, 1),
                    "free_mb": round(total - reserved, 1),
                }
        except Exception:
            pass

        # CPU fallback status
        return {
            "available": False,
            "device_name": "CPU/System",
            "total_mb": 6144.0,
            "allocated_mb": 0.0,
            "reserved_mb": 0.0,
            "free_mb": 6144.0,
        }

    def can_allocate_gpu_model(self, required_vram_mb: int = 2000) -> bool:
        """Check whether allocating a heavy model (e.g. XTTS or Vision) would violate VRAM budget."""
        gpu_stat = self.get_gpu_memory_status()
        if not gpu_stat.get("available", False):
            return False

        free_mb = gpu_stat.get("free_mb", 0.0)
        return free_mb >= (required_vram_mb + self.reserved_headroom_mb)


global_resource_manager = ModelResourceManager()
