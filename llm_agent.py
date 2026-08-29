from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import time
from typing import Any, Iterable, Iterator

import requests

from config import LLMConfig

logger = logging.getLogger("llm_agent")


class OllamaClient:
    """Hybrid LLM client supporting local Ollama with automatic background daemon launcher."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.groq_api_key = os.environ.get("GROQ_API_KEY", "").strip()
        self.openai_api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self._ensure_daemon_checked = False

    def find_ollama_executable(self) -> str | None:
        """Find the local Ollama binary on Windows."""
        in_path = shutil.which("ollama")
        if in_path:
            return in_path

        local_app = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
        if os.path.exists(local_app):
            return local_app

        prog_files = os.path.expandvars(r"%ProgramFiles%\Ollama\ollama.exe")
        if os.path.exists(prog_files):
            return prog_files

        app_data_direct = os.path.expanduser(r"~\AppData\Local\Programs\Ollama\ollama.exe")
        if os.path.exists(app_data_direct):
            return app_data_direct

        return None

    def ensure_ollama_running(self) -> bool:
        """Automatically start the background Ollama daemon if not already active."""
        if self.check_connection():
            return True

        exe = self.find_ollama_executable()
        if not exe:
            return False

        try:
            # Launch 'ollama serve' as a silent background daemon
            creation_flags = 0
            if os.name == "nt":
                creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

            subprocess.Popen(
                [exe, "serve"],
                creationflags=creation_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Wait up to 3.5 seconds for Ollama to become ready
            for _ in range(7):
                time.sleep(0.5)
                if self.check_connection():
                    logger.info("Ollama background service automatically started.")
                    return True
        except Exception as exc:
            logger.warning("Failed to auto-start Ollama: %s", exc)

        return False

    def check_connection(self) -> bool:
        if self.groq_api_key or self.openai_api_key:
            return True
        try:
            response = self.session.get(f"{self.config.base_url}/api/tags", timeout=1.5)
            return response.status_code == 200
        except Exception:
            return False

    def stream_chat(self, prompt: str, history: Iterable[dict[str, str]] | None = None) -> Iterator[str]:
        # If not connected yet, try auto-starting Ollama on first query
        if not self._ensure_daemon_checked:
            self._ensure_daemon_checked = True
            if not self.check_connection():
                self.ensure_ollama_running()

        messages: list[dict[str, str]] = [{"role": "system", "content": self.config.system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        # 1. Try Groq API if key is present (Ultra-fast 500 tokens/s)
        if self.groq_api_key:
            try:
                headers = {"Authorization": f"Bearer {self.groq_api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "stream": True,
                    "temperature": self.config.temperature,
                    "max_tokens": 150,
                }
                with self.session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=5,
                ) as resp:
                    resp.raise_for_status()
                    for raw_line in resp.iter_lines():
                        if not raw_line:
                            continue
                        line = raw_line.decode("utf-8")
                        if line.startswith("data: ") and line != "data: [DONE]":
                            data = json.loads(line[6:])
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    return
            except Exception:
                pass

        # 2. Try Local Ollama
        payload_ollama: dict[str, Any] = {
            "model": self.config.model,
            "stream": True,
            "keep_alive": self.config.keep_alive,
            "messages": messages,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": 150,
            },
        }

        try:
            with self.session.post(
                f"{self.config.base_url}/api/chat",
                json=payload_ollama,
                stream=True,
                timeout=(3.0, float(self.config.request_timeout)),
            ) as response:
                response.raise_for_status()
                for raw_line in response.iter_lines():
                    if not raw_line:
                        continue
                    data_ollama = json.loads(raw_line.decode("utf-8"))
                    message = data_ollama.get("message", {})
                    chunk = message.get("content", "")
                    if chunk:
                        yield chunk
                return
        except Exception:
            pass

        # 3. Friendly offline fallback
        yield (
            "Local AI is currently offline. You can run all desktop voice commands, "
            "or start Ollama with 'ollama run llama3.2:3b' to chat freely."
        )

    def stream_sentences(self, prompt: str, history: Iterable[dict[str, str]] | None = None) -> Iterator[tuple[str, str]]:
        buffer = ""
        full_text = ""
        sentence_end = re.compile(r"([.?!;:\n]+)")

        for token in self.stream_chat(prompt, history=history):
            buffer += token
            full_text += token

            parts = sentence_end.split(buffer)
            while len(parts) > 2:
                sentence = parts[0] + parts[1]
                buffer = "".join(parts[2:])
                parts = sentence_end.split(buffer)
                cleaned = sentence.strip()
                if cleaned:
                    yield cleaned, full_text

        if buffer.strip():
            yield buffer.strip(), full_text
