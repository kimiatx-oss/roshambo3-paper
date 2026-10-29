---
id: T224
title: Bound canonical CPU color scheduling and SIMD micro-optimization
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T222, T220]
priority: highest
artifacts: results/T224/
---

## Merge closeout

This closeout supersedes the status statements below.

Merged after independent Sol approval of tested a14a5dc4 / report b83701a1.
Fresh exact-candidate x86/native T149 pass all 14 arms; ARM helper API corrected
and prior native cache preserved. Standardized T227 same-query/target comparisons
show 6.49% (4P), 6.98% (16P), 6.93% (8P16T) whole-scan throughput gains, exact x86 outputs
unchanged. The old different-query confirmation does not establish regression.
Retained optimization is now mainline. See results/T224/README.md and
results/T227/x86/README.md. Historical T149 counter obligation remains separate.

## Context and queue state

Dispatched at the author's request, 2026-10-10, to Luna-xhigh. Benchmark lease: C4
(the cloud x86 VM); T226 independently owns C4A. Consume T222's reviewed/corrected
profile at `bdb6fd43` (private report).
The wrapper's 29.31% flat self includes checks, loads and transforms, not only
validation; canonical analytic 16.78%, shape 12.07%, optimizer 10.09%.
First hypothesis: hoist immutable query eligibility/plane validation out of
iteration work while retaining all dynamic posed-target safety checks. Choose
at most one second load/scheduling hypothesis from the profile/linked assembly.
Expect incremental rather than dramatic gains;
10-20% is an ambition, not measured headroom or a required success threshold.

## Scope

Select at most TWO narrowly justified changes: independent accumulators/bounded
unrolling to shorten dependency chains, fewer redundant loads/masks, or hoisting
provably invariant validation/plane bookkeeping. Retain required dynamic
safety checks, exact canonical predicate, general fallback, shared pose, exp
mode and exact finals. Inspect generated linked assembly for spills/code size.
No new approximation, full grain tournament, hybrid fields, worker redesign
or ARM work. AVX-512 is not an automatic additional arm; if the profile suggests
an ISA redesign, propose separate scope before implementation.

## Measurement, acceptance and stop

Reuse the existing small correctness/ranking panel and public screening runner.
One-core paired short comparison first, identical useful workload and inputs.
Only a promising winner receives one 24P full-corpus confirmation (one warmup/
two timed pairs). Stop negative if neither change wins beyond observed variation;
do not broaden the candidate set. Report kernel versus whole-screen boundaries,
raw paired variation and exploratory grades; don't multiply independent gains.
Independent Sol review and fresh exact-candidate T149 before source merge.
Defaults require separate approval, not implied by this ticket.

## Working rules

On later dispatch follow CONVENTIONS.md and CPU-COLOR-CLOUD-EXECUTION.md.
Private worktree/build/install; `<scratch>`, max two build jobs; exclusive
coordinator-granted cloud lease and host-qualified CpuLock. No load-average gate or
benchmark harness expansion; shared data/installs untouched, development repository only.

## Final composed candidate checkpoint (2026-10-10)

The candidate is ready for independent review and fresh T149 on the exact
composed x86/ARM source. The x86 behavior measured in T227 is unchanged; the
final patch guards the new cache storage/refresh/lookup to x86-64 and retains
the existing AArch64 NEON plane-vector API and query-plane cache. Focused
cache activation, unsafe fallback, and repack-refresh fixtures cover both
architectures. The independent source review found no remaining blocker.

Focused pre-gate checks passed on both hosts: the x86 AVX2/scalar fixture, an
ARM C++ safe/unsafe/repack cache-only invocation, and the existing native ARM
NEON screening tests (including inactive-plane dispatch). The full legacy C++
fixture has AVX2-specific late expectations and is not valid as a whole-fixture
ARM gate; the report records this limitation. Fresh exact-candidate T149 on
C4 and C4A remains required.

See `results/T224/README.md` for the earlier
negative 24P result, the positive standardized T227 matched panel, provenance,
cross-ISA tolerance evidence, and pending exact-candidate T149 reports. This
ticket remains open until review/integration; ready does not promote defaults.
