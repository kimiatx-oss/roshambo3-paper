---
id: T190
title: Realistic-population strong and weak scaling of CPU combo
phase: 2
lane: host-io
status: closed
model: luna
reviewer: sol
depends_on: [T125, T146, T153]
priority: highest
branch: ticket/T190-realistic-combo-scaling
worktree: <worktree>
artifacts: results/T190/
---

## Sprint closeout — 2026-10-10

Closed for the reviewed realistic-population Roci strong/true-weak results and
the cloud scaling continuation recorded by T210/T211. Historical Roci cells
remain advisory with their original source/host restrictions:
report `results/T190/roci_20261008_current_scaling_R1/README.md`.
Cloud fixed-corpus and SMT results are not relabelled true weak scaling.
The old claim/reservation and mandatory repeated two-host campaign are retired.
A new current-default true-weak scaling test or detailed cause attribution
would be optional T221 work, not an unperformed acceptance criterion silently
certified by this closeout.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical context

### Cloud continuation ownership, 2026-10-09

T210's 6-Luna-max agent owns new C4 scaling execution, after its composed
conformer/molecule top-K baseline. Use realistic unique populations and enough
tasks to sustain 24 physical cores, physical versus SMT, with full preparation
and scan boundaries recorded separately. Commit bounded populations/repeats
and scope for orchestrator review before runs. No automatic historical two-host rerun,
no concurrent T187 profiling, no kernel/scheduler change in a measurement arm,
and no cross-machine speedup. Link T210 evidence here later; historical T190
results and unresolved acceptance remain explicit.

Reviewed Roci current-source scaling completed 2026-10-08:
`results/T190/roci_20261008_current_scaling_R1/README.md`, independent evidence
receipt `sol-t190-roci-scaling-evidence-677ed5ce-20261008`. Twelve cells,
36 warmup/132 timed calls, exact serial/parallel output and census/placement
checks passed. At physical24: strong65536 throughput 75550 pairs/s, paired
10.90x speedup; true weak98304 throughput 74968 pairs/s, efficiency45.0%
(paired95%CI44.4–45.3%). Field build excluded. All cells advisory, despite
aggregate T118 decision. Scaling loss remains with realistic work; cause not
established. Ticket remains open for Tachi/other bounded residuals. No SMT or
T195 baseline was run. Current receipt covers scaling only; explicit campaign
scope enforcement and fresh review are required before those future legs.

Current-source readiness update (2026-10-08): see
`tickets/T190/CURRENT_RUNNERS.md` and `current_protocol.json`. New bounded
primary leg uses pipelined FP32 field shape + analytic color16 on Roci24 or
Tachi28; separate SMT confirmation follows. Frozen original population is
reused unchanged. New runner review is pending and no timing is authorized.
Historical private checkpoint/receipts remain intact; this does not close T190.

Author direction 2026-10-07: T186's fixed approximately 4096-pair populations
are unrealistically small at 28 cores. Do not optimize small-batch edge effects
before measuring realistic sustained work. Main `3c826745` contains reviewed
native independent-worker combo threading and qualified Tachi evidence; its
11.05x/16.21x physical28 pipelined-field scaling is strong scaling, not weak.
T186 remains open only for host residuals, not a blocker to consume merged code.
Luna-max executes, independent Sol-medium reviews.

## Scope

1. No kernel or scheduler changes. Reuse merged T186 implementation and its
   source-identical reviewed private build, strict actual worker affinity,
   immutable prepared query fields and exact per-start/winner semantics.
   Defer persistent pools, dynamic scheduling and packing optimizations until
   this experiment shows an efficiency loss at realistic work per worker.
2. Audit available ordinary read-only corpus groups and canonical molecule/
   conformer IDs across ALL coordinate blocks, not just the first 4096-row
   block. Select a deterministic fixed query and nested unique library prefixes
   in one existing compatible shape/feature bucket. Record exact IDs/pair maps,
   count/layout/dtypes, population hash and shape geometry. No hard-sample
   mining, corpus copies, replacement or repeated molecules labelled unique.
