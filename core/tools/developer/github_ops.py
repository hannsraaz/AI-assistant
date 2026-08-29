from __future__ import annotations

import os
from typing import Any

import requests

from core.tools.base import BaseTool, RiskLevel, ToolResult


class GitHubHelper:
    @staticmethod
    def get_token() -> str:
        return os.environ.get("GITHUB_TOKEN", os.environ.get("GH_TOKEN", "")).strip()

    @staticmethod
    def get_headers() -> dict[str, str]:
        token = GitHubHelper.get_token()
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "Friday-Assistant"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers


class GitHubRepositoriesTool(BaseTool):
    name = "github.repositories"
    description = "List repositories for the authenticated user or an organization."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "username": {"type": "string", "description": "Optional user/org handle. If empty, lists authenticated user repos.", "default": ""}
        },
    }

    def execute(self, username: str = "", **kwargs: Any) -> ToolResult:
        token = GitHubHelper.get_token()
        url = f"https://api.github.com/users/{username}/repos" if username else "https://api.github.com/user/repos"
        if not username and not token:
            return ToolResult(
                success=False,
                error="No GITHUB_TOKEN configured. Set GITHUB_TOKEN in .env or pass a public username.",
            )

        try:
            res = requests.get(url, headers=GitHubHelper.get_headers(), timeout=10)
            if res.status_code == 200:
                repos = res.json()
                summary = [{"name": r["name"], "full_name": r["full_name"], "url": r["html_url"], "stars": r["stargazers_count"]} for r in repos[:10]]
                return ToolResult(
                    success=True,
                    message=f"Found {len(repos)} repositories.",
                    data={"count": len(repos), "repositories": summary},
                )
            return ToolResult(success=False, error=f"GitHub API Error: {res.status_code} - {res.text}")
        except Exception as exc:
            return ToolResult(success=False, error=f"GitHub request failed: {exc}")


class GitHubIssuesTool(BaseTool):
    name = "github.issues"
    description = "List open issues for a GitHub repository (e.g. 'owner/repo')."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Repository in 'owner/repo' format (e.g. 'octocat/Hello-World')."}
        },
        "required": ["repo"],
    }

    def execute(self, repo: str, **kwargs: Any) -> ToolResult:
        url = f"https://api.github.com/repos/{repo}/issues?state=open"
        try:
            res = requests.get(url, headers=GitHubHelper.get_headers(), timeout=10)
            if res.status_code == 200:
                issues = res.json()
                summary = [{"number": i["number"], "title": i["title"], "user": i["user"]["login"], "url": i["html_url"]} for i in issues[:10]]
                return ToolResult(
                    success=True,
                    message=f"Found {len(issues)} open issue(s) for {repo}.",
                    data={"repo": repo, "count": len(issues), "issues": summary},
                )
            return ToolResult(success=False, error=f"GitHub API Error ({res.status_code}): {res.text}")
        except Exception as exc:
            return ToolResult(success=False, error=f"GitHub request error: {exc}")


class GitHubPullRequestsTool(BaseTool):
    name = "github.pull_requests"
    description = "List open pull requests for a repository."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Repository in 'owner/repo' format."}
        },
        "required": ["repo"],
    }

    def execute(self, repo: str, **kwargs: Any) -> ToolResult:
        url = f"https://api.github.com/repos/{repo}/pulls?state=open"
        try:
            res = requests.get(url, headers=GitHubHelper.get_headers(), timeout=10)
            if res.status_code == 200:
                prs = res.json()
                summary = [{"number": p["number"], "title": p["title"], "user": p["user"]["login"], "branch": p["head"]["ref"]} for p in prs[:10]]
                return ToolResult(
                    success=True,
                    message=f"Found {len(prs)} open pull request(s) for {repo}.",
                    data={"repo": repo, "count": len(prs), "pull_requests": summary},
                )
            return ToolResult(success=False, error=f"GitHub API Error ({res.status_code})")
        except Exception as exc:
            return ToolResult(success=False, error=f"GitHub request failed: {exc}")


class GitHubCreateIssueTool(BaseTool):
    name = "github.create_issue"
    description = "Create a new issue on a GitHub repository."
    risk_level = RiskLevel.CONFIRM
    parameters = {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Repository in 'owner/repo' format."},
            "title": {"type": "string", "description": "Issue title."},
            "body": {"type": "string", "description": "Issue description.", "default": ""},
        },
        "required": ["repo", "title"],
    }

    def execute(self, repo: str, title: str, body: str = "", **kwargs: Any) -> ToolResult:
        token = GitHubHelper.get_token()
        if not token:
            return ToolResult(success=False, error="GITHUB_TOKEN is required to create issues.")

        url = f"https://api.github.com/repos/{repo}/issues"
        payload = {"title": title, "body": body}
        try:
            res = requests.post(url, headers=GitHubHelper.get_headers(), json=payload, timeout=10)
            if res.status_code in (201, 200):
                data = res.json()
                return ToolResult(
                    success=True,
                    message=f"Created issue #{data['number']}: '{title}' on {repo}.",
                    data={"number": data["number"], "url": data["html_url"], "title": title},
                )
            return ToolResult(success=False, error=f"Failed to create issue: {res.status_code} {res.text}")
        except Exception as exc:
            return ToolResult(success=False, error=f"GitHub request failed: {exc}")
