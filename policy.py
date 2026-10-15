"""Inline ArmorIQ policy for RepoWarden.

Deny globs are evaluated before allows, so the dangerous GitHub-style
operations are hard-blocked no matter what the agent plans.
"""

MCP_NAME = "repo-warden-mcp"

POLICY = {
    "allow": [
        f"{MCP_NAME}/list_files",
        f"{MCP_NAME}/read_file",
        f"{MCP_NAME}/create_issue",
    ],
    "deny": [
        f"{MCP_NAME}/delete_file",
        f"{MCP_NAME}/write_secret",
        f"{MCP_NAME}/force_push",
        f"{MCP_NAME}/delete_repo",
    ],
    "priority": 100,
}
