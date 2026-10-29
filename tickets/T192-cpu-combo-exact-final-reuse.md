---
id: T192
title: Reuse prepared pose and scratch in exact CPU combo final scoring
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T146, T153]
priority: high
branch: ticket/T192-exact-final-reuse
worktree: <worktree>
artifacts: results/T192/
---

## Context

The author requested parallel exact-final reuse work alongside T191 on 2026-10-07.
Reviewed T187 attribution `1653cd45` records per-start final and winner scoring
diagnostics of 12.56%/3.16% median for pipelined-field/color11; these are
instrumented diagnostic fractions, not additive production shares or Amdahl
ceilings. Main baseline `866e1e50`. Luna-max implements, independent Sol-medium
reviews. T191 owns unified FP32 reduced-frame pose; consume its committed seam,
not a competing transform/numerical contract. No all-core timing prerequisite.

## Scope

1. Identify allocation, pose/layout preparation and scratch repeated during
   exact per-start and winner scoring. Implement a bounded reusable worker-local
   scratch/fixed-pose scorer helper. Every score remains exact under the declared
   T191 contract and source reduction order; no field approximation for final
   scoring, reassociation, polynomial exp substitution or reduced start count.
2. Reuse the already prepared FP32 matrix/reduced translation from T191.
   FP64 scoring arithmetic may consume it, but cannot renormalize/reconstruct
   the quaternion independently. Handle the final pose AFTER the last optimizer
   update, not a stale pre-update gradient pose. Retain physical/reduced type
   distinctions, converted color decay and normalization conventions.
3. Initial ablation reuses scratch/transformed-point preparation but preserves
   all four per-start scores and the distinct winner score evaluation/census.
   Do not silently eliminate the winner evaluation, cache an approximate score,
   change per-start selection/tie order or fake old evaluation counters. Any
   later score-result cache needs separate reviewed scope and truthful counters.
4. Own new exact-final helper cpp/hpp and tests. T191 owns shared optimizer/API
   and pose-related kernel edits; coordinate a committed narrow integration
   patch/handoff, no sibling edits or independent optimizer loop. T188 owns
   color invariant plans, not this helper. Reusable storage is private per
   worker/trajectory batch; independent immutable query state may be shared.
5. Permanent tests for each start/winner pose, exact matrix/score/winner
   equality versus SAME shared-pose uncached scorer, last-step pose invalidation,
   stable ties, masks/odd tails/empty or general color planes, repeated calls,
   mutable input rejection/lifetime and concurrent handles. Color11/16 and
   field/analytic shape final scoring must use identical exact final semantics.
6. Commit and preregister one-core scratch-reuse ON/OFF with shared-pose and
   color-plan settings held fixed. Prefer pipelined-field/color11 and a general
   larger color case, color16 bounded confirmation; no giant tournament.
   Report total combo calls plus separately labelled final-phase attribution
   and allocations/prep. All query/field build outside primary alignment timing.
   Small one-core advisory timing under existing load is explicitly acceptable;
   record T118 context/grade and paired uncertainty without universal claims.

## Deciding measurement

Unchanged exact final scores/poses/winners and counters under the shared-pose
contract, with measured allocation/preparation reduction and matched full-combo
one-core benefit (or bounded negative). No presumed gain from phase fractions.

## Acceptance

Independent Sol source/protocol review before timing and final evidence review,
D029-labelled T191 baseline semantics, source-identical private builds,
T118 host lock/cwd/affinity/repeat/population/source stamps; fresh exact T149
including composed integration. No fast-math, default or ranked-production
promotion. Multicore confirmation remains explicitly pending if unavailable.

## Traps

The winning start's LAST pose may not be its last evaluated gradient pose.
Cache invalidation, point ordering and FP32 matrix construction must be exact.
Allocation wins on microfixtures need whole-combo comparison. CPU field value
is never an exact final score substitute. Shared scratch creates races.

## Bounded execution checkpoint (2026-10-07)

Source/protocol/runner and final evidence passed independent Sol-medium review.
Results/report are committed as `1547596c`, under
`results/T192/tachi_20261007T181957Z_exact_final_reuse_2afe5e18/`.
All three cells preserved exact score/pose bytes, deterministic winners, and
four per-start plus one distinct winner evaluation. Reuse reduced transformed
point preparation from five passes to four. Permanent helper lifetime/parity
and shared-pose scalar/AVX2 tests also pass on the composed integration.

Matched OFF/ON ratios were 1.0114, 1.0006 and 0.9987; all paired 95% intervals
crossed 1. Every cell was advisory under observed Tachi load. This establishes
structural preparation reuse, but **no demonstrated full-combo speed gain**.
Do not promote scratch reuse as a throughput default on these data. Composed
exact-source T149 and final integration approval passed at `a96d20b0`, merged
to main. Report:
`results/T149/premerge/20261007-cpu-shared-pose-integration.json`; all eight
arms were byte-identical. This closes the bounded scratch-reuse implementation
and measurement without claiming a demonstrated throughput gain.

## Multicore closeout confirmation (2026-10-09)

The author confirmed this ticket remains closed after the independently reviewed
composed worker-owned factorial. Roci paired full-throughput ratios for scratch
reuse only were 1.002180 at 8 physical cores (raw T118 decision) and 0.998957
at 24 (advisory); both optional switches together were 0.989506 and 0.984164.
All20 score/GID/MID outputs matched exactly within host. See
`results/T207/composed_highcore_20261009/README.md` and `REVIEW.md`.

No demonstrated whole-combo benefit: retain scratch reuse OFF. Structural
reuse is not a throughput claim. The interrupted 16-core factorial and missing
Tachi repetitions do not block this bounded closeout or warrant more runs.
Removing optional ablation machinery is separate cleanup; exact final scoring
and the mandatory shared FP32 pose contract remain unchanged.

## Working rules

Dedicated worktree, private max2-job builds, committed helpers/tests/
protocol/results/T192, read-only corpus, no shared venv/sibling mutations.
Publish design/tests while T191 builds its seam, then adopt its committed
interface without waiting for whole-ticket closure. Coordinate low-core windows
with T191/T188/the orchestrator, no concurrent timing. Prompt readiness updates, no
self-merge.
