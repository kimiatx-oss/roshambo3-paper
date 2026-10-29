---
id: T193
title: Adopt one shared FP32 pose throughout CPU combo production dispatch
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T191, T153]
priority: highest
branch: ticket/T193-shared-pose-adoption
worktree: <worktree>
artifacts: results/T193/
---

## Context

The author authorized wiring and global simplification after T191 merged at
`a96d20b0`. Sharing the FP32 pose across shape, color and exact scoring is a
correctness requirement, independent of speed. Current main `b39ef3e6` still
defaults to legacy physical-FP64 posing; its shared path covers color11/16
only. Luna-max implements; independent Sol-medium reviews.

## Scope

1. Audit public/native dispatch and callers before editing. Make shared posing
   the normal CPU combo contract, with owned query preparation supplied once
   and reused, or prepared automatically when absent. Honor supplied shape
   handles; avoid duplicate field builds, global caches and stale snapshots.
2. Cover scalar analytic color as well as the supported vector analytic paths
   and field/analytic shape backends. Preserve scalar execution as a meaningful
   reference; do not silently change a requested grain into another one.
3. Audit remaining experimental color grains and mixed field/analytic color.
   Reuse the same prepared FP32 matrix/translation across all consumers;
   lattice mapping is not another rigid pose. Stored-gradient fields and
   existing spacing/precision policies stay unchanged. Do not silently fall
   back to independently posed color. Send a coverage/design checkpoint before
   deleting or retiring experimental modes; preserve supported functionality
   unless the orchestrator approves a narrower explicit retirement.
4. Consolidate optimizer/pose/exact-scoring plumbing rather than keeping two
   production optimizers selected by a performance toggle. Remove redundant
   physical/reduced translation round trips and independently normalized poses.
   Keep the physical-FP64 formula only as an explicitly selected, labelled
   reference/comparator needed by existing numerical tests and historical
   benchmark reproduction; do not weaken independent oracle coverage.
5. Default calls and explicitly prepared shared calls must agree under the new
   contract. Preserve start modes, weights, arbitrary matrices, masks/tails,
   deterministic winners, four per-start plus distinct winner evaluation,
   threading, output buffers and immutable-handle validation. Retain the D029
   declaration; update old tests to select legacy comparisons explicitly,
   never silently relax unrelated failures. Shape-only and GPU behavior must
   not change. Color rescore is an adjacent audit: identify any residual
   independent posing explicitly rather than claiming it was fixed untested.
6. Tests and correctness first. No new timing campaign is required for this
   correctness adoption, no parameter sweep or host-idle prerequisite. Review
   source and actual coverage with Sol, fix findings, run the fresh exact-source
   T149 canary on the final composed revision, then final review before merge.

## Acceptance

Ordinary CPU combo calls use one shared FP32 pose without opt-in flags; scalar
and optimized consumers, fallback and exact scorers share it. Query preparation
is safe and amortizable; unsupported/residual experimental modes are explicitly
documented and never silently use a different production pose. Duplication is
reduced with a clearly isolated independent reference. Permanent dispatch,
numerical, lifetime, start/winner and threading tests pass; fresh T149 and Sol
review pass. No speed-dependent gate for adopting the correctness contract.

## Working rules

Dedicated worktree; private builds at most two jobs. No shared venv, corpus or
sibling-worktree mutation. No GitHub push. Commit early checkpoints, keep the orchestrator informed,
no self-merge. Scope is CPU combo adoption, not a GPU rewrite or exp/grid sweep.

## Completion

Implementation and broad CPU regression evidence are recorded in
`results/T193/shared_pose_adoption.md`
at candidate `37520e57`. The final CPU regression run passed 267 tests, with six
AVX-512 capability skips. Sol approved the composed source and tests, including
restored exact historical FP64-oracle checks.

Fresh exact-source T149 at clean `7649a9c9` passed all eight byte-identity arms;
the report-only commit `aa7ccdff` received final Sol approval and was merged
into main. Evidence: T149 report `results/T149/premerge/20261007-t193-shared-pose-adoption.json`.
No timing gate or speedup claim. Mode-2 rescore remains an explicitly documented
legacy-pose residual; shape-only and GPU behavior are unchanged.
