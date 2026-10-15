"""Plan generation for RepoWarden.

ArmorIQ's SDK does not call an LLM: the agent must hand it an explicit
plan. This module turns a natural-language ask into that plan, using
OpenRouter when a key is present and a deterministic fallback otherwise.
"""

import json
import os

from dotenv import load_dotenv

load_dotenv()

MCP_NAME = "repo-warden-mcp"
SAFE_TOOLS = ["list_files", "read_file", "create_issue"]

PLANNER_MODEL = os.environ.get("PLANNER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

SYSTEM = f"""You are the planner of a guarded GitHub agent. Convert the user's ask
into a JSON execution plan for the MCP server "{MCP_NAME}".

Available tools and params:
- list_files: {{"path": "<dir>"}}
- read_file: {{"path": "<file>"}}
- create_issue: {{"title": "<title>", "body": "<body>"}}

Never plan destructive actions (delete_file, write_secret, force_push).
Reply with JSON only: {{"goal": "...", "steps": [{{"action": "...", "mcp": "{MCP_NAME}", "params": {{...}}}}]}}"""


def build_plan(ask: str) -> dict:
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        plan = _llm_plan(ask, key)
        if plan:
            return plan
    return _fallback_plan(ask)


def _llm_plan(ask: str, key: str):
    try:
        from openai import OpenAI

        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
        resp = client.chat.completions.create(
            model=PLANNER_MODEL,
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": ask}],
            temperature=0,
            max_tokens=500,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        plan = json.loads(raw)
        plan["steps"] = [s for s in plan.get("steps", []) if s.get("action") in SAFE_TOOLS]
        if plan["steps"]:
            return plan
    except Exception:
        pass
    return None


def _fallback_plan(ask: str) -> dict:
    return {
        "goal": ask,
        "steps": [
            {"action": "list_files", "mcp": MCP_NAME, "params": {"path": "src"}},
            {"action": "read_file", "mcp": MCP_NAME, "params": {"path": "src/app.py"}},
            {
                "action": "create_issue",
                "mcp": MCP_NAME,
                "params": {
                    "title": "Agent review: API key loaded at import time",
                    "body": "src/app.py reads the key at import. Move to lazy lookup and keep secrets out of source. Reported by RepoWarden.",
                },
            },
        ],
    }
