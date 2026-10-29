---
id: T291
title: Format-3 builder order and identity -- content-defined corpus order, slot-ordered atoms, variant refusal, quantization at the D034 step
phase: 3
lane: data
status: closed
model: opus
depends_on: [T270, T283, T284, T296]
priority: high
branch: ticket/T291-builder-content-order
worktree: <worktree>
artifacts: results/T291/
---

## Context

Corpus format 3 is a hard compatibility break before release
(`decisions/D034-corpus-format-3.md`, accepted 2026-10-18; byte-level spec
`doc/FORMAT.md`, as T303 left it on main at 8869694d; design discussion
`tickets/T281-corpus-format-3.md`). Where this ticket and D034 or FORMAT.md
disagree, they win; report the disagreement to the author rather than editing
them. Four of its decisions are properties of *how the builder orders and
identifies* what it writes, independent of the new byte layout:

* **D034 item 12 / FORMAT.md section 9.2:** corpus order is a function of
  content, `(bucket, n_real, mol_id, conf_idx)`, and the global conformer id
  (gid) is the position in that order.
* **D034 item 6 / FORMAT.md section 11.1:** heavy atoms are stored in the
  output order of the canonical, **non-isomeric** SMILES of the hydrogen-free
  molecule, so slot *i* is atom *i* of `Chem.MolFromSmiles(smiles)`. Charge
  and protonation variants under one source id are refused; stereo-only
  variants are accepted.
* **D034 item 8:** coordinates are quantized once, at build, at 2^-8 A, and
  stored as int16 in units of the step.
* **D034 item 5:** at most 4,096 conformers per molecule (`n_conf` is u16 in
  the run table, FORMAT.md section 7).
* Plus T275's content and code digests in the resume identity (T275 is closed
  as absorbed here).

This ticket changes the builder's ordering and identity logic in the format-2
builder (`src/roshambo3/prep/`). It does not change the byte format; T293
emits format 3. It lives on the integration branch
`ticket/T281-format3-switch`, because content order silently renumbers gids
on any format-2 build. It must never land on main alone.

**Gate.** Start when the author hands this ticket over **and T296 has merged into
`ticket/T281-format3-switch`** (check that `format/rsb3.py::COORD_SCALE` and
`numerics.WIRE_QUANT_STEP` read 2^-8 on the branch head; on main at 8869694d
they are still 0.001). The other dependencies are closed: T270 (closed
2026-10-18 for practical CPU/CUDA delivery; its Apple/Metal follow-up gates
only T300), T283 and T284.

## Scope

All paths are under `src/roshambo3/` unless stated. Line numbers are from main
at 8869694d and drift; find each symbol by name. Read
`results/T281/inventory.md` (the format-2 inventory) first.

