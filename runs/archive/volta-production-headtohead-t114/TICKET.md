---
id: T114
title: The Volta head-to-head at production settings -- and the combination arm, which has never been run
phase: 3
lane: host-io
status: closed
model: opus
depends_on: [T101, T104, T107, T109, T111]
priority: highest
branch: ticket/T114-volta-head-to-head
worktree: $EXTERNAL_DATA
artifacts: results/T114/
---

## Context

The published head-to-head against ROSHAMBO2 is **57.0x**, taken on tachi's
TITAN V. It has two problems, and the second is the larger one.

**It is stale.** `results/T83/A2-tachi-headtohead.md` was measured at
`6c68da76`. Since then T85, T86, T87, T92, T93, T97, T105, T106, T107, T109 and
T111 have landed -- launch coalescing, the count vector, int16 on the wire, the
merged record, the query-record trim, `STAGED_CARVEOUT = 25`, the work-descending
colour plane order, and the locked operating point. `results/T101/` exists
precisely to license this re-run on Volta and says so in its own words: *"The
production head-to-head is not this ticket's run and was not started here."*

**And it is shape-only.** A2 names this under "Still not measured": *"The
combination objective on tachi. D026 ships for mode 3; this arm is mode 1. The
head-to-head has no combination number on either side."* Every head-to-head this
project has ever run -- T68's five sessions, T83's A2 -- is mode 1. Meanwhile
the submission's *accuracy* claim is a combination claim: T71 and T104 report
combination EF on both panels, and T91 reports ROSHAMBO2's. **We compare the two
programs on retrieval quality with colour in the objective and on speed without
it.** Nobody has ever timed the two tools against each other on the workload the
accuracy claim is about.

## Scope

Two sessions on tachi, LIT-PCBA-20M, the same 8-query `PANEL-8.sdf` panel, one
card. `tickets/T68/run_headtohead.sh` is the harness and its structure is not to
be rewritten: one session per invocation, every cell inside **one** `flock` hold
and **one** clock region, because tachi cannot lock its clocks (D004) and D007
forbids combining numbers taken at different clocks into one ratio.

### Session A -- shape, re-measured at production settings

`run_headtohead.sh headline`, unchanged, on current `main`. Both tools re-run in
the same session: T83's A2 was allowed to reuse T68's ROSHAMBO2 wall times only
because the achieved clock matched to the megahertz (1335.0 both times), and
that is a coincidence to verify rather than a protocol to rely on.

Cells, exactly as `headline` already defines them: ROSHAMBO3 at 11 repeats /
3 warmup with `--dump-topk`; `u2_color_skip` and `u2`, each `in_memory` and
`eager`, 2 repeats.

### Session B -- combination, which does not exist yet

Same panel, same corpus population, mode 3 on both sides. **Three things have to
be built before it can run**, and two of them are data.

1. **`run_roshambo3.py` has no colour path.** Its argparse has no `--color` and
   no `--mixing`, and it screens `ScreenConfig()`'s shape-only defaults. Add a
   combination arm whose spec is *taken from* `tickets/T66/screen_panel.py`'s
   `arm_specs(0.5)["combination"]` by import, not retyped:
   `color=True, mixing=0.5, color_placement=ColorPlacement.IN_GRADIENT,
   pose_search=FIELD, steps=25, lr_t=0.4, lr_q=0.1, start_mode=1`. Retyping it
   is how the two lanes come to differ in something nobody wrote down.
2. **`run_roshambo2.py` hardcodes `color=False`.** Line 237 constructs
   `Roshambo2(..., color=False)` and line 276 calls
   `compute(color_scores=False, optim_mode="shape")`. The combination call is
   already written and verified in `tickets/T91/run_roshambo2_panel.py:145`:
   `Roshambo2(color=True)` with `compute(optim_mode="combination",
   color_scores=True, mixing=0.5)`. Take it from there.
3. **Neither colour corpus is on tachi in a usable state** -- see below.

