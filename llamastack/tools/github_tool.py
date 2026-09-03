"""Re-export. Canonical implementation: mcp-servers/src/granite_mcp/github_tool.py"""

from granite_mcp.github_tool import (
    github_commit_files,
    github_create_branch,
    github_create_pr,
    github_get_file,
)

__all__ = [
    "github_commit_files",
    "github_create_branch",
    "github_create_pr",
    "github_get_file",
]
