# D013 — The acceptance criterion is recall and top-end ranking, not bit-identity

**Date:** 2026-08-16
**Decided by:** the author
**Status:** active — **supersedes the operative use of bit-identity as an acceptance gate**

## The decision

The author decided that bit-exactness is too stringent a criterion, because the end goal is
correct recall and top-end ranking.

A change is acceptable if it preserves **recall@N and the ordering of the top of the list**. It
does not need to be bit-identical, and bit-identity is not evidence of merit.

## Why this needed saying

The project drifted into treating bit-identity as the standard for a "free" change, and it cost
real speed:

- **T13 declined to ship `xhoist`** (1.102× → **1.394×**, a 1.26× multiplier) solely because it
  is a declared numerics change — while measuring that **top-1/5/10/100 sets and order are
  unchanged for 100% of queries**, p99 |ΔT| = 1.10e-5.
- **T14 declined W = 2** on the same grounds.
- Several tickets have framed "bit-identical" as the goal in their acceptance criteria rather
  than as one cheap way of demonstrating safety.

Against the measured budget this is wildly over-conservative. T08 measured that **recall ≥ 0.98
needs ε_sd ≈ 2e-3 with no overfetch, or ≈ 1.5e-2 with 10× overfetch.** `xhoist`'s p99 of 1.10e-5
is **two orders inside** the tighter of those.

## Two different concerns that were being conflated

**Reproducibility** — the same input, on the same configuration, gives the same output. This is
what bit-identity actually serves: regression tests, a stable gold reference, and the ability to
attribute a change. `decisions/D003`'s "pin the arithmetic, do not tolerate an epsilon" is a
*reproducibility* argument and **remains correct for that purpose**.

**Accuracy** — the reported top-N is right. This is the product requirement, and it is measured
in recall and rank agreement, not in ULPs.

**Bit-identity is sufficient for accuracy but far from necessary.** Requiring it as an accuracy
gate imports a reproducibility standard into a place it does not belong.

## The standard a numerics change must now meet

Unchanged in rigour, changed in threshold. Every declared numerics change still reports:

1. Effect **stratified by reference score** (the cliff is at T ≈ 0.55; gold is NOT a per-pair
   reference below 0.4).
2. **Effect on ranked output** — top-1/5/10/100 set *and* order agreement over the panel. This is
   the criterion that decides.
3. Its position against the **task-derived budget** (≈2e-3 / ≈1.5e-2), per `decisions/D010` —
   not against a measurement floor.

A change that leaves the ranked output unchanged over the panel is acceptable regardless of its
ULP distance. A change that moves the top of the list is not, however small its ULP distance.

## What this reopens

- **`xhoist` ships.** 1.26× on top of the tile.
- **int16 coordinate staging** (T27) — T05 measured p99 |ΔT| 7.4e-5, comfortably inside budget.
- **Distance cutoffs** — dropping terms below 1e-4 was previously "not free"; now it is a
  measurable trade like any other.
- **Reduced precision generally**, and **fewer optimiser steps** (T24 measured 25 steps at ~3×
  the throughput of 100), each judged on ranked output rather than on exactness.

Tier 3 remains the *specification* for reproducibility purposes: one canonical kernel,
deterministic reduction order, a pinned toolkit. That is what makes a gold reference possible.
It is not the bar a speedup must clear.
