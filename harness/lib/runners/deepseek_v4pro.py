"""DeepSeek V4 Pro (via OpenCode + OpenRouter) runner adapter.

Invokes `opencode run` with the project-level `opencode.json` (at /workspace)
that wires the MCP Lean server and sets the model + xhigh variant. Wall-clock
budget enforced via the GNU `timeout` wrapper because OpenCode itself has no
turn-cap analogue.
"""
from __future__ import annotations

import os
import shutil
import textwrap
from pathlib import Path

from ..budget import GeneralistBudget
from ._common import render_prompt, stream_subprocess


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

    cmd = [
        "opencode", "run",
        "--dangerously-skip-permissions",
        "--format", "json",
        "--variant", "xhigh",
        "--model", "openrouter/deepseek/deepseek-v4-pro",
        "--dir", str(repo),
        prompt,
    ]

    exit_code, events = stream_subprocess(
        cmd, cwd=str(repo), env=env,
        transcript_path=paths["transcript"],
        wall_seconds=budget.max_seconds,
    )

    tokens_in = tokens_out = tool_calls = 0
    for evt in events:
        etype = evt.get("type") or evt.get("event")
        if etype in {"tool_use", "tool", "tool_call"}:
            tool_calls += 1
        if "usage" in evt and isinstance(evt["usage"], dict):
            u = evt["usage"]
            tokens_in += int(u.get("input_tokens", 0))
            tokens_out += int(u.get("output_tokens", 0))

    proof_text = paths["proof"].read_text() if paths["proof"].exists() else ""

    return {
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tool_calls": tool_calls,
        "proof_text": proof_text,
        "transcript_path": str(paths["transcript"]),
        "exit_code": exit_code,
    }
