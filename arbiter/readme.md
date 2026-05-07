# arbiter — role and invariants

I (Claude Code, the arbiter) run this experiment. I am **not** a contestant. The Claude Code system that competes runs in its own sealed container with a separate session.

## Invariants

1. **Pre-registration is sacred.** Once `preregistration-v1` is tagged, the 16 problems, the mathlib4 commit, the harness image, and the per-system prompts are frozen. Changes after that point are ablations, not the main run.
2. **Same problems, same grader, comparable tool surface.** All three systems target the same `problems/registry.json` and the same `lake build` verdict. Generalists get the MCP Lean server (REPL + `loogle` + `exact?` + `apply?` + `find`) so their tool surface matches what Goedel-V2 was trained against.
3. **Heavy artifacts off root.** Root is at 91% capacity. Anything multi-GB lives on `/mnt/nvme2/atp_runs/` and is referenced from this repo through committed symlinks.
4. **No secrets in git.** `.env` is ignored from line 2 of `.gitignore`. A pre-push secret-scan hook (`arbiter/scripts/check_no_secrets.sh`) is the safety net.
5. **Independence of attempts.** Each (system, problem, sample_idx) attempt runs in a fresh process with no inter-attempt memory. Temperature 0.8 for the generalists; Goedel-V2's k = 16 are likewise independent samples.
6. **Transcripts are evidence.** Every attempt's full transcript is captured to `/mnt/nvme2/atp_runs/transcripts/{system}/{problem}/{sample_idx}.jsonl`. Don't gc them.
7. **Authority over scope.** Run-time bug fixes that don't touch problems, prompts, or grader can be patched in place. Anything that *could* affect the comparison gets a fresh tag and a documented decision in `decisions.md`.

## Files in this folder

- `claude.md` — CLAUDE.md for future arbiter sessions; loaded automatically
- `readme.md` — this file
- `plan.md` — pinned copy of the experiment design (the user's command-args)
- `progress.md` — running log of what's been done
- `decisions.md` — ADR-style log of every consequential choice and reason
- `scripts/check_no_secrets.sh` — pre-push secret scanner

## When in doubt

Read `decisions.md` first. If the question isn't covered, write a new ADR before acting.
