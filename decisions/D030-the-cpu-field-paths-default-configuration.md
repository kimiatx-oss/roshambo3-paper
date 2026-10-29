# D030 — The CPU field path's default configuration

**Date:** 2026-09-07
**Status:** **accepted 2026-09-07 by the author**, as the right-for-now default,
explicitly to be revisited when T145's reference lands. Reviewed by fable
(`results/T136/review-D030.md`, accept-with-changes); all eight required
changes applied before acceptance.
**Source:** `results/T136/candidate_default_roci.json`,
`results/T136/gridxf_allin_revisited_roci.json`,
`results/T133/one_core_ladder_roci.json`,
`results/T133/composition_scaling_{roci,tachi}.json`; tickets T133, T136,
T138, T144
**Constrains:** every CPU throughput or accuracy number quoted after this date,
and the baseline every future CPU arm is measured against

## Why this exists

The CPU backend has accumulated eight field knobs across T124, T133, T136 and
T138, each measured in its own ticket against its own baseline. Nothing said
which combination is *the* configuration, and the practical answer has been
"whatever the benchmark script passed". That is how `library_vaa` came to be
quoted at 1.432x in one ticket and 1.081x in another -- the same arm against
two different denominators -- and how a default shipped on a 1.045x that a
later measurement could not reproduce.

This fixes one configuration, states what it is worth and against what, and
names the one knob that is still a live decision.

## 1. The default

| knob | value | why |
|---|---|---|
| `field_h` | per the spacing policy | unchanged; T137 owns the missing scale term |
| `field_width` | 8 | T122: the conformer grain at AVX2 width |
| `field_unroll` | 0 | the blocked prepare; the unrolled arm is 44% slower |
| `field_pipeline` | true | T124, and required by the arms below |
| `field_gridxf` | **1** | +1% on its own, and required by `field_batched` |
| `field_allin` | **1** | a 3-5% *loss* on its own -- kept only because `field_batched` is guarded on it |
| `field_batched` | **true** | ~16% here; recall 1.0000, RBO 1.0000, max abs dT 3.2e-04 |
| `library_vaa` | **pass it** wherever the sidecar exists | deletes a serial precompute, but with the sidecar **as currently shipped** it costs one top-100 item at both panels (recall 0.9975) -- which is what T139's regeneration targets |
| `field_winner_only` | **not decided here** — see section 4 | carries the entire accuracy cost |

## 2. What it is worth

4 queries x 32,768 from an internal evaluation corpus, 4 physical cores / 4 threads, min of
11 interleaved rounds, against the same field configuration with `gridxf` and
`allin` off. **Both headline figures include `field_winner_only`, which section
4 declines to decide.** Without it the adopted configuration is worth
**1.224x** (`results/T133/composition_matrix.json`, the `vaa + batched` cell),
so roughly a third of the 1.587x rides on the one knob still open:

| configuration | pairs/s | x bare | recall@100 | RBO |
|---|---:|---:|---:|---:|
| bare (no gridxf/allin) | 159.6k | 1.000x | 1.0000 | 1.0000 |
| SHIPPED DEFAULT: pair | 159.5k | 0.999x | 1.0000 | 1.0000 |
| gridxf + vaa + wo | 221.8k | 1.389x | 0.9950 | 0.9977 |
| pair + vaa + wo | 218.2k | 1.367x | 0.9950 | 0.9977 |
| pair + vaa + wo + batched | 253.4k | 1.587x | 0.9950 | 0.9977 |

And against the backend's *actual* default, which is still T119's scalar
analytic kernel -- one physical core, one thread, 4 queries x 4,096:

| rung | start-pairs/s | x scalar |
|---|---:|---:|
| scalar analytic (T119) | 12.3k | 1.00x |
| conformer grain w8 (T122) | 87.5k | 7.09x |
| field, no gridxf/allin | 167.2k | 13.56x |
| field + gridxf/allin (T136) | 165.4k | 13.41x |
| field + stack | 248.4k | 20.13x |

The composition holds off this panel: 1.40x-1.57x at every core count from 1 to
4, with and without SMT, on Zen 3 and on Cascade Lake, all twelve points
computing a `decision` grade (`results/T133/composition_scaling_*.json`) --
though **absent from `runs.jsonl`**: `CpuRun.write()` was never called for that
sweep, so they are advisory by absence of record (T133 closure review).

## 3. `allin` is kept for a reason that is not its own merit

Priced separately for the first time, `allin` is **below 1.0 in all ten cells**
measured (0.950x to 0.988x across core counts, panel sizes and stack
states). Its fast path is not missing -- the census puts it at **95.9-96.6%** of
poses -- it is eliding per-atom bounds work the blocked prepare already does
eight-wide behind a mask.

