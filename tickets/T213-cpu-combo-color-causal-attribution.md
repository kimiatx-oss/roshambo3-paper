---
id: T213
title: Separate analytic color cost from combo scheduler cost on the cloud host
phase: 2
lane: research
status: open
model: luna
reviewer: sol
depends_on: [T211, T212]
priority: deferred
artifacts: results/T213/
---

## Sprint disposition — 2026-10-10

Open, deferred residual diagnostic qualification; no active agent reservation.
Merged evidence and review are in
the bounded report (`results/T213/causal-attribution-20261009/README.md`) and
independent review (`results/T213/causal-attribution-20261009/INDEPENDENT_REVIEW.md`).
The diagnostic hook was not merged. Direct ordinary-output parity against
the pre-hook source and representative source-level hot-loop annotation
remain uncompleted. Shipped T214/T215/T216 and T218 composition do not depend
on this diagnostic follow-up. General optional allocator/worker-phase
telemetry is consolidated in T221, not a new profiler framework here.

This is the current queue state; earlier assignments/status statements below
are historical. No build, code change or experiment was run for closeout.

## Historical context

T211 measured about 5.9x combo/shape scan time at 24 physical cores. T210's
whole-process profile puts 64.84% of cycles in the analytic color evaluator,
but neither measurement isolates the color kernel from combo scheduler and
final-score differences. Produce that distinction without another harness.
Recommended execution: 6-Luna-max (Haiku tier); independent 6-Sol-medium review.

## Scope

1. Reuse T211 inputs, prepared self/query fields, worker ownership and top-K.
   Compare ordinary fast shape, unchanged full combo, and a diagnostic combo
   arm that bypasses numerical color evaluation but keeps the combo shape,
   pose update, batching and reduction machinery. Label the changed objective
   diagnostic-only; never expose it as an ordinary combo result.
2. Setting mixing=0 alone is NOT a bypass: inspect whether color still runs.
   Make one minimal committed diagnostic hook if necessary; distinguish
   suppressed gradient work from final-color work. Census must identify what
   was actually removed. Verify the diagnostic objective's shape correctness.
3. Profile/annotate one representative ordinary combo pass and a small
   diagnostic control with matching symbols/buildID. Separate scalar setup,
   transform/eligibility, vector pair arithmetic, exact finals and optimizer
   overhead where the existing counters permit. Obtain focused perf-stat
   instruction/cycle/cache metrics; execution-port or dependency claims need
   supporting counters/assembly, not IPC alone.
4. Count useful versus issued SIMD pair lanes per plane, actual scalar fallback
   rate and feature counts on this panel. Do not assume wasted lanes explain
   the gap; strategy16 has four starts for each of two conformers.

## Deciding measurement

Matched ordinary-shape, combo-shell and full-combo scan rates plus actual
removed-work census and hot-loop annotation. Explain the attributable color
portion and residual shell cost; do not subtract whole-process profile shares
from scan wall as if their timing boundaries were identical.

## Acceptance

Reproducible bounded diagnostics, exact ordinary-arm outputs, truthful bypass
semantics, source/DSO provenance and independent review. No production default
or numerical change. Publish findings immediately for siblings; they need not
wait for this ticket to close to begin implementation.

## Traps

Pitfalls 11/18: compare complete scans, not isolated kernels or shape speedups
extrapolated to color. Low cache misses do not prove zero memory bottleneck;
flat self shares are not additive phase times. Diagnostic scores are not a
retrieval acceptance test.

## Working rules

Follow CONVENTIONS.md and CPU-COLOR-CLOUD-EXECUTION.md. Own diagnostic helpers
and results only; no new framework, corpus or broad profiling sweep. Exclusive
cloud lock includes diagnostic builds. Any native scoring hook needs fresh
exact-candidate T149 before merge; prefer retaining the hook benchmark-only.

## Partial result (2026-10-09; exploratory)

Reviewed attribution evidence is published in
`results/T213/causal-attribution-20261009/README.md`.
Five short paired passes at 24 physical workers over 188,962 conformers gave
median rates 783,500/s shape, 597,904/s true color-bypass combo shell and 143,662/s
full combo. Removing color removes about 76% of combo scan time. Setting
mixing=0 alone still evaluates color. Whole-process counters are setup-inclusive;
unsupported cache counters and stripped DSO offsets cannot support cache/port
or source-level subphase claims.

Only evidence and independent review are integrated; the diagnostic scoring
hook remains on its ticket branch. Keep this ticket open for direct pre-hook
versus candidate ordinary-output parity and source-level hot-loop annotation.
The independent review records the passing exact source-plus-T149-report pair
at 70b0aed0; it does not certify those outstanding claims.
