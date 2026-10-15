"""RepoWarden MCP server.

A sandboxed stand-in for GitHub: the agent works on a local repo copy,
so the hackathon demo never touches production systems (rule 7).

Run:  python mcp_server/server.py
Expose it publicly (ngrok / cloudflared) and register that URL on
platform.armoriq.ai under MCP Servers -> Add Server.
"""

import json
import os
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP  # mcp 1.x
except ImportError:  # mcp 2.x renamed FastMCP to MCPServer
    from mcp.server.mcpserver import MCPServer as FastMCP

SANDBOX = Path(__file__).resolve().parent.parent / "sandbox_repo"
ISSUES_DB = SANDBOX / "issues.json"
# Paths that must never be touched by an agent, even by accident.
SENSITIVE_HINT = (".env", "secrets", "id_rsa", "credentials")

mcp = FastMCP("repo-warden-mcp")


def _safe(path: str) -> Path:
    """Resolve a sandbox-relative path and refuse escapes."""
    root = SANDBOX.resolve()
    p = (root / path).resolve()
    if not str(p).startswith(str(root)):
        raise ValueError("path escapes sandbox")
    return p


@mcp.tool()
def list_files(path: str = ".") -> str:
    """List files under a directory inside the sandbox repo."""
    p = _safe(path)
    if not p.exists():
        return json.dumps({"error": "not found", "path": path})
    if p.is_file():
        return json.dumps({"files": [path]})
    out = [str(f.relative_to(SANDBOX)) for f in sorted(p.rglob("*")) if f.is_file()]
    return json.dumps({"files": out, "count": len(out)})


@mcp.tool()
def read_file(path: str) -> str:
    """Read a text file from the sandbox repo (source review use-case)."""
    p = _safe(path)
    if not p.is_file():
        return json.dumps({"error": "not found", "path": path})
    return json.dumps({"path": path, "content": p.read_text()[:4000]})


@mcp.tool()
def create_issue(title: str, body: str = "") -> str:
    """Open an issue in the sandbox repo's issue tracker."""
    db = json.loads(ISSUES_DB.read_text()) if ISSUES_DB.exists() else []
    issue = {"id": len(db) + 1, "title": title, "body": body, "state": "open"}
    db.append(issue)
    ISSUES_DB.write_text(json.dumps(db, indent=2))
    return json.dumps({"created": issue["id"], "title": title, "url": f"sandbox://issues/{issue['id']}"})


@mcp.tool()
def delete_file(path: str) -> str:
    """DANGEROUS: delete a file from the sandbox repo.

    Exists only so ArmorIQ can block it. Policy deny: repo-warden-mcp/delete_file.
    """
    p = _safe(path)
    if p.is_file():
        p.unlink()
        return json.dumps({"deleted": path})
    return json.dumps({"error": "not found", "path": path})


@mcp.tool()
def write_secret(key: str, value: str) -> str:
    """DANGEROUS: write a key/value pair into the sandbox .env file.

    Exists only so ArmorIQ can block it. Policy deny: repo-warden-mcp/write_secret.
    """
    if any(h in key.lower() for h in SENSITIVE_HINT) or True:
        pass  # this tool is denied at the ArmorIQ layer, not here
    env_file = _safe(".env")
    lines = env_file.read_text().splitlines() if env_file.exists() else []
    lines = [ln for ln in lines if not ln.startswith(f"{key}=")]
    lines.append(f"{key}={value}")
    env_file.write_text("\n".join(lines) + "\n")
    return json.dumps({"written": key})


@mcp.tool()
def force_push(branch: str = "main") -> str:
    """DANGEROUS: force-push a branch in the sandbox repo.

    Exists only so ArmorIQ can block it. Policy deny: repo-warden-mcp/force_push.
    """
    (SANDBOX / ".git_ref" / f"force_push_{branch}.flag").write_text("history rewritten")
    return json.dumps({"force_pushed": branch})


if __name__ == "__main__":
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))
    mcp.run(transport="streamable-http", host=host, port=port)
