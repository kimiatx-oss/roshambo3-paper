---
id: T186
title: Native CPU combo multicore scaling and ordinary independent-worker SMT
phase: 2
lane: host-io
status: closed
model: luna
reviewer: sol
depends_on: [T125, T146, T153]
priority: highest
branch: ticket/T186-combo-multicore-smt
worktree: <worktree>
artifacts: results/T186/
---

## Context

### Closeout — ordinary SMT positive (2026-10-09)

The author accepted closing this investigation as positive after independent review
of the composed worker-owned campaign. On Roci, matched full-wall SMT gains
were 12.84% at 8 physical cores, 10.08% at 16, and 5.92% at 24. Raw T118 grades
were decision, decision, and advisory respectively. Tachi's completed 24-core
comparison was directionally positive at 17.12%, advisory with substantial
load/order dispersion and limited host visibility. Exact all20 score/GID/MID
parity passed within each host. See
`results/T207/composed_highcore_20261009/README.md` and `REVIEW.md`.

These measurements use independent persistent workers, pipelined field shape
width8, and analytic color16 (two conformers times four starts). No cooperating
SMT or phase-opposed scheduling was introduced. The result supports ordinary
SMT on this composed workload, not universal SMT benefit, intrinsic hardware
scaling, concurrent-query cache behavior, or a changed production default.
The earlier native-only integration evidence below remains historical.

Missing Tachi 8/16-core repeats are not required to keep this bounded hypothesis
open. No further SMT sweep is queued. Reopen for a material workload, host,
working-set, or pipeline change that reverses the measured benefit. Public
pipeline integration remains T167/T207 work; any default policy needs explicit
scope and review.

Reviewed partial integration, 2026-10-07: native threading is merged as an
explicit opt-in, with independently approved source/protocol `e8434ddb` and
qualified corrected Tachi evidence `aba0e83a`. Exact-source T149 passed on
`8aedb525`; all subsequent changes are results-only and CPU tree remains
`e5509f5d3dd2f8cc146e9844a7b8e6b0a1488ac9`. See
`results/T186/INTEGRATION_REVIEW.md`. Roci scaling remains unmeasured; no
shipping-default or universal SMT promotion. Ticket stays open for that host
residual. The earlier scaling01 run is advisory and never upgraded.

### Original context

The author authorized this on 2026-10-07. Main `116505d0` integrates independently reviewed
fast shape into full CPU combo: vector analytic and scalar/paired/pipelined
FP32 fields with analytic color11/16. Tachi single-core evidence is committed
under results/T184; defaults are unchanged. Combo still rejects threads other
than one. T125's shape-only threading is not evidence of combo scaling.
Luna-max implements; independent Sol-medium reviews. T184/T185 residual Roci
and diagnostic measurements are not blockers: consume their merged kernel.

## Scope

1. Own native combo threading/API integration. Reuse T125 topology/runtime
   contracts; expose explicit supported thread count without silently dropping
   it. Preserve threads=1 source behavior and all legacy unsupported guards.
   Release Python GIL safely for native work if needed; no Python timed loop.
2. Partition independent pair/batch work among native workers; each worker owns
   complete optimizer/cache/state and disjoint result rows. Do not split one
   trajectory among cooperating SMT siblings. Share immutable prepared query
   fields, retain query/target lifetimes, and avoid rebuild/repack per step.
   Preserve exact per-start/final scoring, stable ties, canonical caller order,
   arbitrary pair IDs/tails and supported mixed-query guards.
3. Begin with color11, compare trajectory-SIMD analytic shape and pipelined
   FP32 field shape, plus one-core matched anchors. Color16 is a bounded
   confirmation if useful, not another full combinatorial sweep. No new shape
   arithmetic, spacing/precision policy, or scheduling oracle.
4. Preregister rotated same-session runs at 1,2,4 and further doubling up to
   available physical cores, including the full physical-core point. Then
   compare one versus two pinned independent workers per physical core at
   selected counts. Read actual sibling/socket/NUMA topology; never infer it
   from adjacent logical CPU numbers or change machine SMT settings.
5. Test one prepared query against a large enough library/work population to
   saturate workers, then a bounded concurrent-query working-set panel. Reuse
   existing read-only corpus and recorded deterministic selections; no mining
   or corpus copies. If repeating pairs for throughput, identify repeats and
   disjoint outputs explicitly, not as extra molecules or statistical samples.
   Record aggregate field occupancy, query distribution, worker imbalance,
   cache/bandwidth effects and achieved clocks. Scope NUMA first-touch/placement
   to preventing accidental remote-memory confounds, not a placement sweep.
6. Compare static contiguous batch assignment with one bounded chunked/dynamic
   schedule only if heterogeneity causes imbalance; preserve useful SIMD lanes
   and query-field locality. Do not introduce phase-opposed SMT (T161) here.
7. Source/protocol review before timing; coordinate host reservations with T187
   and residual T184/T185 workers. Whole-host scaling needs a genuinely quiet
   host; use Tachi first if Roci fails T118. Missing-host rates remain open.

## Deciding measurement

Actual full-combo throughput and latency at physical-core counts and ordinary
SMT, scaling efficiency relative to matched one-core runs, and query-working-
set effects on both hosts. Field build excluded from primary alignment rates;
report build/prep/bytes/finite reuse separately. Never multiply single-core
kernel speedups by historical T125 scaling factors.

## Acceptance

Permanent serial-versus-parallel output/per-start/tie tests, odd batches,
multiple queries, exceptions, handle lifetime and repeated concurrent calls;
race checks where available. Immutable shared state and truthful threads/ISA/
grain stamps. T118 lock, affinity/topology, quiet/frequency/source/repeat gates,
paired uncertainty with same-regime floor. Exact-source manual T149 before
any CPU codegen merge, including combined integration; independent Sol source
and evidence reviews. Null/negative SMT outcomes are valid. No defaults or
ranked-production promotion without a separate reviewed decision.

## Traps

Physical-core and logical-thread rates are different denominators; false
sharing or duplicate work is not scaling. Shared fields can lose their cache
advantage with concurrent queries. Counters explain, not establish, speedups.
T136/T149 code-size cliffs and multi-ISA ODR hazards remain real.

## Working rules

Dedicated worktree, private builds capped at two jobs, read-only shared corpus,
committed scripts/protocol before rates and results/T186 records. No shared
venv edits, sibling file edits, or destructive sync. T187 owns profiling-only
files, not this optimizer/API. Scoped Tachi code/data sync is authorized.
Send early checkpoints/review requests and continue normal steps without
waiting. No agent self-merge.
