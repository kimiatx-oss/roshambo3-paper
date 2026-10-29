---
id: T199
title: Fuse CPU color double pose writes with the retained FP32 coordinate pack
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T196]
priority: high
branch: ticket/T199-cpu-color-fused-pose-pack
worktree: <worktree>
artifacts: results/T199/
---

## Context

### Reviewed closure, 2026-10-08

Merged the single fused pose-to-FP32-pack candidate after final Sol approval
of `d81e7c38` (`sol-t199-evidence-d81e7c38-20261008`). Two separately
authorized CPU0 sessions met the preregistered advisory adoption gate:
canonical color16 paired median speedups 1.0410x and 1.0392x,
general-asymmetric color16 1.0210x and 1.0248x, and canonical color11 control
1.0275x and 1.0226x. All four color16 confidence lower bounds clear the pinned
host floor. These are bounded Roci observations, not universal throughput or
grain/default promotion. Full integrated twelve-cell score, winning-start,
census, rank and top-20 parity passed; evaluator-local fixtures supply the
separately identified internal edge coverage, not all-cell internal-value
observations.

Fresh exact-source T149 tested clean source `68017733`, with all eight OFF/ON
arms byte-identical; report-only `ff3f85b7` passed independent Sol review
(`sol-t199-t149-canary-ff3f85b7-20261008`). CPU/build inputs stayed unchanged
through the evidence merge. Evidence, failed-attempt record and reproduction
instructions are under `results/T199/`; the earlier untracked diagnostic
correctness attempt remains preserved in the private clone and is not claimed
as accepted evidence. No precision, polynomial, optimizer, pose contract,
field routing, or exact-final semantics changed.

T196's rank-1 support-screen change is merged and closed. It passed exact
12-cell parity and recorded advisory one-core gains of 1.073–1.243x. Its
rank-2 follow-up deferred fusing pose writes with the FP32 coordinate pack.
The current production CPU source tree is `ea834fd982cf03786d1c591e48fc862e8d376bc0`
at main `da1abe85eacf8cb5a53dcd28f3189e31f248ccc7`.

T187's current-source group-5 color16 diagnostics attributed 0.000679422 s
(canonical) and 0.000668019 s (general asymmetric) to `pose_soa_pack`, against
ordinary full-call medians of 0.012290336 s and 0.018916084 s respectively.
The corresponding pose-transform attributions were 0.000625242 s and
0.000625542 s. These phase timers are instrumented, nested attribution, not
exclusive costs or rate savings. They justify one bounded causal test; they do
not predict the result.

## Scope

Test one candidate in
`src/roshambo3/backend/_cpu_src/color_conformer_kernel.cpp`: have the existing
`pose_target_block` optionally emit the vector path's FP32 SoA coordinates as
it writes each already-computed double posed coordinate. Keep the double
buffer and its current expression/order intact. Each FP32 value must be the
same `float(existing_double_coordinate)` value as the current pack. Do not
reconstruct a pose, recompute a transform, or perform transformed-coordinate
math in FP32.

The candidate must preserve the existing `pair_supported` support/fallback
decision. FP32 emitted before `pair_supported` is only a cache write: it must
not participate in support screening or alter `simd_mask`. For each live
coordinate, cast only finite values inside the same accepted coordinate range;
preserve the normal cast's signed-zero bytes. For a non-finite or out-of-range
double, do not cast it: stage neutral `+0.0f` so this call cannot expose stale
workspace data through a broad SIMD load. Existing lane/type masks must keep
those neutral values from affecting support, score, gradients, or term counts.
Inactive/tail slots may retain prior storage only where those same masks prove
they are not consumed, including after workspace reuse. Preserve the existing
coordinate layout and write only live `n_valid` lanes and `library_count`
entries. Tests may inspect internal workspace values through evaluator-local/
native tests; do not add a public API for this check. The reviewed broad
matrix/ISA gate may move after pose validation/setup and output/census reset,
but before `pose_target_block`, so scalar-only calls avoid FP32 workspace
resizing without changing validation/exception order. If safe emission needs
another traversal, changes a support mask, or adds enough work to defeat the
saved pack pass, record a null result and keep the baseline.

The change is limited to this one pose-to-pack path. Keep
`posed_library_xyz_physical` derived from the double pose for physical-grid
sampling. Leave the preposed preparation/consumption contract intact and test
it. Keep shared FP32 pose bytes, support/fallback, field routing, score and
gradient arithmetic, exact-final calls, precision, polynomial, thresholds,
grain/default selection, optimizer, scheduler, and memory budget unchanged.

Use the same read-only ordinary groups 3/5/7 inputs and row identity as T196:
one query plus the first 128 following library rows, start mode 1, four starts,
25 steps, mixing 0.5, one thread, pipelined-FP32-field SHAPE with analytic
color. Use the T196 rank-1 baseline build from source commit
`b41b0d41d7d86f6d5ef4a87b4b2790c60d6485aa` (CPU source tree
`ea834fd982cf03786d1c591e48fc862e8d376bc0`) and compare it to one candidate.
`da1abe85eacf8cb5a53dcd28f3189e31f248ccc7` is the T199 branch's comparison
checkout anchor, not the baseline build source. Do not add a second candidate
or a grain search.

## Deciding measurement

First require baseline/candidate exact parity in all 12 cells:
groups 3/5/7 × canonical/general-asymmetric matrix × color11/16. Then collect
paired one-core full-call rates in only these three preregistered group-5
cells: canonical color16, general-asymmetric color16, and canonical color11 as
the control. Report every paired latency and ratio, per-cell median, and 95%
paired bootstrap interval. The positive-rate criterion is a median speedup of
at least 1.02x in each color16 cell, with each interval's lower bound above
the applicable pinned T118 host floor, and a color11 control median no worse
than 0.99x. For Roci, use the floor 0.007412974607446815 from
`tickets/T189/protocol_v1.json` (`timing.uncertainty`), so each color16 lower
bound must be strictly greater than 1.0074129746074468. Before timing on any
other host, pin that host's applicable measured T118 floor and its source in
the protocol; do not reuse the Roci value.

