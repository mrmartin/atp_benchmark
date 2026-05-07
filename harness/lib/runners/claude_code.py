"""Claude Code runner adapter.

Launches `claude -p` non-interactively with the harness's MCP server pre-wired
via `.mcp.json` at the repo root. The agent is instructed to write the final
proof text to `paths["proof"]`. The runner then grades that proof.

Token accounting: parses Claude Code's stream-json output for usage messages.
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


def _build_user_prompt(problem: dict, proof_path: Path) -> str:
    base = render_prompt("claude-code", problem)
    return base + textwrap.dedent(f"""

        FINALIZE: when your proof is complete and `lean_check` returns
        `success: true`, write JUST the proof text (the term or `by ...`
        block that should replace `sorry`) to:

          {proof_path}

        Then end the conversation. Do not write commentary. Lean's verdict
        from the runner's grader (independent re-check) is the only score.
        """)


def run_attempt(*, problem: dict, sample_idx: int, seed: int, paths: dict[str, Path]) -> dict:
    if not shutil.which("claude"):
        raise RuntimeError("claude CLI not on PATH; run inside the atp-claude-code container.")
    repo = Path("/workspace")
    user_prompt = _build_user_prompt(problem, paths["proof"])
    budget = GeneralistBudget()

    env = os.environ.copy()
    env.setdefault("CLAUDE_PROJECT_DIR", str(repo))

    cmd = [
        "claude",
        "--dangerously-skip-permissions",
        "--print",
        "--output-format", "stream-json",
        "--verbose",
        "--max-turns", str(budget.max_tool_calls),
        "--model", "claude-opus-4-7",
        user_prompt,
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
    tokens_in = tokens_out = 0
    tool_calls = 0
    final_text = ""
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                events.append({"raw": line})
                continue
            events.append(evt)
            etype = evt.get("type")
            if etype == "assistant":
                msg = evt.get("message", {})
                usage = msg.get("usage") or {}
                tokens_in += int(usage.get("input_tokens") or 0)
                tokens_out += int(usage.get("output_tokens") or 0)
                for blk in msg.get("content", []):
                    if blk.get("type") == "text":
                        final_text = blk.get("text", "") or final_text
                    elif blk.get("type") == "tool_use":
                        tool_calls += 1
            elif etype == "result":
                u = evt.get("usage") or {}
                tokens_in = int(u.get("input_tokens") or tokens_in)
                tokens_out = int(u.get("output_tokens") or tokens_out)
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
        "final_text": final_text,
        "proof_text": proof_text,
        "transcript_path": str(paths["transcript"]),
        "exit_code": proc.returncode,
    }
