"""Goedel-Prover-V2 runner adapter.

Defers to `systems/goedel-v2/inference.py` (kept separate because the
Goedel pipeline is whole-proof + verifier-in-loop, not an agent loop).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from ._common import write_jsonl


def run_attempt(*, problem: dict, sample_idx: int, seed: int, paths: dict[str, Path]) -> dict:
    repo = Path("/workspace")
    inference = repo / "systems" / "goedel-v2" / "inference.py"
    if not inference.exists():
        raise RuntimeError(f"missing {inference}")

    cmd = [
        sys.executable,
        str(inference),
        "--problem", problem["id"],
        "--sample-idx", str(sample_idx),
        "--seed", str(seed),
        "--proof-out", str(paths["proof"]),
        "--transcript-out", str(paths["transcript"]),
        "--scratch-dir", str(paths["scratch_dir"]),
    ]
    if problem.get("statement_path"):
        cmd += ["--statement-path", str(repo / problem["statement_path"])]
    if problem.get("informal_statement"):
        cmd += ["--informal", problem["informal_statement"]]

    proc = subprocess.run(cmd, capture_output=True, text=True)

    summary_path = paths["scratch_dir"] / "summary.json"
    summary: dict = {}
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text())
        except json.JSONDecodeError:
            pass

    proof_text = paths["proof"].read_text() if paths["proof"].exists() else ""

    return {
        "tokens_in": int(summary.get("tokens_in", 0)),
        "tokens_out": int(summary.get("tokens_out", 0)),
        "samples_attempted": int(summary.get("samples_attempted", 0)),
        "samples_verified_ok": int(summary.get("samples_verified_ok", 0)),
        "proof_text": proof_text,
        "transcript_path": str(paths["transcript"]),
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }
