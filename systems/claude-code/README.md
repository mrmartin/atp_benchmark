# claude-code system runner

- **Agent:** Claude Code (Opus 4.7), default scaffold.
- **Auth:** host subscription bind-mounted from `~/.claude/` + `~/.claude.json` (no API key).
- **Tools:** the harness's MCP Lean server (REPL + loogle/exact?/apply?/find/lean_check, ripgrep fallback).
- **Per-attempt budget:** 200 K tokens, 30 min wall clock, 40 tool calls (enforced by `harness/lib/runner.py`).
- **Sample independence:** k = 16 fresh processes per problem; no inter-attempt memory.

## Files
- `Dockerfile` — `FROM atp-harness:latest`; installs Node 20 + the Claude Code CLI.
- `prompt.txt` — frozen system prompt (loaded at attempt start; pre-registered alongside the harness).
- `skill.md` — mathlib conventions and tool-surface description.
- `run.sh` — single-attempt entrypoint.
- `runs/` — symlink to `/mnt/nvme2/atp_runs/claude-code/` (transcripts, scratch).

## Running

```
docker compose -f harness/docker-compose.yml run --rm claude-code \
    bash systems/claude-code/run.sh <problem_id> <sample_idx>
```
