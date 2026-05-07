# progress

A running log of arbiter actions. Newest at the top.

## 2026-05-07

- Repo initialized at `git@github.com:mrmartin/atp_benchmark.git`. `.gitignore` written first with `.env` on line 2; verified `.env` is ignored before the first stage.
- Local git identity set on this repo only (`user.name=mrmartin`, `user.email=martin@martintech.co.uk`); global git config untouched.
- Arbiter scaffolding written: `arbiter/{readme.md, claude.md, plan.md, progress.md, decisions.md, scripts/check_no_secrets.sh}`.
- Plan approved (`/home/martin/.claude/plans/staged-wobbling-wolf.md`); a copy is pinned at `arbiter/plan.md`.
- NVMe scaffolding: created `/mnt/nvme2/atp_runs/{claude-code,deepseek-v4pro,goedel-v2,lean-build,transcripts,putnambench-src,holdout-src}` and committed five symlinks pointing into them.
- `arbiter/host_setup.md` documents the Docker `data-root → /mnt/nvme2/docker` migration the user must run with sudo before image builds in step 7.
- Lean toolchain pinned to `leanprover/lean4:v4.25.1`; mathlib4 pinned at commit `77b45269e0888a839059d6678a32631c8066da21` (tag v4.25.1) in `harness/lean-project/lakefile.toml`.
- `harness/setup.sh` symlinks `.lake → /mnt/nvme2/atp_runs/lean-build`, runs `lake update` + `lake exe cache get`, then `lake build`. Smoke build of `AtpHarness.Smoke` succeeded (3019 jobs); 6.6 GB landed on NVMe, root unchanged.
- Step 10 (report stub) and analysis/prices.json placeholders also written.
- Toolchain bumped from v4.25.1 to v4.27.0 to match PutnamBench's own pin (commit 77ea5a04, 2026-04-20). mathlib re-pinned at `a3a10db0e9d6…` (tag v4.27.0). Smoke build of `AtpHarness.Smoke` passes (3068 jobs, 7.3 GB on NVMe).
- Step 5 — pre-registration: 16 problems chosen and copied into `problems/statements/{main,holdout}/`. 12 main from Putnam 2022/2023 stratified 3 algebra / 3 analysis / 3 combinatorics / 3 number-theory; 4 holdout from Putnam 2024/2025 stratified 1 each. All 16 type-check via `lake env lean -- <file>` against the pinned mathlib (sorry-only warnings). Combinatorics holdout swapped from `putnam_2025_a3` → `putnam_2025_a5` because `2025_a3` triggered a `List.Chain` deprecation/type-mismatch warning in v4.27.0 (see ADR-010).
- `problems/registry.json` (16 entries with sha256, area, year, source commit, statement_lines) and `problems/selection_criteria.md` (filters, stratification, rejection log) written. Pre-registration ready to commit + tag.
