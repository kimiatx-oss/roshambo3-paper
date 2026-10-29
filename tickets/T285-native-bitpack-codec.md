---
id: T285
title: Native bit-packed coordinate codec -- bounds-checked C++ core, scalar/AVX2/NEON unpack, direct writers into the GPU and CPU layouts
phase: 3
lane: kernel
status: closed
model: opus
depends_on: [T284]
priority: high
branch: ticket/T285-native-bitpack-codec
worktree: <worktree>
artifacts: results/T285/
---

## Context

Corpus format 3 (`tickets/T281-corpus-format-3.md`, design points 7, 9 and 11)
stores each group's heavy-atom coordinates as int16 in units of the grid step
(2^-8 A, D034), **bit-packed** per (block, axis) with a frame-of-reference minimum
and a fixed bit width (0..16), in the vertical **BP256-16** SIMD layout: each axis
stream is cut into groups of 256 values held as 16 lanes x 16 positions in `w`
256-bit words. There is no general-purpose compressor. Color pseudo-atoms are
not stored; they are **derived at load** from a per-molecule feature table of
(type, heavy-atom indices) by integer mean.

A prototype exists and is measured (`results/T281/bitpack/README.md`,
`bp256.c`, `bitpack.c`, `bench.py`): single-thread decode to the padded layout
at 7.7-24 ns/conformer from the smallest molecules to ~65 heavy atoms, as fast
as today's LZ4 or faster; bucket-weighted 11.2 ns/conformer on D5 at the
0.005 A step. **The prototype is not shippable**: it was written to measure
speed and trusts every byte of its input (see Traps). The threat model
(`results/T281/security/THREAT_MODEL.md`) makes the native decoder the one
component that must be safe on hostile files *whether or not* the Python
validator (T286) ran.

This ticket builds the production codec once, in C++, used by **both** consumers:
the GPU producer (writes the tiled int16 layout `engine/buffers.py::pack_into`
produces today) and the CPU worker path (writes the FP32 layout
`backend/_cpu_src/cpu_block_prepare.cpp::prepare_cpu_block_coords` produces
today). One native, GIL-released call per block replaces the Python decode +
`pack_into` / `prepare_cpu_block_coords` pair (design point 9).

