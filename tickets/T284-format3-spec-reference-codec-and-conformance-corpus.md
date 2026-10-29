---
id: T284
title: Write the format 3 specification, a pure-Python reference codec, and the conformance corpus every implementation is tested against
phase: 3
lane: data
status: closed
model: fable
depends_on: [T281, T283]
priority: high
branch: ticket/T284-format3-spec
worktree: <worktree>
artifacts: results/T284/
---

## Context

T281 (`tickets/T281-corpus-format-3.md`) designs "format 3", a hard-break corpus
format for release; D034 (`decisions/D034-corpus-format-3.md`, written by T283)
records the decisions. What does not exist yet is the **specification**: today the
closest thing is the `src/roshambo3/format/rsb3.py` module docstring, which an
external developer cannot implement from. Every later ticket (native codec T285,
Python reader and validator T286, descriptor T287, builder T291-T293, engine
T294-T297) implements against this spec and is tested against this ticket's
conformance corpus. So this ticket fixes every byte, and the spec, not the code, is
the authority.

This ticket writes three things: `doc/FORMAT.md`; a pure-Python reference
encoder and decoder at `src/roshambo3/format/r3g/reference.py`; and a small
conformance corpus plus adversarial seed files under `tests/data/format3/`. The
spec is written before any production code. It changes no existing behaviour.

