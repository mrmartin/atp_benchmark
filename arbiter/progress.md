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
