---
id: T205
title: Persistent dynamically scheduled CPU combo workers with local preparation
phase: 2
lane: host-io
status: closed
model: luna
reviewer: sol
depends_on: [T204]
priority: highest
artifacts: results/T205/
branch: ticket/T205-persistent-cpu-combo-workers
worktree: <worktree>
---

## Sprint closeout — 2026-10-10

Closed for the reviewed persistent executor/worker-local preparation foundation
and matched strong-scaling campaign
(`results/T205/crossbinary-strong-20261009-root-01/README.md`).
T207 and T212/T219/T220 subsequently integrated the worker-owned public route;
the earlier opt-in-only/default statements below are historical.
The old fixed-2,048-pairs-per-core weak-scaling follow-up, full allocator census,
per-worker peak scratch and exclusive queue/prep/compute/idle attribution were
not completed. They are explicitly transferred to deferred T221 rather than
claimed proven. Existing strong-scaling evidence is not weak scaling and its
cross-binary comparison does not isolate persistence alone.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical context

Dispatched 2026-10-08 to 6-Luna-max. Start from independently reviewed T204
implementation 7479647c10051fdbe56931257f8fa4a47d52de67 plus report-only
f3d9e0246ed6ad369631b2d938643cd670a8cc67; T204 throughput remains pending.
Architecture/code work may proceed, but no build or CPU-heavy tests during
the orchestrator-reserved T204 Roci benchmark window.

The author agreed to the CPU worker architecture on 2026-10-08. The CPU shares an
address space: GPU producer/consumer staging is not a requirement. T203's
in-memory phase map attributed about 331 ms of 427 ms outside alignment workers
to library self-overlaps; T204's prepared-input path removes their recomputation.
The opt-in T204 campaign is complete; stored-frame VAA acceptance remains open.
Remaining preparation should belong to workers rather than a serial caller.
Those figures await T203
independent review and are motivation, not a promised redesign speedup.

## Scope

1. Introduce an explicitly owned reusable CPU executor/session with persistent
   native workers. A single central queue or atomic claim cursor over a work list
   is the initial scheduler. Workers continuously claim coarse library ranges;
   no dispatch/reduce barrier between batches or repeated BSP waves. Keep the
   current synchronous dense scoring API compatible; executor reuse across
   calls must have an explicit lifetime and concurrency contract, not a hidden
   process-global thread pool.
2. Move library-range coordinate preparation, retained grain start/pose packing,
   target workspace allocation/reuse and exact final scratch into workers.
   Share validated immutable query fields, interaction matrices and T204 self
   terms. Do not rebuild query data or recompute self terms per worker/query.
   Preserve shared FP32 shape/color pose and retained grains 11/16.
3. Use bounded reusable per-worker batches, with enough tasks for dynamic load
   balancing. Tail lanes, sparse/repeated/out-of-order pair maps, global IDs and
   original dense output placement must remain correct. Each output row has a
   single writer. Never duplicate a whole library block in each worker.
4. Specify cache-line-aware workspace ownership: separate and appropriately
   align/pad hot mutable per-worker counters, queue bookkeeping, scratch headers
   and reduction placeholders. First-touch large scratch on its owning worker.
   No shared hot allocator/heap or adjacent writable worker state on one line;
   report residual output-boundary sharing rather than claiming padding alone
   eliminates all sharing. Queue synchronization is intentional true sharing.
   Avoid per-alignment central progress atomics; aggregate locally.
5. Validate and pin Python-visible objects before releasing the GIL; execute
   native preparation and scoring without it, including the one-worker path.
   Workers must not access Python objects without the GIL. Define shutdown,
   exception propagation, cancellation, concurrent submissions, repeated calls
   and buffer lifetimes. No deadlock on failure or partial result presented as
   a complete search. Keep one CPU budget; avoid nested compute pools.

## Implementation interface (T205 design checkpoint)

`roshambo3.backend.cpu.CPUComboExecutor` is an explicitly owned, context
managed wrapper around a native executor. Construction fixes the worker count,
bounded `claim_chunk_rows` (default 256), and affinity policy. The existing
dense `optimize` call remains the default; callers may pass the executor with
the matching `threads` count to reuse its native workers across synchronous
calls. There is no process-global pool. Calls using one executor serialize;
separate executors may run concurrently. `close()` is idempotent, waits for an
active submission, rejects later submissions, and joins all native workers.

T205-owned implementation files are `combo_executor.hpp/.cpp`,
`color_scalar.cpp`, the color conformer/mixed packer headers and sources,
`color_experimental_stubs.cpp`, `cpu.py`, `CMakeLists.txt`, and
`tests/test_cpu_combo_executor.py`. T206 owns its independent row collector
and proof/tests; integration is coordinated through the row-sink signature
below.

The native scheduler claims contiguous ranges of work-unit indices from one
cache-line-separated atomic cursor. A claim covers approximately 128–512 pair
rows, rounded down only to whole blocks of the existing color grain; the final
short claim keeps its valid tail. The thread configuration stamp reports the
row chunk, work units per claim, resulting claim count and claim-limited
parallelism bound. Its legacy `workers_used` field denotes one-shot pool
capacity, not observed active workers. Worker-timer diagnostics report actual
scoring claims per worker and `workers_with_claims`, using cache-line-separated
worker-local counters. Queue claims happen once per range, never per alignment.
Distinct library rows are prepared once
from a deduplicated used-row list, independently of repeated pair-map entries.
Score tasks preserve input pair rows and each row has one owner/writer. A
native-only optional row sink receives `(worker_id, output_row, query_row,
library_row, scores, n_score_columns)` after exact final scoring. `scores`
points to the completed dense row and is valid only during the callback. No
Python callback runs on a worker;
the sink must not re-enter or close its executor. A failing call may have
already emitted rows completed before cancellation, so consumers discard sink
state when `score_pairs` raises. This gives a local reducer worker and stable
row metadata while leaving dense output as the default policy.

