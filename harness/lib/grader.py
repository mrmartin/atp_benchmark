"""Official grader: lake-build verdict for a candidate proof.

A proof attempt SUCCEEDS iff:
  - the registered statement file with `sorry` replaced by the candidate proof
  - compiles via `lake env lean -- <file>` exit 0
  - and produces zero `error:` diagnostics in stderr (sorry warnings are OK
    only if the candidate proof itself is `sorry` — which would not be a
    valid attempt; we forbid `sorry` in the candidate).

This module is the SOLE source of the verdict; runners must defer to it.
"""
from __future__ import annotations

import json
import re
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEAN_PROJECT = REPO / "harness" / "lean-project"
PROBLEMS_DIR = REPO / "problems" / "statements"
REGISTRY = json.loads((REPO / "problems" / "registry.json").read_text())
PROBLEMS_BY_ID = {p["id"]: p for p in REGISTRY["problems"]}


@dataclass
class Verdict:
    success: bool
    exit_code: int
    proof_text: str
    candidate_file: str
    stdout: str
    stderr: str

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "exit_code": self.exit_code,
            "proof_text": self.proof_text,
            "candidate_file": self.candidate_file,
            "stdout_tail": self.stdout[-4000:],
            "stderr_tail": self.stderr[-4000:],
        }


def _statement_with_proof(problem_id: str, proof_text: str) -> str:
    """Splice the candidate proof into the registered statement.

    The PutnamBench convention: each statement ends with `:= sorry` (term
    mode) or `by sorry` (tactic mode). We replace the FINAL `sorry` with
    the candidate's proof text.
    """
    rec = PROBLEMS_BY_ID[problem_id]
    src = (REPO / rec["statement_path"]).read_text()
    if "sorry" not in src:
        raise ValueError(f"Registered statement {problem_id} has no `sorry` to replace.")
    # Replace the LAST occurrence of `sorry` (by reversing).
    rev_src = src[::-1]
    rev_proof = proof_text[::-1]
    rev_replaced = rev_src.replace("yrros"[::-1][::-1], rev_proof, 1)  # noqa
    # The above is intentionally explicit; do it cleanly with rsplit:
    head, _, tail = src.rpartition("sorry")
    # Forbid the candidate from itself containing top-level `sorry`.
    if re.search(r"\bsorry\b", proof_text):
        raise ValueError("Candidate proof contains `sorry`; not a valid attempt.")
    return head + proof_text + tail


def grade(problem_id: str, proof_text: str, *, timeout: int = 1200) -> Verdict:
    """Grade a candidate proof against the registered statement."""
    sandbox = LEAN_PROJECT / "AtpHarness" / "_grader"
    sandbox.mkdir(parents=True, exist_ok=True)
    candidate_file = sandbox / f"{problem_id}.lean"
    spliced = _statement_with_proof(problem_id, proof_text)
    candidate_file.write_text(spliced)
    try:
        proc = subprocess.run(
            ["lake", "env", "lean", "--", str(candidate_file)],
            cwd=str(LEAN_PROJECT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        success = proc.returncode == 0 and "error:" not in proc.stderr
        return Verdict(
            success=success,
            exit_code=proc.returncode,
            proof_text=proof_text,
            candidate_file=str(candidate_file.relative_to(REPO)),
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    finally:
        # Keep the file on disk for forensic reading; transcripts reference it.
        pass


__all__ = ["grade", "Verdict", "PROBLEMS_BY_ID"]