**Gate.** Approved by the author on 2026-10-17, together with T282-T290, to run
while T270 is still being built: this ticket is additive (new files, modules,
CI jobs or measurements; no change to main's numerics), so T270 does not gate
it. T291-T302 remain gated on T270. **Finalize after T284 lands `doc/FORMAT.md`**: every byte
layout, field order, limit and rounding rule below is defined there; where this
ticket and the spec disagree, the spec wins and this ticket is amended. This
ticket deliberately does not restate the byte layout.

## Scope

Additive: new code, nothing existing changes behavior. The engine is switched to
it later (T294 GPU source, T295 CPU workers).

### 0. First deliverable: the binding interface stub

Before any kernel work, commit a typed stub `src/roshambo3/format/r3g/native.pyi`
(and the matching C++ header) that fixes the Python-facing interface: function
names, argument order, dtypes and shapes, which arguments are run-table /
feature-table slices, return values (including the timing triple below), and the
error behavior (`ValueError` with a message naming the failed check). T286
(Python reader), T294 (GPU source) and T295 (CPU workers) code against this stub;
changing it later requires updating those tickets. Merge the stub to main as soon
as it is reviewed, ahead of the implementation.

**Inputs are the format-3 tables, not today's sidecars.** Format 3 stores no
per-conformer counts array: the per-molecule run table is
`(mol_id u64, n_conf u16, n_real u8)` and the per-molecule feature table holds
(type, heavy-atom indices) (`doc/FORMAT.md`; T281 design points 3 and 4). The
native writers take the block's **run-table slice and feature-table slice** (the
block's molecule range `[m0, m1)` from the block table) and derive per-row
`n_real`, per-type feature counts and the per-conformer count word the kernels
read themselves. **Output widths come from the group table**: `L_heavy` for the
decode of the stored payload, the device width (`max(n_real + n_color)` padded)
for the GPU and CPU writers. Blocks are never empty: a block with zero rows is
refused.

**Timing.** Every block call returns separate wall timings for (decode, color
derivation, self-overlap binding) so T295 can attribute per-block cost the way
`results/T281/cpublock/REPORT.md` did.

### 1. A pure C++ core with no Python dependency

New files under `src/roshambo3/backend/_cpu_src/` (names indicative):
`r3g_codec.hpp` (API), `r3g_codec.cpp` (dispatch, bounds, writers),
`r3g_unpack_scalar.cpp`, `r3g_unpack_avx2.cpp`, `r3g_unpack_neon.cpp`,
`r3g_encode.cpp`. The core must compile standalone (the libFuzzer harness in
T289 links it without pybind11 or Python).

**API shape, bounds-checked at every entry:**

- every buffer is passed with its length: compressed input `(ptr, in_len)`,
  output `(ptr, out_capacity)` in elements, run-table slice `(ptr, n_molecules)`,
  feature-table slice `(ptr, len)`;
- `rows`, `L_heavy`, the device width and `n_types` passed explicitly (from the
  group table) and checked against the spec's
  limits table (`doc/FORMAT.md`) before any arithmetic;
- every size computed with overflow checks (`__builtin_mul_overflow` /
  `__builtin_add_overflow`), never trusted from the file;
- returns an error code (enum: ok, truncated input, width out of range, count
  out of range, row exceeds width, feature index out of range, output too
  small, ...); never throws across the C boundary, never aborts, never writes
  outside `[out, out + out_capacity)` nor reads outside `[in, in + in_len)`.

**Width dispatch:** the bit width read from the file is validated (`<= 16`)
*before* it selects an unpack routine, and the selection is a `switch` with a
default error arm -- **never** an index into a function-pointer table with a
file byte.

### 2. Unpack kernels: scalar reference, AVX2, NEON

- **Scalar** is the reference: straightforward, obviously correct, and
  bit-identical to the Python reference decoder T284 ships
  (`format/r3g/reference.py`).
- **AVX2** (x86-64-v3, which is the whole extension's baseline:
  `CMakeLists.txt:516`) and **NEON** (armv8-a+simd, `CMakeLists.txt:509`)
  implement the BP256-16 unpack with compile-time constant shifts per width,
  as in `results/T281/bitpack/bp256.c::UNPACK256`.
- **Forced-ISA override for tests**: an internal function (or env var read once,
  e.g. `ROSHAMBO3_R3G_ISA=scalar|avx2|neon`) that forces a code path so CI can
  compare every path on one host. Default selection: AVX2 on x86 (baseline),
  NEON on aarch64.
- Integer-only arithmetic: every path must produce **bit-identical** output.

### 3. Derived color

From the per-molecule feature table (type, heavy-atom indices -- layout in
`doc/FORMAT.md`), compute each feature position per conformer as the integer
mean of the stored int16 heavy-atom coordinates, **rounded half away from
zero** (spec'd in `doc/FORMAT.md`; T281 design point 3). Every atom index is
checked `< n_real` of its molecule *inside the gather loop*. Single-atom
features copy the atom's coordinate exactly. Features are placed immediately
after each row's real atoms in type order (the merged layout the kernels read
with `library_color_offset < 0`).

### 4. Writers straight into the consumers' layouts

- **Untiled `pack_into(tile=False)` is out of scope**; the CUDA kernel refuses it
  (`backend/_cuda_src/interface.cpp`), and only the tiled layouts are written.
- **GPU:** the tiled int16 layout `engine/buffers.py::pack_into` writes today
  (`BTILE = 32`, `src/roshambo3/layout.py:30`): interleaved
  `[tile][atom][lane][component]` (`tile_mode=1`, default) and planar
  `[tile][atom][component][lane]` (`tile_mode=-1`); rows padded to a multiple
  of 32, padding lanes and slots zeroed. Target: the pinned pool buffer the
  producer passes in. Values written are the stored int16 in grid units (the
  device constant change is T296, not this ticket).
- **CPU:** FP32 `[rows][output_width][3]`, atom-major, zero-filled beyond each
  row's real atoms + features, exactly as
  `cpu_block_prepare.cpp::prepare_cpu_block_coords` (line 41) writes it today,
  with the step from the corpus header applied as the dequantization scale.
- **Self-overlap binding:** return (or copy into caller buffers) the block's
  slice of the stored `vaa` (f32) and `color_self` (f64) sections, checked
  against the block's row range and the section lengths in the header.

### 5. Encoder (for the builder, T293)

A native encoder producing the exact bytes the spec defines, from int16
`[rows, 3, L_heavy]` plus the block's run-table slice: per (block, axis) min and minimal width, ragged real
atoms only, BP256-16 groups with zero-filled tail. Must round-trip through every
decoder path and match `format/r3g/reference.py`'s encoder byte-for-byte.

### 6. Thin pybind11 layer

Added to the `_roshambo3_cpu` module (`pybind11_add_module` at
`CMakeLists.txt:594`) **after** `interface.cpp` in the source list
(`CMakeLists.txt:546`; `interface.cpp` first is load-bearing, T146). Releases
the GIL around the core call (pattern: `cpu_block_prepare.cpp`), converts error
codes to `ValueError` with a message naming the failing check. Accepts numpy
arrays / buffers; allocates nothing large itself on the GPU path (writes into the
caller's pinned buffer).

### Suggested split (two agents)

- **A:** core API + bounds + scalar/AVX2/NEON unpack + forced-ISA override +
  encoder.
- **B:** GPU and CPU writers, derived color, self-overlap binding, pybind layer.

A lands its API header first so B builds against it.

## Deciding measurement

1. **Bit identity:** for every block of the T284 conformance corpus
   (`tests/data/format3/`), decoded output equals the reference decoder's for
   scalar, AVX2 (on x86) and NEON (on aarch64 / Apple), forced in turn; sha256
   of the decoded arrays matches the digests committed with the corpus.
2. **Speed:** single-thread decode-to-padded-layout ns/conformer on the
   prototype's sample (`results/T281/bitpack/bench.py` data selection: 8 blocks
   per bucket, D5 buckets 0-9, buckets 8-12 of an internal large-molecule
   corpus, re-rounded to the 2^-8 grid) is within 10% of the prototype's AVX2
   numbers in `results/T281/bitpack/README.md`'s bucket-weighted table, **with
   bounds checks on**: the `bp256` column of the rows "D5, 0.005 A: 107 B /
   11.2 ns" and the internal large-molecule tail row at 0.005 A (19.6 ns),
   i.e. <= 12.3 ns/conformer (D5-weighted) and <= 21.6 ns/conformer (internal
   large-molecule tail), single thread, decode to the padded layout.

## Acceptance

- Exhaustive per-width tests: **every width 0..16** (T289 fuzzes the same
  range), group tails of 1..255 values, `n_real` 1..255 (0 only where the spec
  allows it), `L` at each `L_ALIGN` multiple (`L_ALIGN = 8`, `format/rsb3.py:188`,
  unchanged by format 3) including the edge case `n_real = 255 -> L = 256`;
  random rows; every path round-trips the encoder exactly.
- A zero-row block is refused.
- Every refusal path has a test: truncated input (each byte length short of
  valid), width 17..255, count > L, rows > declared, feature index >= n_real,
  output capacity one element short, overflowing size products. Each returns its
  error code; none crashes.
- C++ test fixtures follow the existing pattern (`tests/*.cpp` compiled by a
  pytest wrapper with `g++`, e.g. `tests/test_shape_field_evaluator.py`:
  `-march=x86-64-v3` on x86, `armv8-a+simd` objects on aarch64) and run in the
  existing CI jobs (`.github/workflows/ci.yml`: `cpu` ubuntu x86, `cpu-macos`
  macos-15 arm64).
- ASan + UBSan clean locally on the full test set (`-fsanitize=address,undefined`
  build of the fixtures); record the command in `results/T285/`.
- `pytest -k "not cuda"` green on x86 and the Mac; the Python bindings decode the
  conformance corpus identically to `format/r3g/reference.py`.
- `scripts/lint_conventions.py --strict` clean (no ticket names in identifiers;
  American English).
- Results and the bench harness committed under `results/T285/`.

## Traps

- **The prototype's bugs are the bugs to not ship** (`results/T281/bitpack/`):
  - `bp256.c` / `bitpack.c` select the unpack routine by indexing a 17-entry
    function table with the width byte read from the file, unchecked: a width
    of 17..255 calls through arbitrary memory.
  - `row_copy` over-reads its source (it loads 8 int16 at a time past the end
    of the ragged stream and relies on unspecified slack).
  - A row with `n_real > L` overflows the output row.
  - No input-length check anywhere; a truncated block reads past the buffer.
  Use the prototype for speed reference and layout understanding only.
- **Validation in Python does not make the native code safe.** T286 validates
  before native code sees bytes, but this decoder must be safe on its own
  (THREAT_MODEL.md: defense in depth; T289 fuzzes it directly, with no
  validator in front).
- **Do not change device constants or `numerics.WIRE_QUANT_STEP` here.** The GPU
  writer emits int16 in grid units; the step change and its declared numerics
  are T296.
- **ISA build flags.** x86 is `-march=x86-64-v3` for the whole extension (AVX2
  is baseline; `CMakeLists.txt:516`), with per-file flags only for
  `grain_avx512.cpp` (`:622`). aarch64 is `armv8-a+simd` with per-file `+fp16`
  only for the fp16 field files (`:628-631`). Put the AVX2 unpack in an
  x86-only source and the NEON unpack in an aarch64-only source (see the
  ARM-only / x86-only source lists around `CMakeLists.txt:570-581`); do not
  add a new global flag. Keep `interface.cpp` first in the source list
  (T146; `tests/test_cpu_isa_definitions_are_not_shared.py` checks this).
- **The CPU writer must match `prepare_cpu_block_coords` exactly**, including
  zero-fill and where color sits; T295 swaps one for the other and expects
  identical top-K.
- **Pitfall numbers**: see `tickets/CONVENTIONS.md`; the GPU lock is not needed
  for this correctness work except the speed measurement, which is advisory
  unless taken under the lock on an idle host.

## Working rules

See `tickets/CONVENTIONS.md` and `tickets/TEMPLATE.md`. Branch
`ticket/T285-native-bitpack-codec` from main, worktree
`<worktree>` (two agents: sub-branches merged into it).
Additive: merges to **main** when acceptance passes. The shared venv's editable
install points at main from a worktree (doc/BENCHMARKING.md); build a venv for
this worktree and check `roshambo3.__file__` before trusting a test result.

## Amended by T284 (2026-10-17): what `doc/FORMAT.md` settled

The spec is authoritative; these are the points this ticket's text deferred to it.

* **Byte layout** (FORMAT.md section 5): every block starts with a **32-byte
  header** -- `min_x, min_y, min_z` (int16 at offsets 0, 2, 4), `w_x, w_y, w_z`
  (u8 at 6, 7, 8), then 23 reserved bytes that MUST be zero and MUST be checked
  -- followed by the three axis streams of `G * w_a * 32` bytes each
  (`G = ceil(total / 256)`). So `in_len` MUST equal
  `32 + 32 * G * (w_x + w_y + w_z)` exactly, with `total` summed from the
  run-table slice, never read from the file (section 17 item 3). Streams are
  therefore 32-byte aligned within the `coords` section.
* **Decoded value** (section 5.6): the int16 written is `min_a + u` reduced
  modulo 2^16 (a 16-bit SIMD add). This is a MUST for every path, scalar
  included -- never saturate, never error on a tampered block -- so all paths
  are bit-identical with the Python reference (`reference.decode_block`),
  which wraps the same way; `tests/data/format3/widths/wrap.bin` is the
  oracle for it, and `widths/w01..w07, w14..w16.bin` are per-width oracle
  blocks for the SIMD paths (the corpora cover widths 0 and 8-13).
* **Tables**: block records are 64 bytes (section 6; `offset` is relative to
  the `coords` section's data start, `sha256` raw); run records are 16 bytes
  (section 7: `mol_id u64, n_conf u16, n_real u8`, 5 zero bytes); the feature
  table is four CSR arrays `feature_offsets u32[n_mol+1]`, `feature_types
  u8[n_feat]`, `feature_atom_offsets u32[n_feat+1]`, `feature_atoms
  u8[n_feat_atoms]` (section 8.1), features sorted by `(type, atom tuple)`
  within a molecule (so the merged layout is the table order).
* **Derived color**: the integer mean is `sign(s) * ((2|s| + k) // (2k))`
  (section 8.3); counts per section 8.5. `color_self` is **absent** when the
  interaction matrices are not canonical (section 18.2): the self-overlap
  binding takes an absent section, it does not fail on one.
* **Widths**: per-block widths are the encoding of major version 3
  (Appendix B.19); nothing in this ticket implements a per-conformer variant.
* **Oracle functions** this ticket must match byte for byte:
  `reference.encode_block(int16[rows, 3, L], n_real) -> bytes`,
  `reference.decode_block(bytes, n_real, L) -> int16[rows, 3, L]`,
  `reference.derive_positions`, `reference.kernel_layout`,
  `reference.derived_counts`; the conformance digests are
  `tests/data/format3/EXPECTED.json` (`heavy`, `merged`, `pseudo`, `counts`
  per group; `tests/data/format3/README.md` says how each is formed).
* **Error codes**: the native enum is this ticket's, but SHOULD map
  one-to-one onto the spec's refusal names where they overlap
  (`limit.bit_width`, `limit.block_length`, `limit.atoms_per_feature`,
  `layout.features`, `layout.block_header`, `decode.overflow`; section 16.5)
  so T289's oracle can compare the Python and native refusals.
* **Decoder contract additions after review** (FORMAT.md section 17 items 5
  and 7): check `out_capacity >= rows * 3 * L` before any write; `n_conf >= 1`
  and `n_real >= 1` per molecule; the `feature_offsets` and
  `feature_atom_offsets` slices against the lengths of the arrays they index
  (and monotone) **before** either is used as an index, stating in
  `native.pyi` whether the binding rebases offsets to the slice; per-type and
  total counts `<= 255` before the u8 count vector or count word is built.
  `color_self` is optional (section 18.2): the binding returns "absent" rather
  than failing. `L_field_width` comes from the group table, not the header.
