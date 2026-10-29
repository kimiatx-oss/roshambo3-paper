---
id: T222
title: Symbolize one current-default CPU combo profile and identify remaining costs
phase: 2
lane: research
status: claimed
model: luna
reviewer: sol
depends_on: [T220]
priority: highest
branch: ticket/T222-current-default-profile
worktree: <worktree>
artifacts: results/T222/
---

## Context and assignment

The author authorized 6-Luna-xhigh execution on the dedicated cloud x86 VM, 2026-10-10.
The current canonical/rawbits-unclamped/factored combo is faster than the
historical general-matrix profile. T218's latest aggregate counters do not
identify its source-level costs. This is one focused diagnostic, not another
benchmark harness or scaling campaign.

## Scope and hard budget

1. Use current-main public screening, supported FIELD/pipelined shape, canonical
   identity interaction, grain16, four starts/25 steps, prepared self and exact
   finals. Reuse bench/t218_fast_combo_profile.py and the existing public-pass
   helpers on the staged 3,605,026-conformer/882-block corpus. Record the actual
   resolved defaults, especially rawbits_unclamped, not a historical override.
2. Obtain matching symbols for the measured Release binary. Prefer retained
   unstripped build output or a symbol-only relink with matching BuildID/text;
   otherwise one private current-source Release build with symbols and unchanged
   optimization/arithmetic. Do not disable LTO/change frame-pointer policy just
   to make profiling convenient. Validate source/build/DSO identity.
3. One unprofiled warmup, one sampled warm public combo call, and one separate
   perf-stat warm call. No repeat/worker/query tournament. Import/cold query
   setup outside the warm window; recurring Source prep remains included.
   Reuse existing perf-control acknowledgement plumbing. One focused recovery
   retry is allowed for a failed invocation, preserving failed records.
4. Report flat self costs and representative hot-loop assembly/source locations:
   pose/conversion and support checks, canonical pair arithmetic/exp,
   force/torque, optimizer bookkeeping, exact finals, decode/prep/reduction.
   If inlining prevents a clean split, label inseparable regions; do not invent
   exclusive percentages. Use available cycles/instructions/branches counters,
   no uncore/provider configuration changes or elaborate event discovery.
5. Stop with a short ranked recommendation for at most two micro-optimizations.
   No production kernel changes, generic profiler framework or precision study.

## Acceptance and handoff

Matched hashes/IDs/all 20 outputs against an unprofiled same-source run;
correct query reuse, worker affinity and native provenance. Independently
reviewed report and committed commands/raw logs/symbol identity. A diagnostic
is not headline throughput or proof of bandwidth/port saturation. Unsupported
events and lost samples are reported. Large perf data may be compressed and
stored externally with durable path/hash; bring the report and useful extracts
back locally. Publish first useful results promptly, then release cloud lease.

## Working rules

Read CONVENTIONS.md and CPU-COLOR-CLOUD-EXECUTION.md completely. All new
worktrees/builds/runs/scratch and TMPDIR use `<scratch>`, max two build jobs.
The orchestrator grants the first exclusive cloud lease; existing host-qualified CpuLock still
required. No cloud load-average gate, no sibling timing/build overlap, no
shared install rewrite, no dataset recopy or push outside the development
repository. T223 can develop locally while this diagnostic runs.