It stays on because `field_batched` is guarded on `field_gridxf && field_allin`
in `interface.cpp`, so dropping it forfeits batching: **1.587x with the pair
and batching, 1.389x without either.**

**That dependence is a dispatch choice, not a property of the kernel.** The
batched path runs the per-pose `conformer_inside` test itself and already
instantiates the general-path gradient for poses that fail it -- just as well,
since the fast path misses ~4% of them. Only `GRIDXF = true` is genuinely
hardcoded. So making batching independent of `allin` is a small dispatch edit,
not a redesign. **The payoff is an extrapolation, not a measurement**:
`allin`'s 3-5% loss was measured on the per-pair path, and an edit that frees
batching from it must also bypass the batched lambda's own per-pose test, which
nothing here has priced. The instantiation economy is deliberate -- T136's inlining
cliff is why -- but **the reopening condition is one edit away, and worth
taking.**

## 4. `field_winner_only` is deliberately NOT decided here

Every cell measured against the same field configuration with `gridxf` and
`allin` off, 4 queries, 4 physical cores.
`tickets/T136/review_isolation_check.py`,
`results/T136/review_isolation_check_roci.json`.

*Measured on the pre-`c06ddf6` binary -- the one still carrying the per-pair
census counter that tripped T136's inlining cliff. Re-run on the shipped binary
during the T136 closure review: recall, the missed-item decomposition, the
census and the containment fraction are **identical**; only the max-|dT| digits
move, in the first significant figure, which is exactly what a 7.4e-05
codegen perturbation does to a 3.4e-02 signal
(`results/T136/review_counter_cliff.json`). The conclusions stand; do not try
to reproduce these digits on a current build.*

| library | configuration | max abs dT | pairs moved | recall@100 | RBO |
|---:|---|---:|---:|---:|---:|
| 8,192 | pair | 3.24e-05 | 78.05% | 1.0000 | 1.0000 |
| 8,192 | pair + vaa | 7.81e-05 | 99.84% | 0.9975 | 0.9994 |
| 8,192 | pair + batched | 3.34e-05 | 78.16% | 1.0000 | 1.0000 |
| 8,192 | pair + wo | 3.40e-02 | 79.42% | 0.9875 | 0.9977 |
| 8,192 | pair + vaa + batched (NO wo) | 9.64e-05 | 99.80% | 0.9975 | 0.9994 |
| 8,192 | pair + vaa + wo + batched (full stack) | 3.40e-02 | 99.81% | 0.9850 | 0.9971 |
| 32,768 | pair | 4.54e-04 | 77.16% | 1.0000 | 1.0000 |
| 32,768 | pair + vaa | 3.31e-04 | 99.87% | 0.9975 | 0.9991 |
| 32,768 | pair + batched | 4.12e-04 | 77.20% | 1.0000 | 1.0000 |
| 32,768 | pair + wo | 2.13e-02 | 80.33% | 0.9975 | 0.9985 |
| 32,768 | pair + vaa + batched (NO wo) | 3.53e-04 | 99.85% | 0.9975 | 0.9991 |
| 32,768 | pair + vaa + wo + batched (full stack) | 2.12e-02 | 99.87% | 0.9950 | 0.9977 |

`field_winner_only` selects the winning start on the field's estimate rather
than on the exact rescore, so on about 6% of pairs a different start survives.
It owns the **max |dT|** outright -- 99.7% of the stack's movers above 1e-3 are
its -- and it is the largest single contributor to the recall cost.

**It does not own all of that cost, and an earlier draft of this decision said
it did.** The stack without it (`pair + vaa + batched`) scores 0.9975, not
1.0000. The missed items decompose disjointly per query: at 8,192, six missed =
five `winner_only` + one `library_vaa`; at 32,768, two missed = one + one. So at
the larger panel **half the recall cost is the stale sidecar's**, which is
exactly what T139's regeneration targets. The earlier claim that "T139's
regenerated sidecar will not recover the recall" holds for `winner_only`'s
share and is wrong for the rest.

**Those counts are 1-6 items on 4 queries, below what this panel resolves** --
and that is part of the finding, not a caveat to it. The apparent shrinkage
from 8,192 to 32,768 is six items against two and it reverses direction at one
of the two matched-K/M comparisons, so the recall trend with panel size is
**unresolvable here**, not established. The deferral to production scale stands
and is firmer for having no measured trend propping it up: decide
`field_winner_only` against a production-sized library and against T145's
reference.

