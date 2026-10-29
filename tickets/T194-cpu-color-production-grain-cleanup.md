---
id: T194
title: Narrow production CPU color grains while preserving experimental reproduction
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T193, T181]
priority: highest
branch: ticket/T194-cpu-color-grain-cleanup
worktree: <worktree>
artifacts: results/T194/
---

## Context

The author approved bounded cleanup first on 2026-10-07, followed by a small matched
benchmark, current inner-loop investigation, field policy and realistic scaling.
Start from main `6fb5ee57`. Luna-max implements; Sol-medium reviews independently.
T193's shared FP32 pose is mandatory, not a speed toggle. Historical T181/T182
negative results justify separating experimental choices, not universal claims
that these grains can never win.

## Completion

Merged independently approved candidate `56b6ade2` into main. The corrected
probe preserves its historical domain without silent scalar remapping. Fresh
exact-source T149 at clean `bbd6be75` passed all eight byte-identity arms;
report `results/T149/premerge/20261007-t194-probe-domain-fix.json`.
Sol source/provenance approval is recorded in `tickets/T194/sol_review.json`.
Broad OFF/ON tests and focused corrected-source tests are detailed in
`results/T194/production_grain_cleanup.md`.
No speedup or historical T149 red-control closure is claimed. T195 owns rates.

## Scope

1. Audit actual mode-2/mode-3 Python/native defaults, callers, tests and kernel
   dependencies before editing. Send a proposed reachability/build-gating map
   to the orchestrator and reviewer before applying it. Keep scalar grain 0 and analytic
   grains 11/16 in the ordinary build; move remaining grain choices behind one
   explicit CPU experimental-color build option, OFF by default. Preserve grain
   numbering and reproducible historical ON builds. Do not silently remap a
   requested grain, change the default selected algorithm, or break rescore
   defaults that require an existing kernel. Escalate any conflicting default
   or shared helper dependency with a concrete bounded proposal.
2. Disabled public and native requests fail explicitly with the build option
   needed to restore them. Publish compiled availability in extension metadata;
   use that capability for tests rather than only hardware ISA detection.
   Gate dead experimental entry points/instantiations, not just Python choices.
   Keep common helpers needed by retained kernels. No broad source rewrite.
3. Retain all useful shape backends and the color node/brick representations.
   Keep existing supported field policies for retained grains; grain17 remains
   reproducible in experimental builds. Preserve mandatory shared pose, query
   snapshots, scalar reference and explicit FP64 comparator, starts, gradients,
   exact per-start plus distinct winner scoring, ties and worker behavior.
   Optional invariant-plan and exact-scratch switches stay OFF by default.
4. Preserve historical oracle assertions and benchmark scripts. Update test
   capability handling, add OFF rejection/metadata tests and ON all-grain tests,
   and compare retained paths across ON/OFF builds on the same inputs. Any
   cross-build numerical difference is investigated, not hidden by tolerance.
5. Record the retained/experimental mapping, rationale, caller compatibility,
   symbols/build-size evidence where available, exact commands and source stamps.
   No speedup claim from code size; no new timing tournament. No GPU changes,
   resolution/precision changes, grain re-search or corpus mutation.

## Acceptance and handoff

Reviewed minimal production build and fully reproducible experimental build;
permanent default/shared-pose/scalar/legacy/field/thread tests; honest ON/OFF
coverage and ISA skips; fresh exact-source T149 before merge. T195 consumes the
reviewed final source pin. Sol reviews source/tests before rates and final
canary evidence before the orchestrator merges. Ticket stays claimed until approved merge.

## Working rules

Dedicated worktree and private CPU builds, max two build jobs. Own
kernel/API/CMake cleanup and its tests only; coordinate source ownership with
T195, which owns benchmark scripts and results. No shared venv/corpus/sibling
worktree changes. Commit runnable checkpoints, report progress and blockers,
no self-merge or GitHub push.

## Checkpoint 2026-10-07

Current core implementation checkpoint: `3b6d16ee`.
The default/experimental build map, clean CPU source stamp, build commands,
ON/OFF test matrix, and retained-path parity evidence are recorded in
`results/T194/production_grain_cleanup.md`. This ticket remains claimed pending
Sol review and a fresh exact-source T149 gate for the probe-domain follow-up;
the earlier canary does not cover that source change. It is not complete or
merged.
