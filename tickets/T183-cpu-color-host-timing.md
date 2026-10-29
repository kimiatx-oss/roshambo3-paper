---
id: T183
title: Finish matched Roci and Tachi timing of merged CPU color arms
phase: 2
lane: research
status: closed
model: luna
reviewer: sol
depends_on: [T146, T153, T154, T156, T181]
priority: highest
branch: ticket/T183-color-host-timing
worktree: <worktree>
artifacts: results/T183/
---

## Sprint closeout — 2026-10-10

Closed as superseded, not as a completed original two-host matrix.
The request to time the older merged binary is no longer the current
performance decision. Reviewed later Roci/Tachi checkpoints are recorded in
T195/T187; dedicated-cloud current-public comparisons belong to T211/T218.
T218 public-mode results (`results/T218/public_modes_cloud_20261010/README.md`)
are the current bounded evidence. Missing historical host/arm cells remain
missing; do not pool hosts or relabel exploratory measurements. No agent is
reserved to finish the obsolete matrix.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical context

Authorized by the author on 2026-10-06: Roci is quiet enough to try qualified timing
now. T158 widths, T180 conformer scheduling, T181 mixed/XMM and T159 prebuilt
field arms have reviewed Tachi evidence on earlier source revisions, but their
latest Roci counterparts and merged `35033d7` binary rates remain missing.
Historical Roci measurements of older kernels do not close these gaps. This
ticket consolidates existing arms only; no new kernel or adaptive policy.
Luna-max execution, independent Sol-medium evidence review.

## Scope

1. Take immediate Roci CPU reservation and build verified private Release CPU
   extension from `35033d7` (or source-identical ticket-ledger descendant) with
   at most two jobs. Respect T118 lock/quiet/affinity, pin one physical-core
   representative, record selected shape/color ISA and compiler/extension/source
   hashes. No shared venv install. Coordinate all sibling builds/tests away from
   the host during timing. Recheck actual load; quiet is not assumed.
2. Reuse committed ordinary panels/scripts from T158/T180/T181/T159, fixing only
   necessary runner plumbing. Freeze a unified matrix before rates: six cells
   groups 3/5/7 canonical/general, 128 conformers, four starts, 25 steps,
   mixing 0.5, three warmups/11 rotated repeats. Arms: scalar color 0;
   feature widths 8/9/10; ordinary/bucketed conformer 11/12; mixed 13/14 and
   XMM conformer 15; nine field arms (fp32/fp16 trilinear and fp32 bricks times
   top1/top2/all-active) sharing grain11. Keep existing fast shape work identical.
   One unified committed runner is preferred; separate existing runners are
   acceptable only with matched same-session baselines and no pooling across
   sessions. Obtain orchestrator/independent quick protocol review before long rates.
3. Prebuild one handle per selected field arm outside optimizer timing; reuse
   across all calls. Record isolated construction/packing/bytes and finite
   reuse separately. Preserve T159 field correctness scope: existing fixed-pose
   fixture pass, finite outputs, invariant schedule/shape/exact-final census,
   independent exact scalar own-winning-pose rescore. Analytic pair-gradient
   terms change when fields replace pairs; record, do not require equality.
   Field-vs-analytic score/rank/pose deltas are descriptive, no retrieval claim.
4. Require a no-rate host/grade/provenance smoke AND check-only before timing,
   launched from exact clean worktree cwd. Preserve failed attempts; final
   CpuRun grade must be decision before advancing or quoting a cell. Ensure
   CpuRun receives actual `n_warmup`/`n_repeats` contract keys. Keep outputs from
   making subsequent source/host cleanliness gates advisory: clean dedicated
   worktrees with outputs outside checkout then commit verified artifacts, or
   another explicit safe strategy. Never hide dirty source or retroactively
   regrade previous runs. No instrumentation/oracle checks in rate loops.
5. Roci first; then repeat on quiet Tachi from the same CPU source tree to close
   final-binary timing. T182 development stays off each reserved measurement
   host. Stop on genuine grade/quality failures, diagnose bounded plumbing,
   and report a partial matrix honestly if quiet windows disappear.
6. Publish one throughput table per host with source/ISA/schedule, absolute
   pairs/s and same-session paired CIs for every baseline. Map residual gates
   back to T158/T180/T159; do not close them automatically if retrieval/oracle
   requirements remain. Update stale review/canary text only with actual
   provenance. Existing T149 integration pass is `b278302`/`35033d7`.

## Deciding measurement

Qualified matched full-combo throughput and intervals on both hosts for the
merged existing analytic/field arms. Keep construction excluded in large-DB
rates. Determine whether observed Tachi ordering reproduces on Roci, not a
universal cutoff or deployment policy.

## Acceptance

Raw JSON/JSONL, populations, scripts/protocol and source/extension stamps are
committed and independently reviewed. Quote decision cells only; keep partial
or unavailable host gates open. No CPU source changes, flags, default promotion
or new grain research. Any unavoidable scoring/codegen change requires fresh
T149 and source review. No cross-host or cross-campaign multiplied speedups.

## Traps

Pitfalls 7/8/11/22/23/27/28: Release build, same inputs, whole calls, shared
datasets, committed procedures and visible/backed-up ledger. Avoid stale
editable extensions, wrong cwd, repeat-key errors and inappropriate field
trajectory/census identity gates encountered in earlier T159 attempts.

## Working rules

Dedicated worktree and private build/install; preserve siblings.
Read T118/T149 conventions, D029/D030/D031 and metrics policy. Durable scratch
outside checkout, read-only corpora, commit and push before measurements. Own
immediate Roci timing reservation and notify T182/the orchestrator before starting/releasing each host. Independent review before merge;
no GPU campaign or experimental implementation in this ticket.
