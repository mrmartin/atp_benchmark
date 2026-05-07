# decisions

ADR-style log. Each entry has a number, date, status, decision, and the reasons it was chosen over alternatives. Add new entries at the bottom.

## ADR-001 — 2026-05-07 — Three-system comparison; Goedel-V2 is the open specialist

**Status:** accepted (per user, 2026-05-07).

**Decision.** Compare Claude Code (Opus 4.7), DeepSeek V4 Pro (`reasoning: xhigh`) via OpenCode/OpenRouter, and Goedel-Prover-V2 32B local.

**Why.** The question is generalist-vs-specialist on hard formal ATP. The cached `DeepSeek-Prover-V2-671B` on `/mnt/nvme2` cannot run on 2× 3090 and is left aside.

## ADR-002 — 2026-05-07 — PutnamBench, not miniF2F; pre-register 12 main + 4 holdout

**Status:** accepted (per user, 2026-05-07).

**Decision.** Use PutnamBench for the main 12 (post-2022, stratified across algebra/analysis/combinatorics/number-theory). Add 4 contamination-free holdout problems from IMO 2025 / Putnam 2024 community formalizations.

**Why.** miniF2F is saturated and likely contaminated. PutnamBench has headroom for discrimination at n = 12. The 4 holdout raises the report's defensibility ceiling against contamination critique.

## ADR-003 — 2026-05-07 — Goedel-V2 runs CPU-only at full bf16, no quantization

**Status:** accepted (per user, 2026-05-07).

**Decision.** Goedel-Prover-V2 32B inference uses `transformers` with `torch_dtype=torch.bfloat16, device_map="cpu"`. No GPU, no quantization. Wall-clock budget is dropped for Goedel; budget becomes k=16 whole-proof samples × 4096 tokens.

**Why.** User chose model fidelity over speed. Host has a 48-core CPU and 128 GB RAM; the 32B bf16 footprint (~64 GB) fits. Quantization (Q4_K_M) was explicitly rejected because we want "the best Goedel-V2 in the benchmark, not a quantized one."

**Cost.** Inference is slow (~0.3–1 tok/s); a full 16×16 grid will run on the order of days. Acceptable.

**Fairness implication.** Goedel-V2's per-attempt token budget is smaller than the generalists'; documented in threats-to-validity.

## ADR-004 — 2026-05-07 — Claude Code authenticates via host subscription, not API key

**Status:** accepted (per user, 2026-05-07).

**Decision.** Bind-mount the host's `~/.claude/` and `~/.claude.json` into the Claude Code container. Do not set `ANTHROPIC_API_KEY` inside the container.

**Why.** User has a Claude Pro/Max subscription and prefers to use it. Cost reporting becomes "tokens against the plan" instead of USD; we record tokens to allow tokens-per-success comparison with the API-priced systems.

## ADR-005 — 2026-05-07 — MCP Lean server uses a real REPL (lean-interact), not just `lake build`

**Status:** accepted (per user, 2026-05-07).

**Decision.** The MCP Lean server drives a real Lean 4 REPL via `lean-interact`. Tools exposed: `repl_open`, `repl_step`, `repl_close`, `loogle`, `exact_q`, `apply_q`, `mathlib_find`, `lean_check`, `mathlib_search` (ripgrep, fallback only).

**Why.** Goedel-V2 was trained against semantic Lean tools (loogle, exact?, apply?, Mathlib.Tactic.Find) running through a Lean REPL. A ripgrep-only `mathlib_search` would sandbag the generalists relative to Goedel's training surface and turn "rough parity" into a fiction. This is the most engineering-heavy piece of the harness — eight smoke tests (REPL lifecycle, `repl_step`, `exact_q`, `apply_q`, `loogle`, `mathlib_find`, `lean_check` ±, parallel-session isolation) must pass before sealing the harness.

## ADR-006 — 2026-05-07 — Heavy artifacts on `/mnt/nvme2/atp_runs/` only

**Status:** accepted.

