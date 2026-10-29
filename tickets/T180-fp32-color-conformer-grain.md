---
id: T180
title: Implement fp32 conformer-grain color in parallel and compare finished grains
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T146, T153, T154, T156]
priority: high
branch: ticket/T180-fp32-color-conformer-grain
worktree: <worktree>
artifacts: results/T180/
---

## Sprint closeout — 2026-10-10

Closed for the independently reviewed conformer-grain implementation;
original integration review in `results/T180/INTEGRATION_REVIEW.md`.
Subsequent T181/T182 grain comparisons, T194's retained-grain cleanup and
T198 occupancy work supersede the original tournament; T218 qualifies the
current composed defaults. The old-source full Tachi oracle-panel request is
retired, not reported as run or passed. Current bounded ranking validation
does not establish global-optimum recall. Preserve original source-specific
measurements and opt-in history; no new old-source campaign is queued.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical context

Reviewed experimental integration 2026-10-06: Sol approved `84c2128`; Roci
ranked gates, six Tachi rate cells and the exact-source canary pass. This is
eligible for nondefault merge. The full Tachi D029/T153 oracle-panel gate is
still pending, so acceptance remains open and no default promotion is made.

T122 selected lane-per-library-conformer for CPU shape. T158's current fp32
color implementation instead evaluates eight target features within one pair;
short planes waste lanes and its initial loop spills terms to ordered scalar
accumulation. The author authorized finishing that grain (including XMM4/YMM8
width tests) first, then testing the shape-like independent-conformer mapping.
Earlier fp64 pair4 color measurements do not settle an optimized fp32 design.
This is bounded Luna-max execution with independent Sol review.

Amendment 2026-10-06: the author authorized parallel implementation. T158's
finished width/feature-grain result is a prerequisite for final matched
comparison, not implementation. Start against the verified experimental
combined baseline `2f392f0` and existing T122/T156 contracts. The dependency
list records only closed implementation prerequisites. T158 results must be
consumed by committed hash before final comparison/closure.

## Scope

1. Start implementation from the verified fp32 baseline and existing numerical
   contract; consume the committed T158 best feature-grain arm for final tests.
   Each lane owns one independent query/target conformer alignment, including
   its pose and gradient accumulators. Implement fp32x8; include fp32x4 only if
   T158 width evidence or a measured conformer tail motivates it. No horizontal
   reduction across independent conformers and no cooperating SMT.
2. Reuse T122 shape conformer-grain layout/pose scheduling where applicable;
   do not compare fast color plus scalar shape against a different shape arm.
   Bound/mask each type segment by its real count. Measure a bounded count-
   bucketed layout versus ordinary order if heterogeneous planes underfill
   vectors; preserve output identity and explicitly price reordering/packing.
3. Keep one fixed exp implementation matched to T158 for the grain comparison.
   Hold schedule, objective, matrix, pair population and exact-final scoring
   constant. Preserve general/asymmetric matrix fallback, empty planes and
   poisoned-padding safety. Scalar exact final output remains the contract.
4. Preregister bounded ordinary canonical/general panels and fixed-pose
   controls. Compare scalar, T158 selected feature grain and conformer grain
   under identical shape work. Record lane occupancy, useful terms, packing,
   transform, color gradient and total-call costs. Production loop shapes and
   dynamic active-lane/stopping behavior must be stated, not hidden in a probe.
5. Run qualified interleaved T118 rates on tachi first; roci rates only under a
   qualified window. Correctness need not wait for a quiet global machine.
   Instrumented phase attribution is not a throughput rate, and reference or
   error-check work must remain outside timed native kernels.

## Deciding measurement

Matched ordinary combo-call speed and per-plane/count-stratum regret versus
the finished T158 feature grain, with separate setup/packing and native color
evaluation measurements. A negative result is complete if the bounded mapping
loses; no new hard-reference mining or rescore-selection research is required.

## Acceptance

- Independent T153 fixed-pose and D029 ranked-output gates pass; selected ISA,
  vector width, exp grade, FP environment and accumulation are stamped.
- Empty/tail/general-matrix cases and independent pose/gradient ownership have
  permanent tests. T156 starts/steps and analytic exact-final semantics remain.
- Any speed selection clears matched T118 variation; pooled results do not
  hide regressions in sparse planes or uneven conformer batches.
- Manual T149 pre-merge scoring/codegen canary passes on the exact clean
  candidate after production/build changes. No shipping default changes here.
- Scripts/protocols are committed before runs and old T158 evidence untouched.
- Closure requires a matched comparison to T158's finished committed feature
  grain. Early timings against the initial arm are not a final grain selection.

## Traps

- T122's shape winner is motivation, not color evidence. Its transcendental
  implementation mattered as much as grain; compare matched exp algorithms.
- SIMD pair batching pays for count divergence and inactive lanes; do not use
  homogeneous synthetic data as the ordinary-molecule result.
- Layout/reordering gains are priced once, not multiplied by independent shape
  or color speedups. Use identical pair populations and shared shape baseline.

## Working rules

Isolated worktree, no edits to sibling branches or shared venv. Share corpora
read-only. Coordinate host timing slots, hold T118 locks and native affinity,
verify the loaded binary and exact source hashes. Commit early; synchronize tachi into a fresh scoped worktree, never reset
existing checkouts. Sol review before merge; report bounded negative outcomes
instead of expanding the experiment without authorization.

Implement conformer kernels/packing/tests in separate files. T158 owns ongoing
`color_scalar.cpp`, `cpu.py` and width-harness edits; agree on a committed
interface and staged binding/build handoff before shared-file integration. No
editing another worktree. T158 has first priority for tachi timing until its
width campaign finishes; T180 may build/test on loaded roci with at most two
build jobs and one runtime thread, but must not run tachi builds/correctness
that contaminate T158 measurements. Serialize host timing through T118 locks.
