---
id: T295
title: Format-3 CPU workers -- expensive-first block directory, native per-block decode and self-overlap binding
phase: 3
lane: host-io
status: closed
model: opus
depends_on: [T270, T285, T293, T296]
priority: high
branch: ticket/T295-format3-cpu-workers
worktree: <worktree>
artifacts: results/T295/
---

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
  - the Deciding measurement's top-K identity across block sizes on corpora
    built with T293's `--block-rows` (phase 1 may already show it on
    writer-built corpora at each `block_rows`);
  - the per-block-size worker throughput sanity check, on rebuilt PUR2 if T299
    has built it.
  Only then is the ticket done.

Byte-level details are in `doc/FORMAT.md`; decisions in
`decisions/D034-corpus-format-3.md` (accepted). Where they disagree with this
ticket, they win -- record the disagreement in your results README. If T293
lands an interface (block directory, run-table expansion, `build.json` fields)
that differs from what you built against, follow T293's and adapt.

The CPU path screens with independent workers that each claim one physical block,
decode it, convert it and score it (`src/roshambo3/engine/engine.py:~1543-1700`).
On tachi (`results/T281/cpublock/REPORT.md`) three things were measured:
- decode plus convert is 0.1-3% of worker time;
- the per-block **stored self-overlap binding** (`engine/cpu_self.py::WorkerSelfCache.block`,
  Python) costs about 4-7 us/row for shape and 20 / 28 us/row for combo at 8 / 28
  workers, and **serializes on the GIL at 56 workers** (12-58% of combo worker time
  at 4,096-512 rows);
- 16,384-row blocks lose 11-28% of wall to tail imbalance.

Format 3 (`tickets/T281-corpus-format-3.md`, design point 9) makes the block
self-sufficient: the block table is the work list (rows, byte range, hash,
molecule range), self-overlaps live in the same group file, and a corpus-wide block
directory lists blocks expensive-first. This ticket moves the CPU worker path onto
that, with one native GIL-released call per block doing decode, color derivation and
self-overlap binding (T285 provides the native pieces).

Integration branch: cut `ticket/T295-*` from `ticket/T281-format3-switch` (T282
creates it from main; if absent, `git branch ticket/T281-format3-switch main`),
merge back into it; never main.

## Scope

**Handed over by T293 (merged 2026-10-21; details in `results/T293/README.md`).**
* Re-cover five engine-side tests that T293 deleted with the format-2
  self-overlap sidecar tests (`tests/test_prepare_self_sidecars.py`, now 3 tests):
  verified stored values used without the verification flag; color recomputed
  for another matrix; rescore counts; a tampered section is refused; unverified
  `vaa` needs the acknowledgment.
* `bench/numerics_end_to_end.py`'s CPU shape cells (analytic for each of the 3
  transforms, field for identity) and its 3 export-fault tests are strict-xfail
  in `NEEDS_T295`: the CPU ordinary route over a format-3 corpus fails in
  `engine/r3g_source.py` ("format-3 GPU blocks require tile=True; CPU workers
  use descriptors"). Make them pass and remove the xfails; these are T270's
  required cpu/x86_64 numerics cells.
* `tests/codec_fixtures.py` now writes format 3 and its color layout passes
  `deep` (`COLOR_DEEP_VALID`).


1. **Descriptors from the block directory.** Replace
   `engine/source.py::_build_cpu_block_descriptors` (`:621-760`) -- which opens every
   reader, validates every block index, and memmaps the `mol_id` sidecar directly via
   `sidecar_paths(group.stem)["mol_id"]`, bypassing `Group` -- with descriptors built
   from the corpus-wide block directory in **expensive-first** order. The
   directory is **built in memory here**, from the group headers when the corpus
   is opened (there is no block-directory file); cost = rows x device width, as
   `doc/FORMAT.md` defines it (FORMAT.md owns the definition; do not invent
   another). Keep `gid_base` and
   `compact_row0` semantics (`CPUPhysicalBlockDescriptor`, `:415`). `engine.py:~1080-1102`
   re-checks descriptor `gid_base` against group offsets -- keep an equivalent check.
2. **Native per-block decode** replacing `decode_cpu_block` (`:762`) plus
   `ext.prepare_cpu_block_coords` (`engine.py:~1605`; C++ in
   `backend/_cpu_src/cpu_block_prepare.cpp:41`): one T285 call writes the CPU FP32
   layout `[rows][library_width][3]`, color pseudo-atoms derived after each row's
   `n_real` atoms, GIL released. `library_width` is the group's device width from
   the group table; blocks are never empty by spec, and the native call refuses
   an empty one as `prepare_cpu_block_coords` does today.
3. **Native self-overlap binding** replacing `WorkerSelfCache.block` (`cpu_self.py:218`)
   for the format-3 route: the group file's `vaa`/`color_self` sections, checked against
   their per-block hashes, are handed to the scorer without Python per-row work. The
   receipt machinery (`sidecar_receipt` `:124`, `_open_receipt` `:155`, `check_block`
   `:87`, `_color_sidecar` `:197`) collapses to one file and per-section digests.
   Route counters (`stored_vaa_verified_blocks`, `color_self_sidecar_blocks`,
   `library_color_self_binding_evaluations`) must keep reporting truthfully.
   **A hash mismatch on a `vaa` or `color_self` section refuses**: raise a typed
   error (e.g. `CorruptCorpusError`) naming the group and block; never fall back
   to a silent recompute. Use T285's separate per-call timings (decode, color
   derivation, binding) for the measurement below.