**Decision.** All `.lake/` build cache, model weights, and transcripts live under `/mnt/nvme2/atp_runs/`. The repo references them through committed symlinks (`harness/lean-project/runs`, `systems/*/runs`, `results/transcripts`).

**Why.** Root partition is at 91% (45 GB free); mathlib build cache alone is several GB and Goedel-V2 weights are ~64 GB.

**Caveat.** Docker `data-root` is *not* yet relocated; the recommendation to move it to `/mnt/nvme2/docker` requires explicit user approval and host config change. Documented in `arbiter/host_setup.md` for the user to run with `sudo`.

## ADR-007 — 2026-05-07 — `.env` ignored at line 2 of `.gitignore`; pre-push secret scan as safety net

**Status:** accepted.

**Decision.** `.gitignore` was written before `git init`'s first stage. Line 1 is a comment, line 2 is `.env`. A `pre-push` hook running `arbiter/scripts/check_no_secrets.sh` greps for known key prefixes (`sk-`, `sk-or-`, `sk-ant-`, `hf_`, `gh[pousr]_`) and rejects pushes that would leak.

**Why.** `.env` already exists in the working dir and contains `OPENROUTER_API_KEY`. The user explicitly asked for "use it but not divulge it." Two layers of defense.

## ADR-008 — 2026-05-07 — Lean toolchain bumped to v4.27.0 (matches PutnamBench)

**Status:** accepted (during step 4 → step 5).

**Decision.** Bump `harness/lean-project/lean-toolchain` from `v4.25.1` to `v4.27.0` and the mathlib pin from `77b45269e0…` (tag v4.25.1) to `a3a10db0e9d6…` (tag v4.27.0).

**Why.** The pinned PutnamBench main commit (`77ea5a04`, 2026-04-20) targets `leanprover/lean4:v4.27.0` and mathlib `v4.27.0`. Pinning the harness to those exact versions lets us copy PutnamBench's statement files in unmodified — no porting, no paraphrasing, no risk of accidental semantic drift between source and registered statement. The earlier v4.25.1 pin was chosen before I'd surveyed PutnamBench; the cost of the bump was one extra `lake exe cache get` (~7 GB on NVMe) and was paid before any pre-registration commit.

## ADR-009 — 2026-05-07 — Holdout drawn from PutnamBench (Putnam 2024 + 2025), not compfiles

**Status:** accepted (during step 5).

**Decision.** All 4 holdout problems come from PutnamBench's own Putnam 2024 and 2025 entries, not from `dwrensha/compfiles` or `google-deepmind/formal-conjectures`.

**Why.** PutnamBench at the pinned commit already includes both Putnam 2024 (December 2024) and Putnam 2025 (December 2025) formalized in Lean 4 + mathlib4 by the official authors. Using a single source means a single mathlib pin and zero porting work; the contamination-free property is preserved because it derives from competition date relative to training cutoffs, not from the formalization being external. Caveat documented in `selection_criteria.md`: Claude Opus 4.7's January-2026 cutoff sits just after Putnam 2025's December-2025 date, so contamination cannot be ruled out for Claude on the holdout — partial protection for two of three systems, full for none.

## ADR-010 — 2026-05-07 — Combinatorics holdout swap: 2025_a3 → 2025_a5

**Status:** accepted (during step 5).

**Decision.** Replace `putnam_2025_a3` with `putnam_2025_a5` as the combinatorics holdout problem.

**Why.** The PutnamBench formalization of `putnam_2025_a3` uses `List.Chain` with its pre-v4.27.0 argument list. mathlib `a3a10db` deprecates that constant in favor of `List.IsChain` with a *different type* (one fewer argument). The statement still compiles but its semantic intent now relies on a deprecated API mid-flux; reviewers could reasonably question whether the registered statement still says what its informal English claims. `putnam_2025_a5` is the next-cleanest 2025 combinatorics problem (11 lines, no deprecation warnings) and is registered instead. Documented as a rejection in `problems/selection_criteria.md`.
