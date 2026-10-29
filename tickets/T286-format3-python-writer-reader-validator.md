---
id: T286
title: Format 3 Python writer, reader and three-tier validator, refusing every hostile input before native code sees a byte
phase: 3
lane: data
status: closed
model: opus
depends_on: [T284, T285]
priority: high
branch: ticket/T286-format3-python-writer-reader-validator
worktree: <worktree>
artifacts: results/T286/
---

## Context

**Dependency on T285.** Only T285's first deliverable (the `native.pyi` binding
stub) is needed to start; the native-path acceptance items wait for T285's
implementation. This ticket also **owns the `roshambo3 verify` CLI** (`--tier
open|scan|deep`, `--all`); other tickets only use it.

**Gate.** Approved by the author on 2026-10-17, together with T282-T290, to run
while T270 is still being built: this ticket is additive (new files, modules,
CI jobs or measurements; no change to main's numerics), so T270 does not gate
it. T291-T302 remain gated on T270. This
ticket is finalized after T284 lands `doc/FORMAT.md`: wherever this file names
a layout detail, the spec section it cites is authoritative, and if the two
disagree the spec wins and this ticket is amended.

ROSHAMBO3 is replacing its corpus format with "format 3", a hard break before
public release (`tickets/T281-corpus-format-3.md`, the design of record; the
decisions are in `decisions/D034-*.md`, written by T283). A corpus becomes a
directory: `corpus.json` (descriptor), `molecules.parquet` (per molecule:
`mol_id`, `ext_id`, slot-ordered SMILES, descriptors), an optional
`build.json` (provenance, never fingerprinted), and one self-contained group
file per group under `groups/` (T281 design point 1). Format 3 corpora will be
downloaded from third parties and read by range requests, so every byte is
attacker-controlled. The threat model
(`results/T281/security/THREAT_MODEL.md`, section 3) requires a **pure-Python
validator that runs before any native code sees a byte**, and a reader that is
safe on its own. The format-2 reader trusted manifest paths and read headers
without a size cap; format 3 removes both. Note also:

* `json.loads` everywhere keeps the **last** of two duplicate keys silently, so
  two readers (or a validator and a reader) can disagree about one file.

This ticket builds the Python side of format 3: writer, reader and validator.
The native codec (T285) and the descriptor/fingerprint module (T287) are
separate tickets; this one calls them.

## Scope

All new code lives in a new package, `src/roshambo3/format/r3g/` (name per
`doc/FORMAT.md`). **It changes no behaviour of the existing reader**
(`format/rsb3.py`, `format/dataset.py`, `engine/source.py` stay as they are
until T298's switch). Nothing in `engine/`, `api.py` or `cli.py` imports the
new package in this ticket except the `roshambo3 verify` subcommand's format-3
path: `roshambo3 verify <corpus> [--tier open|scan|deep] [--all]` (default tier
`scan`; `--all` makes `deep` cover every row instead of a sample). The command
name is `verify` everywhere (T281, T293, T299); there is no `validate` command.

0. **Strict JSON helpers.** `roshambo3.format.r3g.jsonstrict.loads(data: bytes,
   *, max_bytes, max_depth, max_str)` and `dumps(obj) -> bytes` (canonical:
   sorted keys, no NaN, UTF-8). They reject duplicate keys, NaN/Infinity, depth
   and size beyond the spec limits. T287 (descriptor and fingerprint) and every
   format-3 reader use these; nothing in the new package calls `json.loads`
   directly.
0b. **One codec dispatch function.** `format.r3g.codec` defines the single entry
   point the reader and writer use for block encode/decode. It calls the T285
   native binding (interface fixed by T285's `src/roshambo3/format/r3g/native.pyi`
   stub) when the extension provides it, and the T284 pure-Python reference
   (`format/r3g/reference.py`) otherwise. Code against the stub; do not guess
   native names.

1. **Writer.** `write_group(...)` and `write_corpus(...)` emitting the group
   file, `corpus.json`, `molecules.parquet` and `build.json` exactly per
   `doc/FORMAT.md` (byte layout, section table, block table with per-block hash
   and molecule range, 64-byte alignment, header at EOF). The coordinate payload
   is fixed-width bit packing in the BP256-16 layout (T281 design point 7); use
   the T285 native encoder when the extension provides it, else the T284
   pure-Python reference encoder (`format/r3g/reference.py` or wherever T284
   puts it). Both must produce identical bytes. The writer is called by the
   builder in T293; this ticket tests it with synthetic inputs and the T284
   conformance corpus.
2. **Reader.** Opens a corpus directory and exposes groups, the run table
   (`mol_id u64`, `n_conf u16`, `n_real u8` per molecule), the feature table,
   the fixed-width sections (`vaa` f32, `color_self` f64) as read-only mmaps,
   and per-block decode through the dispatch function in 0b. **There is no
   stored per-conformer counts section in format 3**: per-row `n_real` and
   per-type counts are derived from the run table and the feature table, and
   the reader exposes them as derived (computed) arrays. The reader **always runs the `open` tier** below before returning
   anything, and refuses an unvalidated corpus for screening unless the `scan`
   tier has passed (cached, see item 4).
3. **Validator, three tiers** (THREAT_MODEL section 3, "P0. A pure-Python
   validator..."; limits from its P0 limits table, which `doc/FORMAT.md` makes
   normative):
   * **`open`** -- O(header), always:
     * magic, major version, header offset within the file, header ends
       exactly at EOF, header size <= the spec limit (16 MiB in the memo) read
       with a bounded `read(n)`, never `read()`;
     * strict JSON: `json.loads(..., object_pairs_hook=<reject duplicate
       keys>, parse_constant=<reject NaN/Infinity>)`, depth <= 32, string
       length <= the spec limit, closed schema (an unknown key is an error);
     * every count and limit checked, with products computed as Python ints
       (no numpy overflow);
     * sections tile `[16, hdr_off)` with no overlap, 64-byte aligned, each with
       `len == prod(shape) * itemsize`;
     * blocks ascend, row counts sum to `n_conf`, molecule ranges tile the run
       table, no block exceeds the row cap except a single-molecule block within
       the raw-size limit (spec);
     * bit widths are 0..16;
     * the descriptor fingerprint matches (call T287's function; until T287
       lands, a stub that the T287 ticket replaces);
     * interaction matrices finite, `>= 0`, correctly shaped.
   * **`scan`** -- O(fixed sections):
     * derived counts: per molecule `n_real <= L_heavy` and
       `n_real + n_features <= L` (device width);
     * definition text: the RDKit-free pre-pass that `doc/FORMAT.md` specifies
       (size, line count, macro-expansion size, nesting depth), implemented as a
       pure function in the T284 reference; `scan` calls it, and T288 reuses
       the same function;
     * every feature type in range and every atom index `< n_real` of its
       molecule;
     * self-overlaps finite and `> 0`;
     * run-table sums agree with block row counts; `molecules.parquet` schema,
       row count and `mol_id` set equal the run table;
     * string rules: SMILES and `ext_id` length limits, no C0/C1 or bidi
       control characters in `ext_id`.
   * **`deep`** -- opt-in (`roshambo3 verify --tier deep`, `--all` for every row): full block
     decode against block hashes and section sha256s; SMILES parse with
     CXSMILES off and elements matching slots; feature table re-perceived and
     self-overlaps recomputed on a sample seeded from `os.urandom`.
4. **Paths and files.** The group table carries **no file names**: the reader
   derives `groups/bNN_gNNNN.<ext>` from the group index. Open every file with
   `os.open(path, os.O_RDONLY | os.O_NOFOLLOW)` and refuse anything that is not
   a regular file (`stat.S_ISREG`) or resolves outside the corpus root.
5. **Parquet.** Check the schema and row count from the footer metadata
   (`pyarrow.parquet.ParquetFile(...).schema_arrow`, `.metadata.num_rows`)
   before reading any data. `pyproject.toml` already pins `pyarrow>=15`, the
   floor that excludes the pickle CVE-2023-47248; keep that floor and do not
   enable any extension-type deserialization.
6. **Scan cache.** `scan` results are cached keyed by the sha256 of
   `corpus.json` plus the group header hashes, so a corpus is scanned once per
   content, not per screen.
7. **Exceptions.** Every refusal is one typed exception (e.g.
   `CorpusValidationError(ValueError)`) whose message names the file, the
   field and the limit. No other exception type may escape the validator on
   any input (no `KeyError`, `IndexError`, `UnicodeDecodeError`, `MemoryError`).

Out of scope here: the native codec (T285), fingerprint canonicalization and
definition comparison (T287), trust and definitions UX (T288), fuzzing
harnesses (T289, which uses this validator), wiring into the engine (T294-T298).

## Deciding measurement

The adversarial seed corpus that T284 commits (one fixture per row of
THREAT_MODEL section 2's attack-surface tables, plus the spec's limit-edge
cases): **every fixture is refused by `open` or `scan` with
`CorpusValidationError` within the spec's time bound** (the memo uses
"within a time bound"; T284 sets the number), and **the conformance corpus
(`tests/data/format3/` from T284) reads back bit-identical** to its committed
decoded-array digests through both the native and the reference decode path.

## Acceptance

* `pytest tests/test_format3_validator.py tests/test_format3_writer_reader.py`
  (new files) green on x86 Linux and macOS arm64 CI.
* Every adversarial fixture: refused, correct exception type, message names the
  field, wall time under the bound, peak RSS under the cap (measure with
  `resource.getrusage`). The RSS cap is the spec's limits-table value; if
  `doc/FORMAT.md` gives none, 2 GiB.
* **Scan cache**: a second `scan` of an unchanged corpus is served from the
  cache (test asserts no section is re-read); changing one byte of
  `corpus.json` or of any group header invalidates it.
* **Unvalidated refusal**: opening a corpus for screening when `scan` has not
  passed (cache empty, scan not run) refuses with `CorpusValidationError`; the
  same corpus opens after `roshambo3 verify --tier scan` passes.
* Duplicate-key, NaN, deep-nesting, oversized-header, overlapping-section,
  out-of-file-section, width-17, `n_real > L`, atom-index `>= n_real`,
  symlinked group file and `../` cases each have a dedicated test.
* Writer -> reader round trip on the conformance corpus and on randomized
  synthetic groups (widths 0..16, partial final BP256 groups, `n_real` 1..255,
  empty color) is exact.
* Native and reference encoders produce byte-identical group files.
* No change in behaviour of the existing test suite (`pytest -k "not cuda"`
  pass count unchanged against the branch point; read the skip count, see
  Traps).

## Traps

* **The validator is not optional plumbing; it is the security boundary.**
  THREAT_MODEL section 3: "Validators have bugs, and range reads fetch bytes after
  validation" -- so the native decoder (T285) checks bounds on its own as well.
  Do not weaken T285's checks because this validator exists, and do not skip a
  check here because T285 has one.
* **Products of header integers overflow in numpy, not in Python.** Compute
  `rows * L * 3` and section lengths with Python ints, then compare.
* **`json.loads` accepts `NaN`, `Infinity` and duplicate keys by default.**
  Both are needed to be refused explicitly.
* **Never read a file name from JSON.**
* **The threat model predates three decisions.** It discusses zstd checksums,
  signatures and web-app hardening; T281 (decisions 10-17) supersedes it: the
  payload is bit-packed with no compressor, signatures are deferred past
  release (the spec only reserves room), and the web app is a local
  demonstration tool that is not intended for exposure on untrusted networks. Corpora altered only to give wrong answers (e.g. a lowered stored
  self-overlap) are out of the security scope; `scan` still checks finiteness
  and positivity because those prevent crashes and NaN propagation.
* **Pitfall 22**: tests write synthetic corpora to `tmp_path`, never into the
  worktree or beside real corpora.
* **Read the skip count.** A suite run with `$ROSHAMBO3_CORPORA` unset skips
  hundreds of corpus tests (CONVENTIONS); "green" means the same pass and skip
  counts as the branch point.

## Working rules

See `tickets/CONVENTIONS.md`. This ticket is **additive**: branch from main,
merge back to main no-ff when green. It adds a new package and tests and changes
no existing code path, so main stays green. Correctness work: no GPU lock
needed. Commit the adversarial-fixture timing table to `results/T286/`.

## Amended by T284 (2026-10-17): what `doc/FORMAT.md` settled

The spec is authoritative; these are the points this ticket's text deferred to it.

* **Files and names**: group files are `groups/b{bucket:02d}_g{group:04d}.r3g`
  (digits are minimums; section 1); `corpus.json.sig` is reserved and ignored
  (section 12.2); `build.json` is optional and never read by a screen.
* **Exception**: `CorpusValidationError(ValueError)` with attributes `code`
  (the closed enumeration of section 16.5), `tier` and `path`. The
  adversarial manifest `tests/data/format3/adversarial/EXPECTED.json` names
  `(tier, code)` per seed; this ticket's validator MUST refuse each seed with
  the same tier and code the reference does (`reference.validate_corpus` is
  the behavioral oracle for `open` and `scan`). The reference's
  `loads_strict` pre-scans the raw bytes for depth and string length before
  parsing; `jsonstrict.loads` may reuse it.
* **Bounds** (limits 33-34): a refusal within 2 s per corpus file and 2 GiB
  peak RSS, on any input, in `open` and `scan`. Both are normative; the "2 GiB
  if the spec gives none" fallback is moot.
* **`open`** additionally checks: the 48 reserved prologue bytes are zero;
  the header is canonical JSON; sections tile `[64, header_offset)` by
  *extent* (`roundup64(offset + length)`), the first at 64; the block table
  (read at `open`, it is small) tiles rows, molecules and payload bytes; the
  single-molecule row cap is **65,535** (section 6 rule 4; reduced to 4,096 by D034 item 9 as amended 2026-10-18, applied by T303); decoded-size caps
  (limits 20-21); `header_sha256` and the fingerprint against `corpus.json`.
* **`scan`** additionally checks: 32-byte block headers (widths <= 16, 23
  reserved bytes zero, `length == 32 + 32*G*(w_x+w_y+w_z)`); run-table
  reserved bytes zero, order `(n_real, mol_id)`, bucket membership, `mol_id <
  2^63` and unique across the corpus; feature canonical order (section 8.1
  rule 4); `L_field_width` bucket-wide; `color_self` present iff the
  matrices are canonical (section 18.2); the Parquet schema exactly as
  section 11 (`mol_id uint64, ext_id string, smiles string, hac uint8, mw
  float64, rotors uint16`, codecs `UNCOMPRESSED|SNAPPY|ZSTD`), `hac ==
  n_real`; the definition pre-pass is `reference.check_definition_text`.
* **`deep`** additionally: `ids_sha256` recomputed (section 10.6; T293 scope
  10), tail positions and alignment padding zero, no int16 overflow
  (`decode.overflow`), and the RDKit items of section 16.4 (3-4), which the
  reference stubs and this ticket implements -- with `Chem.AddHs` before
  re-perception and `allowCXSMILES=False`.
* **Answers for `tests/codec_fixtures.py`** (T293 scope 11): the smallest
  legal block is one row and `block_rows` may be as small as 1; an empty
  group is invalid; a molecule always ends at a block edge; `codec=`,
  `shuffle=` and a split color layout have no format-3 meaning and a fixture
  keyword naming them is refused, not mapped.
* **Writer**: `write_corpus` with the same molecules, `block_rows` and
  `max_conf_per_group` MUST produce files byte-identical to
  `reference.write_corpus` (canonical JSON headers and descriptor, the write
  rules of sections 6 and 9.3). The Parquet writer options the reference uses
  (no statistics, no embedded Arrow schema, no dictionary pages) keep the
  conformance corpus small and are not normative beyond section 11.

## Amended by T284 (2026-10-18): review fixes that change this ticket

* **Open order** (FORMAT.md section 1 item 2): `os.open(path, O_RDONLY |
  O_NOFOLLOW | O_NONBLOCK)`, `fstat`, `S_ISREG`, then read from that
  descriptor (hand the file object to pyarrow; never reopen by path). A FIFO
  in place of a group file or of `corpus.json` must be refused, not hang
  (generated seeds `group_is_fifo`, `corpus_json_is_fifo`,
  `group_symlink_escapes_root`).
* **`molecules.parquet`** (section 11): `UNCOMPRESSED` and `PLAIN` only,
  every column REQUIRED, file size `<= n_mol x 4,608 + 1 MiB`, row groups
  `<= 2^16` rows, chunk `total_uncompressed_size <= rows x 4,608 + 4 KiB`, all
  checked from the footer before any data page; then one row group at a
  time, with vectorized checks (pyarrow compute), and `molecules_sha256`
  (section 10.7) checked first. The writer is now fully specified (no
  statistics, no embedded Arrow schema, no dictionary pages, row groups of
  2^16 rows), so byte identity with `reference.write_corpus` holds for every
  file except the parquet footer's `created_by` string, which is excluded.
* **Bounds** (limits 33, 34) are per file: `open` 2 s on any input and 2 s
  per seed; `scan`/`deep` linear in bytes read (>= 8 MiB/s of section bytes
  plus 2 s per file); RSS for `scan` `<= 256 MiB + 16 x` the file's fixed
  sections, so no per-molecule Python objects -- vectorize or chunk every
  per-molecule and per-feature check and every cross-group check (sorted
  merges, not sets). The reference does this (`_scan_group`,
  `_scan_parquet`, `_validate`); copy the approach, not just the checks.
* **`open` order**: `header_sha256` is verified before any header value is
  used, and the `blocks` section's hash before the block table is walked.
* **`color_self` is optional**, allowed only with canonical matrices (section
  18.2; the exact definition is there). **`L_field_width` is in the group
  table only.** **`smarts_list` definitions are JSON objects**, not strings.
  **`decode.overflow` no longer exists**; `integrity.molecules_hash`,
  `limit.n_feat_atoms` do.
* **`deep`** decodes with the native decoder (T285) and cross-checks a
  random sample against the reference; before T285 it decodes everything
  with the reference (test-sized corpora only). Re-perception runs inside
  T288's subprocess, never in-process.
* **Definition pre-pass**: call `reference.check_definition_text(definition,
  generator, types)`; the grammar is closed (section 15). 86 seeds now, 12
  generated; the pure pre-pass seeds are bare `definition.json` files; `definition_oversize_prepass` is a bare `definition.fdef`, not a
  corpus (feed it to the pre-pass directly, as the T284 test does).
