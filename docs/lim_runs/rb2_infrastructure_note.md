# RB-2 — Infrastructure Note (recurrence of the RB-1 memory-pressure pattern)

**Classification: infrastructure failure (operating-system memory
pressure), not a model, training-pipeline, or evaluation-code defect.**
Same signature as `rb1_infrastructure_failure_log.md`, recurring after
several more hours of model-loading subprocesses in this session.

## What happened

While running RB-2 (LoRA rank sweep, 6 configs: r∈{8,16,32} × seed∈{42,123}),
a real methodology issue was found and fixed first (see
`rb2_results.md` for the full account): all 6 initial evaluations, at a
fixed `max_new_tokens` (160, then 300), showed 100% of generations hitting
the token cap without completing, confounding the rank comparison. Fixed
with a balanced-JSON stopping criterion in `run_evaluation.py` (stops
generation once a syntactically-complete top-level JSON object is
produced, applied identically to every checkpoint) plus a 512-token safety
cap. Re-running all 6 configs with this corrected methodology:

| Config | Status |
|---|---|
| r=8, seed=42 | Done (`871a2375-...`) |
| r=8, seed=123 | Done (`3cd8c1ee-...`) |
| r=16, seed=42 | Done (`71504999-...`) |
| r=16, seed=123 | **Blocked** — silent process death, then confirmed segfault (exit 139) on retry |
| r=32, seed=42 | Not yet attempted |
| r=32, seed=123 | Not yet attempted |

## Resource state at failure

| Check | 1st attempt (silent death) | 2nd attempt (confirmed segfault) |
|---|---:|---:|
| Free physical RAM | ~2.71 GB | ~2.25-2.30 GB (declining further) |
| GPU free VRAM | 5,789 MiB of 6,144 (idle) | not re-checked, GPU not implicated in attempt 1 either |

Both failures occurred at the identical point in execution: immediately
after Unsloth's own initialization banner, before model-loading progress
begins — the exact signature of RB-1's original blocker (`OSError` 1455 /
segfault at `safetensors` memory-mapped load, `rb1_infrastructure_failure_
log.md`).

## Owner decision

Same remedy as RB-1: owner will free memory / restart, then direct a
retry. Per that established protocol, before retrying:
1. Verify free RAM, GPU VRAM, commit charge, page file usage.
2. Confirm `lim_venv_lock_hash` is byte-identical to its value in the
   completed r=8/r=16 runs (environment parity).
3. Retry the exact same 3 remaining configs (r=16/seed=123, r=32/seed=42,
   r=32/seed=123) with identical settings — no code or configuration
   change, since this is confirmed infrastructure, not software.

Status: **awaiting owner's restart before retry.**
