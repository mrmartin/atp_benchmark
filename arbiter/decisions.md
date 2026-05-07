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
