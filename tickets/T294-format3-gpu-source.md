---
id: T294
title: Format-3 GPU source -- native block decode into the pinned pool, molecule runs expanded per launch
phase: 3
lane: host-io
status: closed
model: opus
depends_on: [T270, T293, T296]
priority: high
branch: ticket/T294-format3-gpu-source
worktree: <worktree>
artifacts: results/T294/
---

## Completion (2026-10-21)

Ticket-specific implementation, prepare-built deciding checks and all four
actual LIT-PCBA throughput cells are complete. Ratios are 2.186158 / 0.994154
(shape 1/8 queries) and 1.198562 / 1.008243 (combo 1/8 queries), each with five
interleaved deciding repeats at independently tuned prefetch depths.
`results/T294/phase2/README.md` records all acceptance checks, explicit author-approved
clock/cache/CPU timing exceptions, original-input repair provenance for a 2K-molecule smoke corpus and raw
receipt hashes. Independent native/harness and final performance reviews are complete. The
combined candidate passed the fresh T149 check at source `862ac334` and was
integrated locally at `a5ec1359`. The subsequent CPU-worker integration also
passed its own fresh T149 check at source `e01a3c9a` (report commit `bee150dd`).
See `results/T281/consumers-phase2/review-T294-performance-final.md` and the
reports under `results/T149/premerge/`. No push was performed.

## Context

**Gate and early start (the author, 2026-10-21).** T270, T285, T286, T287, T288,
T290, T291 and T296 are merged into the integration branch. **T293 (builder
emission) is not yet**: it is in progress in parallel, after T292. This ticket
may start now, in two phases:

* **Phase 1 (now).** Implement everything in Scope against format-3 corpora
  that already exist or can be written today:
  - the committed conformance corpus `tests/data/format3/` (shape and color);
  - corpora you write with T286's writer
    (`roshambo3.format.r3g.writer.write_corpus`), which produces valid format-3
    files to `doc/FORMAT.md` (block size via its `block_rows` argument).
  Put any new test fixtures in new files of your own. **Do not edit
  `tests/codec_fixtures.py`**: T293 rewrites it (its scope 11), and tests that
  build through it stay on format 2 until T293 lands.
* **Phase 2 (after T293 merges into the integration branch).** Merge the
  integration branch into your branch, port the tests that build through
  `codec_fixtures`, and run the measurements that need T293-built corpora:
  - the Deciding measurement on corpora built by T293 from the same inputs as
    the format-2 fixtures;
  - the Acceptance end-to-end throughput gate on LIT-PCBA, which builds
    `$ROSHAMBO3_CORPORA/format3/LIT-PCBA-color` with T293's builder.
  Only then is the ticket done.

Byte-level details are in `doc/FORMAT.md`; decisions in
`decisions/D034-corpus-format-3.md` (accepted). Where they disagree with this
ticket, they win -- record the disagreement in your results README. If T293
lands an interface (block directory, run-table expansion, `build.json` fields)
that differs from what you built against, follow T293's and adapt.

Format 3 (`tickets/T281-corpus-format-3.md`, design points 1, 4, 7 and 9)
replaces the `.rsb3` file plus nine sidecars with one file per group: bit-packed
heavy-atom coordinates in units of the 2^-8 A grid, a per-molecule run table
`(mol_id u64, n_conf u16, n_real u8)`, a per-molecule color feature table, and
fixed-width `vaa`, `color_self` sections. There is no stored counts section:
per-conformer counts are derived from the run table and feature table by T285's
decoder. The GPU producer today
(`src/roshambo3/engine/source.py::Rsb3Source`) decodes LZ4 blocks in Python, reads
per-conformer `mol_id`/`counts` sidecars, and transposes with
`engine/buffers.py::pack_into`. This ticket gives the GPU path a format-3 source
that hands the engine the **same `ConformerBlock` contract**
(`engine/source.py:30-131`), produced by T285's native decoder writing straight
into the pinned pool.

The producer matters at small panels: at one query it is a large share of the
wall (`results/T281/producer/REPORT.md` section 3: kernel 39%, H2D 23%, producer
wait 13%, launch path 15%). The common ultra-scale case is 1-8 queries, so this
source may not be slower than today's LZ4 path (T290 measures that gate).

This ticket works on the integration branch: cut `ticket/T294-*` from
`ticket/T281-format3-switch` (T282 creates it from main; if absent,
`git branch ticket/T281-format3-switch main`) and merge back into it, never into main (T281
cutover; no dual-format code lands on main).