The sink may own row-to-ID maps or hold validated immutable borrowed views.
Borrowed backing owners must be retained strongly through the synchronous score
callbacks and the sink's finalize/abort decision; callers must not mutate the
views concurrently. A sink must not retain the callback's score-row pointer.

The executor keeps cache-line-separated per-worker mutable headers and scratch.
Large scratch is initialized or grown by its owner worker, then worker-local
counters are reduced after the submission. Both Python and native session
locks serialize complete calls; lock waits release the GIL, and shutdown takes
the same lock order before joining workers. Queue cursor sharing is deliberate;
the remaining possible sharing is at boundaries between adjacent dense output
rows and will be reported as such. Exceptions cancel further claims, wake and
join every worker, then propagate to the caller before a result is returned.
The caller's Python arrays and prepared handles stay strongly held through the
synchronous call; workers see only validated native pointers/handles while the
GIL is released, including the one-worker route.

GIL boundary: Python argument conversion and optional color-field backend
coercion/handle snapshot matching remain GIL-held because they inspect Python
array metadata and may invoke NumPy/Python conversion. After those checks,
query/native-field setup, pair-map validation, worker-owned library preparation,
and scoring are native-only and run outside the GIL (including one worker).
When an older caller omits T204 self-overlap handles, the compatibility
self-overlap fallback remains serial, but its pure-C++ computation also runs
outside the GIL. This fallback is not the prepared T204 path and does not
recompute library terms when a complete prepared handle is supplied.

## Measurement and acceptance

Correctness first: compare all score columns, winners and deterministic ordering
against the unchanged serial/dense reference across heterogeneous real rows and
retained grains; use the declared numerics policy, not a new scoring tolerance.
Exercise worker counts, short tails, empty work, skewed costs, concurrent calls,
exceptions/shutdown and reused scratch. Prove unique work ownership and executor
reuse with counters; sanitizer/race checks where supported. Preserve a legacy
reference arm for controlled ablation.

Commit a bounded benchmark/protocol before execution: matched original versus
T204 versus persistent local-prep, 1/2 physical cores initially, then realistic
T190 strong/weak populations when available. Report complete-call and steady
executor costs, queue/prep/compute/idle spans, allocations, peak scratch and bytes
copied by representation. Query/field construction and pool startup separately;
do not exclude recurring library preparation. Contended timings are advisory.
No minimum speedup is assumed. Independent Sol-medium source/protocol review and
fresh manual T149 are required; no promotion of defaults before acceptance.

## Boundaries and traps

This ticket is the native executor/preparation foundation; T206 adds local top-K
and T207 disk ownership. Do not redesign storage or GPU execution. Traps:
pitfalls 5/7/8/11/16/23/27/28; oversubscription, hidden Python/GIL bottlenecks,
small-task queue overhead, mutable shared query data, false-sharing scratch,
benchmarking startup as steady state or hiding copies outside the timer.

## Working rules

Luna-max implementation; independent Sol-medium review. Follow
tickets/CONVENTIONS.md and doc/NUMERICS_POLICY.md in full. Private ticket branch
and checkout. Preserve sibling work, shared corpora, venvs and builds. Max two build jobs; host timing
requires the orchestrator-granted window, T118 lock/placement/provenance protocol and
committed raw records. Do not push to GitHub.

## Status 2026-10-09 — opt-in implementation integrated; acceptance remains open

The explicit persistent executor and worker-local library preparation are integrated as an opt-in CPU path. The ordinary dense API and default behavior were not promoted. The frozen T204-versus-T205 paired strong-scaling campaign on Roci completed at 1, 2, 4, 8, 16, and 24 physical cores, with 65,536 identical unique pairs at every count. It used three warmups and eleven paired timed calls per arm and cell. All 20 score columns and canonical rank order matched exactly. T118 graded the campaign `decision`: its canonical lock was held, host idle gates passed, and no advisory or refusal was recorded. The raw samples, binary stamps, worker affinity/claim diagnostics, independent review, and full median table are at `results/T205/crossbinary-strong-20261009-root-01/README.md`.

At 24 cores, median complete-call latency was 0.563320 s for the prepared T204 one-shot arm and 0.478509 s for the T205 persistent worker-local-preparation arm, a 1.177x throughput ratio. T205's 1-to-24-core median latency ratio was 18.95x on this fixed workset. This cross-binary result does not isolate persistence alone. The earlier same-T205-binary persistence ablation was near parity at one and two cores; its original T118 record refused decision grade because the repeat counts were stored under noncanonical keys. Its raw records remain unchanged at `results/T205/persistence-ablation-20261008-refused/` and are not used as decision-grade speedup evidence.

The final manual two-build T149 canary passed on clean source commit `056527f2397d3df8001298fd20341139e14c4800`; the sole subsequent commit `047c5725a2f7f983e8dc66956a2b7782e0173c6c` added that report at `results/T149/premerge/20261009T004704Z-056527f2397d-T205-final.json`. The CPU source tree remained `27719b45de50c21152b54e7a5aaa183cbd6a1abd`.

Acceptance is still open for a true fixed-2,048-pairs-per-core weak-scaling campaign, specified but unmeasured in `tickets/T205/weak_scaling_followup.md`; a complete allocator census and per-worker peak scratch accounting; and separate queue, preparation, compute, and idle attribution. No result here establishes those quantities or promotes the T205 path to the default.
