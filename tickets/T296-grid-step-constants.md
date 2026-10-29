---
id: T296
title: Move the wire grid to 2^-8 A in every backend and the builder, first on the format-3 branch
phase: 3
lane: kernel
status: closed
model: gpt-6.1-sol-high
depends_on: [T270, T283, T284]
priority: high
branch: ticket/T296-grid-step-constants
worktree:
artifacts: results/T296/
---

## Context

**Gate.** Start when the author hands this ticket over. Its prerequisites are
closed:
* **T270** (the oracle numerics test family) closed on 2026-10-18 for
  practical CPU/CUDA delivery (`tickets/T270-oracle-numerics-test-family.md`,
  "Closure"; `results/T270/PRACTICAL_ACCEPTANCE.md`). Its checks are this
  ticket's acceptance instrument. The closure does not assert universal
  numerical certification or native Apple validation. Apple/Metal is a manual
  follow-up (`results/T270/APPLE_HANDOFF.md`) that gates T300 only, not this
  ticket. T270's closure waives none of the step-specific checks below.
* **T283** (the 2^-8 step check) and **T284** (`doc/FORMAT.md`, which records
  the step as `format.step_log2 = -8`).

**Sources of truth.** `decisions/D034-corpus-format-3.md` item 8 (accepted by
the author 2026-10-18) and `doc/FORMAT.md` (as T303 left it on main at 8869694d).
Where this ticket and either disagree, they win; report the disagreement to
the author rather than editing them.

Format 3 quantizes coordinates up front on a **2^-8 A = 0.00390625 A** grid
and stores the int16 values in units of that step (D034 item 8;
`results/T281/quant-sweep/REPORT.md` for the step sweep). 2^-8 is exactly
representable in float32, so dequantizing an int16 is exact. Today the step
is 0.001 A, pinned in many places across Python, CUDA, Metal, the CPU glue,
the builder and T270's harnesses. This ticket:
* moves **every** one of those sites;
* makes the compiled step checkable against the Python step;
* makes a reader refuse a format-2 manifest whose declared step differs from
  the compiled one;
* records the step change as a declared numerics change
  (`doc/NUMERICS_POLICY.md` section 4e; the last existing entry is 4d).

The format-3 reader needs nothing new: `validate.read_descriptor` already
refuses any `format.step_log2` other than -8 (seed
`tests/data/format3/adversarial/step_wrong`, code `schema.value`).

**Ordering.** This is the **first** ticket to merge into the integration
branch (which already carries main's format-3 work, e.g. T293's
`molecules.parquet` zstd change, because it equals main at 8869694d). The
builder (T291), the GPU source (T294) and the CPU workers (T295) all depend
on it: a format-3 corpus written in 2^-8 units is scored correctly only once
the device and the CPU glue dequantize at 2^-8. It deliberately does **not**
depend on any format-3 builder or engine source; it changes constants, tests
and the step check only.

**What is not here.** NUMERICS_POLICY 4f (tie order) and 4g (derived
centroid), and the rung 2 -> 3 attribution, all need format-3 corpora and
belong to T298 (before the switch merges). The rung-1 and rung-2 artifacts
that this ticket's 4e entry cites were produced by T283's 2^-8 sweep arm. **No
new ladder runs** are made here, and no `format2-ref` worktree is needed.

**Environment** (`tickets/CONVENTIONS.md`, the block with the three
exports): `ROSHAMBO3_CORPORA=<corpora>` (the
default in `paths.py` does not exist on roci),
`ROSHAMBO3_TEST_SDF=<test SDF>`, and
`ROSHAMBO3_GPU_LOCK=<lock base>`. The last is a
**base** for per-device lock files, not a lock file: take the GPU lock through
`bench.gpu_lock.GpuLock(ticket_id="T296", ...)`, which locks
`paths.gpu_lock_path(device_uuid)` and records the ticket id and PID. A literal
`flock $ROSHAMBO3_GPU_LOCK` locks a different file
and excludes nothing.

**One constant pair (D034 item 8).** T283 ran one sweep arm at 2^-8 with the
device constants changed. D034 decides **one constant pair, no split**:
`ROSHAMBO3_STAGE_Q_XYZ = 256.0f` and `ROSHAMBO3_STAGE_INV_Q_XYZ = 0.00390625f`
drive both the library dequantization and `r3_quantize`, and both move
together. The reason (`results/T283/REPORT.md`, "The rotated-query question";
`results/T283/PROTOCOL_ADDENDUM.md`, amendment 1;
`results/T283/rotated_query_check.json`):
* `r3_quantize` of a rotated query runs only in `start_mode_transform`
  (`kernels.cu:279-285`).
* Only `optimize_pairs_analytic_kernel` (`PoseSearch.ANALYTIC`) calls
  `start_mode_transform`.
* The shipped shape and combo configs use `PoseSearch.FIELD`, whose kernel
  stages the query **unrotated** (the start modes live in the initial pose).
  So the shipped path never re-quantizes a rotated query.
* On the analytic path, re-quantizing reproduced the exactly permuted
  integers on all 27,636 (coordinate, start) values of the 12 P1 queries, at
  both 0.001 and 2^-8.

