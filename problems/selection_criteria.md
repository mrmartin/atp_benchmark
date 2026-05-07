# Selection criteria

This file documents how the 12 main + 4 holdout problems in `registry.json` were chosen. **Frozen at pre-registration commit (tag `preregistration-v1`); do not edit later.**

## Source

All 16 statements come from a single source — [trishullab/PutnamBench](https://github.com/trishullab/PutnamBench), pinned at commit `77ea5a04b28b284f2b95f5c02dd46096bf75d33b` (main, 2026-04-20). PutnamBench's `lean4/src/<id>.lean` files are copied verbatim into `problems/statements/{main,holdout}/<id>.lean`. The `sha256` of every copied file is recorded in `registry.json` so any future drift is detectable.

## Lean / mathlib pinning

- Toolchain: `leanprover/lean4:v4.27.0`.
- mathlib: commit `a3a10db0e9d66acbebf76c5e6a135066525ac900` (tag `v4.27.0`).
- These match PutnamBench's own pins so statements drop in unmodified.

## Main set (12)

**Filters:**
1. Statement formalized as a theorem in Lean 4 + mathlib4 (PutnamBench guarantees this).
2. Statement length **strictly greater than 5 lines** after stripping blank lines, `import`, line comments (`--`) and doc-comment blocks (`/- ... -/`).
3. Natural-language Putnam year ∈ {2022, 2023}. (Years ≥ 2022 lower the contamination odds; years 2024–25 are reserved for the holdout.)
4. No published Lean proof exists in mathlib's library nor in PutnamBench's `solutions_replaced_new` glob. (PutnamBench's `lean4/src/` shipping commit has every theorem ending in `sorry`; no separate published proof was found via GitHub code search for any of the 12 IDs as of 2026-05-07.)
5. Stratified across four areas, three problems each:
   - **algebra**, **analysis**, **combinatorics**, **number_theory**.
   The "area" tag is the dominant entry from `informal/putnam.json#tags`; multi-tagged problems are placed in their primary semantic category. `geometry`, `probability`, and `linear_algebra` were excluded from the main stratification (no quota).

**Tie-breaking rule.** When more than three eligible problems remained in a stratum, preference was given to the longest statements (most "non-trivial"), then to a deterministic alphabetical tie-break by `id`. No randomness; the choice is fully reproducible from the filter list.

**Resulting 12:**

| Area | Year | Problem | Lines |
| --- | --- | --- | --- |
| algebra | 2022 | a2 | 11 |
| algebra | 2022 | b4 | 12 |
| algebra | 2023 | a2 | 12 |
| analysis | 2022 | b6 | 8 |
| analysis | 2023 | a3 | 8 |
| analysis | 2023 | b4 | 22 |
| combinatorics | 2022 | a5 | 16 |
| combinatorics | 2023 | a6 | 18 |
| combinatorics | 2023 | b1 | 19 |
| number_theory | 2022 | a3 | 7 |
| number_theory | 2023 | a4 | 14 |
| number_theory | 2023 | b5 | 9 |

## Holdout set (4) — contamination-free

**Filters:**
1. Same Lean 4 + mathlib4 source (PutnamBench).
2. Natural-language Putnam year ∈ {2024, 2025}. The Putnam 2025 competition was held in **December 2025**; Putnam 2024 in **December 2024**. Both post-date the public training cutoffs of DeepSeek V4 Pro (mid-2025) and Goedel-Prover-V2 (Princeton release, 2025). They sit at or just before Claude Opus 4.7's January-2026 cutoff, so contamination cannot be ruled out for Claude on these — the contamination delta is genuine for two of the three systems and partial for Claude.
3. Statement length > 5 lines.
4. One problem per area, same four areas as the main set.

**Resulting 4:**

| Area | Year | Problem | Lines |
| --- | --- | --- | --- |
| algebra | 2024 | a2 | 6 |
| analysis | 2025 | a2 | 7 |
| combinatorics | 2025 | a5 | 11 |
| number_theory | 2025 | a1 | 10 |

(2025 has no problem with `algebra` as a primary tag; `2024_a2` is the freshest pure-algebra option in the eligible window.)

**Rejection log.**
- `putnam_2025_a3` (combinatorics, 20 lines) was the original combinatorics pick. It compiles but the PutnamBench formalization uses `List.Chain` with the pre-`v4.27.0` argument list; mathlib `a3a10db` warns that this constant has been deprecated in favor of `List.IsChain` with a different type. The statement's semantic intent now hinges on a deprecated API in flux; replaced with the next-best 2025 combinatorics problem `putnam_2025_a5` (11 lines, clean compile) to keep the holdout free of API-instability noise.

## Departures from the original brief

- The original brief (see `arbiter/plan.md`) suggested IMO 2025 / Putnam 2024 community formalizations from `compfiles` or `formal-conjectures` for the holdout. PutnamBench at the pinned commit already includes both Putnam 2024 and Putnam 2025 formalized in Lean 4 + mathlib4 by the official authors, so the holdout is sourced from PutnamBench too. This collapses the project to a single Lean source and a single mathlib pin without weakening the contamination-free property.

## Verification

Every entry has been compiled with `lake env lean -- <statement_path>` against the pinned toolchain + mathlib. The expected output is "declaration uses 'sorry'" warnings only; any error or other warning would have rejected the entry.

## What this freezes

- The 16 problem IDs.
- The byte content of each statement file (sha256 in `registry.json`).
- The PutnamBench source commit, mathlib commit, and Lean toolchain.

What is **not** frozen here: the per-system prompts (in `systems/*/prompt.txt`, frozen separately at the harness-sealing commit) and the MCP Lean server (frozen at the same harness-sealing commit).
