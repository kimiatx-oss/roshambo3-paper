---
id: T206
title: Exact worker-local CPU top-K and bounded final reduction
phase: 2
lane: host-io
status: closed
model: luna
reviewer: sol
depends_on: [T205]
priority: high
artifacts: results/T206/
branch: ticket/T206-cpu-worker-local-topk
worktree: <worktree>
---

## Sprint closeout — 2026-10-10

Closed for the exact worker-local collector and reviewed composition into
worker-owned public screening. Historical matched campaign remains
the T206 report (`tickets/T206/performance_run_20261009.md`); larger-corpus conformer and
molecule correctness continues in
the T210 Phase B review (`results/T210/phase_b_review_20261009.md`), and current
public integration/gates are recorded in T220.
The historical "fresh canary pending" and "dense default" checkpoint is no
longer current. Avoided dense payload and planning estimates are not measured
peak RSS; unmeasured RSS/allocator and sink-only occupancy acceptance is
transferred to optional T221. Explicit safeguards remain available, but T220
removed arbitrary default caps without removing bounded K/overflow checks.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical measurement checkpoint — 2026-10-09

The bounded matched T206 campaign is complete; the ticket remains **open**.
The report and archived raw evidence are in
the campaign report (`tickets/T206/performance_run_20261009.md`) and
raw archive (`results/T206/worker_local_topk_roci_20261009T002129Z/raw.tar.gz`).
The separate 24-physical/48-logical SMT follow-up is documented in
its exploratory report (`tickets/T206/performance_smt_run_20261009.md`) with raw
archive `results/T206/smt_followup_roci_20261009T005556Z/raw.tar.gz`; its
formal T118 decision grade does not remove the sampler-overlap caveat or
authorize a causal SMT claim.

At K=100, one query, 65,536 unique conformer-pair rows (6,901 target
molecules), four starts and 25 optimizer steps, exact all-20-column/GID/MID/order
parity passed at 1/2/4/8/16/24 physical workers. The T118 run
`run_1791505866_084a443f` graded `decision`
with no advisory/refusal; both arms used the same prepared self-overlap terms.
Three warmups and eleven timed pairs per arm/cell showed end-to-end runtime
parity, not a demonstrated throughput win. Dense score-row payload avoided is
5,234,880 bytes/call; this is payload arithmetic, not measured RSS. The
reported native memory values remain planning estimates, not an allocator cap
or observed peak. Sink-only worker occupancy is not instrumented; the separate
placement/claim diagnostics were for the dense path only.

This evidence is scoped to the reviewed DSO and the prepared-self-term caller
variant. Dense output remains the default and top-K remains opt-in. The T206
implementation is now composed with authorized main at
`d5c1c83d405044addf4568f520966e1fb87abf6c`; Sol's source/API review passed,
and the composed candidate passed the 23-test real-scorer matrix using the
unchanged source-stamped private DSO. See the
composed parity receipt (`results/T206/native_parity_composed_20261009.md`).
A fresh official T149 canary for the exact final committed candidate remains
required before integration approval. Peak-RSS and granular-telemetry
acceptance remain open, so T206 stays open and dense remains the default.

## Context and scope

Dispatched 2026-10-08 to 6-Luna-max for independent collector/proof/tests
against T205's proposed worker-owned final-row sink. Native integration waits
for T205's stable implementation. No builds/heavy tests during the orchestrator-reserved
T204 Roci benchmark window; coordinate exclusive file ownership with T205.

T205's persistent workers should retain private winners across all claimed
tasks, not stream every alignment score through a central reducer. Implement an
optional CPU search/top-K mode alongside the compatible dense scoring API.

1. Each worker maintains exact local K per query, using the production rank
   score and identical canonical ID tie ordering. Optimize and perform existing
   exact final scoring before admission; no new approximate pruning policy.
   Merge at most workers * queries * K hits at completion. Carry winner IDs,
   score columns and poses required by the public hit contract.
2. Distinguish conformer from molecule top-K. For molecules, first aggregate
   conformer winners using the actual production molecule ranking semantics,
   then retain distinct-molecule candidates. Document/prove the local pruning
   property and tie ordering. Prefer molecule-complete tasks; if split, define
   explicit partial-winner handling and its memory bound. Never reuse the
   ordered sink's tail-open state blindly with out-of-order completion.
3. Avoid library-sized pair maps/dense score arrays in top-K mode. Working memory
   is bounded per-worker scratch plus per-query top-K and declared boundary
   state. Handle many queries with an explicit batching/memory budget; no hidden
   workers * entire-library replication. Dense/callback output stays an explicit
   mode; do not silently truncate or change existing API behavior.
4. Local reducers are worker-private/cache-line separated. A final bounded merge
   needs no dedicated reducer thread by default. Streaming publication, output
   double buffering, shared threshold pruning and hierarchical NUMA reducers
   are deferred unless measured; stale/approximate thresholds must not enter
   correctness through this ticket.

## Acceptance and measurement

Compare exact hit identities, ordering, score columns and winner poses against
dense scoring plus the existing reducer at 1/2/many workers and varied task
orders. Test ties across workers, K=0/1/large, empty inputs, fewer than K hits,
multi-query results, no-color rows, molecule boundary splits and highly uneven
conformer counts. Demonstrate no max_results truncation or lost candidates.
Document any molecular aggregation requiring more state than max-score winners.

Measure scoring/local-reduce/final-merge and end-to-end costs, dense score bytes
avoided, peak memory and master work. Use matched realistic populations and
T118 timing protocol; low-core advisory work may proceed under contention.
Independent Sol-medium review and fresh manual T149 where scoring/codegen is
affected. Preserve dense reference and do not promote defaults without approval.

## Traps and working rules

Pitfalls 9/11/12/16/23/27/28. Raw conformer top-K is not distinct-molecule top-K;
IDs must not depend on completion order. No BSP per-block reduction barrier.
Luna-max implementation, Sol-medium review. Read conventions/numerics fully;
private branch/checkout, shared data/build/venv untouched, max two build jobs,
orchestrator-granted timing windows, artifacts results/T206/.
