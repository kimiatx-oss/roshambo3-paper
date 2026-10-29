---
id: T202
title: Confirm realistic CPU combo physical versus SMT throughput
phase: 2
lane: host-io
status: closed
model: luna
reviewer: sol
depends_on: [T199]
priority: high
branch: ticket/T202-combo-realistic-smt
worktree: <worktree>
artifacts: results/T202/
---

## Context

The author authorized bounded SMT confirmation while Roci is quiet. T197 measured
only a small low-core fixture on older source; T190 current strong65536 now
reaches10.90x at24physical cores. Test the realistic physical24 versus48SMT
contrast, not a huge new thread-count tournament.

## Scope

Observer policy: frequency polling OFF equally for all rate arms; T118 treats
missing frequency as advisory, not hard refusal. Collect separate clock context
only and make no achieved-clock claim for the unobserved rate cells.

Same exact strong65536 group5/general population and T199 ordinary Release
build as T190, field shape library_atom8/analytic color16, fourstarts/25updates/
mix0.5/shared FP32 pose/exactfinal4+1. Arms serial1, physical24, logical48; no
weak scaling or other grains/precisions/default changes. Parent and native
workers must pin to exact verified topology masks. Query/field construction
once outside repeated timing; target setup and optimizer/finals inside.
3warmups/11repeats perarm, rotated same-session paired records. Separate
serial census and worker placement/load diagnostics, post-timer fullhash checks.

The existing T190 current_review receipt approves SCALING ONLY and its measured
driver lacks CLI campaign-scope enforcement. Do not launch SMT/baseline using
that receipt. Add explicit campaign-scope guard or use a new independently
reviewed ticket runner/receipt. Preserve historical measured runner checkpoint.

## Deciding measurement

Does physical24→logical48 improve ordinary full-call throughput on realistic
work, with paired confidence intervals and explicit advisory/host context?

Outcome: reviewed Roci campaign completed at evidence candidate
`abf043885ab2fee8ac91439bf078153ce222c41d`. Physical24 reached 76,610 pairs/s
and logical48 reached 80,011 pairs/s. Paired logical48/physical24 throughput
was 1.06065x (within-session 95% bootstrap interval 1.04435–1.06807).
This is a full-deployment 24→48-worker comparison, not equal-thread SMT
isolation or proof of a hardware bottleneck. All correctness, census and
singleton placement checks passed. T118 remains advisory because frequency
sampling was disabled identically for all arms; no achieved-clock claim.
Report and independent Sol evidence receipt: `results/T202/roci_20261008_R1/`.

## Acceptance

Independent Sol-medium source/protocol and evidence reviews, current exact
source/build/canary/population identity, exact output/census parity, canonical
T118 lock and actual singleton placements. No silently promoted defaults.

## Traps

More threads do not remove serial target preparation. A full-mask sampler
cannot displace its own poller off all measured cores: record observer
placement/overhead and do not manufacture idle or precise achieved clocks.

## Working rules

Luna-max (haiku), Sol-medium (opus). Prepare alongside T201 in the same agent
but use separate ticket branch/checkpoints/receipts/artifacts. The orchestrator serializes
all Roci measurements/builds; no timing until review and explicit window.
