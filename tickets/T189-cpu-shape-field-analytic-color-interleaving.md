---
id: T189
title: Interleave field shape with analytic color within one CPU combo worker
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T193, T194]
priority: high
branch: ticket/T189-shape-color-interleaving
worktree: <worktree>
artifacts: results/T189/
---

## Context

### Reviewed bounded null closure, 2026-10-08

Six ordinary color16 cells and one color11 control passed full score-byte,
winner and gradient/exact-final census parity across four schedules. Seven
one-core Roci rate cells found no paired interval above the pinned floor;
prefetch usually regressed. All session results remain advisory. Independent
Sol review cleared `629d7af3` for results-only closure. Retain the existing
serial production schedule; no experimental selector, prefetch kernel, CPU
API or CMake change was imported. The complete candidate is preserved on the
branch `ticket/T189-low-core-interleaving`; see
`tickets/T189/REPLAY.md` for its exact source and replay boundary, and
`results/T189/rates_roci_20261008_R1/summary.md` for all contrasts. Conditional
two-core confirmation was not warranted. This closes the bounded experiment,
not every possible future software-pipelining design.

### Low-core continuation, authorized 2026-10-08

Start current main `7bdf58bd`; T195's reviewed advisory phase diagnostic now
supplies direct current-source context (color-gradient ~0.036–0.038 s and
field-shape ~0.0073 s in g5 canonical), not exclusive fractions or proof of
latency overlap. Historical T187 closure and whole-host quiet are not blockers.
Luna-max implements; Sol-medium independently reviews. NEW dedicated branch
`ticket/T189-low-core-interleaving` in a fresh dedicated worktree.

Start retained color16 with pipelined FP32 FIELD SHAPE, color11 a bounded
control. Compare current serial shape-then-color, reverse order, and at most
one bounded within-thread pipeline across independent chunks/trajectories.
Prepare shared pose once and preserve the same bytes for both consumers.
Preserve each component's accumulation order, optimizer update barriers and
exact per-start/winner scoring; no reassociation or different pose per component.
Shared transforms alone are already adopted, not a new candidate. Do not pay
extra repacking or weaken a serial comparator to fabricate an overlap win.

Preregister one-core short rotated paired full-combo runs on existing ordinary
inputs; two physical cores only as bounded confirmation. T118 lock, actual pin,
load/SMT-sibling visibility and orchestrator host reservations; busy records remain
advisory. Report code size/register spills where tools permit and observer
limits, no quiet-host prerequisite, no new precision/resolution/SMT phase
opposition. Null findings retain the simpler schedule. Coordinate shared-file
ownership BEFORE edits with T196: evaluator tuning versus scheduler adapters,
dedicated branches, no sibling mutation. Protocol/source review before rates,
fresh exact T149 final CPU source and final Sol evidence review before merge.

The author approved this next direction 2026-10-07. The integrated fast path combines
field shape sampling and compute-heavy vector analytic color. This differs
from T160's interleaving of field and analytic COLOR planes, and requires no
color-field policy. Luna-max implements; independent Sol-medium reviews.
T187 must first identify remaining latency/compute overlap opportunity.

## Scope

Compare shape-then-color, color-then-shape, and one bounded within-thread
software-interleaved schedule across independent atom/feature or trajectory
chunks. Preserve pose state, per-component accumulation order unless explicitly
D029-declared, full update loop, exact final scoring and stable ties. Reuse
prepared fields/target layouts; do not transform/repack merely to enable an
unfair comparator. Start best measured field shape with analytic color11;
confirm color16 only if the schedule admits a genuinely distinct comparison.
Bound pipeline depth/prefetch distance; report register pressure/spills/code
size and causal schedule ablations. Compare against the strongest existing
serial integrated path, not an intentionally weakened endpoint. T186 scaling
evidence informs a bounded multicore confirmation when available.
Phase-opposed SMT belongs to T161 afterwards: independent complete trajectories
only, no cooperating siblings or shared-pose barriers. Do not dispatch that
larger scheduler experiment before ordinary SMT and this overlap evidence.

## Deciding measurement

Whole-combo gain from causal schedule difference on matched populations, with
one-core and selected multicore confirmation. Counters explain but cannot
prove overlap. Null findings retain the simpler serial schedule.

## Acceptance

Source/protocol/final evidence Sol reviews, permanent pose/gradient/exact-final
regression tests, clean source stamps, T118 paired repeats/host gates, fresh
exact integrated T149. Field build outside rates; no defaults or precision/
resolution changes. Record losing arms and bounds reproducibly.

## Traps

Additional live state can erase latency hiding through spills. Reassociation,
changed useful work or omitted exact scoring cannot masquerade as scheduling
gains. SMT phase opposition must beat ordinary SMT, not just one worker.

## Working rules

Dedicated worktree/private max2-job builds, committed scripts/results,
read-only corpus, host reservations and no sibling/shared-env edits. Coordinate
shared kernel ownership with T188; execute those source changes sequentially
unless an explicit nonoverlapping handoff is agreed. Scoped Tachi sync
authorized; no self-merge.
