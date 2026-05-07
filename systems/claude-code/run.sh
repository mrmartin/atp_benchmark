#!/usr/bin/env bash
# systems/claude-code/run.sh — single-attempt entrypoint.
# Stub: the orchestration body lives in harness/lib/runner.py (step 8).
#
# Usage (inside the claude-code container):
#   bash systems/claude-code/run.sh <problem_id> <sample_idx>
set -euo pipefail
problem_id=${1:?problem_id required}
sample_idx=${2:?sample_idx required}
cd /workspace
exec python3 -m harness.lib.runner \
    --system claude-code \
    --problem "$problem_id" \
    --sample-idx "$sample_idx"
