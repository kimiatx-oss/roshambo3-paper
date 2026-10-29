---
id: T204
title: Consume precomputed shape and color self overlaps in CPU combo
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T200, T203]
priority: highest
branch: ticket/T204-precomputed-combo-self-overlap
worktree: <worktree>
artifacts: results/T204/
---

## Sprint closeout — 2026-10-10

Closed for prepared-self implementation and its subsequent reviewed public
integration: public prepared-self review
(`results/T210/public_prepared_self/review_20261009.md`),
followed by T212/T220. Recurring scans use prepared terms rather than redundant
self-overlap evaluation. The author accepted the existing stored-volume
representation for algorithm design; explicit recompute remains available.
The earlier strict trajectory-parity failure is preserved and is not converted
into a pass. General corpus recomputation, quantization/precision and stored
physical-volume qualification remain open T208 work. This explicitly revises
the earlier "do not close" criterion: implementation is closed, corpus
qualification is not. Matrix-specific color terms remain correctly bound.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical context

2026-10-09 author clarification: existing legacy `.vaa.f32` is explicitly
accepted for T207 algorithm-design benchmarks via a distinct acknowledged
experimental binding and native VAA/SHAPE_PREFACTOR conversion. This does not
qualify legacy values as verified stored-frame volumes or relax T204's ordinary
verified API. T208 owns future recomputation/quantization/precision work; it is
not a dependency for the author-authorized benchmark. Same-representation arms
must match; strict parity against recomputed denominators is not a gate.

The author authorized implementation and agent dispatch on 2026-10-08. T203 measured
library shape self-overlap153.9ms and color self-overlap177.5ms on strong65536
group5/general at24 workers, together77.6% of caller CPU. Precomputed values
should be consumed, not recomputed on every alignment call. T203's phase-map
evidence has since been independently reviewed and that ticket is closed; its
diagnostic did not change production kernels.

Shape vaa is already a flat mmap-capable sidecar in cubic Angstrom. T139 fixed
the calculation on a sample but left corpus migration to a human; current prep
still computes vaa before quantization. Missing frame metadata means legacy
prepared-frame, NOT verified stored-frame. Color self-overlap has no current
serialized scalar sidecar and depends on interaction R/P, feature numbering,
counts, coordinates/weights and coordinate convention.

## Status 2026-10-08 — open

Reviewed code source commit: `008d00de3abc4e8b81a638e7e22ffb0976d705bf`;
tested report-only HEAD: `4f6e57dbf09a64445cb414e9f4750d6db1265bf6`. Sol approved
the exact candidate and the fresh T149 report passed all 8/8 arms.

The reviewed opt-in prepared-input path is implemented and correctness-checked
on the frozen T190 strong65536, group-5 population. Shape uses a bounded
immutable native handle containing native reduced-FP32 self terms; color uses
the persisted sidecar generated for the exact general/asymmetric T190 R/P
matrix and library row order. At 1 and 24 workers, all returned result columns
matched recomputation exactly, rankings and serial winners matched, and the
separate work census showed zero prepared-channel query/library self terms.
This validates the selected opt-in native-shape + matrix-specific persisted-
color variant; it does not make the color volume universal or consume the
physical `vaa` sidecar for shape.

The campaign is complete, but its T118 record is **advisory, not
decision-grade**: `git.source_dirty_paths` contained the uncommitted review
receipt required by the approved run protocol, and that was the sole advisory
reason. Preserve its raw journal and medians as advisory evidence; no rerun was
authorized or needed merely to upgrade the grade. The report, receipts,
sidecars, medians and finite-reuse accounting are in
`results/T204/native-20261008/README.md`.

### Remaining acceptance — do not close

The separate attempt to consume the physical stored-frame `vaa` sidecar failed
the strict trajectory parity gate before producing timing samples: 296 of
589,824 output elements exceeded `rtol=2e-6, atol=2e-6` (maximum reported
relative difference 0.00490791). Direct self-term comparison found the stored
values consistent within their declared FP32 representation, so this result
does not identify a frame/data defect; small representation differences can
still amplify through the optimizer and denominator. No tolerance was relaxed.

Before closing T204, retain an explicit correctness decision for stored shape
sidecars under the existing numerics policy, with score/ranking impact checked
on the frozen population. The strict-parity failure above describes this
experiment; it does not establish that the stored representation is
numerically invalid or impose a universal bitwise/trajectory gate. Do not
introduce new precision research or relax tolerances to erase this result. Do
not promote physical stored-`vaa` consumption to a default or rewrite the shared
corpus while this correctness decision remains open. Any further change to the
CPU scoring path needs its required independent review and fresh T149 gate. The
prepared native-shape handle and exact-matrix persisted-color path remain
opt-in; no production default was changed.

## Scope

1. Add a CPU combo input/preparation contract for immutable query and library
   self overlaps (shape and color). Supply matching precomputed values through
   Python/native boundaries to every retained combo grain and final-score
   normalization. Library values must be indexed by library row, not pair row;
   repeated/sparse/out-of-order pair maps must not corrupt them. Keep scalar
   reference/default legacy behavior available when no prepared input is supplied.
2. Consume trustworthy existing shape vaa with explicit units and frame
   validation. Do not blindly accept legacy pre-quantization values. Add the
   smallest producer/reader metadata and opt-in sidecar-only generation utility
   needed to produce stored-coordinate volumes for NEW outputs; no coordinate
   format rewrite or mutation/regeneration of shared corpora. T139 is prior art.
