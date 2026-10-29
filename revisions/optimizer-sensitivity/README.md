# Optimizer sensitivity: why the two engines' rankings disagree

The paper's build runs this analysis: the top-level `Makefile` decompresses
`data/ranking-inputs.npz.xz`, runs `scripts/ranking_discordance.py`, and emits
`generated/constants-optimizer-sensitivity.tex`, which the paper inputs.

Source of the work: ROSHAMBO3 ticket **T169**. The full experimental record
is in the internal development record; this directory carries the subset a
paper revision needs, repackaged to run standalone.

---

## Why this exists

A ROSHAMBO2→ROSHAMBO3 port of a screen showed **~76% top-100 agreement**,
where the migration note led one to expect 0.947–0.997. That note quantifies a *same-codebase numerics A/B*
(the C1/C2/C3 fixes) on 5,510 conformers. It says nothing about the **port**,
which composes those fixes with a rewritten pose search. Nothing in the
repository quantified the composition, so the only available number was being
read as though it bounded the port.

Panel throughout: **200 queries × 75,292 PubChem molecules** (687,440
conformers, ≤10 per molecule), molecule-level by ensemble-max, self-excluded.

## What we did

Four experiments, in order. Each answered a question the previous one raised.

**1. Split the fixes from the rewrite.** Built ROSHAMBO2 with C1 (quaternion
renormalization), C2 (principal-axis reflection) and C3 (combo gradient
weighting) applied onto the upstream commit the ROSHAMBO2 results came from,
and ran two arms from one binary via the `legacy_combo_gradient` runtime toggle
so nothing else could differ.

*Result:* the fixes close **2.1%** of the combination disagreement and **16.8%**
of the shape disagreement. C2 never fires on real molecules (0 of 687,440
conformers). C3 *improves* shape by +0.027 while *costing* combination −0.004 —
it makes ROSHAMBO2 a better optimizer of its own objective without making it
more like ROSHAMBO3. Fully-fixed ROSHAMBO2 against ROSHAMBO3 is **0.768
combination / 0.821 shape**. That is the number a porting user should plan
against.

**2. Separate search from scoring.** Extracted both engines' final poses and
rescored them with `roshambo3.reference.overlap` — a float64 implementation
that shares no code with either kernel, which is the point.

*Result:* every arm reproduces its **own** reported Tanimoto from its **own**
pose to ~2e-6. The scoring term is four orders of magnitude below the effect,
so **neither engine has a scoring bug — they find different optima.** And at
matched step count, two thirds of ROSHAMBO3's shape advantage evaporates:
ROSHAMBO2 at 25 steps ties us on shape. Combination survives the match.

**3. Classify the mechanism.** Defined a basin operationally as the attractor of
local ascent and decomposed the per-pair difference into a depth term (same
basin, one stopped short) and a breadth term (different basins).

*Result, over 1,038 pairs:* **82.3% same-basin/depth, 17.5% different-basin,**
2 distinct-but-equivalent optima. Combination +0.0119 = depth +0.0092 (77%) +
breadth +0.0027 (23%). The classifier is not doing the deciding — largest
same-basin RMSD 2.7e-6 Å, smallest different-basin 1.86 Å, nothing near the
threshold. The mechanism behind breadth is **travel, not the start set**: both
engines use the same four starts, and one engine changes basin on ~1 pair in 8
purely from being given more steps.

**4. Ask the ranking question directly.** Experiments 1–3 are all *pair-level*.
Whether a molecule crosses the top-100 boundary does not follow from a per-pair
win rate, so it was measured separately: when a molecule is in ROSHAMBO2's
top-100 and not in ROSHAMBO3's, did we score it **worse** (demotion), or the
same-or-better while something else overtook it (**displacement**)?

## What we concluded

**On the combination objective — the one both engines actually optimize —
disagreement is displacement, not demotion.**

| fate of ROSHAMBO2(fixed)'s top-100 | count | share |
|---|---:|---:|
| stayed in ROSHAMBO3's top-100 | 15,355 | 76.8% |
| left, and we scored it **≥** ROSHAMBO2 (displaced) | 4,497 | **96.8%** of those leaving |
| left, and we scored it lower (demoted) | 133 | 2.9% |
| left our top-1000 entirely (censored) | 15 | 0.3% |

Mean gain where displaced: **+0.0042**. Mean drop on the 2.9% genuinely
demoted: **0.0015**. Molecules *entering* our top-100 gained a mean **+0.0403** —
an order of magnitude larger than the displacement margin.

So the discordance is **ROSHAMBO3 promoting molecules it optimizes
substantially better**, which push out molecules it also scores fine. It is not
ROSHAMBO3 mishandling what ROSHAMBO2 ranked highly.

**Reading the shape channel alone inverts this, and the inversion is the
explanation, not a contradiction.** On shape, 65.9% of departures are demotions.
But of those shape-demoted molecules that carry a combination score in both
engines' top-1000 (**813 of 2,365**; the rest are censored), **96.9% score
higher on combination under ROSHAMBO3**, with a mean shape drop of 0.0068
against a mean combination gain of 0.0076. We give up shape and are paid in
color, on the same molecule, slightly better than at par.

The control that settles it is within-engine: run **one** engine against itself
at 10 vs 25 steps and the same shape tail appears — 61 of 61 of ROSHAMBO2's own
budget-induced shape "regressions" are trades. **A shape tail is what optimizing
a mixed objective better looks like when you read out one term of it.**

