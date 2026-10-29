---
id: T293
title: Format-3 builder emission -- molecule-aligned blocks, group files, corpus.json, molecules.parquet, build.json
phase: 3
lane: data
status: closed
model: opus
depends_on: [T270, T284, T285, T286, T292]
priority: high
branch: ticket/T293-builder-format3-emission
worktree: <worktree>
artifacts: results/T293/
---

## Context

T291 fixed the builder's order and identity, and T292 its feature table. This
ticket makes the builder write format 3, as `doc/FORMAT.md` (T284) defines it
and T281 designs it (design points 1, 2, 4 and 9):
* one self-contained file per group (extension `.r3g`), holding:
  * bit-packed coordinates;
  * the molecule run table `(mol_id u64, n_conf u16, n_real u8)`;
  * the feature table;
  * the `vaa` and `color_self` sections;
  * a JSON header at the end with the section table, block table and corpus
    fingerprint;
* `corpus.json`, the descriptor;
* `molecules.parquet`;
* `build.json` for provenance.

There is **no stored counts section**: per-conformer counts are derived from the
run table (`n_real`) and the feature table (per-type counts per molecule), as
FORMAT.md defines. There is **no block-directory file** either: the corpus-wide
block directory CPU schedulers use is built in memory from the group headers
when a corpus is opened (T295).

Every format-2 artifact goes: `.rsb3`, the nine per-group sidecars, `ids.i64`,
`structures.sqlite`, and `manifest.json` as it is today.

This ticket absorbs T274 (the vaa `verified` flag written for the prepared frame):
format 3 has one stored frame, so the flag becomes structural (T281 design points
1 and 8).

**Gate.** This ticket is blocked until the author (a) approves the T282-T302 ticket
set and (b) certifies T270 done. It also depends on T292, on T285 (the native
encoder; bindings per `src/roshambo3/format/r3g/native.pyi`), on T286 (the
Python writer and validator) and on T284 (`doc/FORMAT.md`). Every byte-level rule
is `doc/FORMAT.md`'s, not this ticket's.

## Scope

1. **Molecule-aligned blocks.** `prep/build.py::_GroupRowBinder` cuts blocks
   every `block_conf` rows (`BLOCK_CONF = 4096`, `format/rsb3.py`). As a result
   molecules straddle blocks today; `tests/conftest.py` notes 114 do in one
   fixture.

   Cut at the last molecule boundary at or before the block-row cap (default
   4,096). A molecule larger than the cap gets a single-molecule block up to
   FORMAT.md's hard 4,096-row limit (a named constant in the spec and in
   `format/r3g/`; tests import it, never restate it). Above that limit it is
   refused at `_why_reject` time, with the limit named.

   Expose the cap as `BuildOptions.block_rows` and CLI `prepare --block-rows N`
   (default 4,096, for testing and measurement; T295 builds corpora at 1,024,
   2,048 and 4,096 with it). The cap is recorded in `build.json`, not in
   `corpus.json`, since it does not change scores.

   The block size stays ~4,096 rows: `results/T281/cpublock/REPORT.md` found no
   L2 effect, losses below 2,048 rows from Python per-block work, and tail
   imbalance at 16,384. Each block-table entry carries:
   * first row and row count;
   * byte range;
   * a hash;
   * the molecule range `[m0, m1)` (T281 design point 9).
