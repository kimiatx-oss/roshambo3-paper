---
id: T207
title: Worker-owned indexed decoding directly into the CPU search pipeline
phase: 2
lane: host-io
status: closed
model: luna
reviewer: sol
depends_on: [T204, T205, T206]
priority: high
artifacts: results/T207/
---

## Sprint closeout — 2026-10-10

Closed for the reviewed worker-owned decoding/preparation/reduction pipeline
and its subsequent public integration. Historical correctness, bounded
throughput and high-core composition retain their source/representation
restrictions:
throughput report (`results/T207/throughput_campaign_20261009/README.md`),
high-core review (`results/T207/composed_highcore_20261009/REVIEW.md`).
T210/T212/T219/T220 supersede checkpoint claims that prepared self, query reuse,
both ranking levels and public routing are still missing. No universal
zero-copy decompression or no-conversion claim follows: required coordinate
conversion remains distinct from reader-to-worker transport.
Future corpus precision belongs to T208; measured RSS, detailed allocation/
phase accounting and independently verified cold-I/O qualification are
deferred T221 work, not implied by warm-cache throughput.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical context

### Reviewed local acceptance tranche, 2026-10-09

Independent 6-Sol-medium review approved `7e2236cd` after requiring current
raw logs and deterministic peer-cleanup synchronization. Raw sample/full96
JSON, 40/72-test outputs and pins are archived under
`results/T207/local_acceptance_20261009/fb2aaa36/`. The full W2 run proves
393216 rows/96 blocks once and exact all20/GID/MID parity. Current RSS and
process HWM are observed diagnostics, not allocation bounds or a hard cap.
The tranche changes only tests/diagnostic driver/docs/results; no production
scan, native kernel or build configuration changed. Composing with reviewed
T167 opt-in integration passed 133 private-package/private-DSO tests;
`results/T207/composed_local_acceptance_20261009/receipt.json` records lineage.
Full T207 remains claimed; this is not default/precision/I/O qualification.

### Active local acceptance assignment, 2026-10-09

The author authorized the post-cloud-setup work split. Assign 6-Luna-max to a new
private clone/branch `ticket/T207-local-acceptance-20261009`; preserve historical
worktrees. Consume merged implementations of T204/T205/T206 despite their
remaining acceptance status: this continuation completes acceptance, not a
new implementation dependent on their closure. T210 owns all cloud execution.

Own T207 acceptance tests/helpers/results and the Python worker-owned scan
plumbing if a demonstrated acceptance defect requires a fix. Initial tranche:
measured memory high-water/budget behavior; merged/split-color and supported
codec/layout coverage; molecule-boundary/tie ordering; exception/cancellation
and decoded-buffer lifetimes. Reuse existing proofs/tests before adding cases.
Do not rewrite kernels, native executor/collector, Engine/config/API, scoring
policy or volume precision. Report any indispensable native change to the orchestrator
for explicit ownership handoff. Local private builds/tests max two compiler
jobs; no cloud builds/profiles/timings and no shared environment mutation.

Commit a coverage/gap matrix and bounded test plan first; the orchestrator reviews scope
before substantial implementation. RSS observations are diagnostic memory
evidence, not throughput. Coordinate the Python scan seam with T167: T207
owns scan internals; T167 owns Engine/config/API adapters and public-seam tests.
Hand off an opt-in stable call contract, not a default promotion. Independent
Sol-medium review and applicable exact-candidate T149 precede merge. This
assignment does not close T204/T205/T206 or T208 by implication.

### Composed measurement follow-up closed (2026-10-09)

The independently reviewed high-core follow-up is archived under
`results/T207/composed_highcore_20261009/`. The author accepted ordinary SMT as
positive (T186 closed) and confirmed T188/T192 closeout with both switches
OFF. Missing factorial16 and Tachi repeats remain accurately absent from the
archive, but no further runs for these hypotheses are queued. This supersedes
the archive's pending-measurement wording as a queue instruction, not its raw
evidence or limitations. No production default was changed.

