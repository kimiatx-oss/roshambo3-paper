---
id: T179
title: Characterize ordinary combo field locality and cheap setup predictors
phase: 2
lane: research
status: closed
model: luna
reviewer: sol
depends_on: [T153, T154, T156]
priority: high
branch: ticket/T179-cpu-color-locality
worktree: <worktree>
artifacts: results/T179/
---

## Context

Closed 2026-10-06 after independent Sol review of `4a7102d` and integration
checks. Both capped panels match their exact-source uninstrumented controls;
the canonical-diagonal offline analysis is complete and its cheap predictors
are too weak for dispatch. Noncanonical analyzer and field-trajectory transfer
remain T162 work, not claims of this result. See `results/T179/REVIEW.md` and
`REPORT.md`; the bulk trace is preserved in durable scratch with its hash.

D031 chooses static per-plane CPU color with joint shape+color budgeting.
T178's paired primitive sweep shows locality can move the field/analytic
cutover dramatically, but its broad poses are stress cases and its shape work
is a proxy. We need ordinary heterogeneous-plane combo traces and setup-time
predictors, not another accuracy campaign or hard-sample mining. This bounded
characterization suits Luna-xhigh (Haiku tier), with independent Sol review.

## Scope

1. Freeze a small representative tune panel of ordinary color-built molecules
   before tracing (cap 16 queries x 128 targets, T156 shipped starts/steps).
   Stratify real per-plane counts and target sizes, not score or numerical field
   nonzero fraction. Record corpus paths, stable ids, hashes and panel selection.
   Reserve a disjoint similarly bounded validation panel; verify no overlaps
   with T162's evaluation data. No optimizer-reference campaign is required.
2. Capture posed target-feature coordinates at the existing scalar mode-3
   gradient seam in a private replay/trace harness, with shape enabled and
   unchanged T156 math/schedule. Keep src/ production files untouched so this
   lane can run alongside T158/T159. If a production hook is unavoidable,
   propose its file/API to the orchestrator before editing shared kernel files.
3. Offline map those coordinates into D031/GPU-convention grid cells for each
   target-type plane, with the full eight-node interpolation stencil. Model
   cache-line addresses for fp16/fp32 AoS nodes and fp32 bricks; include shape
   accesses and state the brick coefficient layout. Record distinct cells and
   lines by pose/step/window, reuse distance/step overlap, out-of-grid fraction,
   geometry extent and plane bytes. Use logical aligned offsets, not allocator
   addresses. Identify layout/alignment assumptions and effects of loop order.
4. Fit at most two cheap setup predictors in addition to exact interacting
   query counts, target count/tails and allocation bytes: e.g. extent ratios and
   start-strategy labels. Predict access-locality summaries, not backend speed
   or scores. Evaluate once on the disjoint panel. A weak predictor is a useful
   negative result; recommend conservative policy rather than adding complexity.
5. Supply a compact replay format and summary consumable by T162. Traces are
   diagnostics, not hot-path instrumentation or mandatory runtime calibration.
   The analytic trajectory is a first proxy; T162 must check whether forced
   field trajectories materially change its locality conclusions.

## Deciding measurement

Per-plane distribution of accessed-cell/line counts, within-step and successive-
step reuse, and shared shape+color working-set estimates on ordinary tune and
validation trajectories. Report each cheap predictor's held-out error versus
the counts/bytes-only baseline, with worst strata and a no-predictor fallback.
This ticket makes no speed or hardware-miss attribution claim.

## Acceptance

- Synthetic known-coordinate fixtures verify grid indexing, eight-node
  stencils, boundary treatment, bytes/cache-line accounting and reuse counts
  for each layout. Empty/general-matrix planes are covered.
- Trace capture agrees with an uninstrumented scalar mode-3 call on the same
  fixtures under the same implementation/platform; no alternate optimizer math.
- Panel manifests, generator/analysis scripts and compact summaries are
  committed; bulk traces live once with path/size/hash if too large for git.
- Allocation, unique touched lines and estimated residency are labeled
  separately. No numerical-density scan or unsupported claim of exact LLC/DRAM
  behavior. GPU conventions and CPU physical-coordinate scaling are explicit.
- The cap is coded and enforced before execution; do not silently expand the
  campaign. Closure does not require timings, a converged reference or a
  successful geometry predictor.

## Traps

- **D015:** ordinary analytic poses are still a proxy for field-guided poses;
  do not ship a speed rule from these traces alone.
- Unique lines do not encode associativity, prefetching, co-running processes or all
  live optimizer data. Do not add roci's separate L3 domains into one cache.
- Sparse numerical values do not save loads in a full-grid interpolator.
- **Pitfalls 10/32:** tune/validation must be disjoint; implement the panel cap
  as code, not a sentence that a runner can ignore.

## Working rules

Use an isolated worktree and private scripts under tickets/T179/. Share corpora
read-only; never change the shared venv. Commit before running and record actual
loaded source/extension hashes. No GPU or quoted CPU rate measurements are
required; correctness/trace runs keep parallelism low. Follow T118 if optional
timing is later authorized. Return commits and results/T179/ summary for review.