1. **Content order within a bucket.** Today the order is ascending `n_real`,
   then scatter slot (shard filename `n{nnn}_s{slot:05d}`), then the order the
   source emitted molecules (`prep/build.py` module docstring, `_shard_index`
   :669, `_shard_chunks` :714, `_plan_bucket` :756). The new order is
   `(n_real, mol_id, conf_idx)`.
   * **Sort each scatter unit's shards when the unit closes.** A "slot" is one
     scatter work unit (`_scatter_unit` :611 / `_scatter_binary_batch` :637
     open one `_ShardSet` (:228) per unit and call `close()` (:371) at its
     end), so each shard holds at most `records_per_unit` molecules (default 20,000;
     `batch_records` on the binary path) and is read back whole. Shards are
     appended at each flush (`_files` reopens them in append mode and closes
     them, :345-354) and split across files per `n_real` (:356-360): `.xyz` (int16
     planar), `.met` (`SHARD_META_DTYPE`, `format/rsb3.py:204`), `.ccnt`
     (per-type counts) and `.cxyz` (ragged color coordinates); the last two
     exist only for color builds. In
     `_ShardSet.close`, after flushing and before the files are made durable
     for `_BuildCheckpoint.commit_slot` (:1881), read each `n_real` shard
     back, compute one stable permutation by `(mol_id, conf_idx)`, apply it to
     all four files (for `.cxyz`, gather each row's ragged run using offsets
     from the prefix sums of `.ccnt`), and rewrite them. **Keep writing
     `.cxyz`**: T290's derived-color gate may keep stored color, and T292
     decides whether to stop writing it.
   * **Merge across slots.** `_shard_chunks` becomes a k-way heap merge across
     a bucket's shards for each `n_real`, keyed on `(mol_id, conf_idx)`. It is
     the single generator that both `_plan_bucket` (call at :797) and the
     gather writer in `_gather` (call at :1238) walk: keep it the single source
     of order, or the plan and the write disagree (its docstring explains why).
     **New yield contract.** Today it yields `(n_real, shard, off, cnt, met,
     counts_chunk)`, one contiguous range of one shard, and the writer reads
     `.xyz` by `(shard, off, cnt)`. After the merge a chunk interleaves
     shards, so yield each chunk as an ordered list of `(shard, off, cnt)`
     segments (plus the chunk's `met` and `counts_chunk` in merged order),
     and have the writer gather the segments. A k-way merge consumes each
     shard in ascending offset order, so the writer's per-shard running
     `.cxyz` offset (`color_offsets[shard]`, `_gather` :1257-1262) stays
     valid as long as segments are read in yield order and none is skipped;
     rewrite its comment ("Chunks are consecutive within one shard") to say
     so. Resume's `skip_rows` counts rows of the merged order, exactly as the
     plan does.
   * **No straddling.** A molecule never straddles a chunk boundary (today's
     rule in `_shard_chunks`) and never spans groups. Keep both;
     `check_molecule_grouping` (:180) keeps its role.
   * **`conf_idx` width.** `SHARD_META_DTYPE` (`format/rsb3.py:204-206`) stores
     `conf_idx` as `u1`; it is the merge key and must hold 0..4,095 after
     item 7. Widen it to `u2` here (shards are intermediate files; any
     resumable checkpoint from before the change must be refused by item 6's
     code digest). Leave `rsb3`'s format-2 sidecar dtype (`conf_idx` `u1`,
     :200) alone.
   * **Group boundaries are T293's.** Keep today's group-closing rule here;
     FORMAT.md section 9.3's write rule (close a group before a molecule that
     would overflow it) and section 6 rule 5's block rule are implemented by
     T293's emitter.
   * **Duplicate check.** Add an explicit duplicate `(mol_id, conf_idx)` check
     at merge time, naming the id. A merge joins duplicates from two slots into
     one run, which `check_molecule_grouping` cannot see. (`_merge_meta`,
     :1328, already rejects a duplicate *molecule* id through SQLite; the new
     check is per conformer.)
2. **`conf_idx` semantics (decided).** `conf_idx` keeps today's meaning: the
   0-based index among the molecule's **accepted** conformers, in source order
   (`_ShardSet.add` uses `enumerate(rec.conformers)`, so a dropped conformer
   renumbers the rest; `prep/sources.py::_check_conformer_ids` requires input
   ids `0..n-1` for the binary and SQLite sources). This matches FORMAT.md
   section 7 rule 1, where `conf_idx` is a row's offset within its molecule's
   run (no per-conformer index is stored): the builder writes exactly the
   accepted conformers, in `conf_idx` order. Record dropped conformers where failures already go (the per-slot
   `rejects_NNNNN.json`, `_BuildCheckpoint`, and the build summary), with a
   count per molecule id.
