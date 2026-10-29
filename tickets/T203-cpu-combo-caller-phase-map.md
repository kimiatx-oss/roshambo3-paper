---
id: T203
title: Map CPU combo caller phases before optimizing preparation
phase: 2
lane: research
status: closed
model: sol
reviewer: sol
depends_on: [T200]
priority: highest
branch: ticket/T203-caller-phase-map
worktree: <worktree>
artifacts: results/T203/
---

## Context

The author requested exclusive phase attribution before targeting self overlaps. T200
found 0.426 s caller CPU in 0.865 s wall at24 workers, but not a phase breakdown.

## Scope

Diagnostic-only private coarse clocks around Python preparation, native validation,
views/copies, query handles, shape target workspace allocation/preparation, color
start packing, query self overlaps, library shape and color self overlaps, worker
region, result metadata and destruction. Same frozen T190 strong65536 group5/general
population, four starts,25 updates, mix0.5, field shape/library_atom8/color16.
Query field construction outside alignment. Ordinary reviewed T199 DSO is baseline;
private diagnostic build must pass full-output parity before any measurements.
Measure1 and24 workers,3 warmups/11 paired repeats with clocks enabled/disabled.
No production math, cache, scheduling or default changes. No corpus mutations.

## Deciding measurement

Rank exclusive caller phases by wall and caller CPU. Keep worker-region caller
CPU separate from worker-region wall and summed worker CPU. Require closure to
same-call total, explicit Python/native residual and overhead/build caveats.

Execution completed on quiet Roci at private evidence candidate `de635d06`:
ordinary baseline30/30 calls and diagnostic58/58, all score/winner/census and
placement checks passed. Native-free replay3/3 tests passed. At24 workers,
library shape self-overlap153.9ms and color self-overlap177.5ms consume77.6%
of caller CPU; outside-worker wall427.1ms (49.2% of full call). Next bucket:
color start packing44.2ms. Full report: `results/T203/README.md` on main.
Independent Sol-medium review approved evidence closure on2026-10-08. Corrected
report separates same-call aggregate noncaller CPU9707.205ms and worker-region
caller CPU1.056ms, with attribution caveats. Evidence-only commit
0d62de1992f7e16b890ff34f00fbab647340704a imported report/raw journals/runner/tests;
diagnostic CPP remains archived on its private branch, not production. The orchestrator
replayed native-free checks on main (3/3 passed). All timing remains advisory.

## Acceptance

T118 canonical host lock, topology pinning, host context, exact score and winner
checks, archived raw journals, private build provenance and source committed before
running. Diagnostic findings advisory; original source and reviewed build untouched.

## Traps

Census/per-iteration timers perturb execution; do not use them for quoted rate.
Clock boundaries cannot isolate allocator internals or identify bandwidth causes.
Native temporaries must be destroyed before timing the cleanup boundary. Cross-build
parity and disabled-instrumentation baseline mandatory; no subtracting other calls.

## Working rules

Use tickets/CONVENTIONS.md. Private build max2 jobs; serialize measurements.
The author authorized the experiment on 2026-10-08. Keep monitoring until completed.
Independent review required before landing diagnostic artifacts; no kernel merge.
