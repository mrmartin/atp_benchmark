"""DeepSeek V4 Pro (via OpenCode + OpenRouter) runner adapter.

Invokes `opencode` with the frozen `systems/deepseek-v4pro/opencode.config.json`
which wires the MCP Lean server and sets reasoning: xhigh / autoCompact: false.
Like the Claude adapter, instructs the agent to write the final proof to
`paths["proof"]` and then re-grades it independently.

Token accounting: best-effort from OpenCode's stdout JSON; OpenCode's exact
stream-event schema is in flux, so we capture everything and parse what we can.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

from ..budget import GeneralistBudget
from ._common import render_prompt, write_jsonl


def _build_prompt(problem: dict, proof_path: Path) -> str:
    base = render_prompt("deepseek-v4pro", problem)
    return base + textwrap.dedent(f"""

        FINALIZE: when your proof is complete and `lean_check` returns
        `success: true`, write JUST the proof text (the term or `by ...`
        block that should replace `sorry`) to:

          {proof_path}

        Then end the conversation. Lean's verdict from the runner's grader
        (independent re-check) is the only score.
        """)


def run_attempt(*, problem: dict, sample_idx: int, seed: int, paths: dict[str, Path]) -> dict:
    if not shutil.which("opencode"):
        raise RuntimeError("opencode CLI not on PATH; run inside the atp-deepseek-v4pro container.")
    repo = Path("/workspace")
    prompt = _build_prompt(problem, paths["proof"])
    budget = GeneralistBudget()

    env = os.environ.copy()
    if not env.get("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY not set; container env_file is required.")

    config = repo / "systems" / "deepseek-v4pro" / "opencode.config.json"
    cmd = [
        "opencode", "run",
        "--config", str(config),
        "--cwd", str(repo),
        "--no-tty",
        prompt,
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=str(repo),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    events: list[dict] = []
    tokens_in = tokens_out = tool_calls = 0
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            try:
                evt = json.loads(line)
                events.append(evt)
                etype = evt.get("type") or evt.get("event")
                if etype in {"tool_use", "tool", "tool_call"}:
                    tool_calls += 1
                if "usage" in evt:
                    u = evt["usage"]
                    tokens_in += int(u.get("input_tokens", 0))
                    tokens_out += int(u.get("output_tokens", 0))
            except json.JSONDecodeError:
                events.append({"raw": line})
        proc.wait(timeout=max(60, int(budget.remaining_seconds()) + 60))
    finally:
        if proc.poll() is None:
            proc.kill()

    write_jsonl(paths["transcript"], events)
    proof_text = paths["proof"].read_text() if paths["proof"].exists() else ""

    return {
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tool_calls": tool_calls,
        "proof_text": proof_text,
        "transcript_path": str(paths["transcript"]),
        "exit_code": proc.returncode,
    }
