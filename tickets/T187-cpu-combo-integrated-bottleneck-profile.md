---
id: T187
title: Attribute remaining CPU combo cost on integrated fast shape and analytic color
phase: 2
lane: research
status: closed
model: luna
reviewer: sol
depends_on: [T118, T153]
priority: highest
branch: ticket/T187-combo-bottleneck-profile
worktree: <worktree>
artifacts: results/T187/
---

## Sprint closeout — 2026-10-10

Closed for reviewed historical attribution and the practical cloud continuation
delivered under T210. See cloud profile/perf evidence
(`results/T210/simple_diagnostics_20261009/README.md`) and its independent review. The author replaced the elaborate attribution
framework with bounded profiler/perf calls. Setup-inclusive sampled shares
identify analytic color as a target; counters do not prove DRAM saturation or
exclusive scan-phase fractions. Later causal/composed work is in T213/T218.
Optional precise worker-phase/allocator attribution is deferred to T221;
no additional profile campaign is required to close this tranche.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical context

### Cloud continuation ownership, 2026-10-09

T210's 6-Luna-max agent is the sole cloud execution owner. After a composed
conformer/molecule baseline and bounded sustained scaling, collect separate
PMU/phase diagnostics on a frozen reviewed build; do not run an independent
T187 cloud campaign. Current C4 supports empirically verified cycles,
instructions, reference cycles, branch events and L2 misses. These counters
are not complete DRAM/uncore bandwidth telemetry. Existing host evidence stays
historical; no cross-host speedup or concurrent profile/throughput inference.
The orchestrator reviews each bounded protocol before numbers; T210 stores its new cloud
artifacts and links this attribution residual without auto-closing T187.

### Reviewed bounded current-source result, 2026-10-08

Merged the Roci continuation after final Sol approval of `6c21b315`
(`sol-t187-evidence-6c21b315-20261008`). Both fixed g5 color16 cells passed
exact score, winner and census checks; three warmups and eleven ordinary
calls per cell yielded advisory medians 12.290336 ms canonical and
18.916084 ms general-asymmetric per 128 pairs. Query field construction
was outside call timers. Separate, overlapping phase diagnostics identify
remaining analytic-color work but do not establish exclusive Amdahl fractions
or explain T196's canonical improvement causally. Evidence and replay guidance:
`results/T187/current_source_roci_20261008_R1_completed/README.md`.

This is a reviewed partial result, not full closure: broader two-host and
hardware-counter acceptance remains outstanding. No native source or default
changed. The next bounded source-inspection hypothesis is fusion of the
double-coordinate output and subsequent FP32 packing walk, preserving the
shared pose, exact intermediates, eligibility and fallback behavior.

The same two-cell current-source slice has since completed on Tachi, reviewed
as `892dc6e2` (`sol-t195-tachi-evidence-892dc6e2-20261008`) and merged under
`results/T187/current_source_tachi_20261008_R1/`. The limited slice is now
available on both hosts; broader configurations and hardware-counter
attribution remain residual. Raw T118 grades and advisory interpretation are
preserved; no comparison of host clocks or cross-host speedup is inferred.

### Current-source low-core continuation, 2026-10-08

Assigned to a dedicated worktree (Luna-max) after reviewed T196/T197
closure. Begin current main `0d307d33`, with merged T196 CPU source and the
source-identical existing private candidate build if its full inputs match.
Preserve the older checkpoint worktree and its
untracked attribution drafts. Use a new private clone and start two existing
g5 canonical/general cells: pipelined FP32 shape plus analytic color16. Color11
is a bounded diagnostic control, not a new tournament. Reuse existing helpers
and instrumentation; do not write another large benchmark framework. Missing
hardware counters limit causal attribution but do not block phase/assembly
evidence. The orchestrator reserves one-core windows after independent Sol protocol review;
busy observations remain advisory. No CPU/API/CMake edits, defaults, precision
changes, nested-timer summation or multiplication of previous speedups.

