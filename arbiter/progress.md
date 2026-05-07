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
- Pre-registration committed and tagged `preregistration-v1` at `bd1cc45`.
- Step 6 — MCP Lean server: `harness/.venv` provisioned with `lean-interact 0.11.2` and `mcp 1.27.0`. Package at `harness/mcp-lean-server/` (editable installed). Implements `repl_open / repl_step / repl_close / loogle / exact_q / apply_q / mathlib_find / lean_check / mathlib_search` (last is documented fallback). Real REPL backed by `LocalProject(harness/lean-project)`; mathlib preloaded once per process and reused across sessions via env snapshots. All 8 smoke tests in `harness/mcp-lean-server/tests/test_smoke.py` pass against the pinned mathlib.
- Docker `data-root` relocated to `/mnt/nvme2/docker` by user (per `arbiter/host_setup.md`). Confirmed via `docker info` before image builds.
- Step 7 — Docker harness sealed: built four images on /mnt/nvme2/docker.
  - `atp-harness:latest` (4.13 GB / 915 MB compressed): python:3.12-slim + ripgrep + git + elan with Lean v4.27.0 toolchain pre-installed + the `atp-mcp-lean` MCP server.
  - `atp-claude-code:latest` (4.9 GB): + Node 20 + `@anthropic-ai/claude-code` v2.1.132. Subscription auth works via bind-mounted `~/.claude/` and `~/.claude.json`.
  - `atp-deepseek-v4pro:latest` (5.76 GB): + Node 20 + `opencode-ai@1.14.24`. `.env` env_file injects `OPENROUTER_API_KEY` correctly.
  - `atp-goedel-v2:latest` (5.51 GB): + torch 2.6.0+cpu + transformers 4.46.0 + accelerate + Goedel-Prover-V2 cloned at commit `2e9036e1`. CUDA disabled by design.
  - Smoke checks: `claude --version`, `opencode --version`, `python -c "import torch, transformers"`, `lean --version`, `lake build AtpHarness` (3076 jobs OK from /workspace via bind-mount).
- Per-system READMEs, `prompt.txt`, `skill.md` (Claude Code), `opencode.config.json`, and `run.sh` stubs written. Runner body in step 8.

---

## Continuation — 2026-05-07 afternoon

- Step 8 — runner scaffolding committed at `cd9d30d`: `harness/lib/{runner,grader,budget}.py`, per-system adapters under `harness/lib/runners/`, `systems/goedel-v2/inference.py`, `.mcp.json`. Imports clean from the host venv.
- During step 8 first attempt: parallel rebuilds filled `/` to 96 % and crashed the session. Root cause traced to the **system containerd snapshotter** (separate from Docker's `data-root`) keeping rootfs at `/var/lib/containerd`. ADR-011 + `arbiter/host_setup.md §1b` document the fix; user applied it (set `root = /mnt/nvme2/containerd` in `/etc/containerd/config.toml`, restarted both daemons).
- Dockerfile follow-ups committed: non-root `agent` user (UID 1000) so bind-mount writes don't end up root-owned; `lean-interact` import-time cache dir made world-writable at image build (the actual REPL cache redirected to `/mnt/nvme2/atp_runs/lean-interact-cache` via `ATP_MCP_LEAN_CACHE_DIR`).
- Re-built four images post-relocation in parallel; `/` stayed at 39 GB free, `/mnt/nvme2` grew by 6 GB. All 8 MCP smoke tests pass **inside the harness Docker container**, confirming the runtime path the experiment actually uses.

- Step 9 — analysis scaffold committed at `7c36237`. `analysis/_lib.py` provides shared load/compute (pass@k unbiased estimator + bootstrap CI by problem-resampling, heatmap matrix, exact McNemar). Five notebooks under `analysis/notebooks/` are thin wrappers regenerable from `analysis/_build_notebooks.py`. Verified the lib runs cleanly against an empty `results/raw/` (returns zero-fill structures, no crash).
- Step 11 — final verification: `arbiter/scripts/verify_harness.sh` runs 11 explicit checks (repo round-trip + .env-not-tracked + secret scan, in-container `lake build` + 8 MCP smoke tests, four version checks across the three system images, root-disk budget). **11 pass, 0 fail.** Test 5 (end-to-end attempt on a non-registered warmup problem) is explicitly skipped — it would consume API credits and trigger the ~64 GB Goedel-V2 weight download; deferred to the first real run. Full log archived at `arbiter/verify_harness_log.txt`.
- Tagged `harness-ready` to mark this milestone (the experiment can now be RUN; preregistration-v1 marks the immutable problem freeze).

## Harness-ready — 2026-05-07

**Completed:** steps 1–7 (and step 10) of the plan. Pre-registration tagged `preregistration-v1` at commit `bd1cc45`; harness sealed at commit `bcd50a6`. All on `main` at `git@github.com:mrmartin/atp_benchmark.git`.

**Open tasks (resume here):**
- Step 8 — per-system runners (`harness/lib/runner.py` + `harness/lib/budget.py` + `harness/lib/grader.py`; `systems/goedel-v2/inference.py`).
- Step 9 — analysis notebooks (`analysis/notebooks/01..05.ipynb`).
- Step 11 — final 6-test verification + `tag preregistration-final`.

**Background state worth noting on resume:**
- `harness/.venv` is provisioned on the host (lean-interact 0.11.2, mcp 1.27.0, atp-mcp-lean editable).
- 7.3 GB mathlib build cache at `/mnt/nvme2/atp_runs/lean-build`. Lake project at `harness/lean-project` builds end-to-end.
- All four Docker images live at `/mnt/nvme2/docker` (data-root relocated): `atp-harness`, `atp-claude-code`, `atp-deepseek-v4pro`, `atp-goedel-v2`. Re-pull or rebuild not needed unless their Dockerfiles change.
- Goedel-Prover-V2 32B bf16 weights are **not yet downloaded**. ~64 GB. Should land in `/mnt/nvme2/atp_runs/goedel-v2/hf-cache/` on first inference run.
- No residual background processes (only `dockerd` is up, which is correct).

**To resume:**
1. `cd /home/martin/ATP_agent_Putnam_experiment && git pull --tags` (already in sync, but doesn't hurt).
2. Read `arbiter/progress.md` (this file) and `arbiter/decisions.md` (ADR-001 through ADR-010).
3. Pick up at step 8: write `harness/lib/runner.py` and the per-system runner adapters.
