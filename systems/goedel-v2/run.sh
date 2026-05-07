#!/usr/bin/env bash
# systems/goedel-v2/run.sh — single-attempt entrypoint.
# Stub: the orchestration body lives in systems/goedel-v2/inference.py (step 8).
set -euo pipefail
problem_id=${1:?problem_id required}
sample_idx=${2:?sample_idx required}
exec python3 /workspace/systems/goedel-v2/inference.py \
    --problem "$problem_id" \
    --sample-idx "$sample_idx"
