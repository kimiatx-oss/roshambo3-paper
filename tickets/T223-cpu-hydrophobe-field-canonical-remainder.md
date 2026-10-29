---
id: T223
title: Test one shape-and-hydrophobe-field kernel with canonical analytic remainder
phase: 2
lane: kernel
status: claimed
model: luna
reviewer: sol
depends_on: [T218, T220]
priority: highest
branch: ticket/T223-hydrophobe-field-canonical-remainder
worktree: <worktree>
artifacts: results/T223/
---

## Context and assignment

The author authorized 6-Luna-xhigh, 2026-10-10. Existing mixed fields disable the
dedicated canonical analytic helper for the whole call. Test a single focused
alternative: retain fastest field shape, use one Hydrophobe color field, and
keep every other active plane on the dedicated canonical analytic path.
T217's negative top-two experiment is motivation, not a proven universal null.

## Scope and boundaries

1. One explicit experimental fixed plan, chosen before the optimizer loop and
   bound to immutable query/matrix/build/geometry. Discover Hydrophobe by the
   established feature enumeration, not an assumed numeric ID. Only exact
   canonical identity interactions are eligible; noncanonical/custom widths
   retain the existing general route. No automatic production promotion.
2. Reuse existing shape and FP32 color field implementations, stored/interpolated
   gradients, shipped spacing and shared FP32 reduced pose. Build only the
   Hydrophobe field once and retain it across warm public calls. Pick ONE
   existing FP32 color representation before timing using T217 evidence
   (prefer its faster brick arm if supported without a new port); no trilerp/
   brick/half/resolution/subset tournament.
3. Extend the canonical helper narrowly to exclude the selected plane while
   preserving its rawbits-unclamped/factored analytic kernel for the remainder.
   Add the field value/gradient once, with correct frame/torque scales.
   Hydrophobe out-of-grid/unsafe cases fall back to its analytic evaluation
   without double counting or despecializing unrelated canonical planes.
   Exact per-start/winner final scoring remains analytic and unchanged.
4. Small permanent fixtures: selected plane exclusion, mixed analytic/field
   execution, empty Hydrophobe, tails, out-of-grid fallback, shared-pose
   gradient units and noncanonical fallback. Prove both actual field use and
   dedicated canonical remainder use; no per-iteration policy rediscovery.
5. Freeze at most THREE existing-corpus queries using metadata-only hydrophobe
   counts: two ordinary-count cases and one upper-range case, with IDs/counts/
   extents recorded before candidate timing. Reuse T214's small tune/held-out
   correctness panel without mining hard cases or requiring FP64 trajectory
   equality. Apply existing bounded conformer/molecule ranking gates including
   meaningful molecule K41 on the 82-molecule panel, exact finals and ties.

## Deciding measurement and stop rule

Compare with current fastest canonical all-analytic COLOR plus identical field
SHAPE, starts/steps/population/compiler and exact finals. Query field build/
packing is excluded from warm alignment, reported separately for finite reuse.
Initially one physical core, one warmup and five alternating short paired
repeats on the fixed small library subset per query. No expanding query sweep.

If no typical-count case has a repeatable throughput gain above observed paired
variation, STOP negative after correctness/review; no full-library sweep.
If a typical case wins, confirm that ONE case at 24 physical cores on the
staged full public-screen corpus, one warmup/two timed passes per arm.
Upper-range-only wins are conditional, not typical-query promotion.
Record raw samples/cost split and existing T118 exploratory/refusal labels.
No eleven-repeat campaign, SMT matrix or second representation sweep.

## Acceptance and handoff

A reviewed bounded win or negative closes the hypothesis. Report ranking
tradeoffs honestly; exact final scores do not recover missed optimizer poses.
No universal field cutoff or scientific optimum claim. Fresh exact-candidate
T149 and independent Sol review before any source merge; keep default unchanged
unless separately authorized. If an indispensable interface redesign appears,
report it rather than expanding this ticket.

## Working rules and cloud sequencing

Read CONVENTIONS.md, CPU-COLOR-CLOUD-EXECUTION.md, T217 evidence and T218
composition. Private branch/worktree, `<scratch>` for every new build/run/scratch,
max two build jobs; corpora read-only, shared installs untouched. Local design/
implementation/correctness can start now. NO cloud build/profile/timing until
the orchestrator transfers the exclusive lease after T222. Hold canonical host-qualified
CpuLock; no dedicated-host load-average gate. Push only to the development repository.
