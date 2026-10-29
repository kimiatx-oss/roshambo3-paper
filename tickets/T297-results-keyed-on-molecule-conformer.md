---
id: T297
title: Key results on (mol_id, conf_idx) and draw web overlays from SMILES plus decoded coordinates
phase: 3
lane: host-io
status: closed
model: sonnet
depends_on: [T270, T286, T287, T288, T293]
priority: high
branch: ticket/T297-results-by-molecule-conformer
worktree: <worktree>
artifacts: results/T297/
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
  - Deciding measurement (b), screening the same input built twice by T293's
    builder with different gid assignments;
  - any check that needs a builder-produced `molecules.parquet` or
    `build.json` rather than a writer-produced one.
  Only then is the ticket done.

Byte-level details are in `doc/FORMAT.md`; decisions in
`decisions/D034-corpus-format-3.md` (accepted). Where they disagree with this
ticket, they win -- record the disagreement in your results README. If T293
lands an interface (block directory, run-table expansion, `build.json` fields)
that differs from what you built against, follow T293's and adapt.

In format 3 (`tickets/T281-corpus-format-3.md`, design points 4, 5 and 6) a global
conformer id (gid) is only a corpus-local position in content order
`(bucket, n_real, mol_id, conf_idx)`. Anything that must outlive a corpus build --
hit files, web job records, gold sets -- keys on `(mol_id, conf_idx)`. Per-conformer
`mol_id`/`conf_idx` sidecars are replaced by a per-group molecule run table
`(mol_id u64, n_conf u16, n_real u8)`; `conf_idx` is a row's offset within its molecule's run.
`structures.sqlite` is dropped: heavy atoms are stored in canonical-SMILES output
order, so atom *i* of `Chem.MolFromSmiles(molecules.parquet.smiles)` is coordinate
slot *i*. The web overlay therefore needs only that SMILES and the decoded
coordinates.

The web app is a local demonstration tool and is not intended for exposure on untrusted networks.

Integration branch: cut from `ticket/T281-format3-switch` (T282 creates it from
main; if absent, `git branch ticket/T281-format3-switch main`), merge back into it.

## Scope

1. **Catalog** (`src/roshambo3/format/catalog.py`, `class Catalog` `:104`): reimplement
   over the run tables, reading groups **only through T286's reader API**
   (`src/roshambo3/format/r3g/`; the group/corpus reader classes T286 defines --
   do not open group files or parse headers here). `_split` (`:134`, gid -> (group, row) by searchsorted over
   group offsets) stays; `locate` (`:167`) and `mol_ids` (`:180`) derive `mol_id` and
   `conf_idx` from the run table (searchsorted over run starts); `molecules` (`:202`)
   joins `molecules.parquet` on `mol_id`; `coordinates` (`:301`) decodes one block per
   gid through T286's reader (which uses T285's native decoder when built, T284's
   Python reference otherwise) and trims to `n_real`. Add a reverse lookup `(mol_id, conf_idx) -> gid`.
2. **Results** (`src/roshambo3/results.py`): `QueryHits` (`:27`) carries `mol_id` and
   `conf_idx` alongside `gids`; `to_table` (`:234`) emits them; `hit_molecules`,
   `distinct_molecules_in_hits`, `aligned_poses` keep working.
3. **CLI** (`src/roshambo3/cli.py`): the hit printout in `_cmd_screen` (`:71`) and
   `_write_csv` (`:147`) write `mol_id, conf_idx` (and `ext_id`, `smiles` with names); keep `gid`
   as an explicitly corpus-local column. Neutralize spreadsheet formulas in any text
   cell taken from the corpus (`ext_id`, names): a value beginning with `=`, `+`, `-`,
   `@`, tab or CR is prefixed with `'`. (This is output hygiene, not web hardening.)
4. **Web** (`src/roshambo3/web/`): `screening.py::merge_hits` (`:13`) and `run_screen`
   (`:28`) write `hits.json` and `scores.npz` with `mol_id` and `conf_idx`
   (`scores.npz` at `:112`, `poses.npz` at `:119`, `hits.json` at `:120`);
   `app.py::load_overlay` (`:148`) stops calling `structures.get_structure`
   (`:156-166`) and instead parses the hit's SMILES from `molecules.parquet` and
   applies the decoded, posed coordinates via `chemistry.py::molblock_at`
   (`:10`, `preserve_atoms=True`, identity atom map), reassigning stereo from 3D as
   today. The job manifest's corpus fingerprint becomes the format-3 semantic
   fingerprint from `corpus.json`.
5. Leave `format/topology.py`, `web/topology.py` and the external structure index in
   place; T298 deletes them.

### Definitions gate wiring