T207 remains claimed for worker-owned pipeline acceptance/public integration,
not these optional timing cells. Prioritize bounded-memory and public hit
semantics, supported layouts/codecs, cancellation/failure and lifetime
coverage; keep T208 precision/corpus recomputation separate. The completed
conformer-top-K benchmark is not full molecule-top-K or cold-I/O qualification.

2026-10-09 benchmark setup update: the author accepted existing legacy
VAA for algorithm-design timing, deferring precision/recomputation to T208.
`bench/t207_end_to_end.py` uses a distinct opt-in descriptor-bound prepared
shape/color path, both arms consuming the same existing VAA/native conversion
and once-prepared exact-R/P color. Actual native library self evaluations must
be zero in scans; upstream preparation cost remains separately reported and
charged in finite first-use accounting. See `tickets/T207/end_to_end_protocol.md`.
Historical strict recompute correctness receipts remain unchanged. T207 stays
open; no production default promotion, accuracy qualification or high-core
campaign authorization follows from setup.

Rsb3Source already prefetches reads/decompression/packing in a separate producer
pool. The CPU path should instead exploit shared address space and integrate
block ownership with persistent workers. T203 timing excluded disk I/O: it is
not evidence that reading or decompression is a current bottleneck.

## Scope

1. Coordinator parses indexes/maps immutable sidecars once and publishes small
   descriptors (block offsets/sizes, group/row spans, global conformer/molecule
   IDs and metadata references). Persistent workers claim descriptors, read,
   decompress, prepare, align, exact-score and locally reduce. No per-block BSP
   barriers and no coordinate copy to transfer reader-to-worker ownership.
2. One decompression per compressed block per scan, including block-boundary
   molecules. If several compute tasks share a decoded block, share an immutable
   owned buffer with explicit last-consumer lifetime rather than decompressing
   it repeatedly. Test legacy split-color and supported codecs/layouts. Use
   validated T204 sidecars without per-task whole-library fingerprint scans.
3. Consume decoded views directly when supported. Otherwise convert stored
   int16 coordinates once directly into reusable CPU-native working storage.
   Eliminate GPU packing followed by CPU unpacking/copying. Inventory each
   representation, owner, allocation and byte movement, distinguishing required
   int16-to-FP32/pose computation from transport copies. No format rewrite and no
   speculative promise that general decompression can target arbitrary SIMD
   layouts without conversion.
4. Start with a single shared coarse queue and worker-owned buffers. Account for
   the complete CPU budget. If measured read stalls justify async input or a
   bounded decode service, transfer buffer references/ownership without copying
   and prove backpressure/cancellation; two buffers alone do not produce overlap.
   Do not add dense output double buffering in ordinary local-top-K mode.
5. Explicit memory limits for decoded buffers, worker scratch, queries and
   boundary state. First-touch/local reuse; NUMA-aware queues/field replication
   are measured follow-ups, not prerequisites. Coordinator retains only shared
   metadata, bounded scheduling/progress and final top-K merge. Preserve GPU
   source/engine behavior and CPU dense/callback fallbacks.

## Acceptance and deciding measurement

End-to-end reference parity for scores/IDs/ranking, conformer and molecule top-K,
codec/layout variants, row boundaries, empty/short tasks, asynchronous failures
and cancellation. Counters establish each row scored once, each block decoded
once, and zero reader-to-worker coordinate transport copies. Record remaining
conversions explicitly; owned buffers cannot be recycled while referenced.

Compare current source+CPU pipeline with worker-owned pipeline at 1/2 cores,
then realistic strong/weak scaling when a window is available. Separate read,
decompression, conversion/prep, scoring, local and final reduction, idle and
end-to-end time. Report bytes read/written, allocations, peak memory, queue size
and complete thread budget. Warm-cache and verified I/O-inclusive conditions
are separate experiments (conventions pitfall 17 correction); never drop global
caches or mutate shared corpora without explicit permission. Frozen corpus,
T118 lock/placement/build provenance and reviewed protocol required for quoted
timings. No default promotion without demonstrated correctness and review.

