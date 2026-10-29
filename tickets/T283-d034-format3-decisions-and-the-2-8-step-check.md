---
id: T283
title: Record format 3's decisions as D034, after confirming the 2^-8 A step with the device constants actually changed
phase: 3
lane: research
status: closed
model: opus
depends_on: [T281]
priority: high
branch: ticket/T283-d034-format3-decisions
worktree: <worktree>
artifacts: results/T283/
---

## Context

T281 (`tickets/T281-corpus-format-3.md`) designs the release-time corpus format
("format 3") and records the author's decisions of 2026-10-17 in its "Decisions"
sections (numbered 1-17). They outlive any one ticket and constrain every
implementation ticket T284-T301, so they belong in a standing decision record:
**D034** (`decisions/`; read `decisions/D033-*.md` and `decisions/D021-*.md` for the
house format: Date, Status, Source, Constrains, Decision, the measurement, and an
explicit reopening condition).

One decision rests on a measurement that has not been taken. The coordinate step
is **2^-8 A = 0.00390625 A**, chosen because it is exactly representable in float32
(T281 design point 8). The step sweep (`results/T281/quant-sweep/REPORT.md`) found
0.005 A the coarsest passing step and 0.002 A indistinguishable from its control, so
2^-8 passes by interpolation. But the sweep **never changed the device constants**: it
stored coarse values in 0.001 A units and the engine dequantized at 0.001 as today
(REPORT "What this does not establish"). In the CUDA build the same pair of macros,
`ROSHAMBO3_STAGE_Q_XYZ` / `ROSHAMBO3_STAGE_INV_Q_XYZ`
(`src/roshambo3/backend/_cuda_src/kernels.cuh`), drives both the library
dequantization (`r3_fetch*`) **and** `r3_quantize`, which re-quantizes the **rotated
query** on rotating starts (the `rotate` branch of the query transform in
`src/roshambo3/backend/_cuda_src/kernels.cu`, the lines calling
`r3_quantize(&r[0])`). At 2^-8 that query staging coarsens ~4x too. That has to be
measured before D034 can say the step is settled.

