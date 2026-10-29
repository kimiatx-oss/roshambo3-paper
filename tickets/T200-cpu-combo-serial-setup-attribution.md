---
id: T200
title: Attribute realistic CPU combo serial setup versus parallel work
phase: 2
lane: research
status: closed
model: luna
reviewer: sol
depends_on: [T199]
priority: highest
branch: ticket/T200-combo-serial-attribution
worktree: <worktree>
artifacts: results/T200/
---

## Context

The author authorized quiet-Roci attribution before any implementation changes.
Reviewed T190 current-source realistic scaling reaches10.90x at24 cores and
true weak efficiency45.0%. A separate worker diagnostic (0.39–0.46s) versus
ordinary whole-call median (~0.87s) motivated a serial-gap hypothesis but did
not measure it; target workspace preparation alone was0.0133s. This ticket
closed on a narrow no-build first pass measuring caller/process CPU time during
the same full call. It does not identify exclusive setup, packing,
self-overlap, optimizer, or cleanup wall phases.

## Scope

The approved first-pass scope was amended to a same-call CPU-time split; fine
phase attribution remains deferred (see below).

1. Reuse T190's exact65536-pair group5/general population, reviewed T199 DSO,
   field shape `library_atom8` + analytic color16, four starts,25updates,
   mixing0.5, shared FP32 pose, exact four finals plus one winner rescore.
   Use the read-only corpus and build query-owned field handles outside the
   measured call.
2. Under the T118 lock, first run one fresh serial census/output/winner check
   and one24-worker placement/output check. Then compare wall-only and
   same-call process/thread CPU-clocked full `score_pairs` calls at1 and24
   workers, with3 warmups and11 timed repeats per arm/cell. Retain raw paired
   clocks and compare paired wall ratios; do not subtract observer overhead.
3. Use the exact reviewed stripped T199 DSO; no build, relink, profile, source
   or numerical/default/kernel changes. Check source/build/canary/population,
   exact outputs/census, Roci topology and singleton worker placement.
4. Treat T200 as advisory. Preserve raw calls and the T118 record. This first
   pass answers broad caller-thread CPU consumption and observer-overhead
   questions only; it does not supply an exclusive wall-time breakdown.

## Deciding measurement

For the amended first pass, report the median parent-thread CPU and process CPU
per same call, the median of per-call parent/process CPU shares, and the paired
CPU-clocked/wall-only wall-time ratio at1 and24 workers. The24-worker result is
about0.426s parent-thread CPU,10.188s process CPU, and a4.20% median paired
parent/process CPU share; the paired wall ratio median is0.9926. This shows
aggregate caller CPU consumption but does not establish how much exclusive
serial wall time or end-to-end latency it accounts for. The original causal
question—whether setup/self-overlap explains the wall-time efficiency gap—
remains unanswered pending fine phase attribution.

## Acceptance

Met for the amended first pass: independent Sol protocol/source and evidence
reviews; exact reviewed source/DSO and population pins; canonical T118 lock,
quiet-host and topology checks; serial census plus24 singleton placement
diagnostics; all58 optimizer calls returned (2 diagnostics plus56 schedule
calls); all56 measurement outputs match the frozen T190 score hash; exact
schedule and task-join accounting retained; and a non-refused T118 record was
written. The original campaign file remains `interrupted_advisory` because
post-write finalization attempted mapping-style access on a `RunRecord`
dataclass; an offline reconciliation records the valid written T118 result and
does not rewrite the raw campaign or claim a clean original process exit. No
production changes were made. T200 is closed as a partial first-pass answer;
fine phase attribution is explicitly deferred.

## Deferred fine-phase attribution

Still unmeasured: exclusive same-call intervals for input/copy, color/start
packing, query and target self-overlap, worker launch/optimization/finals,
teardown, and any residual. Any follow-up needs its own reviewed protocol and
orchestrator-granted quiet window, same-call exclusive boundaries with an explicit
residual, and observer-overhead validation. It must not infer an Amdahl
fraction from caller CPU, subtract separate-call worker medians, or treat
stripped-Dso offsets/cache counters as source attribution.

## Traps

Caller CPU at24 workers may overlap native worker wall time, so neither its
ratio to wall nor its share of process CPU is an Amdahl fraction. Process CPU
minus caller CPU is aggregate non-parent CPU, not worker wall time. The paired
observer ratio is not a reason to subtract time or claim a clock-read speedup.
Target self-overlap is pose-independent but matrix/count/coordinate-dependent;
this ticket does not authorize unsafe caching or moving it out of the reported
whole-call metric. No repeated synthetic population.

## Working rules

Luna-max (haiku synonym), independent Sol-medium (opus synonym). Private
checkout/branch, own T200 artifacts/scripts/tests and private diagnostic code
only. The orchestrator serializes Roci measurement and build windows with T201/T202. No
benchmark until explicit grant and review. Never overwrite reviewed T199 build.
