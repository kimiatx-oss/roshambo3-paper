---
id: T197
title: Compare one worker, two physical cores and one-core ordinary SMT under load
phase: 2
lane: host-io
status: closed
model: luna
reviewer: sol
depends_on: [T193, T194]
priority: high
branch: ticket/T197-low-core-smt
worktree: <worktree>
artifacts: results/T197/
---

## Context

### Reviewed closure, 2026-10-08

Independent Sol reviewed final evidence `01143f5f`; results/scripts were merged
without CPU kernel or dispatch changes. On the fixed pre-T196 baseline
`46b82dc7` with the exact T194 binary, R3 scored 4,096 unique pairs plus three
labelled tail repeats using nine warmup calls and 33 timed full calls (11 per
placement). Score hashes and actual worker pins matched throughout. Paired
median speedups were 1.8938x for two physical cores and 1.1545x for sibling SMT.
Interpretation remains advisory; do not multiply these gains by T196's results
or infer high-core scaling. R1/R2 refused records remain unchanged for audit.
See `results/T197/rate_summary.md`. No default or universal SMT policy changed.

The author authorized on 2026-10-08 a low-core ordinary-SMT experiment while high-core
T190 is constrained by host contention. T186's native independent-worker code is
already merged; this ticket is measurements, not another threading implementation
or high-core scaling run. Luna-max executes; independent Sol-medium review.
Assigned to a Luna-max agent, now preparing protocol and runner in a dedicated
worktree. The orchestrator reserves rate windows
separately after Sol review; no whole-host idle prerequisite.

## Scope

Read real physical/socket/NUMA/SMT topology and allowed affinity. Compare one
worker on one physical core, two workers on two separate same-domain physical
cores, and two workers on sibling SMTs of one physical core. Use the same fixed
ordinary population and large enough sustained independent pair work, preserving
batch tails, exact final scoring and row identity. Never assume adjacent CPU IDs
are siblings. Each worker owns complete trajectories: no cooperating siblings,
phase opposition, shared pose barriers, scheduler rewrites or machine settings.

Begin pipelined FP32 shape with analytic color16; use color11 only as one bounded
mapping confirmation, not a full sweep. Record actual worker placement and work,
elapsed imbalance, clock/load/sibling visibility, query+field bytes and NUMA
confounds. A repeated pair list may sustain a small available corpus only if
repeats are labelled (not extra molecules or independent statistical samples).
Do not recreate T190's large unique-corpus obligation for this low-core question.

Preregister same-session rotated paired repeats over the three placements.
Report aggregate pairs/s, latency, physical-2 speedup and sibling-2 speedup
relative to one worker, plus worker diagnostics. Query/field build is amortized
outside rates; launch/join, target preparation and exact finals are included.
Use T118 lock/actual affinity and orchestrator host reservations. Busy-host measurements
remain advisory, no quiet prerequisite and no universal SMT/default promotion.
Repeat a small session rather than sweep every core count.

## Acceptance and working rules

Sol protocol review before rates and final evidence review; serial/thread score
bytes, worker counts and topology checked; clean source/population/build pins.
Reuse T194 canary only if CPU/build inputs match exactly; any source changes
require a separate authorized ticket and fresh canary. Explicitly feed T190
and T161 evidence without claiming high-core efficiency or phase-opposed benefit.

Own tickets/T197 scripts/tests/results only; dedicated worktree or
unique scratch fallback, private builds max2 jobs. No shared kernel/API/CMake,
venv/corpus/sibling mutation. Serialize timing with T159/T189/T196/T198 through
the orchestrator; no self-merge or GitHub push.