**Gate.** Approved by the author on 2026-10-17, together with T282-T290, to run
while T270 is still being built: this ticket is additive (new files, modules,
CI jobs or measurements; no change to main's numerics), so T270 does not gate
it. T291-T302 remain gated on T270.

## Scope

### 1. Exhaustive round trip at 2^-8

Extend `tickets/T87/int16_roundtrip.py` (its three arms: numpy float32 with `np.rint`,
a C program with `rintf`, and an nvcc device build calling `__float2int_rn`) with a
step parameter, and run it for 0.001 (must reproduce `results/T87/int16_roundtrip.json`)
and 2^-8 (`Q = 256.0f`, `INV_Q = 0.00390625f`). Expected: identity on all 65,536
int16 values at 2^-8 by construction (both constants are exact powers of two). Write
`results/T283/int16_roundtrip.json`. Keep the script's existing behaviour as the
default; add the step as an argument.

### 2. One sweep arm at 2^-8 with the device constants changed

On the ticket branch only (this experimental build is **never merged**), change:

- `src/roshambo3/backend/_cuda_src/kernels.cuh`: `ROSHAMBO3_STAGE_Q_XYZ` to `256.0f`,
  `ROSHAMBO3_STAGE_INV_Q_XYZ` to `0.00390625f`. Leave the weight macros
  (`ROSHAMBO3_STAGE_Q_W`, `ROSHAMBO3_STAGE_INV_Q_W`) alone.
- `src/roshambo3/numerics.py`: `WIRE_QUANT_STEP = np.float32(0.00390625)` (it feeds
  `DEVICE_CONSTANTS["ROSHAMBO3_STAGE_INV_Q_XYZ"]`; `tests/test_numerics.py`'s header
  parse checks the two agree).
- `src/roshambo3/format/rsb3.py`: `COORD_SCALE = 0.00390625`, so the builder
  quantizes at 2^-8 **and stores int16 in units of 2^-8** (this is the difference
  from the sweep's harness, `results/T281/quant-sweep/quantpatch/sitecustomize.py`,
  which kept 0.001 units and must **not** be used for this arm). The query snap
  (`engine/query.py::snap_to_wire_grid`) and `engine/buffers.py::require_wire_quantization`
  then follow `WIRE_QUANT_STEP` / `COORD_SCALE` automatically; confirm by reading them.
- `src/roshambo3/backend/_cuda_src/kernels.cu`: every inline use of the two stage
  macros, including the `r3_quantize` call sites in the query-transform `rotate`
  branch (around lines 279-285 and 2134-2136) and the inline quantize/dequantize at
  around 3875-3877 (`BX/BY/BZ`), plus 746-748 and 3763-3765. These use the macros, so
  changing the macros changes them; read each to confirm none hard-codes `1000` or
  `0.001` separately. Update any stale "0.001 A" comments (grep `kernels.cuh` and
  `kernels.cu`; one is near `kernels.cu:230`) on the branch so the build reads consistently.
- Sites that follow `COORD_SCALE` / `WIRE_QUANT_STEP` automatically (read each to
  confirm): `prep/build.py` (`stored = q.astype(np.float32) * np.float32(fmt.COORD_SCALE)`
  and the `wire_quantization_step_angstrom` metadata it writes), `cli.py`'s
  `coord_scale` refusal (`if float(r.coord_scale) != float(fmt.COORD_SCALE)`, around
  :481), `engine/query.py::snap_to_wire_grid`, `engine/buffers.py::require_wire_quantization`.
- Sites the arm may leave at 0.001 because the arm screens on **CUDA only**: CPU-only
  contract metadata in `backend/cpu.py` (around :355 and the `WIRE_QUANT_STEP`
  multiplies, which follow the constant anyway), `format/self_sidecars.py` (around
  :60), `format/dataset.py` (around :488 and :632, manifest
  `wire_quantization_step_angstrom` defaults), help text in `cli.py` (around :653)
  and messages in `engine/query.py`. Metal is out of scope (its literal is in
  `src/roshambo3/backend/_metal_src/kernels.metal`).
- Then grep (`grep -rn -E "0\.001|1000\.0f" src/roshambo3`) and record, in
  `results/T283/REPORT.md`, every hit changed and every hit deliberately left, with
  the reason.

Rebuild the extension into a fresh venv in this worktree (per `DEV_GUIDE.md`):

```bash
cd <worktree>
python3 -m venv .venv && . .venv/bin/activate
pip install -e . --config-settings=cmake.define.ROSHAMBO3_ARCH_NATIVE=ON
python -c "import roshambo3; print(roshambo3.__file__)"   # must point into <worktree>/src/
python -c "import roshambo3.backend.cuda"                   # must import
```

`bench/worktree_python.sh` explains why a shared venv silently tests the wrong tree
(the shared venv it names no longer exists; the explanation still applies). Note the
CMake CUDA probe runs a binary, so export `CUDA_MPS_PIPE_DIRECTORY=<scratch>`
before building (CLAUDE.md).

Then build the arm `q2m8` and screen it by **extending** the sweep's harness
(`results/T281/quant-sweep/{build_one.py,build_arms.py,verify_grid.py,
run_screens.py,screen_dudez.py,screen_pubchem.py,analyze.py,bytes_sweep.py}`, copied
to `tickets/T283/` and committed there; leave the originals untouched). Extensions
needed, at least: a `q2m8` entry in `build_arms.py`'s `ARMS`; a build path that does
**not** put `quantpatch/` on `PYTHONPATH` (this arm's quantization comes from the
patched source tree, not the sitecustomize patch); a `STEP` parameter in
`verify_grid.py` (it hard-codes `STEP = 0.001`); the new arm name wherever
`run_screens.py`, `analyze.py` and `bytes_sweep.py` enumerate arms. Read each script
for other hard-coded arm names or steps. Judge under the **pre-registered rule** in
`results/T281/quant-sweep/PROTOCOL.md` section 6, **rule by rule as written there**:
R1 against `ctrl` (`accept(primary_X, base_primary=primary_ctrl)`); R2 against `q001`
(`paired_bootstrap(base=q001, cand=X)`); R3 as its text states (recall paired against
`ctrl`, RBO computed against `q001`). Apply section 6's non-discriminating-criterion
rule for any criterion the control fails. Panels exactly as PROTOCOL section 4: the same 12
DUD-Z targets (fixed in PROTOCOL; read the list there), the PubChem 150K subset and
its 64 library-drawn queries. Write a short `results/T283/PROTOCOL_ADDENDUM.md` before
the first measured screen: arm definition, what differs from the sweep (device
constants and storage units), and that the reading rule is unchanged.

Baselines: the sweep's `q001` and `ctrl` screens under
`<corpora>/` (sha256 sums in
`results/T281/quant-sweep/screens/`). A 2^-8 binary cannot read 0.001 corpora (the
wire-step check refuses them), so baselines come from those stored screens, made with
the stock build; record both build identities. If the stored screens are gone,
rebuild `q001` and `ctrl` with the stock build from main using the sweep's scripts.
DUD-Z sources: `source_sha256.txt` lists the archives; the decompressed SDF under
`_t281_quant/src/` is regenerable from them.

Corpora for the new arm go under
`<corpora>/` (pitfall 22). Verify the grid
with `verify_grid.py` adapted to units of 2^-8: every stored value is an integer, the
manifest's `coord_scale` is 0.00390625, and `vaa` / `color_self` equal a recompute
from the stored coordinates.

Also record the rotated-query question explicitly: the shipped `ScreenConfig()` uses
rotating starts, so R1-R3 at 2^-8 include the coarser rotated-query staging.
"Measurably hurts" is defined by the pre-registered rule and nothing else: **if any of
R1, R2 or R3 fails for `q2m8`**, run one more arm (`q2m8split`) whose library
dequantization is 2^-8 but whose query staging keeps a separate 0.001 constant (a
split macro: e.g. `ROSHAMBO3_STAGE_Q_QUERY` / `ROSHAMBO3_STAGE_INV_Q_QUERY`, used only
by `r3_quantize` and wherever staged query shorts are dequantized -- find every such
site), and judge it the same way. If the split is adopted, D034 must **name** the new
constants, their values, the `numerics.DEVICE_CONSTANTS` entries, and list which
kernel sites use the library pair and which use the query pair, so T296 can
implement it without re-deriving anything.

**Attribution-ladder artifacts.** The `q001` screens (rung 1: format 2 at 0.001 A,
stock build) and the `q2m8` screens (rung 2: format 2 at 2^-8 with the device
constants changed; `q2m8split` instead if adopted) are the first two rungs of the
attribution ladder that T296, T298 and T300 reuse. Record their paths, sha256 sums,
build identities and the commit of each binary in `results/T283/ladder.json`, so
those tickets compare against them instead of re-running them.

### 3. Write D034

`decisions/D034-corpus-format-3.md`. Commit it with **Status: proposed**; it changes
to **accepted** (with the date) only when the author signs off on the text, in a separate
commit. It records, each with its measurement and source path, and with an explicit
mapping table from each D034 item to T281's numbered decisions 1-17 (every one of
1-17 must appear in the table at least once; decisions 6 (all three repos,
internal first), 7 (zstd level 19, superseded by bit packing) and 8 (Parquet for
the molecule table) are recorded as their own items after item 11):

