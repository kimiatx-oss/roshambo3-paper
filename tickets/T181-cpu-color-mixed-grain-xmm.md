---
id: T181
title: Compare mixed conformer-feature SIMD grains and four-conformer XMM color
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T146, T153, T154, T156]
priority: high
branch: ticket/T181-color-mixed-grain
worktree: <worktree>
artifacts: results/T181/
---

## Context

T180's ordinary fp32x8 lane-per-conformer kernel beats the finished feature-grain
baseline by 17-48% in six paired tachi combo cells, with Sol approval for an
experimental merge. The endpoints do not settle intermediate mappings or a
four-conformer XMM implementation. The author authorized this bounded experiment
in parallel with T159's native field/hybrid follow-through. Consume reviewed
T180 commit `84c2128` as the experimental source baseline; it need not be closed
to start independent implementation. Luna-max executes, independent Sol reviews.

## Scope

1. In a YMM fp32x8 register compare the ordinary WA=1 endpoint (eight independent
   conformers) with WA=2 (four conformers, two feature lanes each) and WA=4
   (two conformers, four feature lanes each). Feature lanes cooperate within
   each conformer only; define the segment mapping and reduction explicitly.
   Preserve independent poses/gradient accumulators between conformers. The
   T158 eight-feature single-conformer endpoint remains provenance/control.
2. Add XMM fp32x4 WA=1: four independent conformers per register, not T158's
   four features inside one pair. Use VEX128 and the same polynomial/FMA policy
   as the YMM arms. Do not turn the width test into a separate strict-SSE2
   arithmetic comparison, and do not add AVX-512/SMT arms.
3. Share the T180 packing/workspace, exp grade, numeric guards and scalar exact
   fallback/final scoring wherever possible. Price the added within-conformer
   reduction and any changed packing/transform/setup separately. Keep one
   ordinary scheduling order first; previous count bucketing did not yield a
   clear win and is not another sweep axis here.
4. Permanent fixtures cover canonical/general asymmetric matrices, empty and
   uneven segments, conformer tails, poisoned padding, independent poses,
   fallback and output scatter. Declare the different accumulation/reduction
   under D029; exact scalar per-start/winner score and optimizer schedule remain.
5. Record useful/issued lanes and occupancy at each interacting plane weighted
   by gradient frequency. Include counts 0..17 and ordinary mixed planes. Mask
   per-conformer and per-feature lanes safely; zero lanes do no useful work.
   A count-based dispatch is not inferred from numerical field density.
6. Preregister bounded native preposed diagnostics and the ordinary six-cell
   mode-3 comparison on tachi against T180 ordinary/grain11. Same shape work,
   four starts, 25 steps, mixing and pair population in every arm. Reference,
   checks, logging and Python marshalling stay outside native timed loops.
   Separate uninstrumented total-call rates, setup/packing and instrumented
   attribution. No new oracle mining or interpolation-accuracy campaign.

## Deciding measurement

Paired ordinary combo speed/regret of WA2, WA4 and XMM4-WA1 against YMM8-WA1,
with native color evaluation and occupancy diagnostics by count/matrix stratum.
Select no arm unless matched T118 uncertainty supports it. A bounded negative
result is complete; do not grow the parameter space to find a headline.

## Acceptance

- Independent T153 fixed-pose and D029 ranked-output gates pass with selected
  ISA, width, WA mapping, exp grade and FP/reduction policy recorded.
- No cross-conformer reduction/pose sharing; real-count bounds and fallback
  are tested. The T180 ordinary endpoint is unchanged and remains available.
- Timing uses matched populations, host lock/native affinity/sibling checks,
  rotated repeats and recorded host variation. Every performance claim names
  its baseline; no multiplied cross-ticket or cross-machine speedup claims.
- Manual T149 pre-merge canary passes on exact final clean candidate after
  changes; scripts/protocols committed before measurement, Sol review before
  merge. No shipping default or adaptive selector change in this ticket.
- Full-call and native-kernel measurements contain no independent oracle/error
  checking. Packing/bucketing is charged once where deployment pays it.

## Results (2026-10-06; reviewed)

The six ordinary Tachi mode-3 cells are decision-grade and support no mixed-
grain promotion. Paired speedup is T180 WA1 elapsed time divided by candidate
time. Across cells, WA2 ratios range 0.8445–0.9484, WA4 0.6717–0.8810, and XMM
0.9129–1.0087. None clears Tachi's 7.9349% noise floor; the lone XMM point
above 1.0 is group 7 canonical (1.0087, 95% CI 0.9810–1.0230). Correctness,
exact-winner, census, clean source/ISA stamp, and T118 quiet/lock/affinity
gates passed. A separate SMT-sibling occupancy trace was not retained, so no
stronger sibling-idle claim is made. Roci check-only runs passed on the same
six population hashes. Full results,
weighted useful/issued-lane census, phase attribution, native-loop diagnostics,
and the preserved initial no-timing preflight are in `results/T181/`.

No defaults changed. Independent Sol source and evidence reviews passed. The
exact-source T149 canary passed all eight arms on clean `54ffc7c`, with no moved
outputs; report-only commit `52e9353` preserves the tested source. Integration
retains the reviewed/measured CPU source byte-for-byte. The experimental arms
and bounded negative evidence are merged; ordinary YMM WA1 remains preferred
on this tested panel. No Roci timing or broader architecture claim is made.

## Traps

- WA trades independent alignments for feature parallelism; empty/sparse planes
  may favor WA1, while skewed counts or dense planes may favor cooperation.
  This is a hypothesis, not a dispatch rule.
- More occupied lanes do not imply fewer cycles: reduction, transform reuse,
  instruction issue and register spills can reverse that ranking.
- XMM4 conformer width is not the already-tested XMM4 feature grain. Matched
  polynomial and VEX encoding prevent a width-versus-exp/transition confound.

## Working rules

Use the assigned isolated worktree and fresh branch from reviewed
experimental `84c2128`, incorporating current main ticket-only updates. Do not
reset/delete existing worktrees or edit sibling files. Read standing decisions,
conventions and numeric/metrics policies before implementation. Share corpora
read-only; no shared venv edits. Keep roci correctness/build parallelism low.

T159 owns ongoing prebuilt-field/hybrid optimizer/public-wrapper integration;
implement mixed/XMM kernels/tests in separate files first. Send interface needs
and agree on a committed shared-file/build handoff before integration. T159
has first tachi measurement priority; do not run builds/correctness there during
its timing windows. Then acquire the next host-scoped T118 slot yourself rather
than waiting indefinitely for the orchestrator. Commit early; scoped tachi sync to fresh worktrees, never overwrite existing
checkouts. Return conclusions, hashes, tests and unresolved acceptance for review.
