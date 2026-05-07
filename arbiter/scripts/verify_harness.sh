#!/usr/bin/env bash
# Verify the harness is ready to host the experiment.
#
# Runs the six end-to-end checks from the design (minus the per-system live
# agent attempt — that's deferred since it costs API credits / Goedel weight
# downloads). Output is a brief pass/fail summary suitable for inclusion in
# the report's reproducibility appendix.

set -uo pipefail

repo=$(git rev-parse --show-toplevel)
cd "$repo"

PASS=0
FAIL=0

ok()  { printf '  PASS  %s\n' "$1"; PASS=$((PASS+1)); }
fail(){ printf '  FAIL  %s :: %s\n' "$1" "$2"; FAIL=$((FAIL+1)); }

echo "=== 1. Repo round-trip ==="
if git ls-files | grep -E '^\.env$' >/dev/null 2>&1; then
  fail "1.1 .env not in git" ".env IS tracked"
else
  ok "1.1 .env not tracked"
fi
if bash arbiter/scripts/check_no_secrets.sh >/dev/null 2>&1; then
  ok "1.2 secret scan clean"
else
  fail "1.2 secret scan" "patterns found"
fi
if git ls-remote origin HEAD >/dev/null 2>&1; then
  ok "1.3 origin reachable"
else
  fail "1.3 origin reachable" "ls-remote failed"
fi
if git tag -l | grep -q '^preregistration-v1$'; then
  ok "1.4 preregistration-v1 tag present"
else
  fail "1.4 preregistration-v1 tag" "missing"
fi

echo
echo "=== 2. Lean smoke (in-container) ==="
if docker run --rm \
     -v "$repo:/workspace" \
     -v /mnt/nvme2/atp_runs:/mnt/nvme2/atp_runs \
     atp-harness:latest \
     bash -c 'cd /workspace/harness/lean-project && lake build AtpHarness 2>&1 | tail -3' \
   | tee /tmp/verify-lean.log | grep -q "Build completed successfully"; then
  ok "2.1 lake build AtpHarness"
else
  fail "2.1 lake build" "see /tmp/verify-lean.log"
fi

echo
echo "=== 3. MCP smoke (in-container, all 8) ==="
if docker run --rm \
     -v "$repo:/workspace" \
     -v /mnt/nvme2/atp_runs:/mnt/nvme2/atp_runs \
     atp-harness:latest \
     python3 /workspace/harness/mcp-lean-server/tests/test_smoke.py \
   | tee /tmp/verify-mcp.log | tail -3 | grep -q "All 8 smoke tests passed"; then
  ok "3.1 8 MCP smoke tests"
else
  fail "3.1 MCP smoke" "see /tmp/verify-mcp.log"
fi

echo
echo "=== 4. Container smokes (per-system version checks) ==="
if docker run --rm atp-claude-code:latest claude --version 2>&1 | grep -q "Claude Code"; then
  ok "4.1 claude --version"
else
  fail "4.1 claude --version" "no match"
fi
if docker run --rm atp-deepseek-v4pro:latest opencode --version 2>&1 | head -1 | grep -qE '^[0-9]+\.[0-9]+'; then
  ok "4.2 opencode --version"
else
  fail "4.2 opencode --version" "no semver match"
fi
if docker run --rm atp-goedel-v2:latest python3 -c "import torch, transformers; print(torch.__version__, transformers.__version__)" 2>&1 | grep -q "+cpu"; then
  ok "4.3 goedel-v2 torch+transformers (CPU)"
else
  fail "4.3 goedel-v2 deps" "missing torch+cpu / transformers"
fi
if docker run --rm atp-goedel-v2:latest git -C /opt/goedel-prover-v2 rev-parse HEAD 2>&1 | grep -q "^2e9036e1"; then
  ok "4.4 goedel-prover-v2 pinned commit"
else
  fail "4.4 goedel commit" "wrong"
fi

echo
echo "=== 5. End-to-end on a non-registered warmup problem ==="
echo "  SKIPPED — defer to first real run; would consume API credits / Goedel weights (~64 GB)"

echo
echo "=== 6. Disk budget ==="
root_used=$(df -B1 / | awk 'NR==2 {print $3}')
nvme_used=$(df -B1 /mnt/nvme2 | awk 'NR==2 {print $3}')
echo "  /          used: $((root_used / 1024 / 1024 / 1024)) GiB"
echo "  /mnt/nvme2 used: $((nvme_used / 1024 / 1024 / 1024)) GiB"
root_pct=$(df / | awk 'NR==2 {gsub("%",""); print $5}')
if [ "$root_pct" -lt 95 ]; then
  ok "6.1 root fill below 95 % ($root_pct %)"
else
  fail "6.1 root fill" "$root_pct %"
fi

echo
echo "=== Summary ==="
printf '  %d pass, %d fail\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