## Scope

1. **`R3gSource`** (new, `src/roshambo3/engine/source.py` or a new module beside
   it) implementing the `Source` protocol (`engine/source.py:134`) and yielding
   `ConformerBlock`s with today's contract: int16 coordinates in the tiled layout
   `pack_into` produces (BTILE = 32, `tile_mode` interleaved by default), `counts`
   uint8 `[rows, n_features]`, `mol_id` int64 per row, `tail_molecule_open`,
   `gid_base`, `color_offset`, `buffer`. Field sources in format 3:
   * `color_offset` is always **-1** (merged layout: each conformer's color
     pseudo-atoms follow its own real atoms);
   * `buffer` is the pinned pool buffer, as today;
   * `gid_base` = cumulative `n_conf` of all earlier groups (group-table order)
     + the launch's first row within its group -- the same rule the CPU path
     (T295) uses for its descriptors;
   * `counts` and `mol_id` are produced by the native decoder from the run and
     feature tables.

   Read the existing `Rsb3Source` first:
   `_make_jobs` (`:554`, launch coalescing -- a run never crosses a group or tile
   misalignment), `_decode` (`:877-1017`), `_group_sidecars` (`:871`),
   `_check_groups` (`:251`), `conformers_per_launch` (`:357`), and the `Prefetcher`
   (`:143`), which is format-independent and should be reused.
2. **Decode** with T285's native entry point (bindings per
   `src/roshambo3/format/r3g/native.pyi`; bounds-checked, GIL released) into the
   pinned pool buffer, writing the GPU tiled layout directly -- no Python-side
   decode, no separate `pack_into` pass. Derived color pseudo-atoms are written by
   the same call (design point 3). The source validates nothing the validator
   (T286, `open` tier at least) has not already validated, but must pass buffer
   capacities so the native code can refuse on its own.
