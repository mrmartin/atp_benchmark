#!/usr/bin/env python3
"""Build problems/registry.json from the 16 selected statement files.

Runs once at pre-registration time. Reproducible: the registry is fully
determined by (a) the chosen problem IDs and (b) the byte content of each
copied statement file, both of which are committed.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROBLEMS = REPO / "problems"
PB_SRC_COMMIT = "77ea5a04b28b284f2b95f5c02dd46096bf75d33b"  # PutnamBench main, 2026-04-20
PB_REPO = "trishullab/PutnamBench"
PB_INFORMAL = Path("/mnt/nvme2/atp_runs/putnambench-src/informal/putnam.json")

# Curated selection.  Areas are the dominant tag from informal/putnam.json,
# normalized to one of {algebra, analysis, combinatorics, number_theory}.
# Multi-tagged problems list the chosen primary first.
SELECTION = {
    "main": [
        ("putnam_2022_a2", "algebra"),
        ("putnam_2022_b4", "algebra"),
        ("putnam_2023_a2", "algebra"),
        ("putnam_2022_b6", "analysis"),
        ("putnam_2023_a3", "analysis"),
        ("putnam_2023_b4", "analysis"),
        ("putnam_2022_a5", "combinatorics"),
        ("putnam_2023_a6", "combinatorics"),
        ("putnam_2023_b1", "combinatorics"),
        ("putnam_2022_a3", "number_theory"),
        ("putnam_2023_a4", "number_theory"),
        ("putnam_2023_b5", "number_theory"),
    ],
    "holdout": [
        ("putnam_2024_a2", "algebra"),
        ("putnam_2025_a2", "analysis"),
        ("putnam_2025_a5", "combinatorics"),
        ("putnam_2025_a1", "number_theory"),
    ],
}


def sha256_bytes(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def stmt_lines(p: Path) -> int:
    """Count significant statement lines (skip blank, comment, doc, import)."""
    n, in_doc = 0, False
    for line in p.read_text().splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("import "):
            continue
        if s.startswith("--"):
            continue
        if s.startswith("/-"):
            in_doc = True
            continue
        if in_doc:
            if "-/" in s:
                in_doc = False
            continue
        n += 1
    return n


def main() -> None:
    informal = json.loads(PB_INFORMAL.read_text())
    by_name = {p["problem_name"]: p for p in informal}

    entries = []
    for set_name, items in SELECTION.items():
        for pid, area in items:
            year = int(re.match(r"putnam_(\d{4})_", pid).group(1))
            problem = re.match(r"putnam_\d{4}_([ab]\d)", pid).group(1)
            statement_path = f"problems/statements/{set_name}/{pid}.lean"
            abs_path = REPO / statement_path
            entry = {
                "id": pid,
                "set": set_name,
                "year": year,
                "problem": problem,
                "area": area,
                "tags": by_name[pid].get("tags", []),
                "informal_statement": by_name[pid]["informal_statement"],
                "statement_path": statement_path,
                "statement_lines": stmt_lines(abs_path),
                "statement_sha256": sha256_bytes(abs_path),
                "source": {
                    "repo": PB_REPO,
                    "commit": PB_SRC_COMMIT,
                    "path": f"lean4/src/{pid}.lean",
                },
            }
            entries.append(entry)

    registry = {
        "schema_version": 1,
        "preregistration_date": "2026-05-07",
        "lean_toolchain": "leanprover/lean4:v4.27.0",
        "mathlib_commit": "a3a10db0e9d66acbebf76c5e6a135066525ac900",
        "mathlib_tag": "v4.27.0",
        "putnambench_commit": PB_SRC_COMMIT,
        "stratification": {
            "main": {"algebra": 3, "analysis": 3, "combinatorics": 3, "number_theory": 3},
            "holdout": {"algebra": 1, "analysis": 1, "combinatorics": 1, "number_theory": 1},
        },
        "problems": entries,
    }
    out = PROBLEMS / "registry.json"
    out.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {out} with {len(entries)} entries")


if __name__ == "__main__":
    main()
