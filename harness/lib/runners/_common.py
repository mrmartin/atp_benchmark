"""Shared helpers for the per-system runner adapters."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PROMPT_DIR = REPO / "systems"


def render_prompt(system: str, problem: dict) -> str:
    """Substitute problem fields into the system's frozen prompt template."""
    tmpl = (PROMPT_DIR / system / "prompt.txt").read_text()
    statement = ""
    if problem.get("statement_path"):
        statement = (REPO / problem["statement_path"]).read_text()
    return tmpl.format(
        problem_id=problem.get("id", ""),
        set=problem.get("set", ""),
        theorem_name=_extract_theorem_name(statement),
        statement=statement,
        informal_statement=problem.get("informal_statement", ""),
    )


def _extract_theorem_name(src: str) -> str:
    m = re.search(r"theorem\s+([A-Za-z_][\w]*)", src)
    return m.group(1) if m else ""


def write_jsonl(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def stream_subprocess(
    cmd: list[str],
    *,
    cwd: str,
    env: dict | None,
    transcript_path: Path,
    wall_seconds: int,
) -> tuple[int, list[dict]]:
    """Run cmd, stream stdout line-by-line to transcript_path (jsonl when possible).

    Enforces a hard wall-clock cap via the GNU `timeout` command; if cmd exits
    cleanly within budget, returns (exit_code, parsed_events). On timeout,
    `timeout` sends SIGTERM (then SIGKILL after 10 s) and we surface the
    partial output as-is.
    """
    import subprocess
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    wrapped = ["timeout", "--kill-after=10", f"{wall_seconds}s", *cmd]
    events: list[dict] = []
    with transcript_path.open("w", buffering=1) as tf, subprocess.Popen(
        wrapped, cwd=cwd, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    ) as proc:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip("\n")
            if not line:
                continue
            tf.write(line + "\n")
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append({"raw": line})
        proc.wait()
        return proc.returncode, events