Report the ratio table in A2's shape: ROSHAMBO3 against `u2` and against
`u2_color_skip`, in both data modes. **Note in the record that
`u2_color_skip` and `u2` should converge on this arm**: `fc711a9` skips colour
*evaluation when colour scoring is off*, and here it is on, so a large residual
gap between them on the combination arm is a finding about the fix and not about
us.

## The data, and what is already done for you

| what | where | state |
|---|---|---|
| ROSHAMBO3 shape corpus | `tachi:$D/litpcba/LIT-PCBA-20M` | present, v1, 20,381,286 conformers |
| ROSHAMBO2 shape shards | `tachi:$D/litpcba/h5` | present, 30 GB, **built `color=False`** (`tickets/T68/build_h5.py:134`) |
| ROSHAMBO3 colour corpus | `tachi:$D/litpcba/color_rsb3/library` | present, **and the shipped build will refuse it** |
| ROSHAMBO2 colour shards | `tachi:$D/litpcba/color_hdf5/library` | **in transit from roci, 46 GB, started 2026-08-28** |

`$D` is `$EXTERNAL_DATA/datasets` -- tachi's corpora are on a different
volume from roci's, and `ROSHAMBO3_DATASETS` must be exported or the archived
scripts silently read roci's path.

**The refusal is the interesting one and it is not a bug.** T106 made the
work-descending plane order the default, so a corpus that records no
`features_enum` is refused rather than scored -- the shipped generator emits
Hydrophobe as type 1, an unlabelled corpus emits Donor, and scoring one against
the other is silent. tachi's `color_rsb3/library` manifest carries
`color_generator.features_enum = {Donor: 1, Acceptor: 2, ...}`: the historical
order. Fix it the way roci's 44 corpora were fixed, with
`roshambo3 convert` out of place to `color_rsb3_perm/library`:

    .venv/bin/python -m roshambo3.cli convert \
        $D/litpcba/color_rsb3/library $D/litpcba/color_rsb3_perm/library \
        --note "T114: colour planes re-emitted work-descending"

It is a permutation of the counts vector and the payload runs -- no chemistry is
recomputed -- and on roci the same 20.4 M-conformer corpus took **62 seconds**.
It also lifts the record v1 -> v2 (merged colour, per-group `L`, no shuffle),
which is what the shipped reader wants. Verify against roci's copy rather than
trusting it: `sha256_ids` must be `3bf681cc36d25f6a...`, `n_conformers`
20,381,286, and the log must report slot efficiency `0.7142 -> 0.7686`.

**The two colour corpora must be shown to hold the same conformers before the
ratio means anything.** `tickets/T68/check_same_conformers.py` is the instrument
and it is why it exists. Both descend from T82's colour build off the immutable
conformer archive (`tickets/T82/run_color_build_roci.sh:30` wrote the h5), so
this is expected to pass -- run it anyway; expected-to-pass is not passed.

## Deciding measurement

Four numbers, each a wall-clock ratio on one card in one session:

1. **shape, ROSHAMBO3 vs `u2` (`in_memory` and `eager`)** -- the replacement for
   57.0x / 58.7x.
2. **shape, ROSHAMBO3 vs `u2_color_skip`** -- the honest comparison, replacing
   25.0x / 26.7x.
3. **combination, ROSHAMBO3 vs `u2`** -- new.
4. **combination, ROSHAMBO3 vs `u2_color_skip`** -- new, and expected to equal 3.

Each with its spread over its repeats, and the achieved clock distribution for
**both** arms beside it (D023 headline regime).

## Acceptance

* Every cell of a ratio ran inside one `flock` hold and one clock region, and
  the record says so. A ratio whose arms span two invocations is not a result.
* **Both arms' achieved clock distributions reported, and their throttle
  fractions compared.** D023's reopening condition for the headline regime is
  exactly "the two arms' throttle fractions came out materially different".
