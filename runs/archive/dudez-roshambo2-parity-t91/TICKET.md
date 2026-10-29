---
id: T91
title: The ROSHAMBO2 enrichment baseline, so "equal or better retrieval quality" is an EF claim
phase: 3
lane: accuracy
status: closed
model: opus
depends_on: [T66, T71, T82, T84, T93]
priority: highest
artifacts: results/T91/
---

## Why this is the third claim, and the only one still unmeasured

The submission asserts equal-or-better retrieval quality against ROSHAMBO2.
**Today that is supportable only as rank-list overlap** -- T68 compared top-K
*overlap*, which is a different statement from enrichment. T66 and T71 measured
ROSHAMBO3's EF on 43 DUDE-Z targets (shape 10.417, combination 15.659, paired
+5.242 [+3.012, +8.367]). **Nothing has measured ROSHAMBO2's.**

Until this runs, the accuracy comparison has one arm.

## The trap that decides whether the number means anything

**`decisions/D024`: five states of ROSHAMBO2 exist, three differ by factors large
enough to change a headline, and one of them is our own fork rather than
ROSHAMBO2 at all.** A baseline computed against the wrong ROSHAMBO2 is worse than
no baseline: it is a headline-changing error that looks like a result.

### This is already resolved -- do not re-derive it, and do not use the fork

T68 built and verified all four D024 arms on tachi. They live at
`$EXTERNAL_DATA<arm>`, each a **clean git checkout at the named
commit** with its own `.venv` and a top-level `_roshambo2_cuda.cpython-311-*.so`:

| arm | dir | commit | date | `cuda_src_sha` | `py_pkg_sha` |
|---|---|---|---|---|---|
| U1 | `u1` | `f8fbb88` | 2025-08-13 | `e407e9a6c0523672` | `664bcc3eda4ed1c5` |
| U2 | `u2` | `7ff8237` | 2026-01-15 | `e407e9a6c0523672` | `664bcc3eda4ed1c5` |
| U+C | `u2_color_skip` | `fc711a9` | 2026-08-15 | `3205a6c81c72d3c9` | `664bcc3eda4ed1c5` |
| U+N | `u2_numerics` | `33ef8e1` | 2026-08-20 | `05419ce113a44b52` | `d9f2bdca3f98c592` |

All four embed `sm_60 sm_70 sm_80` (so Volta is native SASS, no JIT), all four are
`-O3` host code (pitfall 7), all four import clean under **python3.11**. Record:
`results/T68/roshambo2_arm_builds.txt`. Re-verify with the committed
`bash tickets/T68/verify_roshambo2_arm.sh <arm>` -- **run it for the arm you use and
put its output in `results/T91/`**, rather than trusting this table.

**Every other `roshambo2` directory on tachi is R3f, our fork, and is disqualified
by D024 as a published baseline.** Verified 2026-08-27: `roshambo3-T11/roshambo2`,
`wt-T15/`, `wt-T17/`, `wt-T17base/` and `wt-T30/roshambo2` are *installed package
trees, not git checkouts*, and every one of them contains `optimize_overlap_sparse`
-- D024's stated marker that a tree is ours ("`optimize_overlap_sparse` exists at
none of the upstream states"). Two of them are also built for py3.12/3.13. An
earlier revision of this ticket named two of these as the candidates; that was
wrong, and the fork marker is how it was caught.

### Which arm is the baseline, and why

**Primary: U+N, `u2_numerics`, `33ef8e1`.** This is an *accuracy* comparison, so
the arm choice must not flatter us. Upstream carries a quaternion-renormalization
defect, a reflection defect in principal-axis alignment, and a combo-gradient
weighting defect; T02 measured 1.2% of upstream's poses reporting a Tanimoto no
rigid motion can achieve. Those defects would *depress ROSHAMBO2's own EF*, so
quoting U2 as the baseline would claim a win partly against their bugs. D024
rule 2 already makes U+N the correctness reference; a retrieval-quality headline
takes the strongest competitor for the same reason.

**Secondary, one run: U2, `7ff8237`** -- "what a reader gets if they clone it
today". Report it, and report the U+N vs U2 gap as the size of their defect, not
as our margin.

**U1 needs no run.** T68's amendment to D024 rule 3 is byte identity on the CUDA
path, and the table above shows it directly: `u1` and `u2` have the *same*
`cuda_src_sha` **and** the same `py_pkg_sha`. On this backend they are the same
program, so a U1 arm would be a re-run of U2 under another name.

**U+C needs no run.** `fc711a9` skips colour evaluation when colour scoring is
off. It is a speed change on a path this ticket does not take, and it cannot move
an enrichment number.

## The data, verified 2026-08-27

Staged to tachi and checked before this ticket was dispatched. `$ROSHAMBO3_CORPORA`
on tachi is `$EXTERNAL_DATA/datasets` (`$EXTERNAL_DATA` on roci).