1. Hard compatibility break; nothing old stays readable (T281 Why).
2. File set and descriptor (design points 1, 2); fingerprint replaces version steps;
   the corpus.json group table carries no file paths (group file names derive from
   the group index).
3. Derived color from a per-molecule feature table, perception at build only
   (design point 3; `results/T281/derive_h.py` evidence).
4. Molecule run table `(mol_id u64, n_conf u16, n_real u8)` per molecule; no stored
   per-conformer counts section -- counts are derived from the run table and the
   feature table, and the producer builds the device's per-conformer count word
   (design points 3, 4).
5. Corpus order `(bucket, n_real, mol_id, conf_idx)`; gid is a position; results key
   on `(mol_id, conf_idx)` (design point 5).
6. SMILES is the graph; structures store dropped; charge/protonation variants under
   one id refused (design point 6).
7. Bit packing, BP256-16 layout, no general-purpose compressor, AVX2 and NEON
   kernels plus a scalar reference (design point 7; `results/T281/bitpack/README.md`,
   `results/T281/producer/REPORT.md`).
8. Step 2^-8 A in units of the step, with this ticket's results (design point 8).
   Coordinate rounding stays `np.rint` (round half to even) as today; derived
   centroids are the integer mean of stored int16 rounded half away from zero.
9. Blocks molecule-aligned, at most ~4,096 rows; block table is the work list
   (design point 9; `results/T281/cpublock/REPORT.md`).