**Gate.** Approved by the author on 2026-10-17, together with T282-T290, to run
while T270 is still being built: this ticket is additive (new files, modules,
CI jobs or measurements; no change to main's numerics), so T270 does not gate
it. T291-T302 remain gated on T270.
It also needs D034 (T283) for the step.

## Scope

### 1. `doc/FORMAT.md`: what it must define, normatively

Read first: T281 design points 1-11 (the design), `results/T281/inventory.md`
(today's files and fields, and the legacy paths that must **not** reappear),
`results/T281/security/THREAT_MODEL.md` sections 2.2-2.4 and 3 (attack surfaces, the
limits table, validator tiers), `results/T281/bitpack/{README.md,bp256.c,bitpack.c}`
(the measured prototype layout), `results/T281/derive_h.py` (derived-color
evidence). Use RFC 2119 words (MUST/SHOULD/MAY). Little-endian throughout.

1. **Corpus directory.** `corpus.json`, `molecules.parquet`, optional `build.json`,
   `groups/bNN_gNNNN.r3g`. Group file names are **derived by the reader** from the
   group table's (bucket, group) integers; the descriptor carries no file paths.
   A reserved file name for a future detached signature over `corpus.json`
   (signatures are deferred past release, D034), which current readers ignore.
2. **Group file.** Prologue (magic, major version u32, header offset u64; fix the
   magic bytes); sections; JSON header at EOF, header length bounded by the limits
   table. Section table entries: name (closed enum), offset, length, dtype, shape,
   hash. Sections 64-byte aligned, tiling `[16, header_offset)` with no gaps or
   overlap, `length == prod(shape) * itemsize` except the coordinate payload. The
   sections: coordinate payload (bit-packed), block table, molecule run table,
   feature table (CSR, below), `vaa` f32[n_conf], `color_self` f64[n_conf] (color
   corpora only). There is **no stored per-conformer counts section** and no
   per-conformer `mol_id`, `conf_idx` or `n_real` array: `n_real` lives in the run
   table (item 6), per-type color counts are derived per molecule from the feature
   table (item 7), and the producer builds the device's per-conformer count word
   from those two (D034; T281 design points 3 and 4). The block table (item 5) is a
   section, not part of the JSON header.
3. **Coordinates.** Heavy atoms only, int16 in **units of the grid step** (2^-8 A,
   D034), frame = heavy-atom centroid and principal axes (as
   `src/roshambo3/prep/conformer.py::prep_conformer` does today). Atom order within a
   conformer = the molecule's canonical-SMILES output order (T281 design point 6).
4. **BP256-16 bit packing.** Exactly as the prototype `results/T281/bitpack/bp256.c`
   lays it out, made normative: per block and per axis (x, y, z), an int16 minimum
   and a u8 width `w` in `[0, 16]`; the axis stream is every **real** atom of every
   conformer of the block in row order; values `v - min` packed into groups of 256
   values = 16 lanes x 16 positions, value `g*256 + 16k + l` in lane `l` at position
   `k`, each lane's 16 values packed LSB-first into `w` consecutive 16-bit words,
   the group stored as `w` 256-bit (32-byte) words. Specify: the tail group (zero
   padding of unused positions, and that decoders MUST ignore them); `w = 0`
   (stream of zero bytes, every value equals `min`); `w = 16`; per-block layout of
   the three axis headers and streams; the byte length formula of a block as a pure
   function of header values (so a decoder can check `in_len` exactly); where padding
   slots come from (they are not stored; a decoder writes zeros).
5. **Block table.** Per block: first row, row count, byte offset and length in the
   payload, hash, molecule range `[m0, m1)`. Blocks MUST be molecule-aligned (never
   split a molecule's run) and MUST hold at most 4,096 rows, except a block holding a
   single molecule, which MAY exceed 4,096 rows up to a limit you set in the limits
   table (T281 design point 9; molecules with > 4,096 conformers exist in principle).
6. **Molecule run table.** `(mol_id, n_conf, n_real)` per molecule in corpus
   order: `mol_id` 64-bit, `n_conf` u16, `n_real` u8 (`1 <= n_real <= 255`; every
   conformer of a molecule has the same heavy-atom count, today asserted by the
   builder). `mol_id` is a non-negative int64 today
   (`prep/conformer.py::stable_id` masks to 63 bits). Store it as **u64** (T285
   and T286 assume u64) with the range rule `0 <= mol_id < 2^63`.
   `conf_idx` of a row is its offset within its run.
7. **Feature table (derived color).** A per-molecule CSR encoding of
   `(type, atom indices)`: e.g. per-molecule feature offsets, per-feature type and
   atom-count/offsets, atom indices as u8 (heavy-atom indices in canonical order,
   `< n_real`). Types are `1..n_types` in the corpus's numbering. The **derivation
   rule** for a pseudo-atom position: a single-atom feature is that atom's stored
   int16 exactly; a multi-atom feature is the integer mean of the stored int16
   coordinates per axis, summed in at least int32, rounded half away from zero (give
   the exact integer formula). The **kernel layout order** of derived pseudo-atoms:
   after the conformer's real atoms, grouped by type ascending (contiguous run per
   type, as today's merged record and `pharmacophore.generate_color_atoms` require),
   within a type in feature-table order.
8. **Corpus order and ids.** Buckets by `n_real` (state the bucket edges; today
   `rsb3.BUCKET_EDGES`), groups within a bucket, rows ordered by
   `(n_real, mol_id, conf_idx)`. The global conformer id is the position in that
   order; results that outlive a corpus key on `(mol_id, conf_idx)`.
   **Scheduling cost model** (normative, used by T293 and T295): a block's cost is
   `rows x device L` of its group; the corpus-wide block directory that CPU
   schedulers order expensive-first is built in memory by the reader from the group
   headers at open -- it is not a file.
9. **`corpus.json` schema** (closed: unknown keys are errors). `format` (major
   version, step, encoding name -- a closed enum with one value), `frame`, `color`
   (absent for shape-only: the definition text verbatim, which families are
   selected, positioning rule incl. weights, numbering `{name: id}`, interaction
   matrices `r` and `p` as values with dtype and shape, RDKit version), `prep`
   (roshambo3 version and commit, input conventions), `groups` (bucket, group,
   `L_heavy`, device `L`, `L_field_width`, `n_conf`, `n_mol`, header hash -- **no
   file names or paths**; item 1), corpus totals (`n_conf`, `n_mol`). The RDKit version is recorded but
   **excluded from the fingerprint** (a mismatch warns, it does not refuse; D034),
   so state that exclusion in the canonicalization. Also fix whether definition
   text is line-ending-normalized (e.g. CRLF -> LF) before hashing, and say so.
   **Fingerprint canonicalization**: exactly which fields, in what canonical
   serialization (sorted keys, explicit encoding, matrices as pinned-dtype bytes),
   hashed with what. Each group header carries the fingerprint.
10. **`molecules.parquet`**: columns (`mol_id`, `ext_id`, `smiles`, plus whatever
    descriptor columns are kept, e.g. `hac`, `mw`, `rotor_count`), row order, and the
    SMILES rule: generated after `RemoveAllHs`, so parsing it with
    `Chem.MolFromSmiles` yields heavy atoms in slot order (element-for-element).
    SMILES MUST NOT use CXSMILES extensions.
11. **`build.json`**: provenance only, never fingerprinted, never required.
12. **Hashes.** Pick one algorithm available in Python's `hashlib` (so the
    reference reader needs nothing else) for block, section and header hashes; state
    why. The magic bytes, the hash algorithm and the `mol_id` dtype are your choices,
    but each MUST be fixed in the spec. The two-level chain: block hashes in the block table, group header hashes in
    `corpus.json`.
13. **Versioning policy.** The major version means byte layout; the fingerprint
    means semantics; a new encoding is a new major version, never a header flag.
    Readers MUST refuse an unknown major version.
14. **Limits table** (normative), adapted from THREAT_MODEL section 3's P0 table to
    format 3. Map every row explicitly:
    - `corpus.json` / group header size, JSON depth, string length: keep.
    - groups, blocks per group, `n_conf` per group: keep (or justify a change).
    - `L_heavy` <= 256 and device `L` <= 512: keep; `L_heavy` is checked against
      the run table's `n_real`, device `L` against `n_real + Σcolor` derived from
      the feature table.
    - features per type per molecule, Σcolor, atoms per feature: keep; they now
      bound the feature table.
    - block `raw_len` 4 MiB: replace by the bit-packed rule -- a block's byte length
      MUST equal the closed-form function of its header (rows, `n_real` per row via
      the run table, the three widths), and the decoded size `rows x L x 3 x 2`
      bytes MUST be within a stated cap; drop the zstd window and every other codec
      row.
    - bit width 0-16: keep.
    - definition-text limits (`AtomType`/`DefineFeature` lines, expanded SMARTS per
      definition and total): keep, and add SMARTS-list limits for custom-SMARTS
      definitions. Adopt these values unless you record why not: <= 256
      patterns, each <= 1 KiB, total <= 64 KiB. **The spec's limits table governs
      every definition limit**; T288 implements whatever it says.
    - SMILES and `ext_id` string rules: keep.
    Add a time bound for refusing any adversarial input (e.g. 2 s) and a peak-RSS
    cap for the validator, both normative.
    **Definition-text pre-pass.** Specify an RDKit-free pre-pass over the stored
    definition text -- byte length, line count, macro (`AtomType`) expansion size,
    `$(...)` nesting depth, SMARTS pattern count and size -- run in the `scan` tier.
    The reference implements it as a pure function (no RDKit import) that T288
    reuses for the trust path. This pre-pass is what refuses the macro-bomb and
    chained-`*` adversarial seeds within the time bound.
    **Validator tiers** `open`, `scan`, `deep` with the checks each performs (start
    from THREAT_MODEL section 3, minus its zstd and counts-section items). The CLI
    surface is `roshambo3 verify [--tier open|scan|deep] [--all]` (default `scan`),
    implemented by T286.
15. **Decoder requirements** that the prototype violates and implementations MUST
    NOT: a width byte used to index anything without a prior `w <= 16` check (the
    prototype selects an unpack function from a 17-entry table by an unchecked file
    byte); writing a row longer than the caller's output width (prototype trusts
    `n_real <= L`); reading past the input buffer (prototype has no `in_len`, and its
    `row_copy` reads 8 values at a time past the last real value). State the decoder
    contract at the level of required checks (input length, output capacity, widths,
    `n_real <= L`, atom indices, overflow-checked sizes; error codes, never abort).
    The concrete native function signatures and Python binding names are **not**
    this ticket's: T285 owns and publishes them.
16. **Rounding.** Coordinates are quantized with `np.rint` (round half to even), as
    `format/rsb3.py::quantize` does today; derived multi-atom pseudo-atoms use the
    integer mean rounded half away from zero (item 7). State both.

### 2. Reference codec: `src/roshambo3/format/r3g/reference.py`

Pure Python plus numpy; no compiled roshambo3 code, no RDKit. It is the oracle, not
the production path, so clarity beats speed. It implements: encode and decode of a
block (BP256-16), the block length formula, the feature-table derivation of
pseudo-atom positions and their kernel-layout order, the fingerprint
canonicalization, the RDKit-free definition-text pre-pass (item 14) as a pure
function, and the `open`/`scan` checks of a whole group file and `corpus.json` (the
`deep` tier's re-perception needs RDKit and belongs to T286; the reference may stub
it). Add `src/roshambo3/format/r3g/__init__.py`. Nothing else in
`src/` imports it yet.

### 3. Conformance corpus: `tests/data/format3/`

- A script `tests/data/format3/make_conformance.py` that writes the corpus with the
  reference encoder from a fixed SMILES list, RDKit-embedded with fixed seeds, color
  features from RDKit's BaseFeatures. RDKit versions differ in embedding, so **the
  committed files are the oracle**, and the script is provenance (record the RDKit
  version used).
- Shape and color variants; a few dozen molecules; at least: a 1-heavy-atom molecule,
  a molecule whose block has `w = 0` on some axis, a block whose stream ends in a
  partial 256-group, a block with exactly 4,096 rows, a molecule near `n_real = 255`
  (synthetic chain is fine), multi-atom features (an aromatic ring, a carboxylate),
  multiple groups and buckets.
- `tests/data/format3/EXPECTED.json`: the fingerprint, and sha256 of every decoded
  array (coordinates in kernel order per group, derived pseudo-atoms, run table,
  feature table, self-overlap columns).
- **Size budget: at most 512 KiB for the whole directory** (`tests/data` is ~1.6 MB
  today). State the actual size.
- `tests/data/format3/adversarial/`: one minimal file per row of THREAT_MODEL
  section 2.2's table and per container rule in section 2.3 (duplicate JSON keys,
  NaN, oversize header, unknown major version, a path-like group entry, section
  overlap, misaligned section, `w = 17`, `n_real > L_heavy`, `n_real + Σcolor` >
  device `L`,
  atom index `>= n_real`, feature type out of range, runs not tiling, block length
  inconsistent with header), plus a definition-text macro bomb and an 18-`*` chained
  SMARTS (THREAT_MODEL appendix gives both), both refused by the `scan` tier's
  definition-text pre-pass. `adversarial/EXPECTED.json` names, per file, the
  validator tier that must refuse it and the error class.
