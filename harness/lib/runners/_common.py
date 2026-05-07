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
