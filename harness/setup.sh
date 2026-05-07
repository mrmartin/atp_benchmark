#!/usr/bin/env bash
# Bootstrap the harness Lean project: link the build cache onto NVMe and pull
# mathlib oleans so `lake build` is fast.
#
# Idempotent. Safe to re-run.

set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
project="$repo_root/harness/lean-project"
nvme_lake="/mnt/nvme2/atp_runs/lean-build"

if [ ! -d "$project" ]; then
  echo "Missing harness/lean-project; aborting."
  exit 1
fi

if [ ! -d "$nvme_lake" ]; then
  echo "Missing $nvme_lake; create it with: mkdir -p $nvme_lake"
  exit 1
fi

cd "$project"

# Symlink .lake onto NVMe so build artifacts and downloaded packages live off /.
if [ -e .lake ] && [ ! -L .lake ]; then
  echo ".lake exists and is not a symlink; refusing to clobber. Move it manually."
  exit 1
fi
ln -sfn "$nvme_lake" .lake

# Resolve toolchain (elan reads ./lean-toolchain automatically when invoked here)
echo "Toolchain: $(cat lean-toolchain)"
lean --version

# Fetch the manifest and download mathlib oleans (cache get pulls pre-built oleans).
lake update
lake exe cache get

# Smoke build
lake build AtpHarness
echo "Lean smoke build OK"