3. **Canonical-SMILES atom order.** Add one helper in `prep/sources.py` (for
   example `canonical_heavy(mol) -> (heavy, smiles, order)`) and call it
   everywhere a heavy-atom molecule is made from a source record: in
   `_prep_one` after `strip_hydrogens` (`prep/conformer.py`, which calls
   `Chem.RemoveAllHs`), **and** in `_group_by_name`'s multi-conformer plan
   branch (`prep/sources.py:880-905`), which calls `strip_hydrogens(mol)`
   and `_prep_raw` directly without going through `_prep_one` (it serves
   merged SDF molecules and multi-conformer binary/SQLite records). The
   helper:
   * compute `Chem.MolToSmiles(heavy, isomericSmiles=False)` (FORMAT.md
     section 11.1, Appendix B.24: the SMILES carries no stereochemistry) and
     read `heavy.GetProp("_smilesAtomOutputOrder")` **from that same call**;
   * permute the heavy-atom coordinates into that order before `_prep_raw`, so
     slot *i* is the *i*-th atom written in the SMILES;
   * produce the stored SMILES from the **same stripped molecule** and the same
     call.

   Today `_descriptors` (`prep/sources.py:75`), called once per molecule name
   in `_group_by_name` (:862), builds the SMILES column with
   `Chem.MolToSmiles(Chem.RemoveHs(mol))` (:84); `RemoveHs` keeps isotopic
   hydrogens (deuterium), so its atom count can disagree with `n_real`.
   Replace it with the helper's SMILES, so `meta` carries the same string the
   coordinates were ordered by (records of one id share one graph after item
   4, so the first record's SMILES is every record's). **Validate at build**
   (D034 item 6, FORMAT.md section 11.1): the elements of
   `Chem.MolFromSmiles(smiles)` equal the slot elements, atom by atom;
   refuse the molecule (`BuildRefused`, naming the id) if not. Stereo-only conformer variants
   share one record under one id (item 4), and display stereo comes from the
   3D coordinates (`web/chemistry.py:24`,
   `AssignStereochemistryFrom3D`). Color feature atom ids must go through the
   same permutation; that remap is T292's, after which T292 sorts each
   molecule's features by `(type, atom tuple)` (FORMAT.md section 8.1 rule 4).
   **Expose the permutation** so T292 can consume it: per conformer record
   (atom-order-only variants of one id have different source orders), the
   array `order` with `order[slot] = source heavy-atom index`, carried
   beside the prepared coordinates in the record `_group_by_name` yields
   (`MoleculeRecord`, `prep/sources.py:62`, or its conformer tuples;
   document which).

   **Numerics note.** Permuting before `_prep_raw` changes the summation
   order of the centroid and covariance (`prep/conformer.py:101-104`), so a
   prepared coordinate can move by an ulp and flip a `rint` tie or an axis
   sign. D034 does not list this among its declared changes; record it in
   `results/T291/README.md` for T298's attribution (alongside 4f/4g) and
   tell the author. Do not avoid it by permuting after `_prep_raw`: the frame
   would then depend on the source's atom order, not on content.
