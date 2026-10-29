---
id: T221
title: Optional CPU screening telemetry and workload qualification follow-ups
phase: 3
lane: research
status: open
model: sol
reviewer: sol
depends_on: [T205, T206, T207, T210, T214, T215, T220]
priority: deferred
artifacts: results/T221/
---

## Purpose and queue state

Created by the documentation-only sprint closeout on 2026-10-10.
Deferred inventory, not a dispatched experiment or production blocker.
It preserves unperformed residuals from closed implementation tranches;
none is claimed measured because the fast public route shipped.

The author authorized ticket updates only. Do not write code, restart a harness,
run perf or reserve a host without a new focused assignment. Sol/Opus is the
design/review tier; bounded execution can use Luna/Haiku when later authorized.

## Residual inventory

- T205: current-default true weak scaling with fixed useful unique work per
  physical core, if needed. Historical strong scaling and T190's old-source
  weak scaling are not this new-source experiment.
- T205/T206/T207: observed allocator/peak-RSS/per-worker scratch and sink-only
  occupancy. Planning estimates and avoided dense payload arithmetic are not
  measured resident memory.
- T205/T207: queue, decode, coordinate conversion, preparation, scoring,
  exact finals, local/final reduction and idle attribution, with explicit
  nesting/concurrency. Worker elapsed sums are not exclusive wall or CPU time.
- T214/T215: useful-work-normalized instruction/issued-pair counts and
  source-plane-count attribution. Elapsed gains and algebra alone are not
  measured instruction savings or removed pairs.
- T207/T210: independently verified cold/I/O-inclusive behavior if storage
  matters for deployment. Warm-cache throughput is not I/O bandwidth.
- T167: an additional ISA/configuration beyond the actually supported/tested
  public route, only if deployment needs it. Fallback/refusal does not prove
  every historical AVX-512 cell was tested.

## Existing evidence and exclusions

Start with T205 strong scaling, T206 exact collector/campaign, T207 pipeline/
high-core review, T210 practical profile/perf, T218 composed public evidence
and T220 public-default verification. Preserve measured source, host,
representation and exploratory grades; do not repeat them to build a harness.

T213 retains diagnostic-hook parity/annotation. T162/T217 own field-policy/
scheduling research; T178 owns crossover qualification; T208 owns corpus
recomputation/precision; T149 owns restored-counter red control. This inventory
does not discharge those scientific/correctness requirements.

## Scope on future activation

Choose one concrete question and a short stop rule before dispatch. Prefer
existing counters, profiler/perf and screening runners. Use current supported
public screening, frozen source/build/input identities and both ranking levels
when relevant. Amortize query/field construction separately from warm alignment;
include recurring library work in end-to-end measurements.
No general instrumentation framework or all-combinations campaign.

## Acceptance

Independently reviewed bounded result or honest negative for the activated
question, with raw records and provenance. Untouched inventory stays deferred
or is split into independently scoped tickets; one result does not close all.
No code/default change is implied. Later scoring/codegen changes need fresh
T149; documentation-only closeout needs no new canary.

## Working rules

Follow CONVENTIONS.md. New worktrees/builds/scratch use `<scratch>`; corpora
remain shared/read-only. Coordinate exclusive cloud timing ownership; do not
gate the dedicated host on load-average decay. Push only to the development
repository.