10. Hardening scope: hangs, resource exhaustion and code execution; not files
    altered only to give wrong answers; the web app is a local demonstration tool, not
    for untrusted networks; custom definitions by
    hash opt-in; signatures deferred; RDKit version recorded and warned on (design
    point 11; `results/T281/security/THREAT_MODEL.md`).
11. T270 items 1-3 gate the step change (T296); its Metal arms and items 4-5 gate
    the paper re-verification (T300).

Reopening conditions: state one per decision where one exists (e.g. step: a later
panel shows R1-R3 failing at 2^-8; bit packing: native decode costs throughput at 1-8
queries against format-2 LZ4 in T290).

Regenerate `decisions/INDEX.md` with `python3 scripts/decision_index.py`; it is
generated ("do not edit by hand").

## Deciding measurement

R1, R2 and R3 of `results/T281/quant-sweep/PROTOCOL.md` section 6 for arm `q2m8`
against `ctrl`, plus the round-trip result at 2^-8 (expected 0 mismatches of 65,536).

## Acceptance

- `results/T283/int16_roundtrip.json`: 0 mismatches at 2^-8 in every available arm;
  0.001 reproduces `results/T87/int16_roundtrip.json`.
- `results/T283/analysis.json` and `REPORT.md`: the arm's R1/R2/R3 verdicts with the
  same tables as the sweep REPORT, bytes per conformer in 2^-8 units (`bytes_sweep.py`
  method), build identity of both binaries, GPU-lock and clock record.
- If any of R1-R3 fails: the split-macro arm run and reported, and D034 states which
  configuration is adopted and why.
- `decisions/D034-corpus-format-3.md` (Status: proposed, with the 1-17 mapping table)
  and the regenerated `decisions/INDEX.md` committed; the status flips to accepted
  only in a later commit after the author's sign-off.
- `results/T283/ladder.json` records the rung-1 and rung-2 screens.
- The experimental constant changes exist only on this branch and are not merged;
  the merge to main carries D034, the round-trip script change and `results/T283/`.

## Traps

- **Do not reuse the sweep's patch.** It stores 0.001 units, which is exactly what
  this arm must not do. A 2^-8 grid left in 0.001 units is also not exactly
  representable (2^-8 is not a multiple of 0.001).
- **Two constants, not one.** `numerics.WIRE_QUANT_STEP` documents why the
  dequantization is `cscale * (INV_Q * (float)v)` -- two roundings -- and must not be
  folded into one constant (NUMERICS_POLICY section 4c: folding cost 17.7% of pairs
  their bits). At 2^-8 the first multiply is exact, but keep the structure.
- **`r3_quantize` and the library share the macro.** Changing it moves the rotated
  query's staging grid. That is part of what this arm measures, not a side effect to
  undo.
- **Pitfall 22:** corpora go under `$ROSHAMBO3_CORPORA`, never into the
  worktree.
- **The sweep's corpora and screens may have been cleaned up.** Check before relying
  on them; regenerate with the stock build if needed, and say so in the report.
- **No timing is quoted.** Accuracy only. Hold the GPU lock for every screen anyway
  (to rule out host contention).
- **Foreign MPS daemon:** `export CUDA_MPS_PIPE_DIRECTORY=<scratch>` before any
  CUDA context (CLAUDE.md).

## Working rules

See `tickets/CONVENTIONS.md`. Worktree `<worktree>` on
`ticket/T283-d034-format3-decisions` from main. GPU: take the GPU lock via `bench.gpu_lock.GpuLock`,
**before** any CUDA context and held for each screen (D011); clocks unlocked
is fine (accuracy only). Merge to **main** (additive), excluding the experimental
constant changes. Never use pytest `-q` (pitfall 26). Commit before long waits.
