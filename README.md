# RepoWarden

A guarded GitHub agent for **Flow State 2026** (ArmorIQ). The agent reviews a
sandbox repo and files issues through its MCP server, but every tool call is
cryptographically gated by ArmorIQ intent enforcement: a signed intent token,
per-step Merkle proofs, and a policy that hard-blocks destructive actions.

## What it shows

- **Allowed**: `list_files`, `read_file`, `create_issue` run end-to-end through
  ArmorIQ's proxy with real token verification.
- **Blocked**: a plan to `delete_file` (.env), `write_secret` or `force_push`
  is refused at token issuance (`PolicyBlockedException`), and an off-plan
  `invoke` fails step verification (`IntentMismatchException`). Nothing
  destructive ever reaches the MCP server.

## Architecture

```
user ask -> planner (OpenRouter LLM, fallback deterministic)
        -> capture_plan()      plan hashed by CSRG-IAP
        -> get_intent_token()  Ed25519-signed token + Merkle proofs
        -> invoke() per step   X-CSRG-Proof verified by ArmorIQ proxy
                              -> repo-warden-mcp (sandboxed GitHub stand-in)
```

## Setup

1. `pip install -r requirements.txt`
2. `cp .env.example .env` and set `ARMORIQ_API_KEY` (from
   [platform.armoriq.ai](https://platform.armoriq.ai) -> API Keys). Keep the
   key out of git and out of chat; `.env` is gitignored.
3. Run the MCP server: `python mcp_server/server.py` (listens on :8000).
4. Expose it publicly, e.g. `ngrok http 8000`, and register the URL on the
   ArmorIQ dashboard: **MCP Servers -> Add Server** (name `repo-warden-mcp`,
   environment Development, capabilities: Tools). Onboard the agent the same
   way under **Agents**.
5. `python agent.py`

Optional: set `OPENROUTER_API_KEY` in `.env` so the LLM writes the plan
instead of the built-in fallback planner.

## Files

| Path | What it is |
| --- | --- |
| `agent.py` | The guarded agent: capture, mint, invoke, block demo |
| `planner.py` | LLM plan builder (OpenRouter) with deterministic fallback |
| `policy.py` | Inline ArmorIQ policy: allows and deny globs |
| `mcp_server/server.py` | FastMCP server with sandboxed repo tools |
| `sandbox_repo/` | The repo the agent works on; nothing here is production |
| `demo/90s_script.md` | Shot list for the 90-second demo video |

## Rules compliance

- Sandbox only: the "repo" is a local directory; no real GitHub API, no
  production systems, no customer data.
- ArmorIQ enforcement is real (platform-issued tokens, real proxy
  verification), never simulated or hardcoded.