2. **Write the group file** through T286's writer and T285's native encoder.
   Sections, as FORMAT.md lists them: coordinates (BP256-16 in D034 step units),
   block table, molecule run table `(mol_id u64, n_conf u16, n_real u8)`,
   feature table, `vaa` f32, `color_self` f64. File name `<group index>.r3g` (or
   FORMAT.md's naming rule).
   The JSON header holds the section table, block table and corpus semantic
   fingerprint, so a group file separated from its directory still names what
   it is. That is T115's deciding measurement, which T281 absorbs.
3. **`corpus.json`.** Format major version, step and frame, the `color` section
   from T292 via T287's schema, the prep conventions, and the group table:
   bucket, `L`, `L_field_width`, `n_conf`, `n_mol`, header hash. The group table
   has **no file paths**; file names are derived from group indices. Compute the
   fingerprint with T287's canonical function.
4. **`molecules.parquet`.** Columns: `mol_id`, `ext_id`, `smiles` (T291's
   slot-ordered, `RemoveAllHs` SMILES), `hac`, `mw`, `rotor_count`.
   `_merge_meta` writes `meta.parquet` today, with the same duplicate-id refusal
   through SQLite; keep that refusal.
5. **`build.json`.** Everything informational: source paths, timings, host,
   worker counts, rejected counts and examples, and the T291 resume identity.
   It may hold private paths. It is never fingerprinted, never read by a screen,
   and T301 redacts it for distribution. Today these live mixed into
   `manifest.json` (`_manifest`: `source`, `timing`, `scratch`, `rejected`,
   `build`).
6. **No block-directory file.** The corpus-wide block directory (group, block,
   rows, device width, cost = rows x device width as FORMAT.md defines it) is
   derived from the group headers at open time by T295; the builder only has to
   write complete block tables. Do not add a file for it.
7. **Delete the format-2 emission:**
   * `write_sidecars`, `write_counts`, `write_color_counts` and the block-index
     writers, as called from `_gather`'s `_close`;
   * `ids.i64`;
   * the topology store: the `build_store` and `finalize_store` calls in
     `prepare`, `_ShardSet`'s `topology_*.sqlite`, and `--no-structures`;
   * the codec and shuffle `BuildOptions` and CLI flags (`cli.py` prepare:
     `--codec`, `--shuffle`, `--vaa-frame`).

   Keep `--no-color-self` (T292 keeps the canonical-matrix rule for
   `color_self`).
8. **Checkpoint and resume.** `_BuildCheckpoint` commits slots and groups. Adapt
   it to the new files and to T291's identity. A resumed build must produce
   byte-identical output.
9. **`roshambo3 verify`** is owned by T286 (`--tier open|scan|deep`, `--all`); this
   ticket only uses it. Use T286's validator tiers,
   and make `verify --tier deep` the acceptance check for every built corpus.

10. **Keep the sampling and id-gate options** the current `prepare` has, because
    T299 and T302 rebuild the D tiers with them: `--sample-seed`,
    `--sample-p-lo`, `--sample-p-hi`, `--hac-window`, `--source-rows`,
    `--max-records`, `--expect-ids-sha256`, `--expect-ids-from` (see `cli.py`'s
    prepare parser). Their semantics are unchanged.

    **The id gate is preserved by definition.** Today the builder writes
    `ids.i64` from the same `ORDER BY mol_id` cursor that fills `meta.parquet`
    (`prep/build.py:1382-1398`, after SQLite's duplicate-id refusal) and hashes it
    as little-endian int64 (`sha256_ids`, `prep/build.py:1403-1408`). The format-3
    id list is defined the same way: the sorted, unique `mol_id` column of
    `molecules.parquet`, serialized as little-endian int64. Its sha256 is therefore
    directly comparable to a format-2 manifest's `sha256_ids` (equivalently, to the
    sha256 of its `ids.i64`). This assumes every `mol_id` is non-negative and below
    2^63 (format 3 stores it as u64; `stable_id` already returns non-negative int64);
    **this ticket adds a build-time refusal of any `mol_id` outside [0, 2^63)**,
    naming the id -- nothing checks it today.
    * `--expect-ids-sha256 H`: compare H with that hash at build end.
    * `--expect-ids-from DIR` accepts a format-3 corpus directory (read its
      `molecules.parquet`) **or** a format-2 directory, from which it reads only
      `ids.i64` (a raw sorted little-endian int64 file; no format-2 reader is
      needed) and `manifest.json`'s `sha256_ids`. The per-unit membership check
      (`prep/build.py` around :2413-2528) is kept.
    * The hash is computed at build end and recorded in `corpus.json` as
      `ids_sha256` (decided 2026-10-17: it describes distributed content, so it
      belongs in the distributed descriptor, not in `build.json`; it is **not** an
      input to the semantic fingerprint -- `doc/FORMAT.md` defines the field).
      `verify --tier deep` recomputes it from `molecules.parquet`. Update
      `roshambo3 info` (`cli.py:50`) and `verify` (`cli.py:270-273`), which read
      `sha256_ids` from the manifest today.
11. **Rewrite `tests/codec_fixtures.py` for format 3** (decided 2026-10-17; the
    matrix row in `results/T282/test_migration_matrix.md` lists the four
    decisions it needs, answered by `doc/FORMAT.md`). It lands on the
    integration branch with this ticket because T294 and T295 both depend on
    T293 and their tests build through it. It writes through T286's writer, not
    through the builder. The test files that only follow it are ported by
    their own owners (T294, T295) as the matrix says.
12. **Print the definition hash** (T287's `definition_hash`) at the end of a color
    build, so it can be handed to colleagues (T288 item 7).

## Deciding measurement

Determinism and validity at real size.
* Build PUR2 (48,660 conformers; T208 built it from the DUDE-Z
  SDF) twice from the same
  input, with different worker counts and one interrupted-and-resumed build. All
  outputs must be byte-identical.
* `roshambo3 verify --tier deep` must report clean on each.

## Acceptance

* A synthetic corpus (pytest, `tmp_path`) and PUR2 both pass
  `roshambo3 verify --tier deep`.
* Every block in both corpora is molecule-aligned. A test covers a molecule of
  exactly 4,096 conformers: it fills one block on its own, and a molecule of
  4,097 is refused (D034 item 9 as amended 2026-10-18: at most 4,096 conformers per molecule, so every block has at most 4,096 rows). Building it at all needs T291's conformer-cap
  lift (256 -> 4,096; T291 scope 7); this is its end-to-end test.
* The id gate: a test builds a synthetic corpus with `--expect-ids-from` pointing
  at (a) a format-3 corpus and (b) a format-2-shaped directory holding only
  `ids.i64` and a `manifest.json` with `sha256_ids` (written by the test, or an
  old manifest), and with `--expect-ids-sha256`; a match passes, a missing or
  extra id refuses before publication, and a `mol_id` outside [0, 2^63) is
  refused (`tests/test_prepare_id_reference.py` ports to this; see
  `results/T282/test_migration_matrix.md`).
* `corpus.json`'s fingerprint is identical for both PUR2 builds, and identical
  when computed in a second process and on tachi. CONVENTIONS covers access to
  that host.
* No format-2 file is written: `ls` of the output shows only `corpus.json`,
  `molecules.parquet`, `build.json` and the `.r3g` group files.
  A search of `corpus.json` for `fdef_path` or any absolute path finds nothing; private paths live
  only in `build.json`.
* A test builds the same synthetic input with `block_rows` 1,024 and 4,096 and
  confirms identical decoded rows and identical `corpus.json` fingerprints
  (block size must not change scores or the fingerprint).
* `pytest tests/test_prepare*.py` (no `-q`; pitfall 26) is green on the integration branch, with
  format-2-specific assertions migrated per T282's test-migration matrix.
* Sizes are recorded in `results/T293/` against T281's predictions. Bit-packing
  at 0.005 Å measured ~107 B/conformer on D5's distribution
  (`results/T281/bitpack/README.md`); 2^-8 adds roughly 3%.

## Traps

* **Pitfall 22.** Real builds write under `$ROSHAMBO3_CORPORA`, out of place,
  never into a worktree.
* **Single source of order.** Block cutting must follow the same row order T291
  established. Re-sorting anywhere downstream breaks gids.
* **Fingerprint canonicalization.** Sorted keys, explicit encoding, matrices
  hashed as pinned-dtype bytes. A fingerprint computed over an unsorted dict or
  a float repr differs across processes. Use T287's function only; never
  reimplement it.
* **`build.json` must stay out of the fingerprint and the screen path.** It
  holds private paths and timings that differ build to build; including it
  breaks byte-identity and leaks paths into distributed corpora.
* **The native encoder is new code.** Validate every group file written with
  T286's `scan` tier (tiers are `open`/`scan`/`deep`; CLI
  `roshambo3 verify [--tier] [--all]`) before declaring the build finished, as
  `_check_block_table`/`_check_written_rows` re-decode format-2 files today.

## Working rules

See `tickets/CONVENTIONS.md`.
* **Branches.** Branch `ticket/T293-builder-format3-emission` from
  `ticket/T281-format3-switch` (T282 creates it from main; if absent,
  `git branch ticket/T281-format3-switch main`), and merge back into it. Worktree
  `<worktree>`.
* **Venv.** Run this worktree's code (rebuild the native extension); verify
  `roshambo3.__file__`.
* **GPU.** No GPU is needed.

## Amended by T284 (2026-10-18): what `doc/FORMAT.md` settled for the emitter

* **Write rules are normative for writers** (sections 6 rule 5 and 9.3): a
  molecule is appended to the current block if the block is empty or
  `rows + n_conf <= block_rows` (`1 <= block_rows <= 4096`), else a new block
  starts; likewise for groups with `max_conf_per_group`. Both parameters are
  recorded in `build.json` (never in `corpus.json`); two builds with the same
  inputs and parameters produce identical group files.
* **Column name `rotors`**, not `rotor_count` (section 11; D034 item 11). The
  Parquet writer is fully specified: `uint64, string, string, uint8, float64,
  uint16`, all columns REQUIRED (non-null), ZSTD-compressed (D034 item 11; level 9, chosen by the author in T303), `PLAIN` (no
  dictionary pages), no statistics, no embedded Arrow schema, row groups of
  2^16 rows; the footer's `created_by` is the only byte that may differ
  between pyarrow releases. The SMILES is non-isomeric (section 11.1).
* `corpus.json` carries `molecules_sha256` (section 10.7) beside `ids_sha256`
  (10.6); neither is fingerprinted. `format.step_log2 = -8` (T296).
* **`--no-color-self` is legal**: `color_self` is optional (section 18.2);
  when written, the matrices must be canonical by the spec's exact definition
  (T292 amendment).
* **The four `codec_fixtures` answers** (scope 11): smallest block one row,
  `block_rows` may be as small as 1; an empty group is invalid; a molecule
  always ends at a block edge; `codec=`, `shuffle=` and a split color layout
  are refused, not mapped.
* **`verify --tier deep` cost** (section 16.4): `deep` decodes every block
  with the native decoder (T285) and cross-checks a sample with the
  reference; until T285 lands it decodes everything with the pure-Python
  reference, which is fine for this ticket's test fixtures and not for a
  D-tier corpus. Budget the acceptance runs accordingly.
