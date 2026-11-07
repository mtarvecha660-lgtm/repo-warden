<div align="center">

# RepoWarden

**A guarded GitHub agent: every repo action it takes must match an intent plan that ArmorIQ verifies before anything runs, and destructive actions are denied by policy.**

![Python](https://img.shields.io/badge/python-3.x-3776AB?logo=python&logoColor=white)
![MCP](https://img.shields.io/badge/tools-MCP-6E56CF)
![Guardrail](https://img.shields.io/badge/guardrail-ArmorIQ%20intent%20enforcement-critical)
![Status](https://img.shields.io/badge/status-hackathon%20demo-orange)

</div>

RepoWarden is a demo of intent-level control for AI agents that touch code. The agent first writes a plan, the plan is captured and signed, and each tool call is checked against that plan. Anything off-plan, or anything on the deny list, is refused before the MCP server runs it. Built for Flow State 2026.

## How it works

1. **Plan.** `planner.py` turns the ask into a JSON plan of steps. It uses an LLM through OpenRouter when a key is set, and a deterministic fallback plan otherwise.
2. **Capture and token.** `agent.py` captures the plan with ArmorIQ and mints an intent token for it.
3. **Verified calls.** Every step goes through `client.invoke()`. ArmorIQ checks the step against the plan (Merkle proof) before the MCP server executes it.
4. **Refusals.** A second, destructive plan is refused at token request, so nothing reaches the MCP server.

## Policy

| Tool | Decision |
|---|---|
| `list_files` | allowed |
| `read_file` | allowed |
| `create_issue` | allowed |
| `delete_file` | denied |
| `write_secret` | denied |
| `force_push` | denied |
| `delete_repo` | denied |

Deny rules are checked before allow rules, so a dangerous operation is blocked whatever the planner writes. The policy lives in [`policy.py`](policy.py).

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env          # add your ArmorIQ API key (and optionally an OpenRouter key)
python agent.py "summarize the repo and file an issue about hardcoded secrets"
```

The MCP server (`mcp_server/server.py`) works on a sandbox copy of a repo in `sandbox_repo/`. If ArmorIQ must reach it over the internet, expose it with a tunnel and set `MCP_PUBLIC_URL` in `.env`.

## Project structure

```
agent.py              the guarded agent: plan, token, verified calls, refusals
planner.py            turns an ask into a plan (LLM or fallback)
policy.py             allow and deny rules for the MCP tools
mcp_server/server.py  MCP server with the repo tools (sandboxed paths only)
sandbox_repo/         a small sample repo the demo works on
demo/90s_script.md    shot list for the 90-second demo
```

## Honest notes

- This is a demo built for a hackathon. The sandboxed MCP server only touches `sandbox_repo/`, but it is not hardened for production use.
- ArmorIQ is an external service and needs its own API key. Without it the agent cannot mint tokens or run verified calls.
- The `.env` file holds keys and is never committed; only `.env.example` (placeholders) is in the repo.
