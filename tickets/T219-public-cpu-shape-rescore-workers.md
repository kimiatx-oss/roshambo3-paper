---
id: T219
title: Route public CPU shape and rescore screening through persistent workers
phase: 2
lane: implementation
status: closed
model: sol
reviewer: sol
depends_on: [T211, T212]
priority: highest
artifacts: results/T219/
---

## Reviewed outcome (2026-10-10)

Explicit public CPUWorkerOptions now supports retained shape-only and
shape-search/color-rescore workers, including shape-only corpora without a
color enum. Tested source `f490c880`, report-only head `b12d8890`, independent
review `d427bea1`: 173 focused tests passed without skips; fresh 13-arm T149
passed with no moved arms, clean stable provenance, and only its exact report
after the tested source. Tests cover actual public dispatch, full-row mode
parity, query/Source-self reuse, molecule reduction, native bounds and lifecycle.

Ordinary implicit shape/rescore defaults remain unchanged. Stored shape VAA
is consumed; exact physical-frame color self is prepared once per Source/
descriptor binding, not borrowed from combo's reduced frame or claimed to be
serialized. No approximate default promotion, historical T149 red-control
closure, or throughput gain is claimed. The implementation tranche is closed;
T218 owns the following same-binary public three-mode timing and automatic
policy qualification.

## Context

T212 intentionally exposed combo workers only. Preparing T218's final public
three-mode comparison revealed that shape-only and shape-optimize/color-rescore
still use the synchronous block route and rebuild fields. T211's ModeScan
helper can measure these kernels, but is not the public screening API. Close
this integration gap before quoting a public shape-versus-combo ratio.

Assigned 6.1-Sol-medium (Opus), independent 6-Sol-medium review. Reuse the
existing worker-owned implementation; this is not another harness project.

## Scope

1. Extend the retained worker route and public facade to the existing supported
   shape-only and shape-optimize/color-rescore modes, preserving their actual
   objectives, four-start schedule and exact final scoring. Do not implement
   rescore as combo or require color features/interaction matrices for a
   shape-only input that does not otherwise need them.
2. Preserve dynamic worker ownership, worker-local preparation and bounded
   reduction, serialized prepared-self reuse, shared FP32 pose, GIL release,
   field reuse and memory accounting. Keep unsupported configurations explicit
   rather than silently changing their calculation. Conformer/molecule ranking
   semantics must be stated and tested, not inferred from attached MID arrays.
3. Reuse bounded immutable query contexts across blocks and repeated public
   runs for each supported mode. Cache keys, mutation/build/policy invalidation,
   failed-run cleanup and memory refusal must remain correct. Shape and rescore
   must not silently execute optimizer color work or build unused color fields.
4. Add focused public-route/native parity and lifecycle tests. Prove actual
   api.screen dispatch and query reuse, not merely calls through ModeScan.
   Document supported settings and remaining divergences. Leave approximate
   optimizer defaults and the general interaction fallback unchanged.

## Acceptance and measurement

Staged routing boundary: expose the new modes through explicit public
CPUWorkerOptions first. Ordinary implicit shape/rescore currently use a
small-input analytic crossover and recomputed-self normalization; switching
them automatically to FIELD/stored-VAA would change existing semantics.
Preserve that ordinary default in this ticket, test it, and document the
explicit fast route. T218 must separately qualify any automatic default policy.
The three-mode comparison supplies explicit worker options for all arms; it
is public api.screen throughput, not evidence that implicit shape defaults
already use workers.

Independent source review and fresh exact-candidate T149 are required before
merge, with coverage of newly exposed scoring modes. A small correctness panel
and one smoke scan suffice during implementation. After approval, reuse the
existing runner to compare actual public shape-only, shape-plus-color-rescore
and full-combo screening on the same binary, query, corpus and schedule at
24 physical cores and 48 SMT threads. Report conformers/s, scan versus public
boundaries and cold setup separately; one warmup and two timed repeats are
exploratory unless the standing decision-grade requirements are met. Do not
delay integration for a new framework, huge accuracy corpus or repeat sweep.

## Traps

D012/D030: helper kernel rates cannot be labeled public-route rates; results
from different objectives, matrices, populations or binaries are not a ratio.
Final conformer TopK with attached MIDs is not independent molecule TopK.

## Working rules

Follow CONVENTIONS.md and CPU-COLOR-CLOUD-EXECUTION.md. Isolated branch and all
scratch/build directories under `<scratch>`; local work on roci only. Coordinate
exclusive cloud compute with the orchestrator; no load-average gate on the dedicated host.
T218 remains responsible for final composed policy qualification; T219 does
not promote approximate defaults or close historical ranking/corpus work.
