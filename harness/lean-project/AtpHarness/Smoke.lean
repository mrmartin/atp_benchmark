-- Smoke test for the pinned Lean + mathlib4 setup.
-- Imports a non-trivial mathlib lemma so the olean cache is actually exercised.
import Mathlib.Data.Nat.Basic
import Mathlib.Tactic

namespace AtpHarness.Smoke

example : 1 + 1 = 2 := by rfl

example (n : ℕ) : n + 0 = n := by simp

example (a b : ℕ) : a + b = b + a := Nat.add_comm a b

end AtpHarness.Smoke
