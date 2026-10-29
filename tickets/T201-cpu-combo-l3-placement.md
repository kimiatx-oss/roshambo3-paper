---
id: T201
title: Compare compact and L3-spread CPU combo placement
phase: 2
lane: host-io
status: closed
model: luna
reviewer: sol
depends_on: [T199]
priority: highest
branch: ticket/T201-combo-l3-placement
worktree: <worktree>
artifacts: results/T201/
---

## Context

The author authorized cache-aware Roci placement after reviewed T190 realistic
scaling. Roci has four separate L3 domains with six physical cores each,
despite one exposed NUMA node. Sequential CPU numbering is compact at4cores
and spans only two L3 domains at8cores. Determine whether physical placement
changes throughput without conflating worker count, SMT or kernels.

## Scope

Frozen T190 strong65536 population, current T199 ordinary Release artifact,
pipelined FP32 field shape/library_atom8 + analytic color16. Compare compact
vs balanced L3-spread physical4 and physical8 masks, deriving topology from
sysfs package/core/thread siblings/cache shared_cpu_list. Compact8 is the
minimum feasible two domains (6+2); spread8 uses2/domain. Spread4 uses1/domain.
No SMT, worker-count sweep or changing thread pool. Strict native singleton
affinity must honor exact selected masks; reject incomplete/unknown topology.
Reuse prepared query handles, exclude field construction, include all target
setup and exact finals. Both arms3warmups/11rotated paired timed calls percell.
Keep correctness, worker placement/load diagnostics separate from rates.

## Deciding measurement

Within-session paired compact/spread full-call ratios at4 and8workers with
raw samples/paired95%intervals. Infer placement sensitivity only; no causal
bandwidth/cache diagnosis without supporting profile evidence.

## Acceptance

Independent Sol-medium runner/protocol review before rates and final evidence
review. Exact source/build/canary/population hashes, same score bytes/winners
and census. Canonical T118 host lock, actual selected core masks, observed
worker placements, thread caps and quiet context. All comparisons advisory.

## Traps

NUMA node count is not L3 count. Adjacent logical CPU IDs may be SMT siblings.
Do not silently remap a requested spread mask via a physical-core helper.
No aggregate idle-core clock median as active-cell frequency evidence.

## Working rules

Luna-max (haiku), Sol-medium (opus). Private branch/checkouts, own T201 scripts/
tests/protocol/results. No kernel/native build required. Prepare in parallel
with T200 but the orchestrator grants serial measurements; never benchmark concurrently.

## Outcome

Completed the reviewed four-cell Roci campaign on the frozen strong-65536
population and ordinary T199 Release DSO. Compact and spread placements
produced matching score/winner hashes and exact census; the canonical T118
lock, quiet-context checks, and singleton worker placements passed.

The paired spread/compact throughput ratio was 0.9929 at four workers
(95% within-session bootstrap interval 0.9892–0.9988) and 0.9917 at eight
workers (0.9470–1.0079). This run shows no throughput advantage from spreading;
the small four-worker difference favored compact. T118 marked the result
advisory because frequency polling was disabled, and the single run supports no
causal cache/bandwidth claim or production-default change. Raw evidence and the
approved evidence-review receipt are under `results/T201/roci_20261008_R1/`.
