# Report outline (~12 pages)

To be filled in after the experiment runs. Each section ends with the figures/tables it owns.

## 1. Abstract
~150 words. Frame the question as **system stack vs. specialist prover**, not "model A vs. model B." State the headline pass@16 numbers and the primary qualitative finding.

## 2. Introduction
- Motivation: the literature has saturated miniF2F but PutnamBench remains open at SOTA ~12 %; whether a generalist + good scaffolding closes the gap is an open question.
- Contributions: (1) pre-registered, sealed harness with semantic Lean tools; (2) three-system head-to-head; (3) contamination-free holdout; (4) reproducible commit and tagged pre-registration.

## 3. Related work
One paragraph each:
- miniF2F / PutnamBench history and current SOTA.
- DeepSeek-Prover-V2 and the prover-LLM lineage.
- Goedel-Prover-V2: training pipeline, verifier-in-loop, miniF2F numbers.
- Agent scaffolds for math: Claude Code, OpenCode, AlphaProof, etc.

## 4. Method
- 4.1 Problem selection (the 12 main + 4 holdout, criteria, pinned mathlib commit, link to `problems/registry.json`).
- 4.2 Harness (Docker layout, MCP Lean server with REPL + loogle/exact?/apply?/find, pinned image hash).
- 4.3 Prompts (the per-system frozen prompts; identical task framing; system-specific tool descriptions).
- 4.4 Budgets (200 K tok / 30 min / 40 tool-call for generalists; k=16 × 4096 tok for Goedel; rationale for asymmetry).
- 4.5 Grading (single source of truth: `lake build` exits 0 on the file with proof replacing `sorry`).

## 5. Results
- Table 1: pass@1, pass@8, pass@16 with bootstrap 95 % CIs (resampling problems) per system, separately for main and holdout.
- Figure 1: 16 × 3 heatmap of pass-counts (the headline figure).
- Table 2: pairwise McNemar p-values on per-problem pass@16.
- Table 3: tokens per success, USD per success (where applicable), wall-clock per success.
- Table 4: holdout vs main delta per system (contamination diagnostic).

## 6. Qualitative analysis
3–4 worked examples:
- One that all three solved (illustrates floor difficulty of the set).
- One only Goedel-V2 solved (specialist advantage).
- One only the generalists solved (scaffold/tools advantage).
- One none solved (frontier of difficulty).
For each: the goal, the proof one or more systems found (or didn't), what the failed traces looked like, mathlib lemmas invoked.

## 7. Threats to validity
- Scaffold confound (we compare stacks, not models).
- Contamination — main set may be in training data; holdout addresses this with caveat that holdout is small (4).
- Power: n = 16 is borderline for McNemar; CIs are wide.
- Prompt sensitivity (no ablation in this run; deferred).
- Goedel-V2 trained with Lean compiler in the loop; generalists were not. The MCP REPL narrows but doesn't close the gap.
- Goedel-V2 ran with smaller per-attempt token budget (k=16 × 4096) than generalists (200 K each); this is system-native, not arbitrary, but documented.

## 8. Conclusion
Two paragraphs. Headline finding + one sentence on what would change the picture (e.g., longer Goedel budgets, larger n, prompt ablation).

## Appendix
- A. Per-problem table with full transcripts pointer.
- B. `problems/registry.json` snapshot.
- C. Image hash + mathlib commit + each system's pinned repo commit.
- D. `arbiter/decisions.md` excerpt covering choices that affected outcomes.