- `tests/test_format3_reference.py`: round trip of every width 0..16 including tail
  groups; decode of the conformance corpus equals `EXPECTED.json`; the fingerprint is
  identical when computed in two separate Python processes; every adversarial file is
  refused by the stated tier within a time bound (e.g. 2 s each) and raises the
  stated error class -- refusals, not crashes or hangs.

## Deciding measurement

`tests/test_format3_reference.py` passes on Linux x86 and on macOS arm64 (CI's
`cpu-macos` job runs `pytest -q -k "not cuda"` over `tests/`, so a new file named
`tests/test_format3_reference.py` without "cuda" in its test names is picked up with no
workflow edit -- confirm in `.github/workflows/ci.yml`), with the fingerprint and
decoded-array digests equal across both; and a **cold read**: an agent with no context, given only `doc/FORMAT.md`,
writes an independent decoder for one conformance group file that matches
`EXPECTED.json` (record the attempt and every ambiguity it reported, fixed in the
spec, in `results/T284/cold_read.md`).

## Acceptance

- `doc/FORMAT.md` covers items 1-16 above; every MUST is testable and the limits
  table maps every row of THREAT_MODEL section 3's P0 table (kept, replaced or
  dropped, with the reason).
- `pytest tests/test_format3_reference.py` green on Linux x86 and in CI on macOS arm64
  (do not pass `-q`: pitfall 26).