| path | roci | tachi | |
|---|---|---|---|
| `dudez/color_hdf5` | 135 files, 16,200,320,357 B | 135 files, 16,200,320,357 B | match |
| `dudez/index` | 47 files, 30,924,258 B | 47 files, 30,924,258 B | match |
| `dudez/conformers` | 319 files, 5,406,124,701 B | 319 files, 5,406,124,701 B | match |

`index/` carries `d002_query_library_mask.json` and `queries/`, so the D002 mask and
the query panel are both present on tachi. Equal sizes are not equal contents, so a
**whole-file md5 of all 135 `color_hdf5` files on both hosts** was run and compared:
`VERDICT: IDENTICAL`. Evidence is committed --
`results/T91/color_hdf5_md5_{roci,tachi}.txt`, produced by
`tickets/T91/verify_h5_transfer.sh`, which re-runs in a few minutes if you want it
again.

Two things that are *not* clean, neither of which blocks this ticket:

* `dudez/color_rsb3` is **2460 files / 1,754,457,462 B on roci and 2454 /
  1,754,116,842 on tachi** -- six files short. T91's ROSHAMBO2 arm reads HDF5, not
  `.rsb3`, so it is untouched by this; but do **not** run a ROSHAMBO3 arm on tachi's
  `color_rsb3` to "check" T66/T71. Those numbers are already measured on roci and
  re-deriving them on a corpus that differs is how a comparison quietly stops being
  paired. Note the discrepancy in `results/T91/` and leave it.
* `$EXTERNAL_DATA/dudez` (44 `.tgz`, 24.8 GB) is an older staging of raw DUDE-Z
  archives, unrelated to the prepared corpus. Do not read it.

Pitfall 22: the corpus is at `$EXTERNAL_DATA` on tachi and is used **by absolute path**.
Never copy it into a worktree.

## Scope

The same protocol T66 and T71 used, so the arms are comparable:

* 43 DUDE-Z targets, one crystal-ligand query each, whole prepared library per
  target, `dudez/color_hdf5` (16 GB, staged to `$EXTERNAL_DATA` on tachi 2026-08-27).
* **Apply T84's D002 mask, every tier** -- drop each masked compound from that
  target's ranked list *and* from the active count. Nine of ten masked compounds
  ranked in T66's top 7, three at rank 1, at **T = 0.75-0.96, not 1.0**, so a
  "drop anything at 1.0" filter catches none of them.
* Per-target denominators asserted against T84 (XIAP screens 23 of 76 actives).
* **Both conformer- and molecule-level** (pitfall 9). T66 measured that at 1%
  pooled, 1,355 conformer slots name only 400 distinct compounds and contain 129
  distinct actives against 257 at molecule level -- a conformer-level analysis
  finds half the actives.
* Report EF1% mean/median with a BCa CI, min and p10 (**pitfall 13, never a bare
  mean**), plus AUC and BEDROC at both alphas.

## The comparison

Paired per target against T66's shape arm and T71's combination arm, with a
dispersion -- not two bare means. Between-target sd on this panel is 9.37, which
is why 43 targets were built rather than LIT-PCBA's 15. Use the pairing.

Declare `delta_min` **before** running, as T71 did (it used 2.8 and required a
result to clear it *and* exclude zero). Carry the selection discount wherever a
best-of is reported (`doc/METRICS.md` section 8).

## Measurement regime

**Accuracy numbers, so no timing claim of any kind**; every run record carries
`measurement_regime: null` with that reason (D023). Clocks were not locked on
this host, and it does not matter here.

**T93 fixed `MoleculeTopK` on device 1**, so both TITAN V run as two independent
lanes -- verified natively on Volta by T101. Use both.

## Traps

Pitfall 22 (never copy a corpus; it is at `$EXTERNAL_DATA` on tachi), pitfall 9, pitfall
10 (nothing is selected on this panel), pitfalls 25-30. D002 is a mask at
evaluation, never a corpus exclusion.


## DECLARED BEFORE RUNNING (2026-08-27)

Written into the ticket and into `results/T91/declared_before_running.json` in a
commit that **precedes the commit carrying any ranking or any number**, as T71
did. The full declaration -- arms, population, settings, statistics -- is in that
file; the part a reader needs on the ticket's face is here.

**`delta_min` = 2.8 EF1% units.** The published DUDE-Z shape -> combination
shift, 6.3 -> 9.1 (`doc/METRICS.md` section 11) -- the same number T71 declared,
because it is the smallest EF1% difference the comparison paper itself treats as
a scientific effect. On ROC-AUC, `delta_min` = 0.01, METRICS section 8's own
threshold.

**Direction, and two readings of one bootstrap.** delta = mean(ROSHAMBO3 -
ROSHAMBO2), paired over the 43 targets, BCa 95% CI, B = 10,000, replication unit
the target. The submission's claim is *equal or better*, which is a
non-inferiority claim, so both readings are declared and both are reported
whatever they say:

