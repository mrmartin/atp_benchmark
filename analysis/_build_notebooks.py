"""Generate the five analysis notebooks under analysis/notebooks/.

Run from the repo root:
    python analysis/_build_notebooks.py

Notebooks are kept minimal: each calls into analysis/_lib.py. Run them after
results/raw/ has been populated by harness/lib/runner.py.
"""
from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

OUT = Path(__file__).resolve().parent / "notebooks"
OUT.mkdir(parents=True, exist_ok=True)


def _cell(kind: str, src: str) -> dict:
    cell = {"cell_type": kind, "metadata": {}, "source": [s + "\n" for s in src.splitlines()]}
    if kind == "code":
        cell["outputs"] = []
        cell["execution_count"] = None
    return cell


def write_notebook(name: str, cells: list[dict]) -> None:
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    (OUT / name).write_text(json.dumps(nb, indent=1) + "\n")


HEADER = dedent("""\
    import sys, os
    from pathlib import Path
    sys.path.insert(0, str(Path('.').resolve()))
    from analysis._lib import (
        load_results, per_problem_pass_count, pass_at_k,
        bootstrap_pass_at_k, heatmap_matrix, mcnemar_pairs,
        REGISTRY, SYSTEMS, K,
    )
    results = load_results()
    print(f'loaded {len(results)} attempt(s) across {len(set((r["system"], r["problem_id"]) for r in results))} (system, problem) cells')
""")


def main() -> None:
    # 01 — pass@k with bootstrap CIs
    write_notebook("01_pass_at_k.ipynb", [
        _cell("markdown", "# 01 — pass@k with bootstrap 95 % CIs (over problems)"),
        _cell("code", HEADER),
        _cell("markdown", "## pass@1 / pass@8 / pass@16 by system, with 95 % CI"),
        _cell("code", dedent("""\
            import numpy as np
            from math import inf
            for set_name in ['main', 'holdout']:
                pids = [p['id'] for p in REGISTRY['problems'] if p['set'] == set_name]
                print(f'\\n=== {set_name} ({len(pids)} problems) ===')
                print(f"{'system':<20}{'pass@1':<22}{'pass@8':<22}{'pass@16':<22}")
                for sys in SYSTEMS:
                    per_problem_c = []
                    for pid in pids:
                        c = sum(1 for r in results if r['system']==sys and r['problem_id']==pid and r.get('verdict'))
                        per_problem_c.append(c)
                    line = f'{sys:<20}'
                    for k in (1, 8, 16):
                        p, lo, hi = bootstrap_pass_at_k(per_problem_c, K, k)
                        line += f'{p:.3f} [{lo:.3f}, {hi:.3f}]   '
                    print(line)
        """)),
    ])

    # 02 — heatmap
    write_notebook("02_heatmap.ipynb", [
        _cell("markdown", "# 02 — Per-problem pass-count heatmap (16 problems × 3 systems)"),
        _cell("code", HEADER),
        _cell("code", dedent("""\
            import matplotlib.pyplot as plt
            import numpy as np
            M, problems, sysnames = heatmap_matrix(results)
            fig, ax = plt.subplots(figsize=(6, 0.4 * len(problems) + 1.5))
            im = ax.imshow(M, aspect='auto', cmap='viridis', vmin=0, vmax=K)
            ax.set_xticks(range(len(sysnames))); ax.set_xticklabels(sysnames, rotation=30, ha='right')
            ax.set_yticks(range(len(problems))); ax.set_yticklabels(problems)
            for i in range(M.shape[0]):
                for j in range(M.shape[1]):
                    ax.text(j, i, str(M[i, j]), ha='center', va='center',
                            color='white' if M[i, j] < K // 2 else 'black')
            cb = fig.colorbar(im, ax=ax, label=f'pass-count out of k={K}')
            ax.set_title('Per-problem pass-count')
            fig.tight_layout()
            fig.savefig('analysis/figures/heatmap.png', dpi=150)
            plt.show()
        """)),
    ])

    # 03 — McNemar
    write_notebook("03_mcnemar.ipynb", [
        _cell("markdown", "# 03 — Pairwise McNemar on per-problem pass@k outcomes"),
        _cell("code", HEADER),
        _cell("code", dedent("""\
            for (a, b), v in mcnemar_pairs(results, k=K).items():
                print(f'{a:<20}vs {b:<20}  b10={v["b10"]:>2}  b01={v["b01"]:>2}  n={v["n"]:>2}  p={v["p"]:.4f}')
        """)),
    ])

    # 04 — Cost / efficiency
    write_notebook("04_cost.ipynb", [
        _cell("markdown", "# 04 — Tokens, USD and wall-clock per success"),
        _cell("code", HEADER),
        _cell("code", dedent("""\
            import json
            prices = json.loads(open('analysis/prices.json').read())
            print(f"{'system':<20}{'attempts':<10}{'successes':<10}{'tokens/success':<20}{'sec/success':<12}{'usd/success':<12}")
            for sys in SYSTEMS:
                rs = [r for r in results if r['system'] == sys]
                ok = [r for r in rs if r.get('verdict')]
                total_tok = sum(int(r.get('tokens_in', 0)) + int(r.get('tokens_out', 0)) for r in rs)
                total_sec = sum(float(r.get('wall_seconds', 0)) for r in rs)
                price = prices.get(sys, {})
                in_p = price.get('input_per_mtok_usd') or 0
                out_p = price.get('output_per_mtok_usd') or 0
                total_usd = sum((int(r.get('tokens_in',0)) * in_p + int(r.get('tokens_out',0)) * out_p) / 1e6 for r in rs)
                tps = total_tok / max(1, len(ok))
                sps = total_sec / max(1, len(ok))
                ups = total_usd / max(1, len(ok))
                print(f'{sys:<20}{len(rs):<10}{len(ok):<10}{tps:<20.0f}{sps:<12.1f}{ups:<12.4f}')
        """)),
    ])

    # 05 — Qualitative
    write_notebook("05_qualitative.ipynb", [
        _cell("markdown", "# 05 — Qualitative: representative attempts"),
        _cell("code", HEADER),
        _cell("markdown", "## Pick one representative attempt per (system, problem) — first successful or last failure."),
        _cell("code", dedent("""\
            chosen = {}
            for r in results:
                key = (r['system'], r['problem_id'])
                if key not in chosen or r.get('verdict'):
                    chosen[key] = r
            for (sys, pid), r in sorted(chosen.items()):
                ok = 'PASS' if r.get('verdict') else 'fail'
                tpath = r.get('lake', {}).get('candidate_file', r.get('transcript_path', ''))
                print(f'[{ok}] {sys:<20}{pid:<24}{r.get("wall_seconds", 0):>6.0f}s  {tpath}')
        """)),
    ])
    print(f"Wrote 5 notebooks to {OUT}")


if __name__ == "__main__":
    main()
