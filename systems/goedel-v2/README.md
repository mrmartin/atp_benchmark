# goedel-v2 system runner

- **Agent:** Goedel-Prover-V2 32B, full-precision bf16, **CPU-only** (no quantization, no GPU).
- **Inference:** `transformers` with `torch_dtype=torch.bfloat16, device_map="cpu"`.
- **Pipeline:** the official `scripts/pipeline.sh` (whole-proof generation + Lean compiler verifier-in-loop).
- **Per-attempt budget:** k = 16 independent whole-proof samples, 4 096 tokens each. **No wall-clock cap** — CPU inference is slow (~0.3–1 tok/s); a clipped wall-clock would just cut Goedel off mid-proof. The asymmetry vs the generalists' 200 K/30 min/40 tool-calls is documented in threats-to-validity.
- **Memory:** ~64 GB for bf16 weights; docker-compose sets `mem_limit: 96g`.

## Files
- `Dockerfile` — `FROM atp-harness:latest`; installs torch CPU + transformers + clones `Goedel-LM/Goedel-Prover-V2` at commit `2e9036e1`.
- `inference.py` — wraps the official pipeline and emits the same per-attempt result schema as the generalists.
- `run.sh` — single-attempt entrypoint.
- `runs/` — symlink to `/mnt/nvme2/atp_runs/goedel-v2/` (HF model cache, samples, logs).

## Running

```
docker compose -f harness/docker-compose.yml run --rm goedel-v2 \
    bash systems/goedel-v2/run.sh <problem_id> <sample_idx>
```

## Caveats
- Goedel-V2 was trained against a Lean 4.9 / older mathlib. Our harness pins Lean v4.27.0 + mathlib `a3a10db` (matching PutnamBench). Some generated proofs may reference renamed lemmas; this is a fairness gap **against** Goedel-V2 and is recorded in threats-to-validity.
