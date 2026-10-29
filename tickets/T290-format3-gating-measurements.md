---
id: T290
title: Format-3 gating measurements -- native decode at small panels, derived vs stored color, widths, CPU block size, range reads
phase: 3
lane: host-io
status: closed
model: gpt-6.1-sol-high
depends_on: [T284, T285]
priority: high
branch: ticket/T290-format3-gates
worktree: <worktree>
artifacts: results/T290/
---

## Context

**Gate.** None outstanding. The dependencies (T284 spec, T285 native codec)
are closed, as are T286 and T303, whose code this ticket also uses. The ticket
is additive (harnesses and measurements; no change to main's numerics), so
T270 never gated it.

**Sources of truth.** `decisions/D034-corpus-format-3.md` (accepted
2026-10-18) and `doc/FORMAT.md` (normative; as T303 left it on main at
8869694d). Where this ticket and either of them disagree, they win; report
the disagreement to the author rather than editing them.

Format 3 chose its coordinate encoding, color representation and block rules
on **advisory** measurements taken under host contention
(`results/T281/producer/REPORT.md`, `results/T281/cpublock/REPORT.md`,
`results/T281/bitpack/README.md`; T285's `results/T285/bench.json`). D034
names this ticket as the gate that confirms them on **decision-grade**
numbers:

- **D034 item 7 / reopen condition 7 (bit packing).** The GPU is the
  expensive resource and the common ultra-scale case is 1-8 queries, so decode
  may not cost throughput at small panels. zstd-19 cost ~15% at one query and
  was rejected; bit packing was chosen because its prototype decodes as fast
  as LZ4. Confirm it in a real producer (item 1).
- **D034 item 4 gate / reopen condition 4 (derived color).** Deriving
  pseudo-atoms moves a gather + integer mean into the producer, the stage that
  is the wall at small panels. If deriving costs more than 3% of the producer
  ceiling at 1-8 queries, D034 says pseudo-atom coordinates are stored instead
  and the feature table is kept for self-description only. A fail **reopens
  D034 item 4** and changes the byte layout (a FORMAT.md change decided by
  the author) -- it is not a T292 implementation choice. T292 (builder feature
  table) is blocked on this result (item 2).
- **Per-block vs per-conformer widths** are decided for major version 3:
  per-(block, axis) widths are the encoding (FORMAT.md section 5.7, Appendix
  B.19); a per-conformer scheme would be a new major version. Item 3 measures
  it as evidence only (T281 estimated 105 vs 107 B/conformer on D5).
- **D034 item 9 / reopen condition 9 (block rows).** The tachi study kept
  4,096 rows because per-block Python self-overlap binding dominated small
  blocks. The per-block path is now native: T285's `native.write_cpu_block`
  and `native.write_gpu_block` take `self_overlaps=`, `vaa_out=` and
  `color_self_out=`. Re-measure 1,024 / 2,048 / 4,096 rows (item 5). Every
  block holds at most 4,096 rows (FORMAT.md section 6 rule 4; a molecule has
  at most 4,096 conformers).
- `L_ALIGN` stays 8 (`format/rsb3.py:188`; FORMAT.md section 2). 8 vs 16 is
  **not measured** here (it needs builder padding changes); record it in the
  report as not measured.

All modules named below are under `src/roshambo3/format/r3g/` and imported as
`roshambo3.format.r3g.<module>`.

**Corpora (roci; export `ROSHAMBO3_CORPORA=<corpora>`
-- the default in `src/roshambo3/paths.py` does not exist on roci).**
- Shape baseline: a format-2 LZ4, no byte-shuffle copy of an internal tuning
  corpus under `$ROSHAMBO3_CORPORA`, made by
  `results/T281/producer/make_codec_copies.py`; exists.
- Color baseline: `$ROSHAMBO3_CORPORA/stored/LIT-PCBA-color` (format 2, LZ4,
  merged color, 20,381,286 conformers).
- Format-3 inputs: re-encode those two corpora with a harness committed under
  `tickets/T290/`, written beside them under `$ROSHAMBO3_CORPORA/_t290/`,
  never into a worktree (pitfall 22). The harness decodes each format-2 block,
  requantizes to the D034 step (`v_new = np.rint(v_old * 0.001 * 256)`, int16),
  groups rows into molecules by `(mol_id, conf_idx)`, and writes the corpus
  with `writer.write_corpus(root, molecules, color=..., prep_version=...,
  prep_commit=None, block_rows=...)`, which sorts into corpus order, encodes
  with the native codec and writes `molecules.parquet` itself. `writer.Molecule`
  needs `vaa`: reuse the format-2 `vaa` values (they describe 0.001-step
  coordinates; acceptable for timing, say so). SMILES may be placeholders for
  a timing corpus (say so); `verify --tier deep` would then refuse it, so run
  `roshambo3 verify <corpus> --tier scan` (T286) on every re-encode before
  timing it. The 0.001 -> 2^-8 requantization double-rounds; that too is
  acceptable for timing, not for numerics. Top-K is therefore not comparable
  between format 2 and format 3 here.

**Baseline code.** The format-2 baseline runs on **main** (main before the T298
switch is format 2), from a separate worktree of main with its own venv. No
`format2-last` tag is needed.

## Scope

All GPU measurements hold the GPU lock through `bench.gpu_lock.GpuLock`
(export `ROSHAMBO3_GPU_LOCK=<lock base>`: it is a
**base** for per-device lock files, CONVENTIONS "environment"; a literal
`flock $ROSHAMBO3_GPU_LOCK` locks a different file and excludes nothing), on an otherwise idle
host, recorded through `bench/run_record.py::build_run_record`. Unlocked clocks
are acceptable for ratio comparisons in one session on one card
(`decisions/D023-measurement-regimes.md`), but record clocks/power for every
run and never combine numbers taken at different clocks. Interleave arms and
repeat (>= 3) so drift shows.

**What this ticket can and cannot run.** No format-3 engine source exists yet
(that is T294, which needs the builder and T296's device constants), so items
1 and 2 are **producer-side measurements**. The candidate producer is a
harness (in `tickets/T290/`) that reads the re-encoded group files with
bounded `pread`s (`native.read_into`; FORMAT.md section 1 item 4) and calls
`native.write_gpu_block` into pinned buffers sized with
`native.gpu_layout_elements(rows, L)`, timed with the null consumer of
`results/T281/producer/producer_scan.py` (T47's `concurrency_scan`). The GPU
side is unchanged by the format, so the pass test compares the format-3
producer ceiling with the **GPU consumption rate** measured end to end on
format 2 at the same panel size (`results/T281/producer/e2e_scan.py`, run on
main). The end-to-end format-3 confirmation is T294's acceptance.

1. **Native decode in the GPU producer, 1 and 8 queries.** Baseline: format-2
   LZ4 (the internal tuning corpus's LZ4 copy) through today's Python
   `Rsb3Source._decode` + `pack_into` path (`engine/source.py:877`), run from
   the main worktree: its producer ceiling (null consumer) and its end-to-end
   conformers/s at 1 and 8 queries. Candidate: the harness producer on the
   format-3 re-encode, producer ceiling only. Shape on the internal tuning corpus, color on LIT-PCBA.
   Sweep the prefetcher (`DEFAULT_PREFETCH_DEPTH = 3`, `engine/source.py:285`;
   shipped 8 x 3; the producer study needed 8 x 8 for zstd). **Pass:** at 1
   and 8 queries, the format-3 producer ceiling at its best prefetch setting
   is no more than 2% below the format-2 producer ceiling at its best setting
   (medians of >= 5 interleaved repeats), and is >= 1.2x the format-2
   end-to-end conformers/s at that panel size (so the producer stays ahead of
   the GPU with margin). A fail is D034 reopen condition 7: report to the author.
2. **Derived vs stored color.** The same harness producer on LIT-PCBA, two
   arms. *Derived:* `native.write_gpu_block` with the per-molecule feature
   table (the shipped format-3 path, FORMAT.md sections 8.3-8.4). *Stored:*
   the same blocks with the format-2 pseudo-atom coordinates stored and
   decoded instead of derived. Format 3 defines no stored-color layout; the
   harness chooses the stored arm's construction and the report describes it.
   It must use the same native BP256-16 decoder and yield the same device
   layout per row as the derived arm, so the only difference is gather + mean
   against decoding more values. Build the feature table by the method of
   `results/T281/derive_h.py`: perceive BaseFeatures on each molecule's stored
   graph (`stored/LIT-PCBA-color/structures.sqlite`) with hydrogens re-added
   (`Chem.AddHs`, D034 item 3), each feature's heavy-atom indices in today's
   slot order (no canonical-SMILES reorder is needed for timing); the writer
   sorts them (FORMAT.md section 8.1 rule 4). **Pass (the D034 item 4 gate):**
   derived color costs no more than 3% of the producer ceiling at the 1- and
   8-query prefetch settings (medians of >= 5 interleaved repeats), and the
   derived arm still meets item 1's margin. State the go/no-go in
   `results/T290/REPORT.md` and to T292 explicitly; a no-go reopens D034 item
   4 -- stop and report to the author.
3. **Per-block vs per-conformer widths (evidence only).** Bytes/conformer and
   decode ns/conformer for both, on the D5 and large-tail samples of
   `results/T281/bitpack/bench.py`. The result cannot change major version 3's
   layout. **Reopen before release:** no corpus has shipped, so a new major
   version is still cheap. If the per-conformer scheme saves more than 5% of
   coordinate bytes on D5 or the large-molecule tail at no decode cost at 1-8
   queries, raise it with the author before the first distributed corpus is built
   (T302); after that the question closes until a later major version.
4. *(removed: `L_ALIGN` 8 vs 16 is not measured; see Context.)*
5. **CPU block size.** Worker-path throughput at 1,024 / 2,048 / 4,096 rows,
   shape and combo, at full socket and at 8 workers, through the native
   per-block path (`native.write_cpu_block` with `self_overlaps=`). Re-encode
   the same molecules at each size with `write_corpus(..., block_rows=N)`,
   which applies FORMAT.md section 6 rule 5 (append while `rows + n_conf <=
   block_rows`; a molecule larger than `block_rows` gets a block of its own,
   still at most 4,096 rows). Schedule in section 9.4's order (`cost = rows x
   L`, descending, ties by group then block index). Reuse
   `results/T281/cpublock/bench_cpublock.py`; T295 re-measures inside the real
   workers. On tachi (see `doc/BENCHMARKING.md`) or another host,
   **confirmed idle before starting**. Record `uptime` and
   `top -bn1 | head -20` before every run; any arm run while a foreign process
   used more than one core is marked contaminated and rerun. 1,024 or 2,048
   rows measuring faster is D034 reopen condition 9; report it.
6. **Optional: one object-storage range-read screen** on a cloud host (10 GbE):
   read group files by byte range from object storage and screen at 1 and 32
   queries; report conformers/s against the link rate. Informational only and
   **excluded from acceptance**. It needs the author to name the host, bucket and
   credentials; skip it (and say so in the report) if they are not provided.

## Deciding measurement

The pass/fail of items 1 and 2 (native decode does not lose to format-2 LZ4 at
1 and 8 queries; derived color within 3%), taken under the GPU lock on an idle
host, with the decisions (go/no-go for derived color; the block-row result;
the width evidence) recorded in `results/T290/REPORT.md`.

## Acceptance

- Every run record carries lock status, clocks, host load and the exact
  corpus/commit; nothing quoted from an unlocked or contended run.
- Arms that should agree give identical output digests: across block sizes and
  prefetch settings always (same corpus, same numerics). For producer-only
  arms this is a digest of the decoded device buffers; for end-to-end arms the
  top-K digest. Format 2 vs format 3 are **not** compared here (different step
  after requantization).
- `results/T290/REPORT.md` states each decision; T292's ticket (open) gets a
  one-line pointer to it. Do not edit closed tickets or D034; any D034 reopen
  condition that fires (4, 7 or 9) is reported to the author by number.
- Harnesses committed under `tickets/T290/` before they run.

## Traps

- **Pitfall: profilers seize the clock** (CONVENTIONS): check
  `ps aux | grep -E "[n]cu|[n]sys"` before every run.
- **Take the GPU lock before creating a CUDA context** (D011) -- the pinned
  buffers' `cudaHostAlloc` creates one. Export
  `CUDA_MPS_PIPE_DIRECTORY=<private directory>` (on roci, per CLAUDE.md) and check for
  a foreign MPS daemon (`pgrep -a nvidia-cuda-mps`).
- **There is no shared venv.** Build one per worktree (this one and the main
  worktree for the format-2 baseline) as `doc/BENCHMARKING.md` "The venv"
  shows, and check that `roshambo3.__file__` points into that worktree; an
  editable install redirects every import to the checkout it was built from.
- **Warm vs cold page cache**: measure warm primarily; cold read was not the
  bottleneck in `results/T281/producer/REPORT.md` but report it if cheap. Do not
  try to drop caches.
- **The 1-query wall has serial components** (launch path ~15%, H2D ~23% in the
  producer study, inferred from stage sums): a producer win may not move the
  wall; report producer ceiling and end to end separately.
- **Do not change the format to win a benchmark.** A failing gate is reported
  to the author for a D034 decision.

## Working rules

See `tickets/CONVENTIONS.md` (GPU arbitration protocol, clock rules, long-job
waiting).
* **Branches.** Cut `ticket/T290-format3-gates` from `main`, worktree
  `<worktree>`; harnesses and results merge back to `main`
  (no-ff). Measurement only.
* **Format-2 baseline** from a second worktree of `main` with its own venv.


## Measurement outcome (2026-10-18)

Report (`results/T290/REPORT.md`): native decode passes D034 item 7; derived color is NO-GO (about 40% ceiling cost), reopening D034 item 4 and blocking T292 pending the author's layout decision. All 217 GPU attempts and 15 decision-grade width samples are preserved; widths do not meet the >5%/no-cost raise condition. CPU item 9 remains unresolved: the retained eight-pair/per-pair shape tail changes two top-100 score/pose rows across block sizes. The original CPU attempt is refused, not a block-size verdict; exact diagnostic arrays are retained. A separately qualified numerical fix or authorized protocol is required before fresh CPU deciding timing. No production math or D034 text was changed.

*Resolved downstream (note added for this excerpt):* T304 qualified scheduling invariance, and T295's block-size × worker-count top-K identity matrices pass (T295, phase 2).

## Wave acceptance — 2026-10-20

Accepted for merge by the author after review of T290 whole-system measurements,
T304 scheduling-invariance qualification, T296 FIELD/ANALYTIC recall and
enrichment, and the matched .001 / 2^-10 / 2^-8 diagnostic matrix. See
`results/wave1/ACCEPTANCE.md` for the scoped decision and remaining limitations.
This supersedes the historical blocked-acceptance wording without relabeling
failed tests as passes. T305 remains open/deferred; T306 owns the proposed
recall-focused test-suite improvements. No CPU block-size winner is claimed.