**What T283 did not measure, and this ticket does** (D034 item 8 and reopen
condition 8). The analytic pose search is user-reachable, and it was never
screened at 2^-8:
* `roshambo3 screen --analytic` reaches it.
* A bare `--color` without `--mode` routes to it on CUDA and CPU
  (`cli.py:79-84`).
* The FIELD path refuses a color launch with a non-canonical interaction
  matrix and names `PoseSearch.ANALYTIC` as the route
  (`backend/cuda.py:550-558`).

T283's R1-R3 were FIELD screens, which never rotate the query, so they could
not have triggered a split. D034's no-split decision rests on the mechanism:
signed-permutation starts, and a float32 rotation error far below half a
step (0.00195 A): D034 quotes "under 5e-5 A"; `results/T283/REPORT.md` ("The
rotated-query question") measured at most 9.5e-7 A. Scope 8 measures the analytic path at screen level.

`r3_quantize` also stages **float32 library records**. Its call sites in
`kernels.cu` are near :1788, :2148-2150, :3891-3893, :3967-3969,
:4330-4332, :4353-4355 and :4371-4373 (line numbers on main at 8869694d).
The off-grid callers named at `_cuda_src/interface.cpp:485-492` send these
records. After this ticket they are staged 3.9x coarser; scope 6 records the
effect.

## Scope

Line numbers are from main at 8869694d; they drift, so find each site by
name and by the greps given. The CUDA sources are under
`src/roshambo3/backend/_cuda_src/`; other paths are under `src/roshambo3/`
unless stated.

1. **Every site that pins the step.**
   - **`numerics.py`.** `WIRE_QUANT_STEP = np.float32(0.001)` is at :130.
     `DEVICE_CONSTANTS` is at :158 and maps the step to
     `ROSHAMBO3_STAGE_INV_Q_XYZ` at :168. Its docstring (:131-152) documents a
     second Python constant (`rsb3.COORD_SCALE`) and states the exhaustive
     0.001 / 1000.0f round-trip facts (:143, :149): rewrite those for 2^-8,
     and say that the step constants must agree (scope 9).
   - **`kernels.cuh`.** Change **both** macros at :143-144:
     `ROSHAMBO3_STAGE_Q_XYZ` (1000.0f -> 256.0f) **and**
     `ROSHAMBO3_STAGE_INV_Q_XYZ` (0.001f -> 0.00390625f). `r3_fetch*`
     (:293-304) and `r3_quantize` (:311-313) follow from the macros.
   - **Every inline use in `kernels.cu`.** Known sites: :279-285, :746-748,
     :1788, :2148-2150, :3802-3804, :3891-3893, :3914-3916 (inline
     `__float2int_rn(ROSHAMBO3_STAGE_Q_XYZ*b)`), :3967-3972 and :4330-4376.
     For the complete list, run
     `grep -n "STAGE_Q_XYZ\|STAGE_INV_Q_XYZ\|r3_quantize" backend/_cuda_src/*`;
     only `kernels.cuh` and `kernels.cu` have hits. There is no split macro
     (D034 item 8): every site keeps naming the one pair, so changing the two
     macros changes them all. T283 read and confirmed each inline site
     (`results/T283/REPORT.md`, "Every hit of `grep ...`").
   - **Stale "0.001 A" / `1000` comments.**
     - `kernels.cuh`: around :138, :186, :193-206, :228, :239, :242, :636 and
       :658.
     - `kernels.cu`: around :223-232, :445, :632, :2143, :2288, :2869, :3919,
       :4319 and :11494.
     - Elsewhere: `_cuda_src/interface.cpp:489`, `backend/cuda.py:161, 224`,
       `engine/source.py:46`, `engine/buffers.py:205`, `prep/build.py:81,
       297, 1295`, `prep/conformer.py:6-7, 137`, `format/rsb3.py:26, 163`
       (the +-32.767 A range), and the help text at `cli.py:686`. T283's
       "Deliberately left at 0.001" table lists most of them.
     - Rewrite each to name the wire step, not a number. Keep T87's verbatim
       precondition expression at `kernels.cuh:193` and add the 2^-8 line
       beside it, as T283 did.
   - **Metal.** The literal `.001f` in `backend/_metal_src/kernels.metal:225`
     (`lib()`, :208), and the comments at :86, :206 and :219.
   - **CPU glue.**
     - `backend/cpu.py` imports `WIRE_QUANT_STEP` (:264, :634, :817, :861) and
       multiplies by it (:272, :636, :818, :862, :1526-1528); it never uses
       `fmt.COORD_SCALE`. These follow the constant; only the comment at
       :1520 (which names 0.001) needs a rewrite.
     - `backend/cpu.py:355` writes a literal
       `"wire_quantization_step_angstrom": 0.001` contract.
     - The same literal is in `format/self_sidecars.py:60`
       (`COLOR_SELF_CONTRACT`, the dict at :51). T283's q2m8 manifests
       carried 0.001 there while the values were verified at 2^-8. That was a
       silent mismatch, because the CUDA route never reads it; this ticket
       changes it. After the change, `cpu.py:401`'s equality check refuses
       T283's q2m8 corpora on the CPU route (their manifests say 0.001);
       that is expected and does not affect scope 8, which is CUDA.
     - `format/dataset.py:488` and `:632` are defaults for legacy manifests
       without vaa metadata, which were built at 0.001. **Leave them at
       0.001** (it is the truth for those corpora) and list them in
       `remaining_0001.md`.
   - **The builder's step.** `format/rsb3.py:164` `COORD_SCALE = 0.001` (its
     module docstring at :23 says 0.001) and `format/rsb3.py:657`
     `quantize(coords_f, scale=COORD_SCALE)`, used by the builder and by
     query snapping. `prep/build.py` imports `COORD_SCALE` at :54. It uses
     it at :300, :1124 (contract), :1299, :1480 (`coord_scale`), :1495
     (contract), :2052 and :2122; `format/rsb3.py:329` defaults a
     `coord_scale` parameter to it. All follow the constant. After this
     ticket, the builder quantizes at 2^-8, in units of the step.
   - **`engine/query.py`.**
     - `snap_to_wire_grid` (:47) calls `rsb3.quantize` (default scale) and
       multiplies by `WIRE_QUANT_STEP`, so it snaps to the 2^-8 grid once the
       constants move.
     - Update the range text at :61, :72-73 and :161, the off-grid message at
       :98, and the other 0.001 text at :11, :48, :114 and :158.
     - int16 at 2^-8 spans exactly [-32768 x 2^-8, 32767 x 2^-8] =
       **[-128.0, +127.99609375] A** (D034 item 8). The 0.001 range is
       [-32.768, +32.767] A.
   - `cli.py:514-517` (the `coord_scale` refusal; :54 prints `coord_scale`)
     and `prep/convert.py:382-384`.
   - **`reference/numerics_contracts.py:30`**: `CoordinateGrid.step = 0.001`
     (T270's contract model). Default it to `float(numerics.WIRE_QUANT_STEP)`.
   - **T270's harnesses**, which must run at the new step for the Deciding
     measurement. These hard-code a `* 1000` wire step:
     - `bench/numerics_cuda_winners.py:39`
     - `bench/numerics_cuda_field_winners.py:48`
     - `bench/numerics_optimizer.py:33`, `:37`
     - `bench/numerics_optimizer_real.py:29`

     Read the constant instead. `bench/metal_cpu_rates.py:33` and
     `bench/metal_combo_provisional.py:76` are Metal/benchmark harnesses:
     fix them the same way, or list them in `results/T296/remaining_0001.md`
     with a reason.
2. **The step check.** `engine/buffers.py::require_wire_quantization`
   (:154-171) compares a corpus's declared step with Python's
   `WIRE_QUANT_STEP`. Make it compare with the **compiled** step (scope 9)
   when the CUDA extension module imports, and with `WIRE_QUANT_STEP`
   otherwise. Reading the compiled step must not create a CUDA context (it
   is a constant exported by the module, read without touching a device):
   `assert_arithmetic_pinned()` runs at every backend entry, and a context
   there would hang under a foreign MPS daemon (CLAUDE.md).
   The refusal must name both values.
   - Its callers (`engine/buffers.py:237`, `format/dataset.py:100-101` and
     `:192-193`, `engine/source.py:639` and `:688`) pass the format-2
     manifest's `coord_scale`. Keep every one: format-2 corpora are still
     read on the branch until T298.
   - For format 3, add to `numerics.assert_arithmetic_pinned()` the
     invariant `np.float32(2.0 ** format.r3g.limits.STEP_LOG2) ==
     numerics.WIRE_QUANT_STEP` (import `limits` inside the function;
     `format/r3g/limits.py` imports nothing from roshambo3, but a top-level
     import from `numerics` risks a cycle through `roshambo3.format`).
     It is exact, because both are powers of two.
     `reference.STEP_LOG2` is a second copy and must agree too. A format-3
     corpus can then only be read by a build whose step equals the spec's.
3. **Tests that pin 0.001.** Update each to read the constant rather than a
   new literal, wherever possible. Fix only the step expectation; each file's
   later owner (`results/T282/test_migration_matrix.md`, rows marked "step
   pin") does the rest. T283 measured the size of this on a build with the
   constants patched: **205 of the 242 tests** in `test_numerics.py`,
   `test_query_wire_grid.py` and `test_pack_into.py` fail. All 205 are in the
   latter two, whose 0.001 fixtures the wire-step check refuses as designed;
   all 27 in `test_numerics.py` pass (`results/T283/REPORT.md`, end of
   "Every hit"). The list:
   - `tests/test_numerics.py:200-224` only checks that the `kernels.cuh`
     `#define` literals agree with `numerics.DEVICE_CONSTANTS`; it has no
     literal step. **Change the header and `numerics.py` in one commit**, or
     it fails.
   - `tests/test_numerics_contracts.py:23-24` (a 1000 / 0.001 wire step
     against `CoordinateGrid`'s default, scope 1) and :27 (`[[33, 0, 0]]`
     expected to overflow, which is in range at 2^-8). Leave :37, which
     builds arbitrary grids (0.002 / 0.001 / 0.003), not the wire step.
   - `tests/test_pack_into.py`: 0.001 at :72, :103, :124, :141, :154
     (`require_wire_quantization`), :167, :204-205, and the planar tests at
     :234, :249, :270-271 and :284.
   - `tests/test_wire_record_cuda.py`: `* 1000.0` at :70 and `np.float32(0.001)` at
     :75, :83 and :140.
   - `tests/test_query_wire_grid.py`:
     - the range test `test_the_edge_of_the_range_is_representable`
       (:107-110; `32.767` / `-32.768` at :108) moves to the 2^-8 edges
       above;
     - the out-of-range parametrize at :94 (`32.768, -32.769`, and `40.0`,
       which is in range at 2^-8);
     - the error-message match at :319.
   - `tests/test_cpu_combo_self_overlaps.py`: :231, :243 and :291.
   - `tests/test_color_field_cuda.py`: :264-270 grid emulation; comments at
     :242 and :246.
   - `tests/test_format.py`:
     - `assert COORD_SCALE == 0.001` at :26 (the `format/rsb3.py` constant,
       re-exported by `roshambo3.format`);
     - the round-trip bound at :73-74;
     - the +-32.767 A note in `test_refuses_to_clip` at :76-77 and its
       `quantize([[40.0, ...]])` overflow expectation at :81 (in range at
       2^-8: use a value beyond 128 A);
     - the `[[0, 1000, -2500]]` int16 values at :165.
   - `tests/test_engine.py`: `pack_into(..., 0.001)` at :221, :230 and :239.
     - The last is in `test_refuses_a_buffer_that_is_too_small` (:236). It
       **will pass for the wrong reason** after the step change: it still
       raises `ValueError`, but for the step instead of the too-small buffer
       it tests. Pass the compiled step, and add a `match=` on the
       buffer-size message so the step refusal cannot satisfy it.
     - Also fix the fake reader's `coord_scale=0.001` at :258 and the
       `_stub_source` reader at :843-846.
   - `tests/test_prepare_self_sidecars.py` (:238, :451) and `tests/test_prep_stored_vaa.py` (:72; :34-35 follow the
     constant). Per their rows in `results/T282/test_migration_matrix.md`,
     T293 rewrites the first and deletes the second, so their affected tests may
     instead be marked `pytest.mark.xfail(strict=True, reason=...)` naming
     T293.
   - `tests/test_cpu_library_coordinate_layouts.py` already reads
     `WIRE_QUANT_STEP`; fix only its docstring (:3).
   - The C++ fixtures `tests/shape_field_evaluator.cpp` and
     `tests/reduced_pose_color.cpp` contain `0.001f` / `1000.0f`. These are
     finite-difference steps, padding and sentinels, not the wire step. Leave
     them, and list them in `remaining_0001.md`.
   - **Outside the T282 census:**
     - **The color-contract fixture.**
       - `tests/test_color_contract.py:868-869` snaps the query at 0.001
         against `tests/data/color_contract_fixture.npz`, whose every input
         coordinate is `float32(k) * float32(0.001)`.
       - Regenerate the fixture at 2^-8 with its generator
         `tickets/T153/generate_color_fixture.py`. Its `wire_grid()` helper
         (:66-90) hard-codes 0.001 at :88 and :90. The generator reads `ROSHAMBO3_TEST_SDF` (see Context, Environment) and
         stamps git and platform.
       - Then rerun `tickets/T153/crosscheck_cuda.py`
         (`results/T153/cuda_crosscheck.json`).
       - `tickets/T159/generate_field_fixture.py` derives
         `tests/data/color_field_fixture.npz` from it, and
         `tests/test_cpu_scalar_color.py:15` also reads it: regenerate and
         rerun both.
       - Rewrite `doc/COLOR_CONTRACT.md` section 9's wire-grid paragraph
         (:259-287), not just its numbers: its 5e-4 / 3.5e-4 figures (:265,
         :276) are 0.001-snapping facts.
     - `tests/test_color_staging_cuda.py` (:81-88, :131-134). It skips on the
       shipped build, so run it on a `-DROSHAMBO3_TUNING_CELLS=ON` build, or
       the break is invisible.
     - `tests/test_metal.py:37` (`np.rint(coords * 1000)`): Mac only; the author
       runs it.

   `tests/test_count_vector.py:186-201` passes 0.001 to `combine_shape_color`
   but takes the float32 branch, which never checks the step, so it does not
   break here. `tests/test_cpu_combo_executor.py:98` (`* 0.001`) is grid
   data; confirm it is not the wire step. Grep
   `0\.001|1000\.0f|\* *1000\b` across `tests/` and `bench/numerics_*` for
   anything newer.
4. **Format-2 fixtures on the branch.** Tests that read external format-2
   fixture corpora now fail the step check by design. These are the
   `tests/conftest.py` fixtures `smoke_corpus` (a 2K-molecule smoke corpus, :92),
   `dev_corpus` (an internal development corpus, :103), `multiconformer_corpus` (an internal
   multiconformer corpus, :115), `color_corpus` (DUD-Z PUR2, :127) and
   `color_corpus_current_numbering` (:143), all through `_corpus_or_skip`
   (:83), plus any test that opens a corpus under `$ROSHAMBO3_CORPORA` (find them
   with `grep -rln "ROSHAMBO3_CORPORA\|corpora_root\|_corpus_or_skip" tests/`).
   Pytest ignores marks on fixtures, so mark the **tests** that use them, and
   only those that actually fail the step check on roci (a strict xfail on a
   test that never reaches the check would XPASS and fail). Mark them
   `pytest.mark.xfail(reason="format-2 fixture; T298 switches to T299 part (a) rebuilds", strict=True)`
   rather than deleting or loosening anything; T298 removes the marks. A
   fixture that *skips* because its corpus is absent stays a skip; record
   which ones ran on roci.
5. **Round-trip precondition: verify.** T283 extended
   `tickets/T87/int16_roundtrip.py` to take the step as an argument (`--step`,
   :214; commit 47fdb656, exhaustive at 0.001 and 2^-8). It compiles its own probe with `nvcc` from the step you pass, so it
   checks the arithmetic, not the branch's headers. Run it at 2^-8 and
   confirm two things:
   - `(short)rint(Q * (INV_Q * v)) == v` for every int16;
   - the two-rounding order `cscale * (INV_Q * (float)v)` documented at
     `kernels.cuh:196-206` is preserved (NUMERICS_POLICY 4c): confirm this
     by reading `r3_fetch*` and every inline dequantization site on the
     branch, since the probe does not read the headers.
6. **Golden FIELD arm.** Regenerate `tests/test_golden.py`'s FIELD arm with
   `bench/make_golden.py` (it writes both arms; regenerate both, since the
   stored analytic data must also be at the new step, but only FIELD is
   compared bit for bit), and record the movement. T128/T270 retired the
   ANALYTIC arm from the bit comparison.
7. **`engine/query.py` module docstring (:22-34).** It says a rotating start
   "re-quantizes the ROTATED query at the same 0.001 A step on the CUDA
   analytic path" (:23), and calls that a numerator/denominator split from
   two coordinate sets. On the shipped start sets (signed permutations), that
   re-quantization is the identity at either step (D034 item 8;
   `results/T283/rotated_query_check.json`), so there is no split on them.
   Rewrite the paragraph to say so. Name the step as the wire step rather
   than 0.001 A, and keep the caveat for a start set that is not a signed
   permutation.
8. **Analytic-path check at 2^-8 (R2/R3 in analytic mode).** T283 screened
   FIELD only (see Context). Run R2 (DUD-Z enrichment) and R3 (DUD-Z
   fidelity) of `results/T281/quant-sweep/PROTOCOL.md` section 6 ("Reading
   rule") with `pose_search=PoseSearch.ANALYTIC`, criteria and thresholds
   unchanged.
   - **Arms.**
     - `q001` (gold and R2 baseline) and `ctrl` (the grid-phase control),
       both screened in analytic mode by a **0.001 build**. R3 is paired
       against `ctrl`, and a cell where the control fails is
       non-discriminating.
     - `q2m8`, screened in analytic mode by **this ticket's 2^-8 build**.
     - Every comparison is analytic against analytic: R2's baseline and
       R3's reference are the analytic `q001` screens; T283's FIELD screens
       are not inputs.
     - **Determinism control** (PROTOCOL.md section 3): run `q001` and
       `q2m8` twice each in separate processes (`q001rep`, `q2m8rep`); gids
       and score words must be byte-identical.
     - **R1 (PubChem shape recall) is not run** in analytic mode (the author,
       2026-10-18): the mechanism argument (D034 item 8) plus R2/R3 cover the
       risk, and D034 reopens only if a check that is run fails. Record the
       omission in `results/T296/README.md`; do not raise it again.
     - The 0.001 build is a fresh build of commit 8869694d (the integration
       branch's base, exactly that sha even if main moves) in a separate worktree
       with its own venv. The T281 and T283 worktrees and their venvs no
       longer exist, so T283's rung-1 binary (`_roshambo3_cuda` sha256
       `79464e34...`) cannot be reused. A rebuilt CUDA binary is not assumed
       bit-identical to it, which is acceptable: every arm here is a new
       analytic-mode screen.
     - Two binaries are unavoidable, because a 2^-8 build refuses 0.001
       corpora. Record both identities: `cuda_src_tree`, `cuda_src_sha256`,
       the `.so` sha256, and the git sha read from the build stamp *in the
       record*, not reconstructed afterwards.
   - **Corpora.** They exist already and are read-only, under
     `$ROSHAMBO3_CORPORA` (see Context, Environment).
     - `$ROSHAMBO3_CORPORA/_t281_quant/{q001,ctrl}/dudez/<target>`
     - `$ROSHAMBO3_CORPORA/_t283_quant/q2m8/dudez/<target>`
     - 12 targets each: ADA AMPC ANDR CXCR4 EGFR FABP4 HMDH HS90A MAPK2 PARP1
       PUR2 RENI.

     Do not rebuild them, and never copy them into the worktree
     (pitfall 22). Write the screens themselves (T283's were 329 MB)
     under `$ROSHAMBO3_CORPORA/_t296_analytic/screens/<arm>/`, and only
     summaries under `results/T296/analytic/`.
   - **Harness.** Copy `tickets/T283/screen_dudez.py`, `run_screens.py` and
     `build_arms.py` to `tickets/T296/`. Rewrite `build_arms.py`'s `PY`
     (today `<repo>/.venv/bin/python`), `env_for(arm)` and `screens_root`
     so each arm runs under the right venv (the 0.001 worktree's for
     `q001`/`ctrl`, this worktree's for `q2m8`) and writes under the root
     above. Give it a
     `--pose-search {field,analytic}` flag that sets `pose_search` on both
     the shape and the combo `ScreenConfig`. Do the analysis with
     `tickets/T283/analyze.py`'s R2/R3 code, extended to read the analytic
     screens. If the analytic path refuses a mode or config the FIELD screens
     used, record the refusal and the config actually run.
   - **Grade.** Decision grade or it does not count:
     - Hold the GPU lock (`bench.gpu_lock.GpuLock`, see Context,
       Environment) before any CUDA context, for the whole run.
     - Export `CUDA_MPS_PIPE_DIRECTORY=<private dir>`, and check that
       `pgrep -a nvidia-cuda-mps` is empty.
     - Record foreign GPU processes and profiler state at the start and the
       end, as `tickets/T283/provenance.py` does.
   - **Outcome.** A pass is recorded in `results/T296/analytic/` and in
     NUMERICS_POLICY 4e. **A fail of R2 or R3 in analytic mode is D034
     reopen condition 8**: stop, report to the author, and measure separate
     query and library constants (the split macro of D034 reopen 8) before
     this ticket closes.
   - **T270 coverage of ANALYTIC with a rotating start: a known gap.** On
     main at 8869694d, T270's fixed-pose and frame checks run the analytic
     path on **CUDA** only at `start_mode=0`
     (`tests/test_numerics_backends.py:136-148` ->
     `bench/numerics_backends.py:169-175`, `steps=0, start_mode=0`). The CPU
     `analytic_simd` checks (`test_numerics_backends.py:200-231`) do run at
     `start_mode=1`, but CPU has no `r3_quantize`.
     - On CUDA, `start_mode=1` analytic runs only in
       `tests/test_numerics_multigpu.py:33-34`, a determinism test that
       needs two GPUs.
     - No T270 test runs ANALYTIC at `start_mode=2`.
     - So `start_mode_transform`'s `r3_quantize` is not exercised by a T270
       bound.
     - This ticket does not edit T270 tests. Confirm the gap on the branch
       head and record it in `results/T296/README.md`. **Decided (the author,
       2026-10-18):** scope 8's analytic-mode screens suffice, because they run
       the shipped rotating start. Each scope-8 run record MUST therefore
       record the `start_mode` actually used, and it must be a rotating one
       (1 or 2); a run at `start_mode=0` does not count toward this.
9. **The compiled step is checked against the Python step.** Today nothing
   notices a 2^-8 CUDA `.so` installed against 0.001 Python:
   `numerics.numerics_stamp()` (:722) reports `DEVICE_CONSTANTS` from Python,
   not from the binary. T283 hit exactly this state: a reverted `src/` with
   a 2^-8 `.so` still installed. Per backend:
   - **CUDA.** The extension exports its compiled step: for example, a
     `compiled_wire_step()` binding returning `ROSHAMBO3_STAGE_INV_Q_XYZ`,
     with `ROSHAMBO3_STAGE_Q_XYZ` beside it.
     `numerics.assert_arithmetic_pinned()` (:687) **raises** -- not warns --
     when it differs from `numerics.WIRE_QUANT_STEP`, or when
     `Q * INV_Q != 1`. `require_wire_quantization` (scope 2) compares the
     corpus's step with this compiled value.
   - **CPU.** The CPU extension compiles no step. `backend/cpu.py` passes `WIRE_QUANT_STEP` in at call time
     (`_cpu_src/cpu_block_prepare.cpp`: `scale = coord_scale` at :115,
     multiplies at :141, :163 and :178). The check has two parts:
     - `numerics.WIRE_QUANT_STEP == rsb3.COORD_SCALE == 2.0 **
       limits.STEP_LOG2 == 2.0 ** reference.STEP_LOG2` (all four Python
       constants; scope 2), asserted in `assert_arithmetic_pinned()`;
     - no CPU source carries a literal step. `grep -nE "0\.001\b|1000\.0f" backend/_cpu_src/*`: the only
       hits today are a comment at `interface.cpp:743` and an unrelated
       `0.001f` at `probe.cpp:349` (without `\b` the grep also matches
       unrelated constants such as `0.00138...` in `color_scalar.cpp`).
   - **Metal.** `backend/metal.py` compiles `_metal_src/kernels.metal` from
     source at run time, and the step is the literal `.001f` in `lib()`.
     Either substitute `WIRE_QUANT_STEP` into the source before compiling
     (`metal.py` already rewrites the source by token with `_replace_once`,
     :28), or assert that the literal equals it before compiling. A test reads
     the source and fails on disagreement; it runs without a Mac.
   - **Tests.** A unit test monkeypatches the binding (or `WIRE_QUANT_STEP`)
     to disagree, and asserts that the refusal names both values. No GPU is
     needed.
10. **NUMERICS_POLICY section 4e (step)**, written from T283's artifacts:
    - rung 1 = format 2 at 0.001 A;
    - rung 2 = format 2 at 2^-8 with the device at 2^-8 (T283's arm);
    - the sweep criteria R1-R3, as `results/T281/quant-sweep/PROTOCOL.md`
      section 6 states them;
    - T270's fixed-pose bias at both steps;
    - the golden FIELD movement;
    - scope 8's analytic R2/R3 result;
    - every site the constants touch (D034 item 8 requires the list): the
      scope 1 sites as moved, by file and symbol.

    Quote numbers verbatim from T283's results. T283's rung-1 records carry
    no `git_sha`, `numerics_stamp` or lock path, so cite rung 1 by
    `cuda_src_tree` `3f4819d6` and `.so` sha256 `79464e34...`
    (`results/T283/REPORT.md`, "Correction (2026-10-17)";
    `results/T283/ladder.json` `rung1.correction`).

## Deciding measurement

T270's check family is green on CUDA and CPU at 2^-8 on this branch, with
every step site moved (the grep in Acceptance is clean). On CUDA, run from the
branch worktree with its own build, under the GPU lock:
`python -m bench.run_numerics_locked --lock-receipt <receipt.json> --native-build <build dir> --report-dir <dir> -- tests/test_numerics_*.py --junitxml=<dir>/junit.xml`.
(`bench.run_numerics_locked` takes the lock itself.) On CPU-only hosts, run
`python -m bench.run_numerics_checks --profile pre-T296 --native-build <build dir> --report-dir <dir>`
(`pre-T296` is the CPU+CUDA profile and the default; `pre-T300` adds Metal).
See `results/T270/PRACTICAL_ACCEPTANCE.md`, "Default gate". Review the pytest
result and the coverage report together. Not-run cells stay visible, and a
skip is not a pass.

## Acceptance

- `pytest tests/test_numerics.py` green, with `DEVICE_CONSTANTS` and the parsed
  `kernels.cuh` literals agreeing at 2^-8 (one constant pair; D034 item 8).
- Every file in scope 3 green, or strict-xfail where scope 3 allows it.
  - This includes `test_color_contract.py` and `test_cpu_scalar_color.py`
    against the regenerated fixtures.
  - `test_color_staging_cuda.py` must run (not skip) on a
    `-DROSHAMBO3_TUNING_CELLS=ON` build.
  - `test_metal.py` is recorded "not run" unless the author ran it on a Mac.
- T270's check family green on CUDA (roci) and CPU (x86, and aarch64 if a host
  is available; otherwise recorded as not run). Metal arms are recorded as
  "not run" if no Mac was used; they gate T300, not this ticket.
- The reader refuses a format-2 manifest whose declared step differs from the
  compiled one, naming both values (test with a manifest at 0.001).
  `tests/data/format3/adversarial/step_wrong` is still refused, and
  `assert_arithmetic_pinned()` refuses a `limits.STEP_LOG2` that disagrees with
  `WIRE_QUANT_STEP` (monkeypatched test).
- `grep -rnE "0\.001f?\b|1000\.0f|\.001f|32\.76[78]" src/roshambo3` has been
  reviewed (the last two alternatives catch the Metal literal and the range
  text). Every
  remaining hit is unrelated to the coordinate step and is listed in
  `results/T296/remaining_0001.md` with a one-line reason each.
  - Start from T283's audit of the 67 hits on main at 21747d8c
    (`results/T283/REPORT.md`, the "Changed" and "Deliberately left at 0.001"
    tables). It names what it left for this ticket.
  - On main at 8869694d the same grep without `\b` gives 68 hits;
    `numerics_contracts.py` is new since T283's audit.
- The rest of the suite is green, except the strict-xfail format-2 fixture
  tests. Record their count in `results/T296/README.md`.
- NUMERICS_POLICY section 4e written with numbers quoted verbatim from T283.
  `tests/test_golden.py`'s FIELD arm regenerated, and its movement recorded
  there.
- **Analytic path (scope 8):** R2 and R3 in analytic mode at 2^-8 against the
  0.001 baseline, judged by `PROTOCOL.md` section 6 unchanged.
  - Decision grade under the GPU lock, with both binaries' identities
    recorded; results in `results/T296/analytic/`.
  - A fail stops the ticket (D034 reopen condition 8).
  - The T270 rotating-start ANALYTIC gap is confirmed, recorded and raised
    with the author, and the author's answer recorded.
- **Compiled step (scope 9):** a CUDA `.so` whose compiled step differs from
  `numerics.WIRE_QUANT_STEP` is refused by `assert_arithmetic_pinned()`, and
  so at every backend entry, naming both values. CPU and Metal checks as scope
  9 states. Tests cover each without a GPU.
- `engine/query.py`'s module docstring no longer describes a rotated-query
  split on the shipped starts (scope 7), and `test_engine.py`'s too-small-buffer
  test matches its own message (scope 3).

## Traps

- **`r3_quantize` shares the dequantization constant, and that is intended.**
  - D034 item 8 keeps one pair, so both move together.
  - Do not reason that the change coarsens the shipped rotated query.
    `start_mode=1` ships, but on the shipped `PoseSearch.FIELD` path the
    start lives in the initial pose and the query is staged unrotated.
  - Only the analytic kernel's `start_mode_transform` (`kernels.cu:279-285`)
    re-quantizes a rotated query. There it is the identity on the shipped
    start sets at either step (D034 item 8; `results/T283/REPORT.md`, "The
    rotated-query question"; `results/T283/rotated_query_check.json`).
  - That is the mechanism, not a screen-level measurement. The analytic
    route is user-reachable and is screened at 2^-8 here for the first time
    (scope 8).
  - What the change *does* coarsen is the staging of the float32 library
    record (scope 6).
- **`Q` and `INV_Q` move together.** `STAGE_Q_XYZ` is the inverse
  (1000 -> 256); changing only one breaks the round trip silently.
- **There are four step constants in Python.**
  - `numerics.WIRE_QUANT_STEP` and `format/rsb3.py::COORD_SCALE` move here.
  - `format/r3g/limits.py::STEP_LOG2` and `format/r3g/reference.py::STEP_LOG2`
    are already -8.
  - Missing `COORD_SCALE` leaves the builder writing 0.001-unit corpora,
    which the new device misreads by 3.9x.
  - Scope 9 asserts that all four agree.
- **Do not fit tolerances to the new tree** (T270 traps). Bounds come from
  declared arithmetic; a check widened until green detects nothing.
- **The Metal literal is easy to miss.** Run
  `grep -rn '\.001' src/roshambo3/backend` before declaring done.
- **Do not delete or weaken format-2 fixture tests.** Strict xfail keeps them
  honest until T298 points them at rebuilt corpora.
- **Build stamps.** The scope 8 0.001 build and this branch's build must each
  be built in their own worktree with their own venv. An editable install
  redirects every import to the checkout it was built from, so check
  `roshambo3.__file__` and the `.so` path in every run record.

## Working rules

See `tickets/CONVENTIONS.md`.
* **Branches.** Cut `ticket/T296-grid-step-constants` from
  `ticket/T281-format3-switch`. That branch exists; at 8869694d it equals
  main, and this is the first ticket to merge into it. Merge back into
  `ticket/T281-format3-switch` (no-ff), **never into main**. Use a
  dedicated worktree.
* **Venv.** There is no shared venv. Build one in each worktree as
  `doc/BENCHMARKING.md` "The venv" shows: this one, plus the scope 8 0.001
  build. Check that `roshambo3.__file__` points into the worktree.
* **GPU.** Export `CUDA_MPS_PIPE_DIRECTORY=<private dir>` and check
  `pgrep -a nvidia-cuda-mps` before any CUDA context, including CMake's CUDA
  probe during a build. Take the GPU lock (`bench.gpu_lock.GpuLock`; Context, Environment) before
  creating a context for scope 8 and for T270's CUDA gate (`bench.run_numerics_locked`
  takes it). Correctness tests may run unlocked.
* No blind sleeps; commit before long waits (D011).


## Implementation checkpoint (2026-10-18)

Claimed by gpt-6.1-sol-high in its own worktree.
Constants, compiled-step guards, fixtures and analytic campaign are implemented;
analytic R2/R3 pass unchanged and both repeats are byte-identical under actual
per-device GPU locks. Evidence and all unresolved failures are recorded in
`results/T296/README.md`. The pinned 8869694d baseline passes its 29 fixed-pose /
optimizer checks. Candidate practical acceptance remains incomplete because of
step-sensitive held-out optimizer-control, E2E basin-separation qualification,
and raw off-grid FIELD/ANALYTIC comparison failures. No thresholds/seeds/fixture
geometry were changed to obtain a pass. The historical multiarch golden regeneration passed all 13 tests; independent
Sol review approved its receipts and the precise wire-refusal xfails. Final
locked T270: 263 passed, 28 skipped, 23 failed, with no setup errors. Native ARM replay completed with 216 passed, 87 skipped and 11 basin failures;
its focused CPU scope passed 274 tests with 6 skips. Full tuning Release
staging passed all 10 tests with zero skips; a separately labelled host-O0
artifact also passed all 10 and proved identical embedded device ELF. Both
artifacts and source/command/hash manifests are preserved outside disposable
worktrees. Implementation and authorized checks are complete, but the acceptance
gate has failed; status is in-review with blocked acceptance. This is not a closure.


## Final review checkpoint (2026-10-18)

The source and evidence remain on `ticket/T296-grid-step-constants`; evaluated
source/harness head is d0db129dafffa81c54ff79efdccbdfcb31562e50. The pinned analytic
baseline is 8869694d. Exact protocol references, every failed gate, both independent
artifact pointers and binary hashes are in `results/T296/README.md`. Independent
Sol review approved source/provenance fixes and both 10/10 staging receipts.
The numerical implementation is not eligible for integration while the held-out
optimizer, empirical basin-qualification and off-grid comparison failures remain.
Thresholds, seeds, geometry and recovery neighborhoods are unchanged. The ledger
is in-review rather than claimed or closed; ticket/harness/results can be archived
for inspection while numerical source stays isolated on its branch.

## Wave acceptance — 2026-10-20

Accepted for merge by the author after review of T290 whole-system measurements,
T304 scheduling-invariance qualification, T296 FIELD/ANALYTIC recall and
enrichment, and the matched .001 / 2^-10 / 2^-8 diagnostic matrix. See
`results/wave1/ACCEPTANCE.md` for the scoped decision and remaining limitations.
This supersedes the historical blocked-acceptance wording without relabeling
failed tests as passes. T305 remains open/deferred; T306 owns the proposed
recall-focused test-suite improvements. No CPU block-size winner is claimed.
