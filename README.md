# atp_benchmark

A pre-registered, reproducible comparison of three ATP systems on 12 PutnamBench problems plus 4 contamination-free held-out problems (IMO 2025 / Putnam 2024).

**Systems under test**
- **Claude Code** (Opus 4.7) — generalist + agent scaffold
- **DeepSeek V4 Pro** (`reasoning: xhigh`) inside **OpenCode** via OpenRouter — generalist
- **Goedel-Prover-V2 32B** (full-precision bf16, CPU) — open specialist prover

**The question.** Does a frontier generalist + agent scaffold close the gap with a purpose-built prover on hard formal ATP?

## Layout

| Path | Purpose |
| --- | --- |
| `arbiter/` | Arbiter (Claude) workspace: role, plan, decisions, progress |
| `problems/` | Frozen 16-problem registry + statements (sealed at pre-registration commit) |
| `harness/` | Sealed Docker harness, MCP Lean server, pinned mathlib4 |
| `systems/` | Per-system runners (claude-code, deepseek-v4pro, goedel-v2) |
| `results/raw/` | Per-attempt JSON results (committed) |
| `analysis/` | Notebooks for pass@k, McNemar, heatmap, cost |
| `report/` | Final write-up |

## Reproducibility

- Pre-registration commit (tag `preregistration-v1`) freezes the 16 problems, the mathlib4 commit, and the harness image.
- All heavy artifacts (mathlib build cache, model weights, transcripts) live on `/mnt/nvme2/atp_runs/` and are reachable through committed symlinks.
- API keys are sourced from a non-committed `.env`; see `.env.example`.

See `arbiter/readme.md` for the arbiter's invariants and `arbiter/plan.md` for the full experiment design.