Collect two separately orchestrator-authorized, same-physical-core sessions, each
containing all three paired cells. In each session, both color16 cells must
independently meet the median and lower-bound criteria above, and the color11
control median must remain at least 0.99x. Keep both sessions labeled
advisory. A single advisory session cannot support the merge throughput claim.
There is no whole-host-idle prerequisite; if the bounded criteria are not met,
report null or inconclusive and do not merge the source change.

The bounded T199 adapter conservatively treats every measured session as
advisory; it has no grade-promotion flag. Before timed workers start their native census
preflights, the coordinator pins itself to the selected physical CPU and holds
the canonical T118 CPU lock. Each worker pre-merges the common options and
per-cell inputs into one immutable kwargs mapping before warmups. The timed
interval wraps only its direct `cpu.score_pairs(**prepared_call_kwargs)` call
and return. Option construction, digest/finite checks, JSON, and IPC remain
outside the interval. The standalone `--preflight-only` path is an untimed diagnostic
and does not qualify as rate evidence. Preserve inherited
`paired_rank1_rates.json` byte-for-byte and store T199 thresholds/interpretation
separately in `t199_interpretation.json`. The inherited raw report's T196
ticket, `candidate_screen`, and rank fields are historical runner-schema labels,
not T199 scientific rank or variant claims; the separate T199 report carries
the T199 identity and interpretation.
The inherited generic frequency-scope string also describes both grains for
each matrix even though the T199 general matrix has only color16; use T199's
exact `timing_cells` and raw cell keys as the sampled-cell authority.

Rates are uninstrumented full mode-3 `score_pairs` calls. Include per-call
target preparation, shared pose, all 25 updates, four distinct exact
per-start finals, and the distinct winner rescore. Build the prepared shape
query/field once outside the timed calls; do not include setup in rates or omit
the per-call work above. Instrumented phase timers are diagnostic only. No
two-core confirmation, counter collection, or whole-host-idle prerequisite is
part of this ticket.

## Acceptance

- Sol approves the source and protocol before any paired rate run; the orchestrator reserves
  the one-core T118 window after that review.
- The accepted 12-cell receipt proves exact public score and winning-start
  bytes, evaluator census/final-evaluation counts, population identity, full
  ranking, and top-20 order. Evaluator-local fixtures separately cover support
  and fallback masks, edge/tail and workspace cases, posed-buffer behavior,
  preposed/physical-field paths, and six descent outputs against fixture
  references. The full-panel runner does not expose internal per-lane masks,
  six descent outputs, or individual per-start exact-final values; those are
  not claimed as 12-cell observations.
- Exercise finite and non-finite coordinates, range rejection, inactive lanes,
  short `library_count` tails, reused workspace, the physical field buffer,
  and preposed preparation. For supported live coordinates, the FP32 buffer
  must equal the cast of the unchanged double buffer. Existing final-score
  evaluation counts must remain 128×4 per-start plus 128 winner rescoring per
  call.
- Use the existing Release CPU build and T118 actual-affinity/lock protocol.
  Preserve all host-load and sibling-visibility records; measurements under
  contention remain advisory and do not require an idle host. If T118 marks
  the session advisory/busy, the two independent same-core sessions above are
  required for this bounded source-adoption claim; they do not authorize a
  general or default throughput claim.
- Merge only if the positive-rate criterion above passes, exact parity holds,
  and a fresh exact-source T149 canary is green on the final candidate source.
  If the safe fusion is not beneficial, close with the negative/null evidence
  and retain the current source. No grain or production-default promotion is
  authorized.

The accepted no-timing receipt at
`results/T199/roci_20261008T144135Z_full_correctness/` remains bound to protocol
SHA-256 `55256b717c18260c333bbc0648b46ff248cb88da53feb9b38503b78c7014236d`.
The current protocol narrows only the coverage claims to fields actually
recorded by that receipt and existing evaluator fixtures; this clarification
changes no source, build, population, input, or arithmetic and is not a new
correctness replay.

## Traps

- **Pitfall 7:** compare optimized Release builds with the same compiler flags;
  a manual `-O0` host build invalidates this small CPU comparison.
- **Pitfall 11:** a faster pack phase does not establish a faster optimizer call.
  Decide from the uninstrumented full call with exact finals included.
- **Pitfall 18:** color work follows padded feature populations. Keep the same
  frozen inputs, row order, and cell in every paired comparison.
- **Pitfall 23:** keep any future runner and emitted number-producing script in
  `tickets/T199/` and commit it before use.
- **Pitfall 24:** T187's phase timings are attribution only; do not present them
  as additive time or a measured speedup.

## Working rules

1. Work only on `ticket/T199-cpu-color-fused-pose-pack`; do not edit main or a
   shared worktree. This design branch is an isolated scratch clone; the orchestrator owns ledger/index integration.
2. Share the read-only corpus by path; do not copy it. Any script that produces
   a result belongs on this branch under `tickets/T199/` before it runs, and
   results belong under `results/T199/`.
3. Match T196's source/build/input stamps and T118 one-core affinity. The orchestrator
   schedules the rate window after Sol review. Do not wait for whole-host
   quiet; record contention and keep the run advisory when T118 says so.
4. Run the exact T149 procedure in `tickets/CONVENTIONS.md` on the final
   source commit before any later merge. Any source or build-input change after
   that `source_commit` requires a fresh run. No self-merge or remote push.
