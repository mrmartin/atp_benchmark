#!/usr/bin/env bash
# systems/goedel-v2/run.sh — single-attempt entrypoint.
# Stub: the orchestration body lives in systems/goedel-v2/inference.py (step 8).
set -euo pipefail
problem_id=${1:?problem_id required}
sample_idx=${2:?sample_idx required}
cd /workspace
# Wrap via the shared runner so the result schema matches the generalists.
exec python3 -m harness.lib.runner \
    --system goedel-v2 \
    --problem "$problem_id" \
    --sample-idx "$sample_idx"