Replace every `Corpus.require_color_features_enum` call site (`api.py:98`,
`api.py:113`, `engine/source.py:539`, `engine/source.py:552`,
`engine/engine.py:593`, `web/screening.py:57`, and the direct enum comparison in
`engine/cpu_self.py:214`) with T287's descriptor comparison followed by T288's
trust gate, and thread `--trust-definition` / `trust_definitions=` from the CLI
and API into it. In `web/config.py` `public()`, replace the `features_enum`
comparison with the gate's verdict (untrusted custom definition -> color modes
disabled with a message pointing at the CLI). Shape-only screens never call the
gate. `engine/source.py:539` and `:552` are in `Rsb3Source`, which T294 replaces
with `R3gSource` (and T298 deletes): put the check in one function this ticket
defines (e.g. `check_corpus_color(corpus, generator, trusted_definitions)`), call
it wherever `Rsb3Source` did and at the equivalent point in `R3gSource` and the
CPU-worker path (T295). Whichever of T294/T295/T297 merges into the integration
branch second adds the call in the other's code; T298 verifies no screen path
bypasses it. Acceptance: an untrusted custom-definition corpus is refused for color
screening through the CLI, the API and the web demo, and accepted after
`roshambo3 definitions trust <hash>`; a shipped-default corpus needs no flag.

## Deciding measurement

Two tests: (a) for every molecule in a format-3 synthetic corpus with color, the
overlay molblock's atom *i* has the element of SMILES atom *i* and the coordinates of
slot *i* (identity map by construction); (b) screening the same input built twice
with **different gid assignments** (e.g. one build including extra molecules that
shift positions) yields identical `(mol_id, conf_idx)`-keyed hit tables.

## Acceptance

- Tests (a) and (b) above committed and green.
- `tests/test_catalog.py`, `tests/test_web.py`, and the CLI tests pass on format-3
  corpora (adapt fixtures; do not delete coverage).
- A CSV round-trip test shows a corpus `ext_id` of `=HYPERLINK(...)` written as
  text.
- `metrics/ranking.py::canonical_ids(mol_id, conf_idx)` (`:47`) is the join key in
  every comparison this ticket adds.

## Traps

- **Do not key anything durable on gid.** gid changes when any molecule is added or
  removed earlier in content order.
- **The SMILES must be the one written by the format-3 builder** (T291:
  `RemoveAllHs`, `_smilesAtomOutputOrder` reorder). Today's `meta.parquet` SMILES
  comes from `Chem.RemoveHs` (`prep/sources.py:~84`), which keeps deuterium and is
  not slot-ordered; an overlay built from it silently scrambles atoms.
- **Molecules with stereo-only conformer variants** share one SMILES; stereo for
  display comes from 3D (`AssignStereochemistryFrom3D(replaceExistingTags=True)`
  in `web/chemistry.py`), so do not "fix" stereo from the SMILES.
- The web `BoundedCatalog` (`web/storage.py:37`) subclasses `Catalog` and overrides
  `_group_sidecars`; adapt it with the base class.
- The shared venv points at main from a worktree; check `roshambo3.__file__`.

## Working rules

See `tickets/CONVENTIONS.md`. Correctness work; GPU lock only for timed numbers.
Before any CUDA context, export
`CUDA_MPS_PIPE_DIRECTORY=<mps-pipe-dir>` and check `pgrep -a nvidia-cuda-mps`.
Branch from and merge into `ticket/T281-format3-switch`, never into main.

## Amended by T284 (2026-10-18): the run-table lookup, exactly

`doc/FORMAT.md` section 7 rule 1: for group-local row `row`,
`m = searchsorted(run_start, row, side="right") - 1` (the last `m` with
`run_start[m] <= row`) and `conf_idx = row - run_start[m]`, with `run_start`
the exclusive cumulative sum of the run table's `n_conf`; `gid = gid_base +
row` with `gid_base` the cumulative `n_conf` over earlier groups in
group-table order (section 9.2). The reverse lookup `(mol_id, conf_idx) ->
gid` finds the molecule's group and run by `mol_id` (a dictionary or a sort
over the concatenated run tables, built once at open) and adds `conf_idx`.
The overlay parses the stored SMILES, which carries no stereo (section 11.1);
stereo is assigned from 3D as today.


## Completion (2026-10-21)

Phase 1 and phase 2 complete at `b9a8fc5012659f44cb41c540b247f375ddde18f3`.
Builder-backed different-GID assignments preserve canonical molecule/conformer
results. Catalog, CSV, hits and coordinate overlays use stable identities.
Definition-gate wiring and distributed corpora without build.json are covered.
See results/T297/phase2.md and phase2-evidence.json, and independent review
results/T281/consumers-phase2/review-T297.md with execution receipts.
Seven retained legacy external-index/topology web failures are handed to T298;
none is hidden with a new expected failure. This closes the consumer scope,
not the complete web fixture migration. The fresh combined T149 check passed at source `862ac334`; local integration
completed at `a5ec1359`, with its report under `results/T149/premerge/`.