4. **Variant refusal.** Today the only graph comparison is in
   `prep/sources.py::_merge_records` (:679), which runs only from
   `SdfSource._iter_merged` (merged SDF with a color generator,
   :319-321). It compares
   `_graph_key(m)` (full; :621) and `_graph_key(m, stereo=False)`. Today
   records that differ in more than stereo return `(None, None)`, and the
   caller falls back to per-record prep under the same name.

   Format 3 refuses at build any molecule id whose records differ in more
   than stereo or atom order. Compare the records' **hydrogen-free,
   canonically ordered** graphs (item 3's `heavy`) with
   `_graph_key(heavy, stereo=False)`: any difference in element, atom count,
   formal charge, isotope, H count or bonds refuses; an atom-order-only
   difference (same canonical graph, e.g. the `reordered` / `order`
   fixtures) is accepted, as is a stereo-only one. (A deuterated and a
   protium record compare equal: `RemoveAllHs` removes both.) Refuse with a
   `BuildRefused` (`prep/sources.py:49`) that names the id and tells the user
   to give each state its own id. Stereo-only differences are accepted and
   ignored. Do the check where all paths meet: in `_group_by_name` (:802), across the
   records of one name (the per-record path serves shape-only SDF builds, the
   over-`MAX_MERGED_CONFORMERS` stream at :347-352, every merge fallback at
   :381-384, and `RDKitSource`, :436-441), and keep `_merge_records`
   consistent with it. Binary and SQLite sources hand one Mol per record, so
   a repeated id there already fails `_merge_meta`'s duplicate-id check; no
   new path is needed for them. It is a refusal, not a silent rejection.

   Two test fixtures put a charge variant under one id and must be rewritten
   here:
   * `tests/test_prepare_topology.py::fixtures()` (:41-49; `CCCN` and
     `CCC[NH3+]` both named `charge`), imported by five other files
     (`test_prepare_progress`, `test_prepare_manifest_stats`,
     `test_prepare_reconcile_durable`, `test_prepare_resume`,
     `test_topology_build_store`). Move `fixtures` / `write_source` (:52) to a
     helper module (e.g. `tests/prep_fixtures.py`) and update the importers;
     T298 deletes `test_prepare_topology.py`.
   * `tests/test_sdf_merge_conformers.py`'s `proto` fixture (:142-144) and its
     per-record-fallback assertions (in `test_merge_is_taken_and_guard_falls_back` :184, the call-count assert
     at :204; in `test_guard_each_difference_refuses` :207, the edits dict
     with `"charge"` at :228, and the `(None, None)` asserts at :236 and
     :239; the "atom order" case now merges), which now expect the refusal.

   Other tests in the Acceptance globs that break and must be updated here:
   * `test_prepare_topology.py::test_chemistry_rejection_does_not_shift_graph_mapping`
     (:148, `CCN` / `CC[NH3+]` / `NCC` under one name "same");
   * `test_sdf_merge_conformers.py::test_merged_path_identical_on_fixture`
     (:165-181, asserts "proto" with 4 conformers);
   * `tests/test_sdf_merge_stereo_guard.py` (imports the merge-test helpers;
     its strict-mode `(None, None)` asserts at :176-204);
   * tests that compare stored coordinates in source atom order, which
     canonical order breaks: `test_prepare.py:145-155, 164-168`,
     `test_sqlite_source.py:246, 458`, `test_prepare_topology.py:120-131`.
     Compare through the exposed `order` instead.

   See `results/T282/test_migration_matrix.md`, rows for these files. (Its
   `test_sdf_merge_conformers` row still says "cap at 65,535"; the cap is
   4,096, item 7.)
5. **Quantize at the D034 step: verify.** `format/rsb3.py::quantize(coords_f,
   scale=COORD_SCALE)` (`np.rint`, round half to even) is called by the
   builder at `prep/build.py:294` (heavy atoms, `_ShardSet.add`), :309 (color
   coordinates) and in the two dry-run samplers (:2051, :2121), always with
   the default `scale`; the stored self-volume uses
   `q.astype(np.float32) * fmt.COORD_SCALE` (:299-301, and :2052, :2122).
   After T296, `COORD_SCALE` is 2^-8, so int16 is stored in units of the step
   and `vaa` is computed from exactly the coordinates a reader recovers
   (T208's stored-frame contract; D033). This item is a check: confirm on the
   branch that no builder site passes or multiplies by a literal step
   (`grep -n "0\.001\|1000" src/roshambo3/prep/`; today all hits are comments
   or unrelated -- `conformer.py:7, 137`, `build.py:81, 297, 1295`,
   `sqlite_source.py:369` `fetchmany(1000)` -- and T296 rewrites the step
   comments), and add the grid test in Acceptance. The constants themselves are T296's.
6. **Resume identity (absorbs T275).** `prep/build.py::_build_identity`
   (:1720) identifies inputs by path, size and `mtime_ns` (:1733), and code by
   `__version__` (:1748). Add a content digest per scatter work unit (the unit `_scatter_unit` /
   `_scatter_binary_batch` reads; computed as the unit is read and stored
   with its committed slot, so resume never re-hashes the whole input), cheap
   enough not to cost what resume saves (see
   `tickets/T275-resume-identity-has-no-content-or-code-digest.md` for the
   options and their costs; its line references are stale), and a code digest of what produces the stored bytes: `prep/`,
   `format/` and the native self-overlap producers (T275 scope 1). A build
   from a dirty tree must not record a clean code digest (T275 trap). The
   SQLite source keeps its own `(size, mtime_ns)` check
   (`prep/sqlite_source.py::_check_unchanged`, :256) and additionally gets
   the unit digest; `RDKitSource` (in-memory) has no input file, so its
   unit digest is over the pickled molecules. Resume must refuse when either
   digest changes, naming which.
7. **Lift the conformer cap to 4,096** (D034 items 5 and 9: at most 4,096
   conformers per molecule, so every block holds at most 4,096 rows).
   `prep/build.py:95` `MAX_CONFORMERS_PER_MOLECULE = 256` and
   `prep/sources.py:46` `MAX_MERGED_CONFORMERS = 256` (mirrored, not imported;
   see its comment at :41-45) both become 4,096. Rewrite the `_why_reject`
   n_conf check (`prep/build.py:113-115`), whose message names "the uint8
   conf_idx sidecar", to name the run table's limit (FORMAT.md section 7,
   `1 <= n_conf <= 4096`). Update the tests that pin 256:
   `tests/test_sdf_merge_conformers.py:318-320`
   (`test_more_records_than_the_bound_stream_per_record` writes
   `MAX_MERGED_CONFORMERS + 3` SDF records; at 4,096 monkeypatch the bound
   rather than write 4,099 records) and `:421-423`
   (`test_merge_bound_mirrors_the_layout_limit`, which stays);
   `tests/test_prepare_topology.py:157-172`
   (`test_layout_rejection_and_binary_prefix` expects a 257-conformer molecule
   rejected; that premise dies; keep the `max_records` prefix half, :166-170).
   `tests/test_format.py:184-187` refuses `conf_idx` 256 in `write_sidecars`;
   that is the uint8 *sidecar* writer, not the cap, and stays until T293/T298
   delete it. Do not change it here.
8. **Variant census dry run.** Before any large rebuild, run the refusal logic
   with a census script committed under `tickets/T291/` (output in
   `results/T291/`). `prepare(..., dry_run=True)` only samples, so it cannot
   count refusals over a whole input. The script runs item 4's comparison
   over every record of:
   * the LIT-PCBA SDF shards on roci under `<corpora>/`
     (`shard_NNNNN.sdf`);
   * the DUD-Z conformer SDFs under `<corpora>/` (43 target
     directories of `shard_NNNNN.sdf.gz`; read them as gzip streams with
     `Chem.ForwardSDMolSupplier(gzip.open(...))`, never decompressed into a
     worktree).

   Report how many ids would be refused, with examples. **Stop rule (the author,
   2026-10-18):** if more than **0.1% of molecules** in LIT-PCBA or in DUD-Z
   (counted per corpus) would be refused, stop and report to the author before
   T299's and T302's large builds start (they would refuse at the same ids).
   At or below 0.1%, proceed and record the count and examples in
   `results/T291/`.

## Deciding measurement

Order and identity are pure functions of content. Build one synthetic input
(~200 molecules, mixed conformer counts, every bucket populated) several ways:
* in input order and with the **molecules** shuffled (each molecule's
  conformer records keep their source order, which defines `conf_idx`);
* with `workers` 1, 2 and 8;
* interrupted with SIGTERM and resumed.

Use a small `records_per_unit` (e.g. 10) so the build has many scatter units
and workers 1/2/8 and the SIGTERM actually interleave, and include molecules
with 72 or more heavy atoms so bucket 12 is populated. Every build must yield
identical `(n_real, mol_id, conf_idx)` order and
identical stored int16 coordinates. The branch still writes format 2 until
T293, so compare the decoded arrays, not file bytes.

## Acceptance

* `pytest tests/test_prep*.py tests/test_sqlite_source.py tests/test_sdf_merge*.py`
  (the `test_prep*` glob covers `test_prepare*`; do not add `-q`, pitfall 26)
  is green on the branch, run with `ROSHAMBO3_TEST_SDF` and `ROSHAMBO3_CORPORA`
  set (unset, 46 tests skip and the run still says "passed"; see
  `results/T291/README.md`). Tests that assert format-2 order are updated to the
  new order, not deleted.
* A new test asserts identical order across shuffled input, worker counts 1, 2
  and 8, and a resumed build. Reuse the SIGTERM/resume harness in
  `tests/test_prepare_worker_death.py`, which imports `tests/scatter_delay.py`
  so it works under `spawn`.
* A new test asserts that for every stored molecule,
  `Chem.MolFromSmiles(smiles)` has `n_real` atoms whose elements equal the slot
  elements in order, and the SMILES has no stereo marks. Deuterated input is
  included (see `tests/test_isotopic_hydrogens_are_stripped.py`).
* New tests refuse a duplicate `(mol_id, conf_idx)` across slots, and a charge
  variant and a protonation variant under one id (id in the message); and an element and an atom-count difference; and accept a stereo-only and
  an atom-order-only variant. Cover the per-record SDF path, the merged SDF
  path and `RDKitSource`.
* A molecule whose SMILES does not reproduce the slot elements is refused at
  build (unit test with a patched helper).
* Every stored int16 is on the D034 grid in step units: dequantized at the
  step (`v * 2**-8`), each coordinate is within step/2 of its prepared value (re-prepare the
  source molecule in canonical order with `_prep_raw` in the test to get it)
  (ties round half to even, as `np.rint`).
* A resume after an input's content changes (same size and mtime) or after a
  builder module changes is refused, naming which.
* `_why_reject` accepts a molecule of 4,096 conformers and refuses 4,097 with
  the limit named; `MAX_MERGED_CONFORMERS == MAX_CONFORMERS_PER_MOLECULE ==
  4096`. This is a unit-level test: an end-to-end build of a molecule with
  more than 256 conformers is T293's acceptance (the 4,096-conformer molecule),
  because until T293 the branch still writes the uint8 `conf_idx` sidecar.
* `tests/test_prepare_topology.py::fixtures()` (moved to a helper) and the
  `proto` fixture in `tests/test_sdf_merge_conformers.py` no longer hold a
  charge or protonation variant under one id, and every importer passes.
* `results/T291/` holds the census report (item 8) and a README stating the
  SMILES rule used (non-isomeric, FORMAT.md 11.1), the `conf_idx` definition
  (item 2) and the RDKit version.

## Traps

* **Pitfall 22.** Builds write beside the corpora under `$ROSHAMBO3_CORPORA`,
  never into a worktree, never in place. Synthetic test corpora live in pytest
  `tmp_path`.
* **The planner and the writer must walk one order.** `_shard_chunks` is called
  by both `_plan_bucket` and the writer loop in `_gather`. A merge implemented
  in only one of them sizes groups for rows they do not hold.
* **Use `RemoveAllHs`, not `RemoveHs`, for the SMILES.** `RemoveHs` keeps
  deuterium; with it, the slot order and the SMILES atom count disagree on
  isotopically labelled molecules (T127).
* **Take `_smilesAtomOutputOrder` from the non-isomeric call.** The isomeric
  and non-isomeric canonical orders can differ; the order and the stored
  SMILES must come from one `MolToSmiles(heavy, isomericSmiles=False)` call.
* **Feature perception happens before H removal** (D034 item 3).
  `_prep_one` calls `generate_color_atoms(mol)` on the H-bearing molecule
  (`prep/sources.py:168`; `strip_hydrogens` is at :161);
  perceiving after removal loses a mean of 7.0 Hydrophobe features per molecule
  (T58). Do not move perception after `strip_hydrogens`. Only the
  *coordinates* and the SMILES are reordered here.
* **Spawned workers.** macOS uses `spawn`, so module-level patches and globals
  do not reach workers. Any test that slows or patches scatter workers must use
  an importable module, as `tests/scatter_delay.py` does.
* **Canonical SMILES order depends on the RDKit version.** Byte-identity of
  rebuilds holds only within one RDKit release (FORMAT.md section 13, item 3). Record
  the version, and do not claim cross-version identity.
* **Shared fixtures carry a charge variant.** Once variant refusal lands, every
  build from `test_prepare_topology.fixtures()` refuses. Rewrite it first
  (item 4), or five files fail at once for one reason.
* **The cap lift is not end-to-end testable here.** Between this ticket and
  T293 the branch still writes the uint8 `conf_idx` sidecar, so a molecule of more than 256 conformers passes `_why_reject` and the
  widened shard metadata, and then fails loudly in `write_sidecars` (a refusal, not the silent duplicate `(mol_id, conf_idx)`
  the cap was added for). Do not test >256 end to end in this ticket.
* **Do not fold T292's feature-table work in here.** Expose the atom
  permutation and leave the feature table to T292.

## Working rules

See `tickets/CONVENTIONS.md`.
* **Branches.** Cut `ticket/T291-builder-content-order` from
  `ticket/T281-format3-switch` (it exists; at 8869694d it equalled main, and
  T296 merges into it first). Merge back into `ticket/T281-format3-switch`
  (no-ff), **never into main**. Worktree `<worktree>`.
* **Venv.** There is no shared venv. Build one in the worktree as
  `doc/BENCHMARKING.md` "The venv" shows and check that `roshambo3.__file__`
  points into the worktree.
* **GPU.** None needed; correctness work, so no lock. Export
  `CUDA_MPS_PIPE_DIRECTORY=<private directory>` and check `pgrep -a nvidia-cuda-mps`
  before building or running pytest (CLAUDE.md: a foreign MPS daemon hangs
  CMake's CUDA probe and the test suite).
