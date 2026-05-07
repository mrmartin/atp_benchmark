"""Per-attempt orchestrator.

Dispatches to a system adapter, captures transcript + result JSON.

Usage (inside a per-system container):
    python /workspace/harness/lib/runner.py \\
        --system claude-code --problem putnam_2022_a3 --sample-idx 0

Output:
    results/raw/{system}/{problem_id}/{sample_idx}.json   (committed, compact)
    /mnt/nvme2/atp_runs/transcripts/{system}/{problem_id}/{sample_idx}.jsonl
                                                          (NOT committed)
    /mnt/nvme2/atp_runs/transcripts/{system}/{problem_id}/{sample_idx}.proof.txt
                                                          (the spliced proof)
"""
from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from pathlib import Path

from .grader import grade, PROBLEMS_BY_ID

REPO = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO / "results" / "raw"
TRANSCRIPTS_ROOT = Path("/mnt/nvme2/atp_runs/transcripts")


def _attempt_paths(system: str, problem_id: str, sample_idx: int) -> dict[str, Path]:
    result_path = RESULTS_DIR / system / problem_id / f"{sample_idx}.json"
    transcript_dir = TRANSCRIPTS_ROOT / system / problem_id
    transcript_dir.mkdir(parents=True, exist_ok=True)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    return {
        "result": result_path,
        "transcript": transcript_dir / f"{sample_idx}.jsonl",
        "proof": transcript_dir / f"{sample_idx}.proof.txt",
        "scratch_dir": transcript_dir / f"{sample_idx}.scratch",
    }


def _adapter(system: str):
    if system == "claude-code":
        from .runners.claude_code import run_attempt  # type: ignore
    elif system == "deepseek-v4pro":
        from .runners.deepseek_v4pro import run_attempt  # type: ignore
    elif system == "goedel-v2":
        from .runners.goedel_v2 import run_attempt  # type: ignore
    else:
        raise ValueError(f"Unknown system: {system!r}")
    return run_attempt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", required=True, choices=["claude-code", "deepseek-v4pro", "goedel-v2"])
    parser.add_argument("--problem", required=True)
    parser.add_argument("--sample-idx", type=int, required=True)
    parser.add_argument("--seed", type=int, default=None, help="optional RNG seed; default = sample_idx")
    args = parser.parse_args()

    problem = PROBLEMS_BY_ID.get(args.problem)
    if problem is None:
        # Allow non-registered "warmup" problems for smoke testing only.
        if not args.problem.startswith("warmup_"):
            print(f"Unknown problem_id: {args.problem!r}")
            return 2
        problem = {"id": args.problem, "set": "warmup"}

    paths = _attempt_paths(args.system, args.problem, args.sample_idx)
    paths["scratch_dir"].mkdir(parents=True, exist_ok=True)

    seed = args.seed if args.seed is not None else args.sample_idx
    started = time.time()
    record: dict = {
        "system": args.system,
        "problem_id": args.problem,
        "set": problem.get("set"),
        "sample_idx": args.sample_idx,
        "seed": seed,
        "started_at": started,
    }

    try:
        attempt = _adapter(args.system)(
            problem=problem,
            sample_idx=args.sample_idx,
            seed=seed,
            paths=paths,
        )
        record.update(attempt)  # adapter contributes proof_text, tokens_*, tool_calls, etc.
        proof_text = attempt.get("proof_text") or ""
        if proof_text.strip():
            paths["proof"].write_text(proof_text)
            verdict = grade(args.problem, proof_text)
            record["verdict"] = verdict.success
            record["lake"] = verdict.to_dict()
        else:
            record["verdict"] = False
            record["lake"] = {"success": False, "stderr_tail": "(no proof produced)"}
    except Exception as exc:  # noqa: BLE001 — record the failure verbatim
        record["verdict"] = False
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["traceback"] = traceback.format_exc()

    record["wall_seconds"] = round(time.time() - started, 2)
    paths["result"].write_text(json.dumps(record, indent=2))
    verdict_str = "PASS" if record["verdict"] else "FAIL"
    print(f"[{verdict_str}] {args.system} / {args.problem} / sample {args.sample_idx} "
          f"({record['wall_seconds']:.1f}s) -> {paths['result']}")
    return 0 if record["verdict"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
