#!/usr/bin/env bash
# Pre-push secret scanner. Exits non-zero if it finds a likely API key string
# in any tracked file. Install as .git/hooks/pre-push.
#
# This is a safety net; the primary defense is `.env` being .gitignored.

set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

# Patterns: openrouter (sk-or-), anthropic (sk-ant-), generic openai (sk-),
# huggingface (hf_), github tokens (ghp_/gho_/ghu_/ghs_/ghr_).
patterns=(
  'sk-or-[A-Za-z0-9_-]{20,}'
  'sk-ant-[A-Za-z0-9_-]{20,}'
  'sk-proj-[A-Za-z0-9_-]{20,}'
  'sk-[A-Za-z0-9]{32,}'
  'hf_[A-Za-z0-9]{20,}'
  'gh[pousr]_[A-Za-z0-9]{20,}'
)

# Only scan tracked files (so .env, even if present, is excluded by virtue of being .gitignored).
files=$(git ls-files)

if [ -z "$files" ]; then
  exit 0
fi

violations=0
for pat in "${patterns[@]}"; do
  # -P for PCRE; redirect both streams; allow pattern not to match
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    echo "SECRET MATCH ($pat): $line"
    violations=$((violations + 1))
  done < <(printf '%s\n' "$files" | xargs -d '\n' grep -InP -- "$pat" 2>/dev/null || true)
done

if [ "$violations" -gt 0 ]; then
  echo
  echo "Refusing to push: $violations potential secret(s) found in tracked files."
  echo "Move them to .env (which is .gitignored) and re-stage."
  exit 1
fi

exit 0