* The same-conformers gate passes on the colour pair, and the shape pair's
  existing gate is re-run rather than inherited.
* `cuobjdump --list-elf` says **sm_70 SASS is embedded and no PTX is**, read out
  of the loaded `.so`, before any number is quoted (pitfall 1).
* Top-K agreement dumped for one cell per tool per objective, so the ratio is
  known to be between two tools answering the same question
  (`tickets/T68/compare_topk.py`).
* The two standing advisories carried verbatim: CUDA 12.9 is not the pinned
  13.2, and the build is `70-real`. Both are unavoidable -- CUDA 13.x dropped
  sm_70 outright, and the TITAN V is the card the comparison paper benchmarked.

## Traps

* **Pitfall 1** is the highest-yield mistake in this project's history. Ask the
  binary, not CMake. `cuobjdump` must be on `PATH` (`/usr/local/cuda/bin`) or
  `bench.build_check`'s probe does not run, and *the probe not running is not the
  probe passing* -- every row comes back advisory with "pitfall 1 was not
  checked".
* **D011's amendment: take the GPU lock before creating a CUDA context.**
  `cudaHostAlloc` creates one and a lock taken after it deadlocks. The `flock`
  is taken in the driving shell, which loads no extension, and `run_headtohead.sh`
  already gets this right -- do not move it into Python.
* **This build is 2.25% slower on Volta than the pre-lock one, deliberately.**
  T107 measured staging colour at `color_stage = 48` at **+4.3% on sm_120 and
  -2.25% on sm_70**, and the operating point was locked for Blackwell with that
  loss accepted (2026-08-28). If session B comes in slightly under what a
  pre-lock binary would give, that is the recorded trade and not a regression to
  chase.
* **Pitfall 12**: `-k` is the counterpart of roshambo2's `max_results` and must
  be stated on both sides. The harness's own advisory
  (`max_results < 10 * n_conformers`) is unsatisfiable for a device-resident
  top-K -- it would demand k = 2e8 -- so it tags the run `advisory`. That is a
  known harness defect on T69; write it into the record's advisory list rather
  than letting it read as a defect in the measurement.
* **Pitfall 17**: tachi has 128 GB and a 20 M-conformer corpus fits in page
  cache outright, so an I/O-inclusive number taken without the drop is measuring
  RAM. `run_roshambo3.py` drops over every corpus file and verifies with
  `mincore`; the colour corpus is 5.2 GB against the shape corpus's 2.9 GB, so
  do not assume the existing drop list covers it.
* **Pitfall 8**: the colour corpus's padding is not the shape corpus's
  (`padding_efficiency` 0.846, `color_padding_efficiency` 0.590 before the
  convert; slot efficiency 0.7142 -> 0.7686 after). Sessions A and B are
  different corpora and their wall times are **not** divisible into each other.
  The combination ratio is a ratio within session B only.
* **Two GPUs.** `bench/gpu_lock.py` refuses to guess a device on tachi, and four
  suite tests that *default* the device fail there for that reason. They are the
  established four (`results/T83/A2`), they are not caused by this branch, and
  they cannot reach the measurement -- `run_roshambo3.py` resolves
  `--device 0` explicitly. Record them; do not chase them.
* **Do not quote D025's estimated combination cost.** T63 *measured* 2.05x on
  Blackwell; 1.25x was a paper estimate and D025 forbids quoting it. Session B
  is the first Volta measurement of this quantity and should be compared against
  T63's Blackwell figure only as a cross-architecture note.

## Working rules

The standard set (own worktree, own venv -- this lane loads a CUDA extension --
datasets by absolute path, every script committed before it runs, partial
results are results). Specific to tachi:

* `bench/setup_tachi.sh T114 ticket/T114-volta-head-to-head` is the canonical
  build path.
* The 46 GB corpus transfer is already running, niced and bandwidth-capped; if
  it is incomplete when you start, wait on byte-count progress with an
  iteration cap -- never a blind `sleep`.
