"""Shared analysis helpers used by the notebooks.

Notebooks are intentionally thin; the load + compute logic lives here so it
can be unit-tested and so all notebooks see the same data shape.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO / "results" / "raw"
REGISTRY = json.loads((REPO / "problems" / "registry.json").read_text())
SYSTEMS = ["claude-code", "deepseek-v4pro", "goedel-v2"]
K = 16


def load_results() -> list[dict]:
    """Walk results/raw/ and load every per-attempt JSON."""
    out: list[dict] = []
    if not RESULTS_DIR.exists():
        return out
    for p in sorted(RESULTS_DIR.rglob("*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except json.JSONDecodeError:
            continue
    return out


def per_problem_pass_count(results: list[dict]) -> dict[tuple[str, str], int]:
    """Count successes per (system, problem) over all sample_idx."""
    counts: dict[tuple[str, str], int] = {}
    for r in results:
        key = (r["system"], r["problem_id"])
        counts[key] = counts.get(key, 0) + (1 if r.get("verdict") else 0)
    return counts


def pass_at_k(c: int, n: int, k: int) -> float:
    """Unbiased pass@k estimator from the Codex paper, given c successes in n samples."""
    if n - c < k:
        return 1.0
    return 1.0 - float(np.prod(1.0 - k / np.arange(n - c + 1, n + 1)))


def bootstrap_pass_at_k(per_problem_c: list[int], n: int, k: int, n_boot: int = 5000, rng=None) -> tuple[float, float, float]:
    """Resample problems (not attempts) to get a 95 % CI on the mean pass@k.

    Returns (point, lo, hi).
    """
    rng = rng or np.random.default_rng(0)
    arr = np.array(per_problem_c, dtype=int)
    if len(arr) == 0:
        return 0.0, 0.0, 0.0
    point = float(np.mean([pass_at_k(int(c), n, k) for c in arr]))
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(arr), size=len(arr))
        sample = arr[idx]
        boots.append(np.mean([pass_at_k(int(c), n, k) for c in sample]))
    lo, hi = np.quantile(boots, [0.025, 0.975])
    return point, float(lo), float(hi)


def heatmap_matrix(results: list[dict]) -> tuple[np.ndarray, list[str], list[str]]:
    """Return (matrix[n_problems, n_systems], problem_labels, system_labels) of pass-counts out of K."""
    counts = per_problem_pass_count(results)
    problems = [p["id"] for p in REGISTRY["problems"]]
    M = np.zeros((len(problems), len(SYSTEMS)), dtype=int)
    for i, pid in enumerate(problems):
        for j, sys in enumerate(SYSTEMS):
            M[i, j] = counts.get((sys, pid), 0)
    return M, problems, SYSTEMS


def mcnemar_pairs(results: list[dict], k: int = K) -> dict[tuple[str, str], dict]:
    """Pairwise McNemar on per-problem pass@k outcomes (binary)."""
    # Per (system, problem): 1 if pass@k > 0 over the sampled attempts, else 0.
    seen: dict[str, dict[str, int]] = {sys: {} for sys in SYSTEMS}
    for r in results:
        key = (r["system"], r["problem_id"])
        seen[r["system"]].setdefault(r["problem_id"], 0)
        if r.get("verdict"):
            seen[r["system"]][r["problem_id"]] = 1
    out: dict[tuple[str, str], dict] = {}
    pids = [p["id"] for p in REGISTRY["problems"]]
    for i, a in enumerate(SYSTEMS):
        for b in SYSTEMS[i + 1:]:
            b10 = b01 = 0
            for pid in pids:
                xa = seen[a].get(pid, 0)
                xb = seen[b].get(pid, 0)
                if xa == 1 and xb == 0:
                    b10 += 1
                elif xa == 0 and xb == 1:
                    b01 += 1
            # Exact McNemar via binomial(b10+b01, 0.5).
            n = b10 + b01
            if n == 0:
                p = 1.0
            else:
                from math import comb
                k_obs = min(b10, b01)
                tail = sum(comb(n, i) for i in range(k_obs + 1)) / (2 ** n)
                p = min(1.0, 2 * tail)
            out[(a, b)] = {"b10": b10, "b01": b01, "n": n, "p": p}
    return out
