# RB-3c Phase 0 — Infrastructure Interruption (2026-07-30 → 2026-07-31)

**This is an infrastructure/runtime observation, not an experimental
result.** No data from this interrupted run should be interpreted as
evidence for or against H1/H2. The pre-registered design
(`rb3c_experimental_design.md`) is unchanged and unaffected.

## What happened

Phase 0's checkpoint audit (`scripts/lim/rb3c_phase0_checkpoint_audit.py`)
was launched at 2026-07-30 20:51 (local) to probe RB-3b's existing
checkpoint-10/20/30/40 in a single session. By the next check, the
process was no longer running, and the machine had been left
unattended overnight without a restart (`LastBootUpTime` unchanged since
2026-07-30 15:03, before the run was even launched).

## Diagnosis

- **The background monitor was stopped cleanly** via `TaskStop` on
  request; this only detaches the log-watching wrapper and does not by
  itself kill the underlying process.
- **The underlying Python process was already gone** — `ps aux` showed no
  matching process at the time of the check. It was not force-terminated
  by this session; it had already exited (or been terminated
  externally) before the check was performed.
- **No Python traceback, exception, or error string appears anywhere in
  the log** (`/tmp/rb3c_phase0.log`, preserved in full, 12,183 bytes,
  last modified 2026-07-30 21:04:13 — about 13 minutes after launch).
  This rules out an in-process crash of the kind seen earlier this
  session (e.g. RB-3b's GPU-memory `RuntimeError`, or the `OSError`
  paging-file failures in RB-1/RB-2) — those always left a Python
  traceback. This interruption did not.
- **Progress reached, inferred from the log**: exactly one `--- checkpoint
  -10 ---` marker (never reached checkpoint-20/30/40), and exactly 24
  occurrences of the `model.generate()`-specific "Both `max_new_tokens`…"
  warning — matching all 24 held-out examples' main generation step for
  checkpoint-10. The process died somewhere after the last example's
  generation but before printing that checkpoint's completion line (no
  "probed 24 examples" message appears), and before any output was
  written (the script only writes its output JSON once, after all four
  checkpoints — nothing was written).
- **GPU state at time of check**: fully idle (38MB / 6144MB used) —
  consistent with the process being gone, not hung.
- **System free RAM at time of check**: 1.85GB / 15.64GB free — low,
  consistent with this session's recurring memory-pressure pattern
  (documented repeatedly across RB-1/RB-2/RB-2b/RB-3/RB-3b). A plausible,
  **not confirmed**, contributing factor: an unattended, multi-hour-idle
  GPU process on a machine under memory pressure is a more exposed
  condition than the short, actively-monitored runs this protocol was
  originally built around. This is offered as a hypothesis for the
  *next* verification step, not a diagnosis.

## Conclusion

Best available reading: an **external termination** (most consistent
with the process being killed by the OS/session environment during an
extended unattended period — e.g. sleep, a session/terminal teardown, or
a resource reclaim — rather than a Python-level crash). This cannot be
confirmed with certainty from the evidence available; it is recorded
honestly as the most likely explanation, not a certainty.

## Artifacts preserved

- `/tmp/rb3c_phase0.log` — full log, unmodified, referenced above.
- `scripts/lim/rb3c_phase0_checkpoint_audit.py` — the Phase 0 script as
  written and launched; unmodified by this interruption.
- **No partial data file was produced** (`docs/lim_runs/
  rb3c_phase0_probe_data.json` does not exist) — the script only writes
  output after all four checkpoints complete, so there is nothing
  partial to preserve from the run itself beyond the log.
- **No registry entries were created or partially written.** Verified
  directly: the training registry's most recent run is still RB-3b's
  `8d265e59-...` and the eval registry's most recent run is still
  RB-3b's `5beeee3c-...` — Phase 0's script never calls either
  registry's write path, so this is expected, not merely assumed.

## Repository state

Confirmed clean: `git status` shows only this note and the (already
-written, not modified) Phase 0 script as new/untracked; no other
uncommitted changes exist anywhere in the working tree. Both will be
committed together so nothing is at risk across the planned restart.

## Design integrity

`rb3c_experimental_design.md` (frozen at commit `76a2708`) is untouched.
The early-stopping rule, hypotheses, metrics, and success criteria are
exactly as approved. Per the standing instruction, this interruption
changes nothing about the design — Phase 0 simply needs to be re-run to
completion after the environment is verified post-restart, using the
identical script and identical checkpoints.

## Next step (not taken yet)

Per instruction: do not restart Phase 0 yet. After the machine restarts,
the standard verification protocol established earlier this session
applies before retrying — confirm free RAM/GPU/commit charge are
healthy, confirm the `lim_venv_lock_hash` and checkpoint files are
unchanged, then re-launch the identical, unmodified Phase 0 script.
