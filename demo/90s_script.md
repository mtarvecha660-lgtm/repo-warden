# 90s demo shot list (Flow State 2026)

0-8s   Hook: "AI agents can act. Who stops them when they go rogue?"
8-20s  Problem: agent gets an ask, plans tool calls. Plan structure shown.
20-40s Allowed run: plan captured -> intent token minted -> list/read/create_issue
       all pass through ArmorIQ, MCP executes. Show the platform audit trace.
40-65s The attack: same agent tries "delete .env, force-push history".
       ArmorIQ refuses the intent token. Red BLOCKED line. MCP never called.
65-80s Off-plan invoke also rejected (Merkle proof mismatch). Screenshot of the
       platform dashboard trace showing one allowed action + one blocked action.
80-90s Close: RepoWarden, intent-level enforcement for every tool call.
       github.com/<you>/repo-warden
