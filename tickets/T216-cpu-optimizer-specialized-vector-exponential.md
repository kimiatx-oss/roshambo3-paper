---
id: T216
title: Specialize FP32 vector exponential for color pose optimization
phase: 2
lane: kernel
status: closed
model: sol
reviewer: sol
depends_on: [T212]
priority: highest
artifacts: results/T216/
---

## Sprint closeout — 2026-10-10

Closed for the bounded approximation decision and author-authorized unclamped
default. Raw-bits approximation passed the constrained ranking tests; the
public screening clamp ablation gave identical six-pass results and an
exploratory +2.133% throughput gain. See
cloud ablation (`results/T216/unclamped-exp-cloud-20261010/REPORT.md`),
default report (`results/T216/unclamped-default-20261010/REPORT.md`) and
independent final review (`results/T216/unclamped_default_final_review_20261010.md`).
Fresh 14-arm T149 passed. Public CPU combo AUTO selects the reviewed fast path,
with explicit accurate/guarded opt-outs and entry-time guarded fallback for
incompatible execution/FP-mask settings. No hot-loop FP-control toggles,
noncanonical optimization promotion or changed exact-final semantics.
T220 carries the public routing/resource policy, not another exp experiment.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical context

The analytic hot loop already uses bounded FP32 polynomial exp, not scalar
FP64 exp. Current range reduction plus seven dependent Horner FMAs is costly.
The author explicitly prioritizes reaching/ranking good poses over per-step strict
FP64 accuracy; final scoring can remain more expensive and exact.
Recommended 6.1-Sol-medium (Opus), independent 6-Sol-medium review.

## Scope

1. Specialize for nonpositive finite Gaussian exponents and canonical fixed
   decay. Inspect generated linked assembly and existing degree-seven/-80-tail
   implementation. Fold constants/exp2 conversion into query/plane preparation
   when useful, preserving shared reduced coordinates and the fallback path.
2. Test a small purposeful set: existing baseline, shorter centered-range
   minimax polynomial, and a latency-aware schedule (Estrin or independent
   accumulators/unrolling). No unrestricted polynomial-degree/ISA tournament.
   Optimize end-to-end instruction cost, not FLOPs or standalone exp latency.
3. Approximation applies ONLY to iterative value/gradient evaluations. Preserve
   exact per-start final evaluation and winner rescoring initially. Validate
   behavior near 0, range boundaries, negligible tails and exceptional inputs.
   Report derivative/value consistency and whether the gradient uses the
   approximated Gaussian or its approximant derivative. Do not hide a changed
   far-distance cutoff or nonsmooth behavior.
4. Do not extend this ticket into winner mining or selective final scoring.
   If exact scoring of a subset is proposed later, it needs a valid conservative
   score-error bound and separate reviewed scope; ordinary top-K truncation is
   not such a bound. Provide isolated helpers for T214/T215 composition.

## Deciding measurement

Paired whole-combo rate and bounded top-K retention at exact final scores,
with error/cost characterization of the few candidate approximants. Prefer the
cheapest candidate passing the agreed ranking budget, not the closest to FP64.

## Acceptance

Shared small tune/held-out panel and top-K gates, tiny interval/gradient tests,
no nonfinite outputs or altered exact final-score semantics. Preserve the
existing accurate exp/reference arm and general fallback. Fresh exact-candidate
T149 and independent review; publish negative or conditional outcomes honestly.

## Traps

Replacing scalar expf is not novel here: the baseline is already vector
polynomial. Shorter Horner chains may remain latency-bound; unrolling may spill.
An exact final score cannot recover a pose lost by a poor approximate gradient.
Do not require FP64 per-step equality or claim global-optimum recall from a
baseline top-K overlap test.

## Working rules

Follow CONVENTIONS.md and CPU-COLOR-CLOUD-EXECUTION.md. Own an optimizer-exp
helper and its tests/benchmark hook; no compiler-wide fast-math change, exact
scorer modification or GPU work. T214/T215 are parallel, not dependencies.

## Author-authorized follow-up (2026-10-10)

The initial cubic Horner candidate passes the bounded panel and gains 2.91%
on a matched canonical full scan; retain that frozen evidence. Extend the
small purposeful set with the unpolished minimax-biased float-bit exponential
and the two-FMA mantissa correction described in
[Exponentials in 3 Instructions](https://specbranch.com/posts/fast-exp/).
Test the raw approximation directly rather than assuming its roughly 3%
relative error is unacceptable. An additional cheap quadratic is optional,
not a broad approximation tournament. Verify the published correction's
range-boundary jumps/non-monotonicity instead of assuming smoothness.

Keep the Gaussian-weight gradient convention explicit, exact per-start/winner
finals unchanged, the existing tail policy, and the same frozen tune/held-out
ranking gates. One evaluation per arm suffices for correctness. Compare with
the retained degree-seven and measured cubic; short paired timing first, then
only the best passing positive candidate receives full-panel confirmation.
All new worktrees/builds/staging/runs/scratch use `<scratch>`. Cloud timing
waits for the exclusive cloud lease; local work can overlap T214 timing.

## Author-authorized unclamped default (2026-10-10)

The matched public screening clamp ablation improved throughput by 2.133%
with identical six-pass results. The author authorized promotion to public CPU
combo AUTO, retaining explicit guarded/baseline opt-outs and once-per-native-call
guarded fallback for incompatible execution/FP-mask settings. 181 affected tests
and the fresh 14-arm pre-merge gate passed; independent review approved. See
`results/T216/unclamped-default-20261010/REPORT.md` and the archived cloud
screening ablation for bounded evidence. This does not promote other exp
approximators or change exact finals/noncanonical scoring.
