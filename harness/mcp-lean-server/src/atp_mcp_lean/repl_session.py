"""Per-attempt Lean REPL session management.

Wraps `lean-interact` so that each (system, problem, sample_idx) attempt gets a
fresh REPL backed by the pinned `harness/lean-project/` (Lean v4.27.0 + mathlib
a3a10db). Each session tracks one open proof state derived from a registered
problem statement.

The contract: tools either succeed with structured Lean output or raise. There
are no silent fallbacks — fail fast (per ADR/decision).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from lean_interact import (
    Command,
    LeanREPLConfig,
    LeanServer,
    LocalProject,
    ProofStep,
)
from lean_interact.interface import LeanError


REPO = Path(__file__).resolve().parents[4]
LEAN_PROJECT = REPO / "harness" / "lean-project"
PROBLEMS_DIR = REPO / "problems" / "statements"

# Where lean-interact caches its REPL build. Default to a writable location on
# /mnt/nvme2 (bind-mounted) so the non-root agent user inside the container
# can write here. Override via ATP_MCP_LEAN_CACHE_DIR if needed.
DEFAULT_CACHE_DIR = Path(
    os.environ.get(
        "ATP_MCP_LEAN_CACHE_DIR",
        "/mnt/nvme2/atp_runs/lean-interact-cache",
    )
)


def _problem_path(problem_id: str) -> Path:
    """Resolve a registered problem ID to its statement file."""
    for sub in ("main", "holdout"):
        p = PROBLEMS_DIR / sub / f"{problem_id}.lean"
        if p.exists():
            return p
    raise FileNotFoundError(f"Unknown problem_id: {problem_id!r}")


def _strip_proof_to_sorry(src: str) -> tuple[str, str]:
    """Remove the trailing `sorry` that closes the registered theorem and
    replace it with `by sorry` (or leave it as-is if already in tactic mode)
    so that the REPL hands us back a proof_state we can drive.

    Returns (rewritten_source, theorem_name).
    """
    # The PutnamBench convention: the theorem ends in "sorry" or ":= sorry"
    # (term mode) or "by sorry" (tactic mode).  We force tactic mode so the
    # REPL exposes a proof state.
    m = re.search(r"theorem\s+([A-Za-z_][\w]*)", src)
    if not m:
        raise ValueError("Could not find `theorem <name>` in statement.")
    name = m.group(1)
    # Replace the FINAL `:= sorry` (term-mode) with `:= by sorry`.
    # Be conservative: only act on a trailing `sorry` token.
    rewritten = re.sub(r":=\s*sorry\b\s*$", ":= by sorry", src.strip(), count=1)
    return rewritten, name


@dataclass
class Session:
    session_id: str
    problem_id: str
    theorem_name: str
    mathlib_env: int
    proof_state: int | None
    initial_goal: str
    history: list[dict] = field(default_factory=list)


class ReplPool:
    """Holds at most one LeanServer alive at a time, keyed by config.

    Spawning a server takes ~10-30 s (REPL build cached), so reuse it across
    sessions; sessions are isolated by `env` snapshots, not by separate processes.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._server: LeanServer | None = None
        self._mathlib_env: int | None = None
        self._sessions: dict[str, Session] = {}

    def _ensure(self) -> LeanServer:
        with self._lock:
            if self._server is None:
                DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                config = LeanREPLConfig(
                    project=LocalProject(directory=str(LEAN_PROJECT)),
                    cache_dir=DEFAULT_CACHE_DIR,
                    verbose=False,
                )
                self._server = LeanServer(config)
                # Warm mathlib once.
                resp = self._server.run(Command(cmd="import Mathlib"))
                if resp.has_errors():
                    raise RuntimeError(
                        f"`import Mathlib` failed in REPL: {resp.get_errors()}"
                    )
                self._mathlib_env = resp.env
            return self._server

    @property
    def mathlib_env(self) -> int:
        self._ensure()
        assert self._mathlib_env is not None
        return self._mathlib_env

    # ----- session API ----------------------------------------------------
    def open(self, problem_id: str) -> Session:
        srv = self._ensure()
        path = _problem_path(problem_id)
        src = path.read_text()
        rewritten, name = _strip_proof_to_sorry(src)

        # Strip the leading "import Mathlib" — the REPL already has it loaded.
        body = re.sub(r"^\s*import\s+Mathlib\s*\n", "", rewritten, count=1)

        resp = srv.run(Command(cmd=body, env=self.mathlib_env))
        if resp.has_errors():
            raise RuntimeError(
                f"Problem statement {problem_id} failed to load: {resp.get_errors()}"
            )
        if not resp.sorries:
            raise RuntimeError(
                f"Problem statement {problem_id} produced no sorries; cannot open a proof state."
            )
        # Convention: the LAST sorry corresponds to the registered theorem's
        # main proof obligation.  Earlier sorries (e.g., putnam_..._solution
        # abbrev) are also tracked but the agent's job is to discharge the
        # theorem, not the abbrev.  We pick the sorry whose location is on
        # the `theorem` line.
        chosen = resp.sorries[-1]
        sid = uuid.uuid4().hex[:12]
        sess = Session(
            session_id=sid,
            problem_id=problem_id,
            theorem_name=name,
            mathlib_env=self.mathlib_env,
            proof_state=chosen.proof_state,
            initial_goal=chosen.goal,
        )
        self._sessions[sid] = sess
        return sess

    def step(self, session_id: str, tactic: str) -> dict:
        srv = self._ensure()
        sess = self._sessions[session_id]
        if sess.proof_state is None:
            raise RuntimeError("Session has no open proof state.")
        resp = srv.run(ProofStep(tactic=tactic, proof_state=sess.proof_state))
        out = self._normalise_proof_response(resp)
        # Update the open state so the next step starts from here.
        new_state = getattr(resp, "proof_state", None)
        if new_state is not None and new_state != sess.proof_state:
            sess.proof_state = new_state
        sess.history.append({"tactic": tactic, **out})
        return {"session_id": session_id, **out}

    @staticmethod
    def _normalise_proof_response(resp) -> dict:
        if isinstance(resp, LeanError):
            return {"errors": True, "messages": [{"severity": "error", "data": resp.message}]}
        out: dict = {
            "messages": [
                {"severity": m.severity, "data": m.data}
                for m in (getattr(resp, "messages", None) or [])
            ],
            "errors": bool(resp.has_errors()) if hasattr(resp, "has_errors") else False,
        }
        new_goals = getattr(resp, "goals", None)
        if new_goals is not None:
            out["goals"] = new_goals
        proof_status = getattr(resp, "proof_status", None)
        if proof_status is not None:
            out["proof_status"] = proof_status
            out["closed"] = proof_status == "Completed"
        return out

    def close(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def get(self, session_id: str) -> Session:
        return self._sessions[session_id]

    # ----- semantic search -----------------------------------------------
    def loogle(self, query: str) -> dict:
        srv = self._ensure()
        cmd = f"#loogle {query}"
        resp = srv.run(Command(cmd=cmd, env=self.mathlib_env))
        return self._search_response(resp)

    def find(self, pattern: str) -> dict:
        srv = self._ensure()
        cmd = f"#find {pattern}"
        resp = srv.run(Command(cmd=cmd, env=self.mathlib_env))
        return self._search_response(resp)

    def exact_q(self, session_id: str) -> dict:
        return self._tactic_query(session_id, "exact?")

    def apply_q(self, session_id: str) -> dict:
        return self._tactic_query(session_id, "apply?")

    def _tactic_query(self, session_id: str, tactic: str) -> dict:
        srv = self._ensure()
        sess = self._sessions[session_id]
        if sess.proof_state is None:
            raise RuntimeError("Session has no open proof state.")
        resp = srv.run(ProofStep(tactic=tactic, proof_state=sess.proof_state))
        # Do NOT update sess.proof_state — the agent must explicitly take a
        # suggestion via `repl_step`.
        return self._normalise_proof_response(resp)

    @staticmethod
    def _search_response(resp) -> dict:
        if isinstance(resp, LeanError):
            return {"messages": [{"severity": "error", "data": resp.message}], "has_errors": True}
        return {
            "messages": [
                {"severity": m.severity, "data": m.data}
                for m in (getattr(resp, "messages", None) or [])
            ],
            "has_errors": bool(resp.has_errors()) if hasattr(resp, "has_errors") else False,
        }

    # ----- whole-file check (final verification) -------------------------
    def lean_check(self, file_relpath: str, source: str) -> dict:
        """Write `source` into a sandbox file and run `lake env lean -- <file>`.

        Used as the official grader: success ⇔ exit 0 with no errors. Exists
        in addition to the REPL because the registered problem's `lake build`
        verdict is what ultimately scores an attempt.
        """
        srv = self._ensure()  # ensure REPL exists (and project is built)
        sandbox = LEAN_PROJECT / "AtpHarness" / "_sandbox"
        sandbox.mkdir(parents=True, exist_ok=True)
        if ".." in file_relpath or file_relpath.startswith("/"):
            raise ValueError(f"Unsafe file_relpath: {file_relpath!r}")
        target = sandbox / file_relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source)
        try:
            proc = subprocess.run(
                ["lake", "env", "lean", "--", str(target)],
                cwd=str(LEAN_PROJECT),
                capture_output=True,
                text=True,
                timeout=600,
            )
            success = proc.returncode == 0 and "error:" not in proc.stderr
            return {
                "success": success,
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        finally:
            try:
                target.unlink()
            except OSError:
                pass