3. Large strong scaling: target at least 65536 unique query-library pairs held
   fixed across 1,2,4,8,16 and full physical-core counts. True weak scaling:
   start with 4096 unique pairs PER physical worker, so population is N(p)=4096*p.
   Freeze actual sizes before rates. If corpus cardinality cannot support these
   sizes, explicitly report it and propose the largest supported ordinary
   panel; don't silently repeat the 4k fixture or inflate molecule counts.
4. Bound first matrix to one query, analytic color11, trajectory analytic shape
   and pipelined FP32 field shape. Same four starts/25 steps/mix0.5, existing
   T137 spacing/padding, exact final included. No scalar shape, color16, eight-
   query, SMT or new ISA full sweeps initially. A later bounded confirmation
   needs evidence, not automatic multiplication of all dimensions.
5. Field construction stays outside primary alignment timing. Report query
   build separately and record in-call target packing/preparation, launch/join
   and actual worker-search diagnostic costs where existing surfaces permit.
   Do not subtract diagnostic timers from production rates. Use separate
   worker elapsed/work-count diagnostics; per-worker CPU time, host-visible
   quota/throttle/pressure and active-core clock measurements are desirable
   only where available without kernel changes or elevated host configuration.
6. Report strong speedup S(p)=T(1,N)/T(p,N) and efficiency S(p)/p;
   weak efficiency E(p)=T(1,N0)/T(p,p*N0). Rate comparisons must use actual pair
   counts, same frozen prefix construction and independent repeat samples.
   Separate baseline molecule-mix effects from scaling: variable atom/feature
   cost and static chunk imbalance can change with N. Record per-worker useful
   counts and elapsed distributions, and do not call equal pair counts equal
   computational work. No top-k reduction is timed by this entry point.
7. Preregister a bounded session budget and repeat schedule using T118; retain
   sufficient raw repeats and paired uncertainty. Do not undertake a new 84-arm
   tournament. First Tachi, with Roci optional only when genuinely qualified.
   Process visibility on the benchmark host cannot prove the hardware is idle: record
   visible limitations and request host telemetry if needed.

## Deciding measurement

Does the physical-core efficiency loss persist with realistic per-worker work?
Large-population strong and actual weak scaling for the two fast shape arms,
with uncertainty, work-count/imbalance evidence, setup accounting and available
clock/host diagnostics. Distinguish small-call effects from sustained resource
limits; absent counters are not proof of bandwidth or power bottlenecks.

## Acceptance

Independent Sol protocol/source-continuity review before rates and final
evidence review. T118 exact cwd/provenance/tool PATH/host lock/actual affinity/
quiet/frequency/source/population gates, clean private build and exact final
correctness. Preserve T186 advisory records separately. No default changes.
Existing T149 may be reused only after verifying CPU/build source identity;
otherwise fresh exact-source T149 is required. Missing host/counter data remains
explicit; a qualified Tachi-only bounded result is a valid partial handoff.

## Traps

Strong scaling is not weak scaling. Increasing thread count with unchanged
4k work recreates the same small-call problem. Repeated pairs are not a larger
database. Instrumented phase fractions or all-CPU pooled frequency cannot
identify Amdahl serial fractions or active-core throttling. A host-local lock
does not arbitrate workloads it cannot see.

## Working rules

Dedicated worktree; own only tickets/T190 scripts/tests/protocol and
results/T190. No shared kernel/API/CMake changes, shared venv edits or corpus
copies. Private build max2 jobs if actually needed. Coordinate measurement
windows with T187/the orchestrator, never overlap profiles with rates. Commit before rates,
notify the orchestrator on review readiness/first result/completion, and continue ordinary
steps without waiting for the author to check in. No self-merge.
