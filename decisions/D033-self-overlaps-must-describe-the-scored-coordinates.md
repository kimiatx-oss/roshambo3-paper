# D033 — Self-overlaps must describe the scored coordinates; a row that shows otherwise is refused

**Date:** 2026-10-15
**Status:** accepted by the author; Amendment 1 (two-tier margin) accepted by the author 2026-10-16, **not yet active** (see its activation conditions)
**Source:** T268 (also T139, T152, T208)
**Constrains:** every backend's Tanimoto denominator, every consumer of stored self-overlaps (the CPU worker route's `self_overlap_policy="prepared"` today; T208's qualified sidecars and any GPU consumer of them), `roshambo3.scores.SELF_OVERLAP_BOUND_MARGIN`

## Decision

**1. A non-positive shape Tanimoto denominator reports 0, on every backend.**
`V_AA + V_BB - V_AB <= 0` scores 0, as CUDA (the specification, T152) and Metal
always did; the CPU shape paths now do too (T268).

**2. A scored row whose overlap exceeds the mean of its self-overlaps is an
error, not a score.** `2 V_AB > (V_AA + V_BB)(1 + 1e-3)` raises `ValueError`
naming the conformer. Gaussian overlaps obey
`V_AB <= sqrt(V_AA V_BB) <= (V_AA + V_BB) / 2`, so consistent inputs cannot
produce such a row; it means the self-overlaps were computed on something other
than what was scored -- in practice a stored sidecar from another preparation.
The test covers both failure shapes: a Tanimoto above 1 (the row ranks first)
and a non-positive denominator (it reports 0 and ranks last). **Raise, not
warn**: the author's ruling, because such a row signals an inconsistency
between corpus preparation and the running code.

**3. Where the check runs.** Wherever stored self-overlaps can enter, on every
scored row: in the CPU worker-local top-K collector (the engine's worker route
and `cpu.score_pairs(worker_local_topk=...)`), and on every row
`cpu.score_pairs` returns when given `library_vaa`. So a clamped row that would
rank last is caught. Elsewhere, on the rows the engine's sink returns (top-K
and dense results; a `Callback` sink returns none) -- for CUDA and Metal a
guard against bugs, since they compute self-overlaps in-kernel.

**4. Any consumer that starts reading stored self-overlaps owns a complete
check.** When T208 wires stored self-overlaps into a device backend, that
backend needs a kernel-side flag for rows past the bound -- a returned-row check
cannot see the clamped ones. Deferred to T208 by the author rather than built
before the exposure exists.

## The margin, and what it admits

`SELF_OVERLAP_BOUND_MARGIN = 1e-3`, relative. Every current corpus carries the
legacy sidecar computed before coordinate quantization (T139: up to 1.4e-4
relative off the scored coordinates). On the default prepared route it puts a
few rows just past the bound -- Tanimoto up to 1.0001; excess at most 5.3e-5 on
a 2K-molecule smoke corpus and 4.9e-5 on an internal development corpus -- and the margin **admits them
silently**. Recompute and CUDA stay within rounding of the bound: none of
their measured rows crossed it, and a synthetic 255-atom self-match reaches
1.000002. A tighter margin would stop the default CPU route
on every existing corpus; anything more than 0.1% off is refused. Bringing the
corpora to spec is T208's.

## Evidence

T268: bit-identical output on consistent input (every row of a scan of a
2K-molecule smoke corpus, both self-overlap policies); the measured excesses
above; the clamp verified on every CPU shape arm; corrupted sidecars refused in
shape and combo scans.

## Reopen if

- T208 qualifies regenerated sidecars and the corpora migrate: the margin can
  then tighten toward rounding (about 1e-6 at most measured, on a synthetic
  255-atom self-match), and should, so a frame error like T139's is refused
  rather than admitted.
- Color self-overlaps come from storage: the color term is not bounded this way
  for arbitrary interaction matrices, so it needs its own contract (T208 scope 6).
- A measured legitimate row exceeds the margin.

## Amendment 1 (2026-10-16): a two-tier margin, and `mixed` scans are refused

**Accepted by the author on 2026-10-16**, from the options laid out in T208's
independent review (`results/T208/INDEPENDENT_REVIEW.md`, finding 3) and the
proposal text that preceded this note (`results/T208/PANEL_REPORT.md` section 5,
`results/T208/CONTRACT.md` (g)). Accepted as a design; **the margin values do not
change in code until the activation conditions below hold.**

| route | margin | why |
|---|---|---|
| `verified_stored` (stored-frame sidecar, bound and validated) | **1e-5** | the denominators describe the scored coordinates; only rounding separates them |
| recompute (`self_overlap_policy="recompute"`; every non-worker CPU call; CUDA and Metal, which compute self-overlaps in-kernel) | **1e-5** | same |
| `legacy_acknowledged` (pre-T208 sidecars, prepared frame, T139) | **1e-3, unchanged**, then the tier is **retired** | the legacy frame error is up to 1.4e-4 relative (T139); a tight margin refuses legacy self-match rows |
| `mixed` (verified and legacy blocks in one scan) | **refused** | mixed provenance in one ranking is what this decision exists to catch |

"Until the legacy route is retired": T207 is already closed, so the condition is
that the author-accepted algorithm-design benchmarks that use the legacy route have
no remaining user, or their corpora are migrated. **The author names the moment.**

**Activation conditions** (the tight tier does not switch on until all hold):

1. The 1e-3 literal is single-sourced and the route reaches the native sink per
   block (today it lives in `scores.py:86`, `_cpu_src/worker_local_topk_sink.hpp`,
   and, on the unmerged GPU work, the pybind default and Metal's float32 predicate).
2. `mixed` is refused by code, with a test.
3. The LIT-PCBA rerun, including molecules with n_real > 41, shows no positive
   excess above 2e-6 on the verified and recompute routes, so 1e-5 keeps 5x
   headroom (expected about 3e-6 at n_real ~ 80, an estimate, not a measurement).
   The CUDA paths' excess at 1e-5, counted so far only at 1e-3, is measured too;
   Metal stays loose or unflagged until it has been run.
4. The color channel's D033 excess is measured and an fp64 color oracle exists
   (T276), or the author scopes the tight tier to shape only. *This and the GPU clause
   of item 3 were added by the drafting agent after the review; they were not part
   of the choice put to the author, who may scope them.*
5. Any CPU scoring change this needs passes the manual T149 premerge check.

**Why 1e-5.** T268's synthetic 255-atom self-match reaches +2e-6 by rounding
alone, so 1e-5 is that plus 5x headroom. The panel adds only that no consistent
row is refused (verified and recompute arms: maximum excess <= -4.5e-7 on every
panel, 2.4M rows; legacy arm: +2.6e-5 on PUR2 combo, +1.8e-5 on a 2K-molecule smoke corpus, +6.1e-6 on
the internal development corpus). The pre-registered rule's data clause was vacuous (it bound at <= 0); the
number was determinable before the run. Float32 predicates (Metal) are adequate
at 1e-5 (about 84 ULP) and not at <= 1e-6.

**Reopen (additionally):** a measured legitimate row on a consistent route
exceeds 1e-5; a backend's predicate cannot represent the tight margin; the legacy
route is retired (delete its tier); color gets a measured bound.
