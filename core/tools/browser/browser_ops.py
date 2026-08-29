from __future__ import annotations

import logging
import os
import re
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any

import requests

from core.tools.base import BaseTool, RiskLevel, ToolError, ToolResult

logger = logging.getLogger("browser")


class BrowserController:
    """Hybrid browser controller supporting fast requests and optional interactive Playwright."""

    _playwright = None
    _browser_instance = None
    _current_page = None

    @classmethod
    def get_playwright_page(cls) -> Any:
        if cls._current_page is not None:
            return cls._current_page
        try:
            from playwright.sync_api import sync_playwright
            cls._playwright = sync_playwright().start()
            cls._browser_instance = cls._playwright.chromium.launch(headless=False)
            cls._current_page = cls._browser_instance.new_page()
            return cls._current_page
        except Exception as exc:
            logger.info("Playwright not initialized (%s). Using standard browser fallback.", exc)
            return None


class BrowserOpenTool(BaseTool):
    name = "browser.open"
    description = "Open a URL or webpage in the web browser."
    risk_level = RiskLevel.SAFE
    capabilities = ["web_navigation", "browser"]
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Web address / URL to open (e.g. 'https://github.com', 'youtube.com')."}
        },
        "required": ["url"],
    }

    def execute(self, url: str, **kwargs: Any) -> ToolResult:
        clean_url = url.strip()
        if not clean_url.startswith(("http://", "https://")):
            clean_url = "https://" + clean_url

        try:
            webbrowser.open_new_tab(clean_url)
            return ToolResult(
                success=True,
                message=f"Opened {clean_url} in browser.",
                data={"url": clean_url},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=ToolError(code="BROWSER_OPEN_FAILED", message=f"Could not open browser: {exc}"),
            )


class BrowserSearchTool(BaseTool):
    name = "browser.search"
    description = "Perform a web search using Google, YouTube, or Bing."
    risk_level = RiskLevel.SAFE
    capabilities = ["web_search", "browser"]
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search term or topic."},
            "engine": {"type": "string", "enum": ["google", "youtube", "bing"], "default": "google"},
        },
        "required": ["query"],
    }

    def execute(self, query: str, engine: str = "google", **kwargs: Any) -> ToolResult:
        encoded = urllib.parse.quote_plus(query.strip())
        urls = {
            "google": f"https://www.google.com/search?q={encoded}",
            "youtube": f"https://www.youtube.com/results?search_query={encoded}",
            "bing": f"https://www.bing.com/search?q={encoded}",
        }
        target_url = urls.get(engine.lower(), urls["google"])
        try:
            webbrowser.open_new_tab(target_url)
            return ToolResult(
                success=True,
                message=f"Searching {engine.capitalize()} for '{query}'.",
                data={"query": query, "engine": engine, "url": target_url},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=ToolError(code="SEARCH_FAILED", message=f"Search failed: {exc}"),
            )


class BrowserReadTool(BaseTool):
    name = "browser.read"
    description = "Fetch, clean, and extract structured text, headings, and readable content from a web page."
    risk_level = RiskLevel.SAFE
    capabilities = ["web_scraping", "page_reading"]
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Web page URL to read."},
            "max_chars": {"type": "integer", "description": "Maximum characters to return.", "default": 2500},
        },
        "required": ["url"],
    }

    def execute(self, url: str, max_chars: int = 2500, **kwargs: Any) -> ToolResult:
        clean_url = url.strip()
        if not clean_url.startswith(("http://", "https://")):
            clean_url = "https://" + clean_url

        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(clean_url, headers=headers, timeout=10)
            resp.raise_for_status()

            raw_html = resp.text

            title_match = re.search(r"<title>(.*?)</title>", raw_html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else ""

            headings = [h.strip() for h in re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", raw_html, re.IGNORECASE | re.DOTALL)[:5]]

            text = re.sub(r"<script.*?</script>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

            snippet = text[:max_chars]
            return ToolResult(
                success=True,
                message=f"Read page: '{title or clean_url}' ({len(snippet)} chars).",
                data={
                    "url": clean_url,
                    "title": title,
                    "headings": headings,
                    "content": snippet,
                    "total_length": len(text),
                },
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=ToolError(code="FETCH_FAILED", message=f"Failed to fetch webpage: {exc}"),
            )


class BrowserClickTool(BaseTool):
    name = "browser.click"
    description = "Click a button, link, or element on the current web page using DOM selector."
    risk_level = RiskLevel.CONFIRM
    capabilities = ["dom_interaction", "browser_click"]
    has_side_effects = True
    parameters = {
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS selector or text (e.g. 'button.submit', 'text=Login')."}
        },
        "required": ["selector"],
    }

    def execute(self, selector: str, **kwargs: Any) -> ToolResult:
        page = BrowserController.get_playwright_page()
        if page:
            try:
                page.click(selector, timeout=5000)
                return ToolResult(success=True, message=f"Clicked element '{selector}'.")
            except Exception as exc:
                return ToolResult(success=False, error=ToolError(code="CLICK_FAILED", message=str(exc)))
        return ToolResult(success=False, error=ToolError(code="INTERACTIVE_BROWSER_UNAVAILABLE", message="Interactive browser driver unavailable."))


class BrowserTypeTool(BaseTool):
    name = "browser.type"
    description = "Type text into an input field on the web page."
    risk_level = RiskLevel.CONFIRM
    capabilities = ["dom_interaction", "browser_typing"]
    has_side_effects = True
    parameters = {
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS selector for input field."},
            "text": {"type": "string", "description": "Text to type."},
        },
        "required": ["selector", "text"],
    }

    def execute(self, selector: str, text: str, **kwargs: Any) -> ToolResult:
        page = BrowserController.get_playwright_page()
        if page:
            try:
                page.fill(selector, text, timeout=5000)
                return ToolResult(success=True, message=f"Typed text into '{selector}'.")
            except Exception as exc:
                return ToolResult(success=False, error=ToolError(code="TYPE_FAILED", message=str(exc)))
        return ToolResult(success=False, error=ToolError(code="INTERACTIVE_BROWSER_UNAVAILABLE", message="Interactive browser driver unavailable."))


class BrowserDownloadTool(BaseTool):
    name = "browser.download"
    description = "Download a file or document from a web URL to the user's Downloads folder."
    risk_level = RiskLevel.SAFE
    capabilities = ["file_download", "browser"]
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Direct download URL."},
            "filename": {"type": "string", "description": "Optional target filename.", "default": ""},
        },
        "required": ["url"],
    }

    def execute(self, url: str, filename: str = "", **kwargs: Any) -> ToolResult:
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)

        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, stream=True, timeout=15)
            resp.raise_for_status()

            if not filename:
                parsed = urllib.parse.urlparse(url)
                filename = Path(parsed.path).name or "downloaded_file.bin"

            out_path = downloads_dir / filename
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            size_kb = round(out_path.stat().st_size / 1024, 1)
            return ToolResult(
                success=True,
                message=f"Downloaded {filename} ({size_kb} KB) to Downloads folder.",
                data={"path": str(out_path), "filename": filename, "size_kb": size_kb},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=ToolError(code="DOWNLOAD_FAILED", message=f"Download failed: {exc}"),
            )