## Traps and working rules

Pitfalls 7/9/11/12/16/17/22/23/27/28. Head-of-line waiting, compressed-block
duplicate decoding, implicit GPU layout, nested oversubscription, unsafe buffer
handoff, hidden whole-library copies and cache-warm I/O claims.
Luna-max implementation, independent Sol-medium review and fresh T149 for CPU
scoring/codegen changes. Read full conventions/numerics; private ticket branch,
shared data/venvs/builds read-only, max two build jobs, orchestrator-granted timing
window, own artifacts results/T207/.

## Current checkpoint (2026-10-09)

The reviewed candidate now has a clean-source real-corpus correctness
checkpoint at `ef24c3ba2a15de6a34ffb640bd538dd3c2bf039f`, after composing main's
active-ticket ledger commit `8033041d` as branch commit `921b17e3`. The fixed
6-block selection passed at W=1 and W=2; the fixed 96-block / 393,216-row
selection passed at W=2. All 25 reported invariants hold, including exact
20-column top-K score/GID/MID parity, once-only rows/blocks, and two shared
query-self contexts with exactly two shape plus two color A/A evaluations
total. The full run keeps its 96 per-block library self-overlap fallback
calls explicitly counted. The combined private-package/private-DSO regression
suite passed 100 tests with one expected skip because experimental CPU color
grain 3 is not compiled; it also emits the expected host-only arithmetic-pin
warning. Detailed build/source/query/corpus pins, hashes, raw logs, JSON
reports, memory estimates, baseline scratch-test comparison, and residuals are
in `results/T207/worker_owned_scan_real_correctness.md` and its linked
artifacts.

This does not close T207 or authorize performance claims. Library self terms
still fall back per block; no compatible serialized native reduced-shape
values or color-self sidecar are consumed; native query views and per-block
decode/unshuffle, FP32 layout conversion, pair maps and scoring scratch are not
reused across blocks. The memory figures are estimates rather than RSS, and
real-corpus parity here used merged color only. No timing campaign has run.
The fresh exact T149 canary on the frozen candidate and remaining acceptance
work are outstanding. Keep the ticket open.

## Algorithm-design throughput checkpoint (2026-10-09)

The preceding checkpoint is historical recompute correctness, not the current
benchmark representation. The author subsequently accepted existing legacy VAA
for algorithm-design benchmarking; T208 owns future recomputation/precision
qualification. Both benchmark arms use the same native-converted stored VAA
and once-prepared exact current-R/P color, with actual shape/color self
evaluations zero during every scan. Same-mode all20 score/GID/MID parity holds;
recompute trajectory parity is not asserted for this accepted representation.

The authorized six-cell, fixed393216/96-block warm-cache campaign is complete.
W24/16/8/4 used 3 warmups/11 timed pairs and T118 decision grades. The author
shortened W1/W2 to 1 warmup/3 timed pairs; their raw T118 repeat-count refusals
remain intact and results are exploratory, not formal advisory/decision-grade.
Native CPU source/DSO arithmetic is invariant across the benchmark-only budget
change, and both exact measured source freezes passed fresh official T149.

Worker W24 full outer rate is 140646 conformers/s; paired same-W24 ratio is
1.9226, with important AB/BA dispersion (medians1.9421/1.7660). Once-only prep
and scan versus full boundaries are separate. Raw logs, all152 calls, review
receipts, source/canary lineage and committed reproducible analysis are in
`results/T207/throughput_campaign_20261009/README.md`. This does not close T207,
promote defaults, qualify legacy volume precision, establish measured RSS,
or claim the fastest existing reference pipeline.