The author authorized this on 2026-10-07; Luna-max executes with independent Sol-medium review.
Main `116505d0` has reviewed fast shape plus vector analytic color. Tachi
whole-combo speedups versus scalar shape are 1.98–4.99x vector analytic and
2.34–7.49x pipelined field across bounded cells/color mappings. Those gains
shift the bottleneck; old shape-only phase fractions cannot identify it.
This ticket is attribution, not kernel tuning or another accuracy campaign.

## Scope

1. Freeze and stamp the merged kernel; reuse T184 actual corpus groups3/5/7,
   canonical/general, four starts/25 steps/mix0.5 and existing shape geometry.
   Compare trajectory analytic and pipelined field shape, color11/16, using
   existing native phase/census entry points and reviewed T185 fixed-pose
   companion evidence where available. Residual upstream ticket status is not
   a blocker. No new reference mining or field build in alignment rates.
2. Attribute query build/prep, target packing, pose transforms, shape
   value/gradient, analytic color, mixing/optimizer updates, exact per-start
   and winner final scoring, and dispatch/scheduling remainder. Use exclusive
   regions or explicitly explain nesting; never add overlapping timers as if
   exclusive. Preserve production numerical policy and final score semantics.
3. Collect bounded hardware profiles where permissions allow: cycles,
   instructions, cache misses/stalls, bandwidth, load/address pressure,
   achieved frequency; inspect hot assembly for register spills, redundant
   loads/transforms, scalar reductions and library calls. Report unavailable
   counters honestly rather than blocking all attribution.
4. Separate uninstrumented throughput from phase/census/profile calls.
   Instrumented durations are diagnostic, not rates; never subtract their
   costs from a production rate or claim counter changes establish a win.
   Validate observer overhead on a bounded matched sample.
5. Publish a ranked short list for T188: concrete source hotspot, measured
   fraction, hypothesized removable work, plausible Amdahl ceiling, correctness
   risks and one causal ablation per candidate. Specifically assess shared
   shape/color transformed-coordinate reuse, field address/load/pipeline
   pressure, sparse color occupancy/reductions, optimizer and exact-final cost.
   Absence of a worthwhile hotspot is a valid bounded result.
6. Work in parallel with T186 without changing shared optimizer/API/CMake.
   Prefer existing instrumentation. If a new native hook is indispensable,
   propose isolated helper/probe and agree committed ownership handoff first;
   obtain source review and fresh T149 for any production codegen change.
   Multicore confirmation consumes T186 later, not a prerequisite to start.

## Deciding measurement

Reproducible integrated one-core cost attribution and evidence-ranked next
optimizations, with whole-combo Amdahl ceilings and uncertainty/observer cost,
on both hosts when qualified. Missing Roci rates remain explicit, not guessed.

## Acceptance

Independent Sol review of protocol and final attribution, exact source/build/
grain/population stamps, T118 lock/quiet/affinity for quoted rates, committed
scripts and raw profiles/records. No copied corpus, changed precision/resolution,
default promotion or profiling-session rates presented as ordinary throughput.
Bounded Tachi-only report can be partially merged if Roci remains contended.

## Traps

Timer/census perturbation, double-counted nested phases, and old phase fractions
after composition can all invent a bottleneck. A microkernel win or a spill
count is not a measured full-combo gain. Ordinary and 2x4 color mappings must
use matching populations and schedules.

## Working rules

Own tickets/T187 profiling scripts, tests and results/T187, not T186 shared
kernel files. Dedicated worktree, private builds max2, read-only
corpora, no shared venv edits. Commit protocol/scripts before numbers. Serialize
measurements with T186 via host reservation/T118; profile on the other quiet
host when possible, otherwise alternate short windows. Scoped Tachi sync only.
Notify the orchestrator promptly on readiness, blockers or completion; no
self-merge.
