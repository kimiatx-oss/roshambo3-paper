---
id: T198
title: Measure retained color11 versus color16 across batch occupancy and heterogeneity
phase: 2
lane: research
status: closed
model: luna
reviewer: sol
depends_on: [T193, T194]
priority: high
branch: ticket/T198-color-batch-occupancy
worktree: <worktree>
artifacts: results/T198/
---

## Context

### Reviewed bounded closure, 2026-10-08

Sol reviewed evidence `8d546de6`: all 11 real-panel cells and both grains
passed exact prepared/default, reversed-order, prefix and final-score/census
checks. Two separate Roci sessions each recorded 66 warmups and 242 timed full
calls. Color16 was 30–33% faster for one/two-pair cells and 15–19% for four-pair
cells; ten cells favored it beyond the floor in both sessions, while the
homogeneous eight-pair cell remained unresolved. All interpretation is advisory
and panel-specific; no new dispatch threshold/default is justified. Results
and reproducible scripts are merged; CPU/API/CMake remain unchanged. See
`results/T198/roci_20261008_R1/README.md` for all paired intervals and exact
source/build/population pins. Both retained grains remain available.

The author authorized on 2026-10-08 low-core occupancy tests. Color11 owns one conformer
pair per AVX2 lane; color16 owns two pairs times four independent starts.
T195's 128-row cases do not determine short-batch/tail or heterogeneity behavior.
Luna-max executes; independent Sol-medium review. No new grain search.
Assigned to a Luna-max agent after its reviewed T159
handoff. Protocol/runner preparation is authorized; the orchestrator reserves native
correctness/build/rate windows separately. Record the selected source pin.

## Scope

Compare retained grains11/16 with the same four-start schedule and mandatory
shared pose at pair counts1/2/4/8/16 plus one ordinary sustained anchor. Include
short SIMD tails and a small preregistered homogeneous versus heterogeneous
real feature-count panel, especially few conformers per library molecule.
Record canonical molecule/conformer IDs and pair order; count pairs separately
from molecules. Use deterministic existing read-only selections, no mining,
copies, fabricated feature populations or zero-padding as useful work.

Use pipelined FP32 shape initially; trajectory analytic shape is a bounded
confirmation only if shape execution grain materially explains a reversal.
Report useful/issued lanes, pack/setup and per-start/winner census separately
from uninstrumented latency/throughput. Query prep/build stays outside rates;
per-call target setup and exact scoring remain inside. Small-batch overhead
is the question here, not an excuse to tune T190's sustained scaling edges.

Preregister a capped matrix, one core, short rotated same-session repeats,
T118 lock/actual pin and orchestrator reservation. Report paired intervals, repeat-session
consistency and advisory host limits. No score lookahead, runtime trial alignments,
default dispatch rule or universal grain16 win. Produce an evidence-based simple
dispatch proposal or a null finding; any implementation is a later reviewed task.

## Acceptance and working rules

Sol protocol/source-continuity review before rates, final evidence review;
exact default/prepared and order/tail/start/final-score checks, clean stamps,
honest molecule counts and timings. Preserve both retained grains. Reuse exact
T194 canary only after source/build identity verification; no CPU source edits.

Own tickets/T198 scripts/tests/results only. Dedicated worktree or
unique scratch fallback; private builds max2 jobs, no shared venv/corpus/sibling
edits. Serialize all team timing/profile/build windows on each host. No GitHub
push or self-merge.
