---
id: T211
title: Compare shape, shape-pose color rescore, and combo CPU screening scaling
phase: 2
lane: research
status: closed
model: sol
reviewer: sol
depends_on: [T210]
priority: highest
artifacts: results/T211/
---

## Request and scope

The author requested dedicated-cloud screening throughput in conformers/s for
shape-only, shape optimization followed by color rescore, and full combo
optimization, at 8/16/24 physical cores with SMT off and on.
6.1-Sol-medium owns the minimal local runner; 6-Luna-max is sole cloud
operator; independent 6-Sol-medium checks route semantics and evidence.

Reuse retained implementations, not new kernels or a benchmarking framework.
First check that mode 1/2 use the fast retained field shape path rather than
silently pricing legacy scalar analytic shape against optimized combo.
Color rescore evaluates the shape-selected winning pose, not combo optimization.
Record any unavoidable API/kernel/prepared-self differences explicitly.
Use persistent block ownership and bounded block output/reduction; no ordinary
library-sized dense output. All arms screen the same conformers and return K100.

## Initial bounded campaign

### Author-approved prerequisite correction

The one-block pilot measured about 87 ms query-field construction per 4096 rows,
and source inspection found GIL-held one-thread old shape optimization and
fixed-pose color rescoring. The author authorized fixing query-field
reuse and GIL release before the comparison. Reuse existing prepared shape
evaluators through a const FieldNaive32 view; do not change sampler/kernel
math. Release GIL around numerical work only, outside Python allocation/API
operations. Test old/reused bit identity, handle binding/lifetime and mode 2
pose identity, then run fresh official exact-candidate T149. Final 18 cells use
one common reviewed binary. Earlier old-binary combo 8P data is preliminary,
not part of the final matched matrix. Prepared color-self input for the older
rescore API is not part of this prerequisite; report its current cost.

Use the verified LIT-PCBA color corpus groups 7/8 (3,605,026 unique conformers,
882 physical blocks) and frozen T169 query already staged on the cloud x86 VM.
Fixed 25 steps, four starts, field resolution and exact final scoring;
color modes use mixing 0.5. Shape-only has no color work.
This is finite-population strong scaling, not weak scaling.

Six topology-verified placements: 8P, 8P/16T, 16P, 16P/32T,
24P, 24P/48T. Use singleton affinities, adding the actual sibling threads
of the same physical cores, not a contiguous logical-CPU count assumption.
One warmup and two timed repeats for each of 18 mode/placement cells.
No low-core anchors, eleven-repeat floor, simultaneous profiler, or unrelated
parameter sweep. Preserve T118 repeat-budget refusals; label the small-budget
rates exploratory rather than promote grading.

Report scan/end-to-end boundaries and conformers/s, both raw repeats and
summary; amortize query-field and once-only library-self construction outside
scan, reporting their costs separately. Do not silently hide per-block field
builds or recomputation inside one arm. Warm-cache, not cold-I/O, evidence.
Check exact per-mode output against its same-mode reference/other worker
counts; different objectives need not produce identical poses or rankings.
Verify full unique-row/block coverage and mode 2 shape-pose identity.

## Working rules

Follow tickets/CONVENTIONS.md. Isolated local source branches, cloud datasets
and existing installations read-only; max two compiler jobs if necessary.
Canonical CPU lock and guest load checks; no transfers/builds during timing.
Commit runnable scripts before execution, archive commands/raw records/results
under results/T211, never push to GitHub.
No native changes authorized merely to enable this benchmark; report a genuine
route capability gap first. Fresh T149 applies if scoring/codegen is changed.

## Measurement result (exploratory)

The matched 18-cell matrix and its provenance are archived in
`results/T211/simple_mode_screening_20261009/`.
Across the six placements, median throughput ranged from 322k to 1.010M
conformers/s for shape-only, 304k to 849k for shape-plus-color rescore, and
54.9k to 162.5k for full combo. The matrix uses one warmup and two timed
repeats per cell; T118 records the short schedule as refused, so these are
exploratory rates and do not close the ticket as decision-grade evidence.