3. **Launches and molecule runs.** A launch is a run of consecutive **whole**
   blocks of one group, up to `conformers_per_launch`. The native writer tiles
   from the launch's first row, so tiles are launch-relative; only the final
   partial tile is padded with zero rows, exactly as `pack_into` pads today. The
   format-2 rule that a coalesced run must start on a tile boundary
   (`source.py:~943`) therefore no longer applies -- do not carry it over. Blocks
   are molecule-aligned and FORMAT.md forbids a molecule spanning blocks
   (design point 9), so `tail_molecule_open` is **always `False`** at every
   launch end; keep the field because the sink contract uses it. Expand the run table to the per-row int64 `mol_id` array
   the sinks need: `engine/sink.py::MoleculeTopK` (`:358`; `before_block` stages
   `mol_id` and `tail_open`; `before_block` at `sink.py:442`, the `tail_open`
   read at `:463`), the CUDA molecule top-K
   (`backend/_cuda_src/molecule_topk.cu`, carry check at `:310`, which throws if a
   carry is live and the next block's first `mol_id` differs), and Metal's
   `backend/metal.py::MetalTopK` (`:1126`), which **deduplicates by mol_id value
   across blocks and needs a per-row id**. Keep the expansion per launch; do not
   change the sinks in this ticket.
4. **Widths and color.** `L`, `L_field_width` and the device width come from the
   group table in the descriptor (design point 3 "two widths"), not from a file
   header read per block. `L_field_width` sets the query-field lattice and changes
   numerics -- carry it exactly.
5. **Web.** `web/storage.py::BoundedSource` (`:13-26`) subclasses `Rsb3Source` and
   overrides `_group_sidecars` and `_decode` (another class in the same file,
   `BoundedCatalog`, has its own `_group_sidecars` at `:~44` -- that one is T297's);
   give `BoundedSource` the equivalent on `R3gSource`.
6. **Engine wiring.** `api.screen` and the CLI choose the source; with the hard
   break there is only one. Remove nothing legacy here -- T298 deletes.

## Deciding measurement

`tests/test_engine.py::TestScreen::test_result_is_independent_of_how_blocks_were_produced`
(line ~422; find it by name) and the CUDA/CPU parity tests, run on format-3
corpora built by T293 from the same inputs as their format-2 fixtures. The number:
**top-K identity** (gid-free: compare on `(mol_id, conf_idx)` via
`metrics/ranking.py::canonical_ids`) across launch sizes and prefetch settings,
and CUDA vs CPU agreement at today's documented tolerance.

## Acceptance

- **End-to-end throughput gate** (deferred here from T290): under the GPU lock,
  format-3 end-to-end conformers/s at 1 and 8 queries, shape and combo modes,
  on LIT-PCBA is no more than 2% below format 2 (`stored/LIT-PCBA-color` on
  pre-switch main) at each one's best prefetch setting. The format-3 corpus is
  built by this ticket with T293's builder from
  the LIT-PCBA source files into
  `$ROSHAMBO3_CORPORA/format3/LIT-PCBA-color` -- the same path T302 uses, so
  T302 reuses it rather than rebuilding (about an hour on 16 workers); report
  the numbers as format 3 at the D034 step against format 2 at 0.001 A, medians of >= 5 interleaved repeats; record in `results/T294/`.
  This gate also stands in for T150 scope item 3 (the kernel-side cost of int16
  loads, never measured; see T150's 2026-10-17 amendment): it includes that cost
  but does not isolate it, and the README must say so.

- The block-production independence test passes on format 3, parametrized over at
  least three `conformers_per_launch` values and `workers x prefetch_depth` in
  {8x3, 8x8}.
- `tests/test_molecule_topk_cuda.py` passes, with a format-3 corpus whose
  molecules have 1 and >1 conformers.
- A synthetic corpus (built with `prepare()`, shape and color) screens identically
  through CUDA and CPU within the existing parity tolerance; Metal on a Mac if
  available, otherwise record "not run" in the results README.
- No Python-level per-block decode remains on the GPU path (`grep` for
  `decode_block`/`pack_into` calls in `R3gSource` returns nothing).
- Commands and outputs recorded in `results/T294/README.md`.

## Traps

- **gid is a position.** gids come from `gid_base + row` (see `topk_add_block` in
  `backend/_cuda_src/topk.cuh`), with
  `gid_base` from cumulative `n_conf` in group order. Format 3 defines corpus order
  as `(bucket, n_real, mol_id, conf_idx)` (design point 5), so gids differ from
  format 2 for the same molecules: never compare runs on gid; use
  `canonical_ids(mol_id, conf_idx)`.
- **MetalTopK needs a per-row mol_id** and merges by value, not by contiguous run.
  A run-table shortcut that works for CUDA silently breaks Metal.
- **`BoundedSource` overrides `_decode`.** Changing the base class without the web
  subclass breaks the demo with no test failure outside `tests/test_web.py`.
- **Tile alignment is launch-relative now.** Format 2 required coalesced runs to
  start on tile boundaries (`source.py:~943`) because rows were copied into a
  shared tile grid; format 3's writer tiles from each launch's first row, so a
  molecule-aligned block need not be tile-aligned. Padding rows appear only at
  the end of a launch; `gid = gid_base + out_t` stays correct because they are
  never scored as real rows (counts zero), as today.
- **The shared venv lies from a worktree** (`doc/BENCHMARKING.md`, "The shared venv
  lying to you from a worktree"): build and install from this worktree; check
  `roshambo3.__file__`.
- **Pitfall 22**: corpora are never copied into the worktree.

## Working rules

See `tickets/CONVENTIONS.md`. Correctness tests may run unlocked, but anything
that creates a CUDA context must first export
`CUDA_MPS_PIPE_DIRECTORY` to a private directory and check `pgrep -a nvidia-cuda-mps`
(an MPS daemon the process cannot use hangs context creation with no error). Any timed number takes
the GPU lock as `CLAUDE.md` describes (`bench.gpu_lock.GpuLock`; a plain
`flock $ROSHAMBO3_GPU_LOCK` excludes nothing) before creating a context. Branch
from `ticket/T281-format3-switch`; merge back into it, never into main.

## Amended by T284 (2026-10-18): single-molecule blocks can be large

**Superseded 2026-10-18 (D034 item 9 as amended 2026-10-18: at most 4,096 conformers per molecule, so every block has at most 4,096 rows):** the largest block decodes to
`4,096 x 512 x 6` = 12.6 MB in the device layout; the 65,535-row case below no
longer exists. Still size buffers from the block directory, not a constant.

`doc/FORMAT.md` section 6 rule 4: a block holding one molecule may have up to
65,535 rows (the u16 `n_conf`), so one block can decode to
`65,535 x 512 x 6` = 201 MB in the device layout (100.7 MB of heavy
coordinates). A launch is a run of whole blocks, so the pinned-pool buffer
sizing must take `max(rows over the corpus's blocks) x L x 6` from the block
directory, not assume 4,096 rows; `conformers_per_launch` smaller than a
block's rows means that block is its own launch. `L_field_width` is read
from the group table of `corpus.json` only (it is not in the group header).