**The honest summary for a paper is therefore not "ROSHAMBO3 wins."** At matched
steps, shape is a tie; the advantage is on combination and color. The claim
that survives is about *mechanism*: where the rankings disagree, it is
predominantly because the rewritten search reaches better optima on the
optimized objective, and secondarily because a mixed objective trades one term
against the other.

### Limits, stated

- **Iso-step is not iso-work.** ROSHAMBO3 uses `ADAGRAD_EXP` with a derived
  `lr_t`; ROSHAMBO2 uses its own rule and a free `lr_t`. A mirror arm at 10
  steps bounds this (means move from +0.0042/+0.0196/+0.0119 to
  +0.0044/+0.0206/+0.0125) but does not remove it. Iso-*travel* needs an `lr_t`
  sweep, not run.
- **Censoring.** An oracle keeps only the per-query top-1000. A molecule that
  leaves a top-1000 has no score on that side and is counted separately, never
  assumed demoted.
- **A preparation difference exists and is small.** ROSHAMBO3 strips isotopic
  hydrogens; ROSHAMBO2 keeps them. 1 library conformer in 526 is a different
  molecule to the two engines.
- **The 64-restart float64 reference does not converge on multi-modal pairs.**
  Doubling moved it 1.3e-2 on the fixture; 256 restarts converge to 2e-16. The
  basin script refuses to report if its own doubling test fails.
- Grade **advisory**: run unlocked by decision, because overlap and ranking
  statistics are deterministic and clock-independent. **No timing or throughput
  figure appears anywhere in this package**, at any grade.

## The diagnostic fixture

`data/isostep-fixture.npz` — **48 pairs, 104 KiB, five arms.** Stratified 3
objectives × 3 outcome bins (clearly better under ROSHAMBO3 / indistinguishable
/ clearly better under fixed ROSHAMBO2) × 5 pairs, chosen at the
10/30/50/70/90th nearest-rank percentile of each cell rather than by seed, plus
four deliberately-included extremes labeled as such.

It carries both engines' preparation of every conformer, every arm's raw
20-column pose row, and every reported and oracle-rescored score. It needs no
GPU, no corpus, no oracle directory and no network, and it re-derives every
score from the stored coordinates rather than re-reading them.

Its value beyond this analysis is as an **optimizer-sensitivity regression
set**: a change to the pose convention, the feature numbering, the mixing rule
or the reference oracle fails it in under a second instead of surviving until
someone re-runs a 470 MB panel.

## How to reproduce

Requires the `roshambo3` package importable (the fixture verifier deliberately
calls the *live* `roshambo3.reference.overlap`, so that a change to the oracle
is detected rather than hidden). On a machine with a foreign MPS daemon, export
`CUDA_MPS_PIPE_DIRECTORY=$HOME` first — without it anything creating a CUDA
context hangs silently.

```bash
cd revisions/optimizer-sensitivity

# 1. Verify the diagnostic fixture -- ~0.8 s, no GPU, no corpus.
#    Re-derives all 48 pairs x 5 arms from stored coordinates and asserts
#    against the recorded values.
python scripts/verify_fixture.py --fixture data/isostep-fixture.npz
#    expected: recompute residual 0.00e+00, round-trip gate 1.05e-06, PASS

# 2. The ranking result -- displacement vs demotion, from packaged inputs.
#    The inputs ship xz-compressed; decompress them once first.
xz -dk data/ranking-inputs.npz.xz
python scripts/ranking_discordance.py
#    expected: combo demoted 2.9% / displaced 96.8% / censored 0.3%
#              shape demoted 65.9% / displaced 29.6% / censored 4.5%
#    writes generated/ranking-discordance.json

# 3. Semantic LaTeX constants for a future \input.
python scripts/emit_constants.py
#    writes generated/constants-optimizer-sensitivity.tex
```

`generated/` is disposable; the three commands recreate it.

`data/provenance.json` records the sha256 of every input, the engine
configurations, the source oracle directories, and the roshambo3 commit this
came from.

## Files

| path | what |
|---|---|
| `data/isostep-fixture.npz` | 48-pair diagnostic set, self-contained (104 KiB) |
| `data/isostep-fixture.meta.json` | per-pair bin, objective, selection rank, extremes |
| `data/ranking-inputs.npz.xz` | per-query top-1000 index+score, both engines, for experiment 4 (5.9 MB uncompressed) |
| `data/provenance.json` | sha256s, engine configs, source oracles, upstream commit |
| `scripts/verify_fixture.py` | re-derives and asserts the fixture |
| `scripts/pose_rescore.py` | pose reconstruction + float64 scoring, imported by the verifier |
| `scripts/ranking_discordance.py` | displacement vs demotion |
| `scripts/isostep_basins.py` | basin classifier (depth vs breadth), carried for reference |
| `scripts/isostep_fixture.py` | the builder that produced the fixture — carried as provenance; it needs the 470 MB panel and will **not** run standalone |
| `scripts/emit_constants.py` | semantic LaTeX constants |

`generated/` is not committed; the commands above recreate it.

## Interpretation

1. This is not a quality win over ROSHAMBO2: at matched step count, shape is a
   tie. What the analysis supports is the **mechanism** (displacement, not
   demotion, on the optimized objective) and the **trade** (a shape tail is the
   signature of a better-optimized mixed objective).
2. The comparator is ROSHAMBO2 **with the C1/C2/C3 fixes**. Comparing against
   the unfixed engine would attribute its defects to the rewrite, which
   experiment 1 exists to prevent.