4. **Worker-local top-K** keeps receiving per-row `molecule_ids`
   (`ext.make_worker_local_topk_block_row_sink`, `engine.py:~1678`; validated in
   `backend/cpu.py:~1658-1673`): expand the run table per block.
5. Remove nothing legacy (T298 does).

## Deciding measurement

Top-K identity on `(mol_id, conf_idx)` across block sizes {1,024, 2,048, 4,096}
(corpora built by T293's `--block-rows`) and worker counts {1, 8, all physical
cores}, shape and combo modes, on a synthetic corpus and on rebuilt PUR2 (T299
part (a)) if available. Plus the binding cost per row at 8 and 28 workers, same method as
`results/T281/cpublock/` (`bench_cpublock.py`'s per-block timer), to show the GIL
serialization is gone. From the same block-size runs, report worker-path throughput
per block size as a sanity check (informational; not a gate). If 1,024 or 2,048
rows is faster than 4,096 by a margin that matters in practice, report it to
the author under D034 reopen condition 9; otherwise 4,096 stays.

## Acceptance

- `tests/test_cpu_worker_owned_scan.py` (including
  `test_worker_owned_scan_matches_dense_scores_and_topk` and
  `test_exact_rank_ties_use_source_gid_across_worker_shards`) and
  `tests/test_self_overlap_routes.py` pass on format-3 corpora.
- Top-K identical across the block-size x worker-count matrix above.
- Every block takes the verified stored route; a deliberately corrupted `vaa` or
  `color_self` value in a test corpus is **refused** with the typed error naming
  group and block, and the D033 checks (`src/roshambo3/scores.py`,
  `SELF_OVERLAP_MARGIN_POLICY`) still fire on an over-claimed self-overlap.
- Binding cost per row at 56 workers no longer grows as blocks shrink (the
  cpublock signature of GIL serialization); numbers in `results/T295/`, labeled
  advisory unless run on an idle host.

## Traps

- **Forged lowered self-overlaps are out of scope** (T281 design point 11): the
  hardening goal is no hang/no OOB, not detecting a corpus built to give wrong
  answers. The per-block hash catches corruption (and refuses); do not add a full
  recompute "for safety".
- **Self-overlaps must describe the scored coordinates** (D033,
  `decisions/D033-*`): they are computed on the 2^-8 grid by the builder. Do not
  recompute them from anything else.
- **Blocks are molecule-aligned now**; the worker-local molecule reduction no
  longer needs a cross-block carry, but keep the check that a molecule never spans
  two descriptors (refuse rather than assume).
- **CPU timing needs a quiet host.** The tachi run that motivated this ran on a
  busy host (+-15% noise). Record `uptime` and top consumers.
- The shared venv points at main from a worktree; build from this worktree and
  check `roshambo3.__file__`.

## Working rules

See `tickets/CONVENTIONS.md`. CPU-only work needs no GPU lock; if a test creates a
CUDA context, export `CUDA_MPS_PIPE_DIRECTORY` to a private directory first and take the GPU
lock as `CLAUDE.md` describes (`bench.gpu_lock.GpuLock`; a plain `flock $ROSHAMBO3_GPU_LOCK`
excludes nothing) for anything timed. Never a blind sleep. Branch from and
merge into `ticket/T281-format3-switch` .

## Amended by T284 (2026-10-18): block cost and the large single-molecule block

`doc/FORMAT.md` section 9.4 defines `cost = rows x L` and the expensive-first
order (descending cost, ties by group-table index then block index). Every block holds at most 4,096 rows (D034 item 9 as amended 2026-10-18: at most 4,096 conformers per molecule, so every block has at most 4,096 rows) (at most 12.6 MB in the
device layout); the worker's per-block buffers are still sized from the block
directory's maximum, and the
expensive-first order already puts such a block first, where its tail cannot
dominate. `L_field_width` comes from the group table of `corpus.json`
(section 8.6), not from the group header. `color_self` is optional (section
18.2): a corpus without it takes the recompute route, as today.


## Roci phase-2 topology and current source checkpoint (2026-10-21)

The author corrected local worker counts to 8/24/48 on Roci (24 physical cores,
48 logical CPUs). Historical 28/56 runs are retained as exploratory
oversubscription data; their row-cost signature alone is not a GIL regression
verdict. Source `3ba81f41` caches validated query self once, retains exact public
mutation fingerprints with batched byte-identical hashing, and uses a private
released-GIL library-validation/value-copy entry. T285 already fuses its native
decode/color/physical-value bind; scorer-handle preparation is the separate
compatibility seam. All 242 regressions, seven mandatory CPU cells and both
18-cell identity matrices pass. `results/T295/phase2/SOLVER_CHECKPOINT.md`
records remaining full-wrapper cost and limitations. Status remains open for
final-source public sanity, final independent review and combined canary/merge;
no zero-contention or default-change claim is made.


Final-source public sanity on `0d678071` / native `88a12fcf…` passes all
12 configurations (8/24 workers, three block targets, shape/combo), with 36
timed records and exact top-K. Rates remain explicitly diagnostic/refused for
1-warmup/3-repeat. Full combo wrapper consumes about 0.6% of worker spans at 8,
and 1.0–2.5% at 24; native-copy time is reported separately. The literal flat-row
full-wrapper proxy remains unsatisfied at 24, so no total-contention-removal
claim is made. Current recommendation is to accept the concrete native/query
fix with that limitation, rather than add an opaque protocol without evidence
of a material screening bottleneck. The orchestrator's final acceptance/canary/merge remain.


## Acceptance clarification and completion (2026-10-21)

Acceptance was scoped to end-to-end screening behavior (parity or improvement).
The flat per-row wrapper-cost criterion was not met and is not claimed.

The implemented scope is complete at b1c1576986e1bee255704beb7f197b101a74b892:
expensive-first descriptors, fused native decode/color/authenticated-value bind,
GIL-released native scorer preparation, query self preparation once, exact
batched fingerprints with unchanged public mutation guards, and bounded worker
storage. All required identity/score-bit matrices and CPU numerics/export cells
pass. Independent rebuilt-source reviews and execution receipts are under
results/T281/consumers-phase2/; implementation evidence is results/T295/phase2/.

Final-source PUR2 screening sanity places the combo wrapper at about 1% of worker
spans at default 4096 rows and up to 2.5% at 1024 with 24 physical workers. These
are diagnostic measurements, not a causal wall-time bound or a certified matched
format-2 CPU performance comparison. The short run's refused rate grades remain
visible. T294 separately passed its matched GPU end-to-end throughput gate.
Block-size occupancy/tail differences do not justify changing 4096.

The independently reviewed candidate passed its fresh T149 manual check at
source `e01a3c9a5006546a37448f2cb759000daa3499ac` and was integrated locally into
`ticket/T281-format3-switch` at evidence-only report commit
`bee150ddf8d0e1ba4f6a15e491ea6bb5efd004f7`. The report is
`results/T149/premerge/20261021-format3-cpu-workers-e01a3c9a.json`. No push was
performed; historical restored-counter T149 acceptance remains separate.
