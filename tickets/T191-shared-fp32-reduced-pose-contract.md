---
id: T191
title: Shared FP32 reduced-frame pose contract for CPU shape and analytic color
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T146, T153]
priority: highest
branch: ticket/T191-shared-pose-contract
worktree: <worktree>
artifacts: results/T191/
---

## Context

The author authorized on 2026-10-07: shape and color must consume the same FP32 rigid
pose, not independently normalize/reconstruct it at different precisions.
Prescale query color coordinates into shape's reduced frame once per query,
amortized over the library. Implement this contract and run a matched single-
core benchmark, preferably on Tachi; advisory timing under external host load
is explicitly acceptable. Main `34604258` includes reviewed T184/T185 kernels
and T186 threading. This is a correctness/design invariant plus a measured
optimization, distinct from T188's optional transform micro-optimization.
Luna-max implements; independent Sol-medium reviews. T190 high-core timing
remains held and is not a dependency.

## Scope

1. Document and implement one prepared per-trajectory pose constructed once
   per optimizer iteration, after existing start composition. Normalize and
   build rotation in FP32 once, then share identical prepared bytes with shape
   and color. Neither evaluator nor fallback may independently reconstruct a
   rotation from the quaternion. Keep pose/state private per worker/start/lane.
   Use an explicit checked contract/API and truthful stamps; preserve legacy
   entry points as labelled comparators rather than silently claiming they
   satisfy the new contract. Separate experimental selection until reviewed.
2. Let s=COORD_SCALE, A'=s*A, M=s*R, t'=s*t_physical. Existing library atom and
   color-feature coordinates can remain physical: both consumers use
   B'=M*B+t'. Prescale QUERY color features once in owned immutable query
   preparation, not once per call/batch/iteration. Do not unnecessarily
   prescale library coordinates or change producer storage. Shape/color may
   have different point sets; sharing pose does not imply sharing all posed
   coordinate arrays. Field lattice mapping remains evaluator-specific, not a
   second rigid pose. Retain existing shape spacing/padding/stored gradients.
3. Convert color Gaussian parameters once: for coefficient*c exp(d*|A-B|^2)
   with existing signed decay d, use d'=d/(s*s) on reduced distances and leave
   the physical overlap amplitude/coefficient unchanged. Prepare canonical
   and general matrix entries consistently, including weights, zeros and
   inactive planes. Coordinate reduction also serves analytic shape, not only
   fields. No global fast-math, exp-policy, resolution or precision sweep.
4. Derive reduced-space gradients independently. Color translation descent
   is directly with respect to t', eliminating the current physical translation
   round-trip and 1/s gradient conversion; rotation/half-angle torque must retain
   existing sign/factor and frame. Verify self-overlap/normalization invariance,
   mixing and optimizer learning-rate units; no duplicate scaling. Hoist only
   truly invariant query/matrix work.
5. Primary coverage is shape scalar/analytic SIMD/scalar field/paired/pipelined
   field with vector analytic color11 and standard color16 (2 pairs x4 starts).
   All actual consumers in a supported shared-contract call, including exact
   per-start/winner scoring and scalar analytic fallback, must use that pose.
   Reference arithmetic may accumulate/evaluate in FP64 but must consume the
   prepared FP32 transform, never silently renormalize the quaternion in FP64.
   Retain a separately labelled physical-space high-precision oracle for
   validation of the declared numerical change, not a second production pose.
   Unsupported legacy color-field/other-grain combinations must explicitly
   refuse shared-contract mode or receive a separately reviewed adapter;
   silently falling back to differently posed color is forbidden.
6. Query preparation must own reduced coordinates and effective matrix data,
   validate frame/config/query/matrix identity and lifetimes, and reuse safely
   across calls/threads. Distinguish physical versus reduced buffers in types/
   metadata; reject mismatched prepared handles. Preserve masks, tails, mixed
   queries, caller order, nonstandard-start handling and deterministic ties.
