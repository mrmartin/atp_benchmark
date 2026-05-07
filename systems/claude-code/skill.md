# Lean ATP skill — mathlib conventions and tools

You are proving a registered theorem from PutnamBench against a pinned mathlib4. The harness exposes a single MCP server (`atp-mcp-lean`) with these tools — use them, in roughly this order, before reaching for ripgrep:

1. **`repl_open(problem_id)`** — opens a fresh Lean REPL session loaded with the problem statement and full mathlib. Returns `{session_id, theorem_name, initial_goal}`.
2. **`repl_step(session_id, tactic)`** — applies one tactic. Returns the new goals (or `closed: true`) plus any messages. Iterate.
3. **`exact_q(session_id)`** — asks Lean's `exact?` to suggest closing terms for the current goal. Free; try it on every leaf goal.
4. **`apply_q(session_id)`** — `apply?` for one-step lemma matches.
5. **`mathlib_find(pattern)`** — runs `Mathlib.Tactic.Find`. Use a syntactic pattern, e.g. `(_ + _ = _ + _)`.
6. **`loogle(query)`** — semantic search by goal type. Examples: `Nat.add_comm`, `List.length, _ + _ = _`.
7. **`mathlib_search(query)`** — ripgrep fallback. Use only when the semantic tools above failed.
8. **`lean_check(file_relpath, source)`** — full-file compile via `lake env lean`. This is the **official grader**. Call it once you think the proof is complete to confirm.

## mathlib4 conventions you should rely on

- `Nat.add_comm`, `Nat.mul_comm`, `Nat.add_assoc` — the obvious ones.
- `simp [...]` with lemma list; `simp only` to keep the rewrite small.
- `omega` for linear arithmetic over ℤ/ℕ; usually closes goals after `intro`/`subst`.
- `decide` for decidable propositions; works on small finite cases.
- `linear_combination` for ring identities; `polyrith` for polynomial proofs.
- `field_simp; ring` for field arithmetic.
- `Finset.sum_range_succ`, `Finset.sum_comm`, etc. for finite-sum manipulation.
- `Nat.recOn`, `Nat.strongRecOn`, `Nat.le_induction` for induction patterns.
- `Set.eq_def`, `Set.mem_def` to peel set comprehensions.

## Tactic style

- Prefer `intro h; …` over implicit binders for clarity.
- Use `refine ?_` to leave subgoals you can shape with `exact?` after.
- `change <new_goal>` to rewrite the goal definitionally; cheap and helps when `simp` over-rewrites.
- For the `IsGreatest` / `IsLeast` / `sSup` problems common in PutnamBench, expand the definition with `unfold IsGreatest; refine ⟨?_, ?_⟩` and discharge each side independently.

## What to record in your transcript

- Every `repl_step` you take, the goal before, the result.
- Every `exact_q` / `apply_q` suggestion you accepted or rejected, and why.
- The final `lean_check` verdict (must be `success: true` for the attempt to count).

## Termination

You have a fixed budget per attempt: 200 K tokens, 30 minutes, 40 tool calls. The harness enforces these. If the budget runs out, write your best partial proof to a file and call `lean_check`; a partial-but-incorrect attempt scores 0 just like no attempt at all, so spend your last few tool calls on `exact_q` rather than chain-of-thought.
