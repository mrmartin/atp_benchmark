# Experiment design (pinned)

This is the user's original brief, copied verbatim. The arbiter's working plan derived from it lives at `/home/martin/.claude/plans/staged-wobbling-wolf.md` (and is the basis of `arbiter/decisions.md`).

---

A few naming points up front since they materially change the design:

- "DeepSeek V4 Max" doesn't exist as a SKU — there's V4 Pro and V4 Flash. The "max" knob is `reasoning: xhigh` on V4 Pro. I'll assume that's what you mean.
- "OpenProver" doesn't map to a single named system. The natural open-source specialist contestant is **Goedel-Prover-V2** (Princeton, current open-source SOTA on miniF2F at ~88%) or **DeepSeek-Prover-V2-671B** (also open weights, ~89% miniF2F / 7.4% PutnamBench). I'll design around Goedel-V2 unless you tell me otherwise — it's the more interesting comparison because it isolates "specialist prover trained from scratch" from "generalist DeepSeek lineage."

So the real question your experiment answers is: **Does a frontier generalist + agent scaffold close the gap with a purpose-built prover on hard formal ATP?** That's a worthwhile question and the literature doesn't have a clean answer yet.

## Domain choice: formal Lean 4

Pick formal-only. Natural-language math comparisons get strangled by grading subjectivity and you can't beat Lean's binary kernel verdict for an objective signal. All three systems can target Lean 4 + mathlib4.

## Benchmark: PutnamBench, not miniF2F

miniF2F is saturated (the field is hitting 85–90%) and almost certainly contaminated for both Claude and DeepSeek. PutnamBench gives you headroom — leaderboard SOTA is ~12% — so a 12-problem sample actually discriminates between systems instead of all three scoring 11/12.

Sample 12 problems with explicit criteria: stratify across algebra (3), analysis (3), combinatorics (3), number theory (3); within each stratum pick problems where (a) the formal statement is non-trivial (>5 lines), (b) no published Lean proof exists in mathlib or the PutnamBench solutions repo, (c) the natural-language Putnam year is post-2022 to lower contamination odds. **Pre-register the 12 problems and pin a mathlib4 commit hash before you run anything.** Otherwise reviewers (including future-you) will suspect cherry-picking.

If you want a contamination-free fork: replace 4 of the 12 with formalized Putnam 2024 or IMO 2025 problems. There are recent community formalizations on GitHub.

## Protocol

For each (system, problem) cell:

- **Pass@k with k = 16**, independent samples, temperature 0.8.
- Per attempt: 200K-token budget, 30-minute wall clock, max 40 tool calls.
- Success = `lake build` exits 0 on the file with the proposed proof replacing `sorry`.
- Same harness for all three: a sealed Docker container with mathlib4 pre-cached, a `lean_check` tool the agent calls, a `mathlib_search` tool (ripgrep over mathlib + a `loogle`/`exact?` shim).

Why pass@16 and not pass@1: with 12 problems and binary outcomes, pass@1 has a standard error of ~0.14 even at p=0.5. Pass@16 averaged over independent samples gives you ~10× better precision per dollar than running more problems with k=1, and it matches how prover papers report results.

## System-specific configuration

**DeepSeek V4 Pro** in OpenCode v1.14.24+, OpenRouter, `reasoning: xhigh`, `autoCompact: false` (you want full transcripts for the report). Lean tools exposed via MCP.

**Claude Code** with Opus 4.7, default scaffold, same Lean MCP server, same skill file describing mathlib conventions and the `lean_check`/`mathlib_search` tools. Use `--dangerously-skip-permissions` inside the container so the loop runs unattended.

**Goedel-Prover-V2** native pipeline: whole-proof generation with verifier-in-the-loop. The 32B variant fits on your 3090 at Q4_K_M (~22GB); use the official inference script with k=16 samples per problem. Don't put it in OpenCode — that's not how it was trained to operate and you'd handicap it.

Critical fairness move: **the two generalists get the same Lean tooling and same per-attempt budget Goedel-V2 gets**. Don't give Claude Code 64 turns of Lean feedback while Goedel-V2 only gets one shot — that's not a comparison, it's a sandbagging.

## Metrics

Primary: pass@1, pass@8, pass@16 with bootstrap 95% CIs over the 12-problem set (resample problems, not attempts).

Secondary: tokens per success, USD per success, wall-clock per success, mean proof length in tactics, count of compile errors before success, mathlib lemmas invoked.

Pairwise: McNemar's test on per-problem pass@16 outcomes between each pair of systems. Per-problem heatmap (12 problems × 3 systems × pass count out of 16) — this single figure usually communicates more than the aggregate numbers.

## Threats to validity (be explicit in the report)

1. **Scaffold confound.** You're comparing system stacks, not models. Frame it that way in the abstract or you'll get destroyed in review.
2. **Contamination.** Document training cutoffs vs. benchmark dates; ideally include a "natural-language familiarity" probe — ask each model for the NL solution to each problem first, before the formal task, and report.
3. **n=12.** With 12 problems even a 4/12 vs 8/12 split is only borderline significant by McNemar. Acknowledge the power constraint or expand to 24.
4. **Prompt sensitivity.** A single prompt format can favor one system. Run a small ablation: 3 prompt variants on a held-out 4 problems, pick the per-system best, then run the main 12 with frozen prompts.
5. **Goedel-V2 was trained with a Lean compiler in the loop.** The two generalists were not. The Lean tool you give them partially equalizes this, but not fully.

## Cost envelope

Roughly: V4 Pro 16×12 attempts at ~80K tokens each = ~$15. Opus 4.7 at the same budget = ~$200. Goedel-V2 local = electricity. So the experiment is bounded by Claude API spend; budget $300 for the main run plus a re-run.

## Report structure

Eight sections, ~12 pages: Abstract → Introduction (frame the generalist-vs-specialist question) → Related work (one paragraph each on miniF2F/PutnamBench, DeepSeek-Prover-V2, Goedel-Prover, agent scaffolds for math) → Method (problem selection, harness, prompts, budgets — link to the pinned repo) → Results (the heatmap, the pass@k table with CIs, the cost-normalized comparison) → Qualitative analysis (3–4 worked examples: a problem all three solved, one only Goedel solved, one only the generalists solved, one no one solved) → Threats to validity → Conclusion.

If you want, I can draft the orchestration code (Docker harness + MCP Lean server + per-system runners + the heatmap and stats notebooks) as the next step. That's the part that determines whether the experiment is reproducible or just one more LLM-vs-LLM blog post.

---

## Subsequent user clarifications

- **Two open provers** confirmed: Goedel-Prover-V2 (local) + DeepSeek V4 Pro (OpenRouter via OpenCode). Three systems total with Claude Code.
- **GitHub remote**: `git@github.com:mrmartin/atp_benchmark.git` (already created, empty).
- **Pre-register** 12 main problems now as part of env prep.
- **OpenCode** installed inside the per-system Docker image, not on host.
- **Add 4 contamination-free held-out** (IMO 2025 / Putnam 2024) — explicitly overrides "out of scope" note for the contamination fork.
- **Claude Code uses subscription login**, not API key (bind-mount `~/.claude/`).
- **Goedel-V2 runs CPU-only at full bf16, no quantization** (host has 128 GB RAM and a strong CPU; user prefers fidelity over speed).
- **`.env`** is the source of truth for OpenRouter creds; never commit it.
- **MCP Lean server must be a real REPL** (lean-interact / Goedel-V2's bundled REPL), not a ripgrep stub — this is the most engineering-heavy and most underspecified piece; build it before sealing the harness.
