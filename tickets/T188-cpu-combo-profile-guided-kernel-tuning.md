---
id: T188
title: Bounded profile-guided CPU combo micro-optimizations
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T146, T153]
priority: high
branch: ticket/T188-combo-kernel-tuning
worktree: <worktree>
artifacts: results/T188/
---

## Context

Parallel execution amendment, 2026-10-07: consume independently Sol-approved
T187 diagnostic attribution `1653cd45` (raw `05a0b328`), without waiting for its
missing hardware-counter residual to close. T188 now owns the bounded COLOR
evaluator invariant-work ablation only. T191 owns the shared-pose contract;
T192 owns exact-final scratch/reuse. Those are sibling tasks, not closed-ticket
prerequisites; coordinate their early committed interfaces. Main baseline is
`866e1e50`. Advisory single-core comparisons are acceptable under the author's
T191 timing guidance; retain actual grade and do not claim all-core wins.

### Active execution scope

1. Audit and hoist only pose-independent color matrix support/active interaction
   metadata and ISA capability checks into immutable preparation. Preserve
   pose-dependent finite/range/eligibility checks, masks, fallback, term counts,
   general matrix behavior and exact evaluation. The matrix-screen diagnostic
   includes pair checks: its 23.65% median child fraction is NOT a removable
   matrix-predicate fraction or a predicted speedup.
2. One causal change first, strongest baseline unchanged elsewhere; do not
   sweep widths, field policies, polynomial exp or reductions. Invariant plans
   must own/validate matrix/query/count snapshots and never become stale when
   callers mutate arrays. No per-step planning or unused preparation work.
3. Prepare a new color-invariant-plan helper TU/header and independent tests
   first. T191 owns shared `color_scalar.cpp`, public API and pose-related
   `color_conformer_kernel.cpp` edits. Agree a committed integration handoff;
   no simultaneous edits of those files and no independent quaternion/frame
   implementation. Consume T191's shared FP32 reduced-pose seam when ready.
4. Permanent eligibility/mask parity tests for canonical/general coefficients,
   widths/zeros/extremes, unsupported fallback, tails, reused/concurrent handles,
   caller mutation/lifetime and pose-dependent changes. Independent exact
   scoring/reference uses the shared T191 pose, not a separately rebuilt one.
5. Benchmark isolated invariant hoist ON/OFF using the SAME shared-pose
   implementation and numeric semantics. Matched one-core full combo on small
   canonical and larger general cells with color11 first, color16 confirmation.
   Query/plan/field prep outside alignment timing and reported separately.
   Commit source/protocol before Sol review and timing. Preserve advisory
   status under known contention; T118 lock/cwd/affinity/stamps still required.
6. Fresh exact-source T149 and Sol final evidence review before merge, including
   composed integration. Multicore confirmation deferred to host availability;
   no shipping default or unmeasured whole-machine gain. A bounded negative
   is valid and should not retain losing production machinery.

### Original planning context (superseded where narrowed above)

Follow T187 attribution rather than a broad tuning sweep. The author approved this
sequence 2026-10-07. Luna-max implements bounded candidates; Sol-medium reviews.
T186 scaling evidence should inform choices when available, without requiring
all host residuals to finish before a justified single-core experiment starts.

## Scope

Select at most three T187-supported changes with stated Amdahl ceilings and
causal ablations. Candidates include field address/load scheduling, pipeline
depth/register spills, analytic color occupancy/reductions, transformed-
coordinate reuse, optimizer setup and exact-final redundant work. Preserve
stored-gradient field sampling, spacing, precision, full combo updates and
exact per-start/final semantics. No new AVX512/XMM/mixed-grain sweep unless
attribution specifically justifies one and scope is reviewed first.
Compare each alone, then a bounded composition with unchanged arithmetic or
explicit D029-declared changes. Confirm whole-combo one-core rates and selected
T186 physical-core/SMT points: a one-core win that regresses the machine is not
a universal default. Query construction stays outside primary rates.

## Deciding measurement

Matched whole-combo rate gains above the applicable host floor, causal isolated
and composed results, and selected multicore confirmation. A negative result
closes the measured hypothesis without shipping losing machinery.

## Acceptance

Independent oracle/gradient/tie regression tests and source/protocol/evidence
Sol reviews; T118 stamped clean builds and rotated paired repeats; fresh exact
integrated T149 for CPU codegen merge. No default or accuracy-budget changes.

## Traps

Do not multiply isolated gains, time build with a tiny library, weaken exact
final checks, or infer speed from counters. Preserve noinline/separate-TU
codegen boundaries and multi-ISA safety.

## Bounded execution checkpoint (2026-10-07)

Source/protocol/runner and final timing evidence passed independent Sol-medium
review. Tachi evidence is committed as `16f3c639`, under
`results/T188/tachi_20261007T180957Z_{g3,g7}/`. All eight matched plan ON/OFF
comparisons preserved score/pose bytes and diagnostics. ON was directionally
0.8–3.8% slower, but every effect was below the pinned 7.9349% host floor and
all cells were advisory because the host was not quiet. The supported result
is **no demonstrated benefit**, not a definitive or universal slowdown.

Keep the hoist an explicitly optional research ablation; do not promote it as
a throughput default. The shared immutable query preparation belongs to the
mandatory T191 contract and is not itself disproved by this ablation. Exact
composed-source T149 and final integration approval were satisfied at
`a96d20b0`, merged to main. The exact-source report is
`results/T149/premerge/20261007-cpu-shared-pose-integration.json`; all eight
arms were byte-identical. This closes the bounded invariant-hoist hypothesis,
without promoting a throughput default or claiming a universal slowdown.

## Multicore closeout confirmation (2026-10-09)

The author confirmed this ticket remains closed after the independently reviewed
composed worker-owned factorial. Roci paired full-throughput ratios for plan
only were 0.983837 at 8 physical cores (raw T118 decision) and 0.977668 at 24
(advisory); both plan and scratch together were 0.989506 and 0.984164. All20
score/GID/MID outputs matched exactly within host. See
`results/T207/composed_highcore_20261009/README.md` and `REVIEW.md`.

No demonstrated whole-combo benefit: retain the invariant-plan switch OFF.
The 16-core factorial was interrupted and is not evidence;
missing repetitions do not block this bounded closeout or warrant more runs.
This does not disprove mandatory shared-pose/query preparation. Optional
ablation code removal is separate cleanup, not performed by this closeout.

## Working rules

Dedicated worktree/private max2-job builds, shared read-only corpus,
committed scripts/results, no sibling/shared-env modifications. Coordinate
with T186 before shared optimizer edits. Scoped Tachi sync; reviewed handoff, never self-merge.