* **non-inferior** iff the CI's lower bound exceeds **-2.8** -- the panel
  excludes a deficit as large as the literature's own effect size;
* **better** iff the CI excludes zero **and** the point estimate exceeds
  **+2.8**.

**What would falsify the submission's claim:** a paired CI whose lower bound
falls below -2.8 on either the shape or the combination arm. That would be
reported as measured.

**Settings: each tool at its own shipped defaults, and the difference stated.**
ROSHAMBO2 runs at `start_mode=1`, `steps=100`, `lr_q=0.1`, `lr_t=0.1`
(`cuda_backend.py:32`); T66 and T71 ran ROSHAMBO3 at `start_mode=1`, `steps=25`,
`lr_t=0.4`, `lr_q=0.1`. The baseline therefore gets **four times the optimizer
budget** of the arm it is compared with. That is the non-flattering direction and
it is the same principle that makes `u2_numerics` the primary arm rather than
`u2`.

**`mixing` = 0.5**, the paper's lambda, taken from the paper. Nothing on this
panel selects any parameter, so no selection discount applies to the headline
(`doc/METRICS.md` section 8); one is reported wherever a best-of appears.


## OUTCOME (2026-08-27) -- measured, both arms, 43 of 43 targets

`results/T91/README.md` carries the numbers, the CIs, the dispersions and the
provenance. In brief:

* **The third claim now has two arms.** Against **`u2_numerics` (`33ef8e1`,
  D024 U+N)**, on the same panel, corpus, mask and denominators as T66 and T71:
  shape-only mean EF1% **10.453** [8.039, 13.538] against ROSHAMBO3's 10.417,
  and combination at lambda = 0.5 **15.647** [11.986, 19.939] against 15.659.
  Paired over 43 targets, **delta = ROSHAMBO3 - ROSHAMBO2 is -0.037 [-0.293,
  +0.000] on shape and +0.012 [-0.232, +0.214] on combination.** Both clear the
  declared non-inferiority bar of -2.8; neither clears superiority; every CI
  includes zero. **On shape, 42 of 43 targets return the identical EF1%** -- the
  exception is ADRB2 -- while the baseline runs at four times the optimizer
  budget (its own shipped 100 steps against ROSHAMBO3's 25).

* **The null is not underpowered.** sd_d on the shape pair is 0.240, so 43
  targets resolve 0.072 EF1% units, thirty-nine times finer than `delta_min`;
  `required_n_for_delta(2.8)` is one target.

* **A finding that was not asked for: T66's unadjudicated level discrepancy is
  now localized.** ROSHAMBO2 -- the program that produced the published 6.3 --
  gives **10.453** on this corpus and this query panel, and **15.647** on
  combination against the published 9.1. The two programs land on the same wrong
  level to within a hundredth of a unit and on the same 26/6/11
  improved/unchanged/worse split. That eliminates the one candidate T66 could
  not test from inside itself -- our own scoring -- and leaves its four, all of
  which are properties of the corpus, the preparation or the query panel. It
  does **not** say which of the four.

* **D025's margin is a null on the baseline too.** `rescore -> combination` --
  color in the objective on top of color in the score -- is **+0.317 [-0.311,
  +0.981]** on ROSHAMBO2 against T71's +0.143 [-0.436, +0.812] on ROSHAMBO3. T71's
  central finding is not an artifact of our pose search.

* **U+N against U2, as the size of upstream's own defect and never as our
  margin:** **+0.388 EF1% [+0.084, +0.971]** on shape, the only cell whose CI
  excludes zero; +0.433 [-0.005, +1.151] on combination; -0.209 on color.

* **Reported honestly rather than dropped:** the secondary `color` arm against
  the secondary `u2` arm **fails** the declared AUC non-inferiority margin
  (-0.0047 [-0.0118, +0.0008], lower bound past -0.01) while its CI still
  includes zero. The same cell against the primary arm passes.

* **`measurement_regime: null` in every run record with its reason.** No timing
  claim of any kind is made anywhere in `results/T91/`.

**Two defects found on the way, both in this ticket's own code and both fixed
before any number was quoted:** the first version of the rank-column audit
checked conformer ties against `conf_mol_id`, which two conformers of one
compound share, so 105 of 172 files "failed" while every one of them was
correctly ordered; fixing that surfaced a real one, the `rescore` column being a
float64 blend rounded to float32 on the way to disk with 12 of 43 files then
carrying float32-equal rows whose ids did not ascend. Both arms were re-run with
the ranking taken on the stored float32. The final audit is **344 of 344 clean**
and no molecule-level statistic moved.

**Not done, and flagged:** no matched-optimizer-settings arm was run (the
comparison is each tool at its own shipped defaults, which is the right
comparison for a baseline and the wrong one for attributing the residual);
nothing here adjudicates which of T66's four candidates moves the level; nothing
here touches LIT-PCBA or ROSHAMBO2's `cpp` backend; and ADRB2, the single shape
target that differs, is named and not explained.
