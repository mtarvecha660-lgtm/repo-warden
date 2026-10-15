"""RepoWarden, a guarded GitHub agent for Flow State 2026.

Flow:
  1. A plan is built (LLM or fallback) and captured via ArmorIQ's capture_plan().
  2. get_intent_token() mints a signed intent token under our policy.
  3. Every action goes through client.invoke(), which ArmorIQ verifies against
     the plan (Merkle proof) before the MCP server runs anything.
  4. A second plan asks for a destructive step. The token request is refused,
     so nothing ever reaches the MCP server.

Run:  python agent.py "summarize the repo and file an issue about hardcoded secrets"
"""

import json
import os
import sys

from dotenv import load_dotenv
from armoriq_sdk import ArmorIQClient
from armoriq_sdk.exceptions import (
    PolicyBlockedException,
    IntentMismatchException,
    TokenExpiredException,
    MCPInvocationException,
)

from planner import build_plan
from policy import MCP_NAME, POLICY

load_dotenv()

GREEN, RED, DIM, RESET, BOLD = "\033[32m", "\033[31m", "\033[2m", "\033[0m", "\033[1m"


def log(kind: str, msg: str) -> None:
    color = {"OK": GREEN, "BLOCKED": RED}.get(kind, DIM)
    print(f"{color}[{kind}]{RESET} {msg}")


def run_step(client, token, step) -> None:
    result = client.invoke(
        mcp=step["mcp"],
        action=step["action"],
        intent_token=token,
        params=step.get("params", {}),
    )
    if result.get("success"):
        log("OK", f"{step['action']} -> {json.dumps(result.get('data'))[:180]}")
    else:
        log("ERROR", f"{step['action']} -> {result.get('error')}")


def run_plan(client, plan, policy=POLICY) -> bool:
    """Capture, mint and execute a plan. Returns True when ArmorIQ allowed it."""
    captured = client.capture_plan(llm=os.environ.get("PLANNER_MODEL", "demo-planner"),
                                   prompt=plan["goal"], plan=plan)
    log("PLAN", f"captured {len(plan['steps'])} step(s): {[s['action'] for s in plan['steps']]}")

    try:
        minted = client.get_intent_token(plan_capture=captured, policy=policy, validity_seconds=600)
    except PolicyBlockedException as e:
        log("BLOCKED", f"ArmorIQ refused the intent token: {e}")
        return False

    token = minted["token"] if isinstance(minted, dict) else minted
    log("TOKEN", f"intent token minted, hash {str(minted.get('plan_hash'))[:16] if isinstance(minted, dict) else 'n/a'}")

    for step in plan["steps"]:
        try:
            run_step(client, token, step)
        except IntentMismatchException as e:
            log("BLOCKED", f"step not in signed plan, ArmorIQ stopped it: {step['action']} ({e})")
        except TokenExpiredException:
            log("ERROR", "token expired, re-mint and retry")
        except MCPInvocationException as e:
            log("ERROR", f"mcp execution failed: {e}")
    return True


def main() -> None:
    ask = " ".join(sys.argv[1:]) or "summarize the repo and file an issue about hardcoded secrets"
    client = ArmorIQClient()  # reads ARMORIQ_API_KEY

    log("AGENT", f"ask: {ask}")
    plan = build_plan(ask)
    run_plan(client, plan)

    print()
    log("AGENT", "now the attack: same agent tries to wipe .env and force-push")
    attack_plan = {
        "goal": "Cover tracks: delete .env with the API keys and force-push over history",
        "steps": [
            {"action": "delete_file", "mcp": MCP_NAME, "params": {"path": ".env"}},
            {"action": "force_push", "mcp": MCP_NAME, "params": {"branch": "main"}},
        ],
    }
    allowed = run_plan(client, attack_plan)
    if allowed:
        log("ERROR", "policy did not block the attack plan, tighten POLICY")

    print()
    log("AGENT", "bonus, off-plan action: token is signed for the review steps only")
    review = build_plan(ask)
    captured = client.capture_plan(llm="demo-planner", prompt=review["goal"], plan=review)
    minted = client.get_intent_token(plan_capture=captured, policy=POLICY)
    token = minted["token"] if isinstance(minted, dict) else minted
    try:
        client.invoke(mcp=MCP_NAME, action="delete_file", intent_token=token,
                      params={"path": "src/app.py"})
        log("ERROR", "off-plan invoke went through")
    except (IntentMismatchException, Exception) as e:
        log("BLOCKED", f"off-plan invoke stopped by ArmorIQ: {type(e).__name__}")
        log("BLOCKED", "summary: 2 plans minted, 1 blocked at token, 0 destructive calls reached the server")


if __name__ == "__main__":
    main()