3. Provide reusable color self overlaps computed outside alignment, keyed to exact
   R/P, feature semantics/counts, coordinate frame and weights. Allow canonical
   and general/asymmetric matrices. Prepare once per immutable library/matrix,
   not once per query/start/call; support explicit persisted, versioned sidecars
   for a chosen matrix if practical. Do not assume a universal color volume.
   If persistence needs a larger format project, finish the validated reusable
   handle + minimal serialization contract and clearly record the residual.
4. Shape and color share the existing FP32 pose contract. Validate empty/no-color
   rows, padding, row subsets, mismatched metadata/matrix, mutated inputs and
   nonfinite/negative data. Establish an immutable ownership/lifetime contract;
   no stale cache from array identity alone and no unbounded global cache.
5. Keep numerical differences explicit: stored-coordinate FP64-prep volumes and
   native reduced FP32 sums are not necessarily bit-identical. Unit/frame parity
   is mandatory; never recompute per alignment merely to preserve old rounding.
   Prepared values from the native baseline algorithm should give exact parity;
   other supported stored-volume representations need declared score/ranking
   tolerance tests per numerics policy. No arbitrary new precision choice.
6. Benchmark same frozen T190/T203 population on1/24 workers, current field
   shape/library_atom8 + analytic color16, same4starts/25updates/mix0.5. Compare
   legacy recompute, prepared shape only, prepared color only, prepared both.
   Report preparation/sidecar generation/loading separately and finite-reuse
   amortization; unchanged ordinary alignment including exact finals inside.
   Query field build outside timings. Instrumentation is not a throughput arm.
   Do not reuse or merge T203 diagnostic CPP; work from clean main CPU source.

## Deciding measurement

Do normal prepared-input combo calls perform zero query/library self-overlap
recomputation? Does validated same-corpus normalization preserve correctness
and remove the measured serial cost? Report full-call rates, residual caller
cost, preparation cost and reuse count rather than just kernel timing.

## Acceptance

Independent Sol-medium review and fresh manual T149 premerge canary for native
kernel/codegen changes. Correctness and mismatch tests, work counters proving
no self terms for prepared calls, existing retained-grain tests, appropriate
score/ranking validation, complete source/build provenance. T118 canonical
lock and observed singleton placement; advisory when host contended. Do not
wait for perfect machine silence to complete correctness/implementation.
No native timings/builds concurrent with another orchestrator-granted campaign.
Commit scripts/protocol before timing; keep raw journals. Do not promote
defaults or mutate shared datasets without explicit approval.

## Traps

Stale vaa frame, physical volume versus reduced sum, custom/asymmetric color
matrices, per-pair duplicates, snapshots checked too expensively, changing
denominators moving trajectories, silently moving prep out of one metric into
another. Query field construction amortization must stay separate.

## Working rules

Luna-max execution, independent Sol-medium review. Private branch/checkout;
preserve all siblings' files. Scope: CPU normalization/plumbing, focused producer/sidecar metadata,
tests and own ticket artifacts. No Engine scheduling/topK/I/O redesign or
shared venv changes. Read tickets/CONVENTIONS.md and numerics policy fully.
T203 clocks/results are preserved on branch ticket/T203-caller-phase-map.

## Status 2026-10-08

Implementation candidate 458ece44d771a4b98eada31b48ea7ebab87ae7f6;
T149 report-only commit c9e36ef5f8545707bf5653fd361b7ec5e6d31aa8.
Agent reports focused CPU/prep correctness passed and fresh two-build T149
passed with no moved arms. Report on candidate branch:
results/T149/premerge/20261008T204000Z-458ece44d771-T204.json.
Independent Sol-medium review requested changes: the stored-vaa metadata hash
certifies float32-cast values but native consumes original float64 inputs.
Enforce the certified representation at consumption and add a regression test.
Fix completed at 7479647c10051fdbe56931257f8fa4a47d52de67, with fresh green T149
report-only commit f3d9e0246ed6ad369631b2d938643cd670a8cc67. Independent
Sol-medium code and four-arm protocol re-review approved. The orchestrator granted Roci
window T204-roci-20261008-root-01 for isolated preparation and benchmarking;
execution still requires all receipt/lock/idle gates. Merge pending. Optional
dependency coverage remains incomplete (pyarrow/RDKit unavailable in borrowed
test environments). No population sidecars generated or throughput campaign
run. Four-arm T190 campaign scaffolding exists, gated on reviewed protocol and
an exclusive orchestrator-granted timing window. T205-T207 track the separate CPU worker
architecture; it is not part of T204.

## Current status 2026-10-09

The preceding 2026-10-08 entry is a historical pre-window snapshot. The reviewed T204 opt-in native-shape and exact-matrix persisted-color baseline has since been measured, reviewed, and merged into `main` through `1991700a6eed0e0b8ced121e0b44ff49561adb76`. Its native campaign, receipts, finite-reuse accounting, and advisory T118 qualification are recorded in `results/T204/native-20261008/README.md`. The T205 cross-binary strong-scaling comparison subsequently used this frozen T204 Release binary as its prepared one-shot baseline; see `results/T205/crossbinary-strong-20261009-root-01/README.md` for the graded paired rates and exact score/rank agreement.

T204 remains open for the stored physical-`vaa` shape-sidecar correctness decision described above. The native prepared-shape handle and matrix-specific persisted-color input remain opt-in; no default promotion or shared-corpus rewrite followed from the completed native benchmark.
