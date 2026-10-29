---
id: T196
title: Tune retained analytic color inner loops with bounded one-core causal tests
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T193, T194]
priority: highest
branch: ticket/T196-analytic-color-low-core
worktree: <worktree>
artifacts: results/T196/
---

## Context

### Reviewed closure, 2026-10-08

Rank-1 deduplicates active-type eligibility scans without changing arithmetic
or fallback predicates. Exact full-panel parity passed in 12 cells; paired
one-core Roci gains were 1.073–1.243x, advisory under contention. Evidence
`772fac31` passed independent Sol review; fresh exact-source T149 at the same
CPU source passed all eight arms (report-only commit `7899441d`). Merged as
`e1d51082`. No rank-2 candidate, two-core confirmation, precision change or
grain/default selection was required or claimed. Reports live under
`results/T196/20261008_full_correctness/` and
`results/T196/roci_20261008T044501Z_rank1_rates/`.

The author authorized on 2026-10-08 low-core development under prolonged contention.
Start from reviewed main `7bdf58bd`. T195's instrumented g5 cell has color-gradient
work around 0.036–0.038 s versus field-shape around 0.0073 s, not an exclusive
Amdahl attribution. T188's earlier eligibility hoist showed no demonstrated win.
Luna-max implements; Sol-medium independently reviews source/protocol/evidence.

## Scope

Inspect current retained color11/16 hot assembly and actual per-step work first:
feature traversal, eligibility checks, coordinate/SoA loads, accumulation,
polynomial-exp evaluation and spills. Rank at most three concrete removable-work
hypotheses, then implement at most two causal candidates. No new SIMD grain,
global optimizer rewrite, precision/resolution/cutoff change or numerical oracle
relaxation. An exp polynomial/reduction arithmetic change needs a separate D029
declaration and independent validation before eligibility; prefer unchanged math.

Primary integrated arm: pipelined FP32 field SHAPE with analytic color16;
color11 is the retained control. Use existing read-only ordinary groups3/5/7
canonical/general, four starts/25 steps/mix0.5. Fix identical useful work, inputs,
starts and exact per-start/winner scores. Prepared query build stays outside
rates; per-call target preparation and exact finals stay inside. A microkernel
win alone does not justify adoption.

Preregister a small one-core paired baseline/candidate matrix; two physical
cores are a bounded confirmation only after a repeatable one-core direction.
Same pinned cores, rotated short repeats, host load/sibling visibility and
clock records, T118 lock. Contention is expected: publish advisory observations
and session consistency, never reclassify busy records or default-promote near
ties. No prerequisite of whole-host quiet or hardware counter availability.

## Acceptance and working rules

Permanent shared-pose/gradient/exact-final/tail/general-matrix/thread tests;
clean stamps, causal ablation, assembly/code-size evidence and honest nulls;
Sol source/protocol review before rates and final evidence review. Fresh exact
T149 for every final changed CPU candidate before the orchestrator merges it. No default
promotion without a separately reviewed decision.

Dedicated worktree (unique scratch fallback if read-only), private builds
max2 jobs; no shared venv/corpus/sibling edits. Own evaluator tuning only, not
T189 scheduler changes. Keep candidate APIs additive/build-gated and agree any
shared-file boundary with T189 before edits. T159/T197/T198 own scripts/results
only unless separately agreed. Reserve measurement windows through the orchestrator and
T118; no simultaneous benchmark/profile/build on the same host from this team.
Commit runnable checkpoints, notify the orchestrator promptly, no self-merge, no
GitHub push.
