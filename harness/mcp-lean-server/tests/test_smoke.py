"""Eight smoke tests for the MCP Lean server's tool surface.

Run from repo root with:
    harness/.venv/bin/python -m harness.mcp-lean-server.tests.test_smoke
or simply:
    harness/.venv/bin/python harness/mcp-lean-server/tests/test_smoke.py

Each test exercises the same ReplPool the MCP server uses. They MUST all pass
before the harness is sealed.
"""
from __future__ import annotations

import sys
import textwrap
import traceback
from pathlib import Path

# Allow running as a script.
HERE = Path(__file__).resolve()
SRC = HERE.parents[1] / "src"
sys.path.insert(0, str(SRC))

from atp_mcp_lean.repl_session import ReplPool  # noqa: E402


def _ok(name: str) -> None:
    print(f"  PASS  {name}")


def _fail(name: str, msg: str) -> None:
    print(f"  FAIL  {name}: {msg}")


def main() -> int:
    pool = ReplPool()
    fails: list[str] = []

    # 1. repl_open returns expected goal shape for a registered problem.
    sess = pool.open("putnam_2022_a3")
    g = sess.initial_goal or ""
    if "f" in g and ("MOD" in g or "≡" in g or "5" in g):
        _ok("01 repl_open puts us in a non-trivial goal state")
    else:
        _fail("01 repl_open", f"unexpected goal: {g!r}")
        fails.append("01")

    # 2. repl_step with a benign no-op tactic returns structured output without error.
    r = pool.step(sess.session_id, "skip")
    if "messages" in r and not r.get("errors"):
        _ok("02 repl_step accepts `skip` and returns structured output")
    else:
        _fail("02 repl_step", f"unexpected: {r}")
        fails.append("02")

    # 3. exact_q proposes a closing term on a freshly-opened, simple goal.
    pool.close(sess.session_id)
    # Build a tiny goal directly via REPL: open `1+1=2` in tactic mode
    srv = pool._ensure()
    from lean_interact import Command, ProofStep
    resp = srv.run(Command(cmd="example : 1 + 1 = 2 := by sorry", env=pool.mathlib_env))
    if not resp.sorries:
        _fail("03 exact_q setup", "no sorry from inline example")
        fails.append("03")
    else:
        ps = resp.sorries[-1].proof_state
        r2 = srv.run(ProofStep(tactic="exact?", proof_state=ps))
        msgs = " ".join(m.data for m in (r2.messages or []))
        if "exact" in msgs.lower() or "rfl" in msgs.lower() or "Try this" in msgs:
            _ok("03 exact_q proposes closing terms on a simple goal")
        else:
            _fail("03 exact_q", f"no suggestion in messages: {msgs[:200]}")
            fails.append("03")

    # 4. apply_q on a goal that matches Nat.add_comm.
    resp = srv.run(
        Command(cmd="example (a b : ℕ) : a + b = b + a := by sorry", env=pool.mathlib_env)
    )
    ps = resp.sorries[-1].proof_state
    r3 = srv.run(ProofStep(tactic="apply?", proof_state=ps))
    msgs = " ".join(m.data for m in (r3.messages or []))
    if "Nat.add_comm" in msgs or "add_comm" in msgs or "Try this" in msgs:
        _ok("04 apply_q suggests add_comm-shaped lemma")
    else:
        _fail("04 apply_q", f"no suggestion: {msgs[:200]}")
        fails.append("04")

    # 5. loogle returns ≥1 hit for a syntactic pattern.
    out = pool.loogle("Nat.add_comm")
    msgs = " ".join(m.get("data", "") for m in out.get("messages", []))
    if "Nat.add_comm" in msgs or "found" in msgs.lower() or "•" in msgs:
        _ok("05 loogle returns hits for Nat.add_comm")
    else:
        _fail("05 loogle", f"no hits: {msgs[:200]}")
        fails.append("05")

    # 6. mathlib_find with #find.
    out = pool.find("(_ + _ = _ + _)")
    msgs = " ".join(m.get("data", "") for m in out.get("messages", []))
    if msgs.strip():
        _ok("06 mathlib_find returns something for a syntactic pattern")
    else:
        _fail("06 mathlib_find", "empty")
        fails.append("06")

    # 7. lean_check returns success on a correct proof, failure on a broken one.
    good = textwrap.dedent("""
        import Mathlib
        example : 1 + 1 = 2 := by rfl
    """).strip() + "\n"
    bad = textwrap.dedent("""
        import Mathlib
        example : 1 + 1 = 3 := by rfl
    """).strip() + "\n"
    r_good = pool.lean_check("smoke_good.lean", good)
    r_bad = pool.lean_check("smoke_bad.lean", bad)
    if r_good["success"] and not r_bad["success"]:
        _ok("07 lean_check returns success/failure correctly")
    else:
        _fail(
            "07 lean_check",
            f"good={r_good['success']} bad={r_bad['success']}; stderr_bad={r_bad['stderr'][:200]}",
        )
        fails.append("07")

    # 8. Parallel sessions stay isolated.
    s1 = pool.open("putnam_2022_a3")
    s2 = pool.open("putnam_2024_a2")
    if s1.session_id != s2.session_id and s1.theorem_name != s2.theorem_name:
        # Take a step in s1, verify s2 is unaffected.
        pool.step(s1.session_id, "skip")
        s2_check = pool.get(s2.session_id)
        if s2_check.theorem_name == "putnam_2024_a2":
            _ok("08 parallel sessions don't interfere")
        else:
            _fail("08 parallel sessions", f"s2 theorem changed: {s2_check.theorem_name}")
            fails.append("08")
    else:
        _fail("08 parallel sessions", "session_ids or theorem names collided")
        fails.append("08")

    pool.close(s1.session_id)
    pool.close(s2.session_id)

    print()
    if fails:
        print(f"FAILED: {len(fails)} test(s) — {', '.join(fails)}")
        return 1
    print("All 8 smoke tests passed.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
