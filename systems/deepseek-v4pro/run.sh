#!/usr/bin/env bash
# systems/deepseek-v4pro/run.sh — single-attempt entrypoint.
# Stub: the orchestration body lives in harness/lib/runner.py (step 8).
set -euo pipefail
problem_id=${1:?problem_id required}
sample_idx=${2:?sample_idx required}
: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY must be set (env_file from compose)}"
cd /workspace
exec python3 -m harness.lib.runner \
    --system deepseek-v4pro \
    --problem "$problem_id" \
    --sample-idx "$sample_idx"