- `tests/data/format3/` within 512 KiB; `make_conformance.py` regenerates
  byte-identical files under the recorded RDKit version.
- `results/T284/cold_read.md` shows the independent decoder matching.
- No production code path changed.

## Traps

- **Do not specify today's format with new names.** `results/T281/inventory.md` lists
  every legacy path (split color, byte shuffle, version-3 numbering trick, `t` plane,
  counts synthesis, per-conformer `mol_id`/`conf_idx`, structures store). None
  returns. If a field exists "for compatibility", delete it: there is no old reader.
- **Feature atom ids today index the H-bearing molecule.**
  `pharmacophore.make_feature_plan` returns RDKit atom ids of the molecule with
  hydrogens; the stored table must use heavy-atom indices in canonical-SMILES order.
  The spec states the stored meaning; the remap is the builder's job (T292).
- **Hydrophobe perception needs explicit hydrogens.** Re-perceiving BaseFeatures on
  the H-stripped graph gets Hydrophobe wrong in ~98% of conformers; with `AddHs`
  every set matches (`results/T281/derive.py` vs `derive_h.py`). Any spec text about
  re-perception (the `deep` tier, query featurization from the corpus definition)
  MUST say "after adding hydrogens".
- **Derived centroids differ from today's stored pseudo-atoms by up to one quantum**
  (single-atom features exact). That is a declared change (T296), not a spec bug.
- **Canonical SMILES order is RDKit-version dependent.** Byte-identity of rebuilds
  holds within one RDKit release; say so in the spec.
- **Fingerprint noise.** A digest over an unsorted dict or a float `repr` is noise;
  hash pinned-dtype bytes and test across processes.
- **2^-8 not 0.001.** Every example in the spec uses the D034 step. Range: int16 at
  2^-8 A covers +-128 A.
- **Do not edit T270** (another agent system owns it).

## Working rules

See `tickets/CONVENTIONS.md`. Worktree `<worktree>` on
`ticket/T284-format3-spec` from main; merge to **main** (additive: new doc, new
module nothing imports, new test data). No GPU. Build and test with this worktree's
own venv (`bench/worktree_python.sh` explains the silent wrong-tree trap; verify
`roshambo3.__file__`). Commit before long waits.
