"""Goedel-Prover-V2 single-sample inference (CPU, bf16, no quantization).

Contract (matches harness/lib/runners/goedel_v2.py):
    --problem <id>
    --sample-idx <n>
    --seed <int>
    --statement-path <path-to-registered-Lean-statement>
    --informal <english-statement>
    --proof-out <path-for-the-final-proof-text>
    --transcript-out <path-for-jsonl-transcript>
    --scratch-dir <writable-dir-for-this-attempt>

What it does (one sample):
    1. Loads Goedel-Prover-V2-32B at bfloat16 on CPU (cached at $HF_HOME).
    2. Builds a prompt from the registered statement.
    3. Generates up to 4096 tokens at temperature 0.8 with seed = --seed.
    4. Splices the candidate into the statement and runs `lake env lean`.
    5. If errored and rounds remain, feeds the diagnostic back and regenerates.
    6. Writes the best candidate (preferring the first successful one) to
       --proof-out and a per-sample summary to <scratch_dir>/summary.json.

Caveats:
    * Loading 32B bf16 on CPU is ~5-10 min and ~64 GB RAM. For batch runs the
      caller may want to keep this process alive across samples; this script
      is single-shot for the simple per-sample contract.
    * Goedel-V2 was trained against an older mathlib than our pinned
      v4.27.0 a3a10db; some lemma names may differ. Verifier-in-loop helps
      but does not eliminate this asymmetry. Documented in
      threats-to-validity.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

REPO = Path("/workspace")
LEAN_PROJECT = REPO / "harness" / "lean-project"

# Goedel-V2 model IDs (set by env to override; default 32B per ADR-003).
MODEL_ID = os.environ.get("GOEDEL_MODEL_ID", "Goedel-LM/Goedel-Prover-V2-32B")

MAX_TOKENS_PER_SAMPLE = int(os.environ.get("GOEDEL_MAX_TOKENS", "4096"))
VERIFIER_ROUNDS = int(os.environ.get("GOEDEL_VERIFIER_ROUNDS", "3"))


def _build_prompt(statement: str, informal: str, prior_attempt: str = "", prior_error: str = "") -> str:
    """Goedel-style prompt. The official pipeline includes the formal statement
    (with `sorry`) and instructs the model to output a complete Lean 4 proof."""
    parts = []
    if informal:
        parts.append(f"-- Informal statement:\n-- {informal}\n")
    parts.append("-- Complete the following Lean 4 + mathlib4 proof. Output ONLY the proof text\n"
                 "-- that should replace `sorry`; do not echo the statement.\n\n")
    parts.append(statement.strip() + "\n")
    if prior_attempt:
        parts.append(f"\n-- Prior attempt FAILED with diagnostic:\n-- {prior_error.strip()[:1500]}\n")
        parts.append(f"-- Your prior text was:\n-- {prior_attempt.strip()[:1500]}\n")
        parts.append("-- Try again, accounting for the error above.\n")
    return "".join(parts)


def _extract_proof(generation: str) -> str:
    """Extract the proof body from a generation. The model is instructed to
    output only the replacement for `sorry`; we trim common framing."""
    text = generation.strip()
    # Strip Markdown code fences if the model added them.
    text = re.sub(r"^```(?:lean4?)?\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def _splice(statement: str, proof: str) -> str:
    head, _, tail = statement.rpartition("sorry")
    return head + proof + tail


def _verify(spliced_path: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        ["lake", "env", "lean", "--", str(spliced_path)],
        cwd=str(LEAN_PROJECT),
        capture_output=True,
        text=True,
        timeout=1200,
    )
    success = proc.returncode == 0 and "error:" not in proc.stderr
    diag = (proc.stderr or "") + ("\n" + proc.stdout if proc.stdout else "")
    return success, diag


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", required=True)
    ap.add_argument("--sample-idx", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--statement-path", required=True)
    ap.add_argument("--informal", default="")
    ap.add_argument("--proof-out", required=True)
    ap.add_argument("--transcript-out", required=True)
    ap.add_argument("--scratch-dir", required=True)
    args = ap.parse_args()

    statement = Path(args.statement_path).read_text()
    scratch = Path(args.scratch_dir)
    scratch.mkdir(parents=True, exist_ok=True)
    transcript: list[dict[str, Any]] = []
    started = time.time()

    # Lazy import torch + transformers (avoid importing if user is just doing --help).
    import torch  # noqa: WPS433
    from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: WPS433

    transcript.append({"event": "load_start", "model_id": MODEL_ID, "ts": time.time()})
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, torch_dtype=torch.bfloat16, device_map="cpu", low_cpu_mem_usage=True,
    )
    model.eval()
    transcript.append({"event": "load_done", "elapsed_s": round(time.time() - started, 2)})

    torch.manual_seed(args.seed)
    best_proof = ""
    best_success = False
    best_diag = ""
    tokens_in = tokens_out = 0
    samples_attempted = 0
    samples_ok = 0

    prior_attempt = prior_error = ""
    for round_idx in range(VERIFIER_ROUNDS):
        prompt = _build_prompt(statement, args.informal, prior_attempt, prior_error)
        inputs = tokenizer(prompt, return_tensors="pt")
        tokens_in += int(inputs["input_ids"].shape[-1])
        gen_started = time.time()
        with torch.no_grad():
            out_ids = model.generate(
                **inputs,
                max_new_tokens=MAX_TOKENS_PER_SAMPLE,
                do_sample=True,
                temperature=0.8,
                top_p=0.95,
            )
        new_tokens = out_ids.shape[-1] - inputs["input_ids"].shape[-1]
        tokens_out += int(new_tokens)
        generation = tokenizer.decode(out_ids[0, inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
        proof = _extract_proof(generation)
        samples_attempted += 1
        spliced_path = scratch / f"round_{round_idx}.lean"
        spliced_path.write_text(_splice(statement, proof))
        success, diag = _verify(spliced_path)
        transcript.append({
            "event": "round",
            "round": round_idx,
            "tokens_new": int(new_tokens),
            "gen_seconds": round(time.time() - gen_started, 2),
            "verifier_success": success,
            "diagnostic_tail": diag[-1500:] if not success else "",
            "proof_len": len(proof),
        })
        if success:
            samples_ok += 1
            best_proof, best_success, best_diag = proof, True, diag
            break
        # Otherwise feed back into the next round.
        prior_attempt, prior_error = proof, diag
        if not best_proof:
            best_proof, best_diag = proof, diag

    Path(args.proof_out).write_text(best_proof)
    Path(args.transcript_out).write_text("\n".join(json.dumps(e) for e in transcript) + "\n")
    summary = {
        "model_id": MODEL_ID,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "samples_attempted": samples_attempted,
        "samples_verified_ok": samples_ok,
        "best_success": best_success,
        "wall_seconds": round(time.time() - started, 2),
    }
    (scratch / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
