# deepseek-v4pro system runner

- **Agent:** DeepSeek V4 Pro (`reasoning: xhigh`) inside OpenCode v1.14.24.
- **Provider:** OpenRouter; auth via `OPENROUTER_API_KEY` from `.env` (compose `env_file`).
- **Tools:** the harness's MCP Lean server (same as Claude Code).
- **Config:** `opencode.config.json` sets `reasoning: xhigh`, `autoCompact: false`, MCP Lean wired.
- **Per-attempt budget:** 200 K tokens, 30 min wall clock, 40 tool calls.
- **Sample independence:** k = 16 fresh processes per problem.

## Files
- `Dockerfile` — `FROM atp-harness:latest`; installs Node 20 + `opencode-ai@1.14.24`.
- `opencode.config.json` — frozen OpenCode config (pre-registered with the harness).
- `prompt.txt` — frozen system prompt.
- `run.sh` — single-attempt entrypoint.
- `runs/` — symlink to `/mnt/nvme2/atp_runs/deepseek-v4pro/`.

## Running

```
docker compose -f harness/docker-compose.yml run --rm deepseek-v4pro \
    bash systems/deepseek-v4pro/run.sh <problem_id> <sample_idx>
```