7. Permanent tests: exact shared matrix/translation identity and construction
   count per pose; independent reduced/physical Gaussian value and finite-
   difference gradient fixtures; quaternion norm/start composition; coincident
   shape/color feature points; general matrices/weights/empty planes; atom and
   pair tails; color11/16; all shape backends; concurrent immutable handles;
   own-pose exact per-start/final scoring and stable winners. Declare FP32 pose/
   reduced-color rounding changes under D029; do not require old FP64-pose
   bitwise trajectory identity or weaken the new shared-pose invariant.
8. Commit a bounded matched one-core campaign with unchanged library/query
   populations, four starts/25 steps/mix0.5, new versus labelled legacy baseline,
   both color mappings and at least pipelined-field plus trajectory analytic
   shape on representative small/general-color cells. Reuse existing panels;
   no hard reference mining or full 84-arm tournament. Query preparation/build
   stays outside alignment timing; report setup/bytes separately. Include total
   call rates and causal shared-pose/prep attribution, not inferred gains from
   old instrumented fractions. Larger single-core batches are optional if
   helpful, not another blocked all-core scaling campaign.

## Deciding measurement

Supported shape/color paths provably consume one FP32 pose in one reduced
frame, with correct values/gradients/exact scoring and immutable query reuse;
matched single-core full-combo speed/overhead versus the labelled old contract.
A no-speedup result does not invalidate the shared-pose design requirement.

## Acceptance

Independent Sol-medium source/protocol review before timing and final evidence
review before merge; D029 numerical declaration and independent oracle checks;
fresh exact-source T149 including combined integration. T118 lock, exact cwd,
affinity, source/build/ISA/population/repeat stamps and paired uncertainty.
The author explicitly allows advisory single-core timing on contended Tachi:
retain that grade and visible host/context limitations, never upgrade it to
decision or universal throughput. Do not borrow or require an all-core
reservation; coordinate short low-parallel windows.

## Traps

Prescaling query coordinates without decay/gradient conversion changes the
objective. FP64 reference accumulation is not permission to independently
rebuild the pose. Changing exact reference semantics requires declaration,
not merely relaxed tolerances. Shared transforms cannot make distinct feature
point arrays identical. Preserve noinline/separate-TU codegen/ODR boundaries.

## Execution checkpoint (2026-10-07)

Source, permanent independent scalar/AVX2 numerical tests, declared D029
contract, protocol and runner passed independent Sol-medium review. Complete
Tachi campaign evidence is committed through `07a1457f`, under
`results/T191/tachi_20261007T1837Z_6933f984/`; the earlier reporting failure is
preserved separately and explicitly excluded as incomplete/invalid.

All sixteen measured shape/color arms preserved the panel's full rank order,
Spearman correlation and top-20 set. Cross-contract score and pose trajectory
deltas are recorded descriptively; they are not fixed-pose accuracy errors or
bitwise-parity gates. Paired legacy/shared medians ranged 0.9734–0.9980, so no
speed advantage was demonstrated. Preserve the actual T118 `decision` records
but interpret these measurements as advisory under known host
contention, not an exclusive-host or universal throughput claim.

The shared FP32 transform is **required for correctness regardless of speed**.
Near-parity timing does not justify independent shape/color poses. Retain the
reviewed supported shared-pose contract; legacy FP64 posing is an explicitly
labelled comparator, not the intended contract for the new CPU combo kernels.
Optional T188 planning and T192 scratch ablations are separate decisions.
Final evidence review and composed exact-source T149 passed at `a96d20b0`,
merged to main. Report:
`results/T149/premerge/20261007-cpu-shared-pose-integration.json`; all eight
arms were byte-identical. The supported shared-pose API is available with
explicit `pose_contract='shared_fp32_reduced_v1'` and owned query preparation;
existing legacy entry-point defaults are retained for compatibility, not
presented as satisfying the new shared-pose correctness contract.

## Working rules

Dedicated worktree, private extension builds max2 jobs, read-only
corpus, no shared venv or sibling edits. Own shared-pose implementation; T188/
T189 shared kernel edits must wait or use explicit committed handoffs. T187/
T190 diagnostic scripts stay untouched. Commit contract/tests/protocol before
timing. No GitHub push. Send early design checkpoint and review requests to
the orchestrator, proceed normal steps without waiting for the author to check in, no
self-merge.