## 5. What this does not decide

* **The optimizer schedule.** Every ratio above is measured against 4 starts x
  25 steps, and T144 measured that schedule as 3-6% short of a reference
  optimum, dominated by 10 x 10 at equal cost. T145 is computing the reference.
  If the schedule moves, **every number here moves with it** -- they are
  ratios, and their denominator is the shipped schedule.
* ~~**The wiring.**~~ **Closed 2026-09-07.** The CPU backend is now reachable
  through `Engine` and this configuration is what it selects, above a measured
  library-size **and query-atom** thresholds. Worth **1.55x end to end** on
  an internal development corpus, top-100 overlap 99/100, against 1.67-1.78x at the kernel level
  for the same query size.
  `tickets/T136/engine_default_end_to_end.py`,
  `results/T136/engine_default_end_to_end_roci.json`.

  **Three corrections to this paragraph as first written, all found reviewing
  T136 for closure.** (a) It claimed 1.90x from a measurement with no committed
  script or artifact -- pitfall 23, inside a decision document. (b) That
  measurement used the corpus's first two conformers as queries, which are
  **one-atom molecules**, and compared against the scalar anchor rather than
  the analytic grain, so both of its sides were wrong: the field path's whole
  advantage is deleting the `N_A` factor from `O(N_A N_B)`, and at one query
  atom it measures **0.54x**. (c) Below the library threshold the default
  returned `{}`, which let the extension fall through to `grain=-1, width=1` --
  D029 section 4's reference **anchor**, at 12.2k pairs/s against the analytic
  conformer grain's 82.5k on the same panel. Every small Engine screen ran at a
  seventh of the available rate, silently. It now returns T122's conformer
  grain below either threshold.

  **The default was also missing its dominant variable.** T124's deciding
  measurement was the crossover **in query atoms**, not in library size, and
  this default thresholded only on the latter. Measured with the library fixed
  at 8,192 (`results/T136/crossover_in_query_atoms_roci.json`): 0.54x at 1
  query atom, 0.83x at 4, 1.07x at 8, 1.67-1.78x from 16 to 32 -- which is
  where real panels sit, the mean being 22.6. `FIELD_PATH_MIN_QUERY_ATOMS = 8`
  is now a second condition, and the Engine passes the **median real** atom
  count rather than the padded width.
  Two things the wiring had to respect, both recorded in
  `backend/cpu.py::default_screen_knobs`: the extension's own defaults are
  D029 section 4's stamped anchor and `test_anchor.py` reaches them through
  this seam, so the configuration is *published for the Engine to ask for*
  rather than applied inside `score_pairs`; and T137's missing scale term is
  real, so the field path is selected only at or above
  **2,048 library conformers per launch** -- below that it loses, 0.26x at 128.
  `library_vaa` is still absent because the block does not carry the sidecar;
  worth about 1.08x when it does.

  What follows was the state before that, kept because it is why the gap
  existed:

* **The wiring, which is worse than an earlier draft said.** Nothing in the
  package selects any of this, and a plain `Engine` run on the CPU backend does
  not quietly fall back to T119's scalar kernel -- it is **refused at the
  seam**, because the Engine unconditionally passes `library_tile_mode` and the
  CPU backend rejects it. The CPU path is not merely un-defaulted, it is
  unreachable through the Engine at all; every number in this workstream was
  taken by calling `score_pairs` directly. This decision says what the default
  *should* be, not what it *is*, and closing that gap is unowned.

## Reopening condition

**Scheduled, not merely possible: T145.** This decision was accepted on the
understanding that it is revisited when the brute-forced reference optimum
lands. Two of its numbers are known in advance to be provisional -- the
accuracy column is measured against a gold the shipped optimizer produced, and
`field_winner_only` is deferred precisely so it can be judged against something
better.

Also any of: `field_batched` made independent of `field_allin`; T145's reference
changing the accuracy picture; `field_winner_only` measured at production
library scale; or the optimizer schedule changing, which invalidates the
denominator of every ratio here.

## Grade

**Only the two section-2/3 timing artifacts are advisory** -- the machine was
under CPU contention (one core fully occupied) during those runs. The one-core ladder
and the twelve composition points also cited in section 2 computed a
`decision` grade in their own artifacts, though they were never written to the
ledger (see section 2); an earlier draft of this paragraph mislabelled them. Accepted by
the author on 2026-09-06 on the grounds that the margin over today's baseline --
20x on the ladder -- is far larger than the contention's effect, and that ten
cells agreeing in sign carry the qualitative result. The 1% margins in
section 3 specifically want a quiet machine before they are cited alone.
