---
id: T195
title: Refresh bounded CPU combo baselines on shared-pose retained kernels
phase: 2
lane: research
status: closed
model: luna
reviewer: sol
depends_on: [T193, T194]
priority: high
branch: ticket/T195-post-cleanup-combo-baseline
worktree: <worktree>
artifacts: results/T195/
---

## Sprint closeout — 2026-10-10

Closed as a reviewed bounded baseline checkpoint, superseded for current
default rates by T210/T211/T218. Historical two-configuration Tachi evidence
and its independent review remain in
the Tachi report `results/T187/current_source_tachi_20261008_R1/README.md`;
the Roci evidence retains its own source and advisory limitations.
The refreshed 24-configuration old-source matrix was not fully run and is
retired, not reported complete. No new host reservation or comprehensive grain
tournament is needed; current performance claims cite current-public evidence.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical context

Current T199-source runner refresh (2026-10-08):
`tickets/T190/measure_current.py --campaign baseline` prepares the complete
24-configuration matrix on Roci or Tachi. See `tickets/T190/CURRENT_RUNNERS.md`.
Historical runner/receipts and measured older-source evidence are unchanged;
new independent review and an explicit quiet measurement window are pending.
No current-source baseline timings were run during readiness preparation.

### Reviewed current-source partial continuation, 2026-10-08

Two existing g5/color16/pipelined-shape configurations now have reviewed
current-T196-source observations on Roci and Tachi through the reused T187
runner. Tachi evidence candidate `892dc6e2` passed final Sol review
(`sol-t195-tachi-evidence-892dc6e2-20261008`) and is merged under
`results/T187/current_source_tachi_20261008_R1/`. Three warmups and eleven
ordinary calls per configuration passed exact score, winner and census
checks; advisory medians were 29.794618 ms canonical and 43.773251 ms
general-asymmetric per 128 pairs. Roci's separate session is recorded under
`results/T187/current_source_roci_20261008_R1_completed/`; no cross-host
speedup ratio is claimed. Query fields were prepared outside rate timers.

The exact current-source extension/cache and source checkpoints were synced,
not rebuilt on Tachi. This is partial, not closure of the original four-arm
by six-cell (24 arm-cell) campaign: the other 22 configurations remain
residual. No source, grain, precision or default was changed. See
`tickets/T195/current_source_readiness.md` for reproduction and provenance.

The author approved a small matched benchmark after cleanup, not another full grain
tournament. Older T184/T187 numbers predate mandatory shared posing. Luna-max
prepares protocol/scripts in parallel with T194; measurements wait for a
reviewed complete cleanup source pin and independent protocol approval.

## Scope

1. Reuse read-only ordinary groups3/5/7, canonical/general matrices and exact
   population/geometry provenance from T184. Bound the arms to color11/16 crossed
   with trajectory analytic and pipelined FP32 field shape, four starts,
   25 steps, mixing0.5 and one physical core. No older color arms, additional
   ISA search, rescore-policy study or hard-reference mining. A representative
   scalar control can be correctness-only; do not expand the timed matrix.
2. Default/minimal build, mandatory shared FP32 pose, optional invariant plan
   and exact scratch OFF. Freeze exact source/build/options before rates.
   Verify exact final scoring, rank/pose/count correctness and handle reuse.
3. Primary throughput is uninstrumented full alignment calls including ordinary
   target preparation and exact per-start/winner scoring, with reusable query
   preparation/field construction outside the repeated timing. Report those
   one-time costs separately. Never subtract diagnostic phase timers to invent
   an alignment rate. Record which final-score/setup components are included.
4. Use T118 same-session paired repeats, rotated arms, actual affinity and host
   lock/quiet/provenance gates on Roci and Tachi. Do not overlap profiles or
   other agents' CPU builds/timing on a measured host. Limited host visibility
   does not prove the hardware is idle. Contended results remain advisory; a bounded
   one-host result is a useful partial handoff, not a reason to wait indefinitely.
5. Add separate diagnostic phase calls on a small representative subset to
   check whether color still dominates after T193. Label observer overhead and
   nested timers honestly. Inspect current hot assembly if available; unavailable
   hardware counters are not evidence of memory bandwidth saturation.
6. Publish paired uncertainty, per-cell winners and ties, exact build/population
   stamps and limitations. Recommend retained default candidates, not an
   automatic numerical/grain/field-policy promotion. Give T189 an evidence-based
   overlap opportunity or a bounded null finding. Feed T159/T162 current strong
   analytic comparator and T190 the retained source, without changing their
   kernels or undertaking their sweeps.

## Acceptance and handoff

Sol protocol review before rates and final evidence review; committed scripts,
raw records and concise report. Any CPU source changes must belong to T194 or
a separately approved follow-on, with fresh exact-source T149. Reuse an existing
canary only after verifying CPU/build source identity. No default changes here.

## Working rules

Dedicated worktree; own tickets/T195 scripts/tests and results/T195,
not shared kernel/API/CMake files. Private builds max two jobs, read-only corpus,
no shared venv mutation. Coordinate host reservations with the orchestrator and T190. No
GitHub push or self-merge.
