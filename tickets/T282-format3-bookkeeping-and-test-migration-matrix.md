---
id: T282
title: Close the tickets format 3 supersedes, and map every corpus-touching test and bench script to its fate
phase: 3
lane: infra
status: closed
model: sonnet
depends_on: [T281]
priority: high
branch: ticket/T282-format3-bookkeeping
worktree: <worktree>
artifacts: results/T282/
---

## Context

T281 (`tickets/T281-corpus-format-3.md`) designs a hard compatibility break of the
on-disk corpus format before release ("format 3"). Nothing in today's format stays
readable. Several open tickets are answered or absorbed by that design. Before the
switch ticket (T298) can be planned in detail, someone has to know which of the
test files and `bench/` scripts that touch the corpus survive the switch, need
porting, or die (the census grep below returned 96 files at 541b9f53: 75 under
`tests/`, 21 under `bench/`; the number at your commit is whatever it returns).

This ticket is pure bookkeeping plus one inventory, plus creating the integration
branch the switch tickets share. It changes no code under `src/`.

**Gate.** Approved by the author on 2026-10-17, together with T282-T290, to run
while T270 is still being built: this ticket is additive (new files, modules,
CI jobs or measurements; no change to main's numerics), so T270 does not gate
it. T291-T302 remain gated on T270.

## Scope

### 1. Close or annotate superseded tickets

Edit only the ticket files named here. For each, append a dated section (house style:
see `tickets/T128-*.md`'s "Resolution" section) and set frontmatter `status` as stated.

| Ticket | Action | What to write |
|---|---|---|
| `T150-int16-coordinates-in-the-producer-format.md` | `status: closed` | Already delivered by T87: the library record crosses the wire as the corpus's own int16 and the kernel dequantizes at the point of use. Cite the `pack_into` docstring in `src/roshambo3/engine/buffers.py` ("What crosses the wire now is the corpus's own shorts ...") and `numerics.WIRE_QUANT_STEP`'s docstring in `src/roshambo3/numerics.py`. Cite `results/T281/producer/REPORT.md` section 4 ("Host prep is small now") for the measurement that D021's 33% host-prep share no longer exists. |
| `T115-the-color-numbering-belongs-in-the-file.md` | `status: closed` | Superseded by T281 design point 2 (descriptor carries the full definition text, numbering, matrices and a fingerprint) and implemented by T284/T287. |
| `T273-convert-drops-self-overlap-sidecar-records.md` | `status: closed` | Absorbed: `prep/convert.py` is deleted by T298; self-overlaps live inside the group file (T281 design point 1). |
| `T274-vaa-verified-flag-is-written-for-the-prepared-frame.md` | `status: closed` | Absorbed: format 3 has one frame (stored, quantized); the flag becomes structural (T281 design points 1 and 8; T293). |
| `T275-resume-identity-has-no-content-or-code-digest.md` | `status: closed` | Absorbed into T291 (content and code digests in the build identity). |
| `T143-should-coordinates-be-quantized-at-all.md` | `status: closed` | Answered: quantize up front at 2^-8 A, single basis for every derived quantity. Point to T281 design point 8, `results/T281/quant-sweep/REPORT.md`, and D034 (written by T283; if T283 has not landed, say "D034, pending T283"). |

Then run `python3 scripts/ticket_index.py` to regenerate `tickets/INDEX.md`, and
`python3 scripts/ticket_index.py --check` to confirm it is clean (the scripts need
only the standard library; use `python3`, there is no `python` on roci).

### 1b. Create the integration branch

The switch tickets T291-T298 all branch from, and merge into, one integration
branch. Create it from main as part of this ticket (branch only; no worktree, no
commits on it):

```bash
git branch ticket/T281-format3-switch main
```

If it already exists, leave it alone and say so in the ticket's closing note.

### 2. The test-migration matrix

Produce `results/T282/test_migration_matrix.md`: one row per file, every file found by
this exact command run from the repo root (record the command and the commit in the
file's header). Git pathspec `*` matches across `/`, so subdirectories are included;
do not use shell globs (`**` without globstar silently matches nothing):

```bash
git grep -l -E 'prepare\(|Corpus\(|Catalog|corpora_root|rsb3|manifest\.json|sidecar|structures\.sqlite|mol_id|conf_idx|Rsb3Source|convert_corpus|counts\.u8|color_self|vaa' \
    HEAD -- 'tests/*.py' 'bench/*.py' | sed 's/^HEAD://' | sort -u
```

At 541b9f53 this returns 96 files (75 tests, 21 bench); your count is whatever
it returns at your commit -- state it.

Columns: `file`, `class`, `what it touches` (one line), `target action`, `owner ticket`.

`owner ticket` is assigned by what the file tests: builder behaviour (`prep/`) ->
T291, T292 or T293 (order/identity, feature table, emission respectively); engine
sources and CPU workers -> T294 or T295; results, CLI output and the web app ->
T297; everything else -> T298.

`class` is exactly one of:

- **synthetic**: builds its own corpus with `roshambo3.prep.prepare(...)` or a
  manifest writer in a tmp dir. Usually survives the switch with the new builder
  (owner T298, or the builder ticket T291-T293 if it tests builder behaviour).
- **external-fixture**: uses a corpus under `$ROSHAMBO3_CORPORA` via
  `tests/conftest.py` (`corpora_root()`; today a 2K-molecule smoke corpus, an internal development corpus,
  an internal multiconformer corpus, DUDE-Z PUR2). Needs the rebuilt fixture from T299 part (a) (owner T298).
- **internals**: reaches into format internals: `rsb3` reader/writer, sidecar file
  names, `Group.sidecars()`, `group.reader`, block records, `catalog._group_sidecars`,
  the topology store. Must be rewritten against the new reader or deleted.
- **legacy-only**: tests a path format 3 deletes (split color `.color.rsb3`, byte
  shuffle, version 3 / `permuted_color_order`, the `t` plane, counts synthesis,
  `convert`, the structures store, the legacy self-overlap route). Target: delete.
- **helper**: a non-test module the grep hits (e.g. `tests/cell_groups.py`,
  `tests/codec_fixtures.py`, `tests/conftest.py`). Classify by what it provides and
  give it the same target-action vocabulary.

`target action` is one of: keep as is; port (say to what); port-new-expected-values
(ports the same way but its assertions encode today's layout numerically and need
new expected values -- say which); rewrite (say what it must assert under format 3);
delete (say why); archive (bench only: move to `tickets/T<NN>/` byte-for-byte, as
`tickets/README.md` describes for closed campaigns).

Add a summary table (counts per class and per owner ticket) and a short list of
**tests whose assertions encode today's layout numerically** (gid values, byte sizes,
`coord_scale == 0.001`, block row counts of 4096 straddling molecules) -- those need
new expected values, not just a new fixture. Starting points known to pin 0.001:
`tests/test_format.py`, `tests/test_pack_into.py`, `tests/test_wire_record_cuda.py`,
`tests/test_query_wire_grid.py`, `tests/test_cpu_combo_self_overlaps.py`,
`tests/test_prep_stored_vaa.py`, `tests/test_prepare_self_sidecars.py`,
`tests/test_numerics.py` (parses `kernels.cuh` literals against
`numerics.DEVICE_CONSTANTS`). Verify each by reading it.

`results/T281/inventory.md` lists every corpus file, its writer and readers with
file:line, and the legacy read paths with line estimates; use it to classify, but
check each file yourself.

## Deciding measurement

The matrix covers every file the grep returns (row count equals `grep ... | wc -l`),
and every row has exactly one class and one target action.

## Acceptance

- The six ticket files carry their dated sections and statuses; `python3
  scripts/ticket_index.py --check` exits 0.
- `git branch --list ticket/T281-format3-switch` shows the integration branch.
- `results/T282/test_migration_matrix.md` exists, names the grep and the commit it ran
  at, and its row count equals the grep's line count (state both numbers in the file).
- No file under `src/`, `tests/` or `bench/` is modified.

## Traps

- **Pitfall 27 (ticket bookkeeping lands on main at claim):** read it in
  `tickets/CONVENTIONS.md`. Commit the status changes promptly so parallel agents do
  not claim the closed tickets.
- **Classify by reading, not by grep hit.** `mol_id` appears in metrics and results
  code that never opens a corpus; such a file may be `synthetic` or not
  corpus-touching at all. If a grep hit does not touch the corpus, keep the row and
  mark it `not corpus-touching -- no action`.
- **`bench/` holds live harnesses and dead campaign code.** Several Metal and CPU
  scripts read via `Catalog` or reach into `group.reader.coord_scale`,
  `group.counts()`, `merged_color`, `g.sidecars()` (e.g. `bench/metal_combo_provisional.py`,
  `bench/metal_binding_provisional.py`, `bench/xcheck_roshambo2.py`). Some record
  literal gid lists (e.g. `bench/metal.py`); gid values change under format 3's
  content order, so flag those.
- **The web app subclasses the source.** `src/roshambo3/web/storage.py`
  (`BoundedSource`) overrides `_decode`; tests of the web app therefore touch decode
  internals even when they look like API tests.
- **Do not edit T270.** Another agent system owns it.

## Working rules

See `tickets/CONVENTIONS.md`. Branch `ticket/T282-format3-bookkeeping` from main,
in a dedicated worktree; merge to **main** (this is an additive
ticket). No GPU, no corpora written. Commit messages end with the attribution lines
the dispatching session specifies.

## Resolution -- 2026-10-17

- Closed T150, T115, T273, T274, T275 and T143 with dated sections; `scripts/ticket_index.py --check` is clean.
- Integration branch `ticket/T281-format3-switch` created from main at 21747d8c (branch only, no worktree, not pushed).
- `results/T282/test_migration_matrix.md`: 96 census rows (75 tests, 21 bench) for 96 grep hits at 21747d8c. 24 rows are not corpus-touching; of the 72 that are, 21 synthetic, 13 external-fixture, 26 internals, 9 legacy-only, 3 helper. Gaps outside the census are listed in the file.
- No file under `src/`, `tests/` or `bench/` changed.

## Review amendments -- 2026-10-17

An independent review of the matrix was verified and applied on
`ticket/T282-review-fixes`: the matrix now has 106 rows (the 96 census rows plus 10
out-of-census rows marked `†`), with recounted summary tables and a dated
"Review amendments" section at its top listing every change. T150's resolution was
amended (its scope item 3 was never measured), and T291, T293, T294, T296, T298,
T299, T300 and T302 were updated to match (conformer cap, id gate, step pins, T69
suite, bench archive dependencies).
