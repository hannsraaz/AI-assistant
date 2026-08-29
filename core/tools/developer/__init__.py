"""Developer & Android tools for Friday."""
from core.tools.developer.android_ops import (
    AndroidBuildTool,
    AndroidDevicesTool,
    AndroidLogcatTool,
    AndroidTestTool,
)
from core.tools.developer.git_ops import (
    GitAddTool,
    GitBranchTool,
    GitCheckoutTool,
    GitCommitTool,
    GitCreateBranchTool,
    GitDiffTool,
    GitLogTool,
    GitPullTool,
    GitPushTool,
    GitStatusTool,
)
from core.tools.developer.github_ops import (
    GitHubCreateIssueTool,
    GitHubIssuesTool,
    GitHubPullRequestsTool,
    GitHubRepositoriesTool,
)
from core.tools.developer.terminal_ops import TerminalExecuteTool
from core.tools.registry import ToolRegistry


def register_developer_tools(registry: ToolRegistry) -> None:
    """Register all developer, Git, GitHub, and Android tools."""
    tools = [
        TerminalExecuteTool(),
        # Git
        GitStatusTool(),
        GitDiffTool(),
        GitLogTool(),
        GitBranchTool(),
        GitAddTool(),
        GitCommitTool(),
        GitPushTool(),
        GitPullTool(),
        GitCreateBranchTool(),
        GitCheckoutTool(),
        # GitHub
        GitHubRepositoriesTool(),
        GitHubIssuesTool(),
        GitHubPullRequestsTool(),
        GitHubCreateIssueTool(),
        # Android
        AndroidDevicesTool(),
        AndroidBuildTool(),
        AndroidTestTool(),
        AndroidLogcatTool(),
    ]
    registry.register_many(tools)


__all__ = [
    "register_developer_tools",
    "TerminalExecuteTool",
    "GitStatusTool",
    "GitDiffTool",
    "GitLogTool",
    "GitBranchTool",
    "GitAddTool",
    "GitCommitTool",
    "GitPushTool",
    "GitPullTool",
    "GitCreateBranchTool",
    "GitCheckoutTool",
    "GitHubRepositoriesTool",
    "GitHubIssuesTool",
    "GitHubPullRequestsTool",
    "GitHubCreateIssueTool",
    "AndroidDevicesTool",
    "AndroidBuildTool",
    "AndroidTestTool",
    "AndroidLogcatTool",
]
