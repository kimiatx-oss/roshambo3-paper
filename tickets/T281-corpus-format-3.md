---
id: T281
title: Corpus format 3 -- one hard break before release, self-describing and simpler
phase: 3
lane: data
status: open
model: opus
depends_on: []
priority: high
branch: ticket/T281-corpus-format-3
worktree: <worktree>
artifacts: results/T281/
---

## Why

The corpus format grew by accretion: three version steps that each name a
silent failure rather than a layout, ten files per group, two sidecars that
duplicate a third, a structures store as large as half the coordinate payload,
and a manifest that records a path to its color definitions instead of the
definitions. Every one of those was the right local fix. Together they are a
format an external developer cannot implement from a spec, because there is no
spec (the `format/rsb3.py` docstring is the closest thing), and that we cannot
change once other people hold corpora we cannot re-emit.

The author decided on 2026-10-17: **hard compatibility break at release.** No
historical format stays readable, including today's; simplify.

That one decision removes the reason for most of the complexity: every legacy
read path, `prep/convert.py`, the version-3 refusal trick, and the
manifest-or-version double guard exist to keep old corpora readable or to
migrate them. A corpus that is rebuilt from source needs none of it.

This ticket is the design and the work breakdown. The work packages below
are specified as tickets T282-T302.

## What exists today, measured (2026-10-17)

From the code inventory (file:line references in `results/T281/inventory.md`)
and the rebuilt LIT-PCBA corpus (20,381,286 conformers, 407,664 molecules):

| Piece | Size on LIT-PCBA | Needed for |
|---|---:|---|
| `bX_gNNNN.rsb3` coordinates (LZ4) | 4.55 GB | screening, poses |
| `structures.sqlite` | 2.34 GB | web-app overlays only |
| `.counts.u8` | 137 MB | screening (the kernel reads only this) |
| `.n_real.u8`, `.n_color_by_type.u8` | 20 + 117 MB | nothing -- duplicates of `counts.u8`, kept for pre-T86 readers |
| `.mol_id.i64`, `.conf_idx.u8` | 156 + 20 MB | molecule top-K, result resolution |
| `.vaa.f32` + `.vaa.blocks` | 78 MB | CPU path only |
| `.color_self.f64` + `.blocks` | 156 MB | CPU combo only |
| `meta.parquet`, `ids.i64` | 15 + 3 MB | names/SMILES; verify |
| `manifest.json` | 64 KB | group table, numbering gate; the rest informational |

Facts the design leans on (`results/T281/inventory.md`):

* **A molecule's conformers are one contiguous run inside one group**, and
  `conf_idx` is always `0..k-1` in run order. The builder asserts the first
  (`check_molecule_grouping`); the second follows from `enumerate(rec.conformers)`.
  So per-conformer `mol_id` and `conf_idx` are recoverable from a per-molecule
  run table.
* **The global conformer id is a position** (`catalog.py:18-25`) and it is the
  tie-break for every top-K, on device and host. Corpus order is therefore
  load-bearing for ranking.
* **Within a bucket, order is `n_real`, then worker slot, then shard append
  order** (`build.py:14-17, 733-753`) -- a function of how the build was
  scheduled, not only of its input.
* **The structures store is used only by the web app**, which reads heavy atoms
  in rsb3 slot order with an identity atom map and then *reassigns stereo from
  3D* (`web/chemistry.py:10-24`). It stores a per-conformer graph because SDF
  parsing assigns stereo per record; on PUR2, 57 of 811 molecules had two graphs
  for that reason alone. The overlay throws that stereo away.
* **Slot order is the input molecule's heavy-atom order** after `RemoveAllHs`,
  recorded nowhere except implicitly in the stored graph.
* **The color definitions are not recorded.** `manifest.color_generator.fdef_path`
  is an absolute path into the build venv (`<scratch>/.../BaseFeatures.fdef`). No
  RDKit version, no H policy, no roshambo3 version. The interaction matrices
  appear only as sha256 digests inside the CPU self-overlap sidecar record.
* **Every sampled `.rsb3` (400 files) has `t_all_zero: true`.** The per-slot type
  plane is dead.

### Codec measurements

*The first-pass survey that led to design point 7. zstd was later ruled out on
small-panel throughput (`results/T281/producer/`) and replaced by bit packing
(`results/T281/bitpack/`); the tables below are kept as the record.*

Real blocks, single thread, `nice`, under host contention -- **ratios are
exact, throughputs indicative**. Scripts and raw output in `results/T281/`.
"shuf" is the int16 byte-plane split (low bytes, then high bytes).

Merged color (LIT-PCBA, 113 MB raw):

| Encoding | Ratio | B/conformer | Decode (raw GB/s) |
|---|---:|---:|---:|
| lz4 (today) | 1.738 | 166 | 5.5 |
| zstd-3 | 2.097 | 137 | 1.50 |
| zstd-3 + shuf | 2.221 | 130 | 1.82 |
| zstd-9 + shuf | 2.274 | 127 | 1.94 |
| zstd-15 + shuf | 2.282 | 126 | 1.97 |
| zstd-19 + shuf | 2.498 | 115 | 1.32 |
| zstd-22 + shuf | 2.498 | 115 | 1.29 |

What the numbers say:

1. **The byte-plane split helps zstd** (6% on color at level 3) and hurts LZ4. D021's "drop the
   shuffle" was measured with LZ4 and is right for LZ4 only.
2. **On color data zstd-19 jumps 12% over zstd-15**, with decode dropping to
   1.3 GB/s. The reason is structural, not tuning: **87.2% of color pseudo-atoms
   sit exactly on a heavy atom's coordinates** (Hydrophobe, Acceptor and Donor
   100%, PosIonizable 77%; Aromatic and NegIonizable are ring/group centroids,
   0%) and only level 19's match finder reaches back far enough to find the
   duplicate. See design point 3: if those features are stored as atom indices,
   the duplicate disappears from the payload and the level-19 advantage with it.
3. **Removing padding before compression** (ragged storage) gains +3.7% on
   color at zstd-19 + shuf. Not worth a layout change on its own.
4. **Build cost of level 19 is affordable**: ~5 MB/s/core of raw input. LIT-PCBA
   (7.0 GB raw) is ~90 s across 16 workers against a 2,734 s scatter; D5
   (~99 GB raw) ~21 minutes across 16 workers.

### Decode against the GPU and against the network

D021 retired codec work for *local read bandwidth* and set a reopening
condition (read > ~10% of an end-to-end pass). That still holds and this ticket
does not claim otherwise. The new motivation is different: **bytes at rest and
bytes over a network**, for distribution and for screening directly from object
storage.

* **10 GbE delivers 1.25 GB/s.** At today's LZ4 that is ~7.8 M conformers/s
  (shape) or ~7.5 M (color); at zstd-19 + shuf ~9.8 M and ~10.9 M.
* **Decoding that stream with zstd costs about 1.1 cores (shape) to 2.4 cores
  (color)** at the measured single-thread rates -- affordable, but not free.
* **The GPU consumes conformers at (pair rate) / (panel size).** A one-query
  color screen ran the kernel at ~31 M conformers/s (`results/T88` section 5.2, on an
  internal corpus), and the shipped producer ceiling is ~11 M/s
  (`doc/BENCHMARKING.md`, T85) -- **at small panels the producer is the wall
  already**, and decode is part of the producer. At large panels the kernel
  slows by the panel factor and both network and decode hide behind it. The
  break-even panel is roughly (current pair rate) / 10 M; this needs the current
  cloud-GPU pair rate from the paper runs to state as a number.
* **Decode is ~9% of producer CPU today** (D021: decode 3.2% against host prep
  33.1%). A ~4x slower decoder makes it ~30%, so at fixed threads the producer
  ceiling drops by roughly a quarter. The shipped producer runs three of its
  eight threads (`prefetch_depth=3`); 8x8 measured 1.96x. So the cost is
  recoverable by default tuning, but **it is a measurement this ticket must take,
  under the GPU lock, before zstd ships** (WP-4).

## Design

Each point is a design decision with its reason.

### 1. One file per group; the corpus is a directory of three kinds of file

```
corpus/
  corpus.json          descriptor: everything that changes what a score means
  molecules.parquet    per molecule: mol_id, ext_id, smiles, hac, mw, rotors
  build.json           provenance: sources, timings, host -- optional, never
                       fingerprinted, redacted before distribution
  groups/bNN_gNNNN.r3g one self-contained file per group
```

The group file replaces the `.rsb3` and all nine sidecars:

```
prologue   magic "RSB3", major version u32, header offset u64   (16 B)
sections   coordinate blocks      bit-packed (design point 7), hash per block
           molecule runs          (mol_id u64, n_conf u16, n_real u8) per molecule, raw
           features               per-molecule feature table (design point 3)
           vaa                    f32 [n_conf]                  raw
           color_self             f64 [n_conf]   (color corpora) raw
header     JSON at EOF: section table (offset, length, dtype, shape, sha256),
           block table, group fields, and the corpus semantic fingerprint
```

* Fixed-width sections stay **uncompressed and 64-byte aligned**, so they mmap
  exactly as the sidecars do today. Only coordinates are compressed.
* **The header carries the corpus fingerprint** (design point 2), so a group file
  separated from its directory still names what it is -- T115's deciding
  measurement.
* **Integrity is built in**: every block has a hash in the block table and every
  section a sha256 in the header, for `verify`, transfers and range reads
  (design point 11). This subsumes T208's
  separate `.vaa.blocks` / `.color_self.blocks` block indexes: the self-overlap
  values are now bound to their coordinates by living in the same file under one
  header, written once.
* Recomputing self-overlaps (T208's workflow) rewrites the group file, copying
  coordinate frames verbatim. That costs one file copy per group, which is the
  price of one file instead of ten.
* `ids.i64` goes: it is `molecules.parquet`'s `mol_id` column, sorted.

### 2. The descriptor, and the fingerprint that replaces version steps

`corpus.json` holds only what changes the meaning of a score, plus the group
table:

* `format`: major version, coordinate step, encoding name. **No flags**: one
  encoding (bit packing, design point 7), one layout (merged color), no `t`
  plane, no shuffle switch, no codec field. A future encoding is a new major version, not a header bit.
* `frame`: the conformer frame (heavy-atom centroid, principal axes), and the
  H policy (`RemoveAllHs`; features assigned before removal).
* `color` (absent on shape-only corpora):
  * the **full definition text** -- the `.fdef` file verbatim, or the SMARTS
    list for the custom generator -- plus which families were selected;
  * the **positioning rule** (weighted centroid; weights recorded);
  * the **type numbering** `{name: id}`;
  * the **interaction matrices** `r` and `p`, as values;
  * the **RDKit version** that perceived them.
* `prep`: the roshambo3 version and commit, and the input conventions
  (no protonation, no standardization, conformers as given).
* `groups`: index (the file name derives from it; no paths in the descriptor),
  bucket, `L`, `L_field_width`, `n_conf`, `n_mol`, sha256.

**The semantic fingerprint** is sha256 over a canonical serialization of
`format`, `frame`, `color` and `prep.conventions` (sorted keys, explicit
encoding, matrices hashed as pinned-dtype bytes). The reader:

* refuses a group whose fingerprint differs from its descriptor's;
* compares the corpus `color` section against the query's generator **by
  content** and refuses a mismatch naming the first difference (numbering,
  definition text, matrix, positioning rule). An RDKit version difference
  warns rather than refuses -- the definitions can be identical and still match
  differently, and that is a reproducibility note, not a numbering error;
* can **featurize a query from the corpus's own definition** -- the generator is
  built from the stored text rather than from whatever fdef the installed RDKit
  ships. That is the author's suggestion and it falls out of storing the text.

The version number then means one thing: the byte layout. Today's
`PERMUTED_COLOR_ORDER_VERSION`, `READABLE_VERSIONS`, `version_for` and the
manifest-or-version double guard all go.

### 3. Color features as atom indices, not coordinates

**Recommended, gated on a producer measurement.** The reconstruction itself is
verified (`results/T281/derive_h.py`, 81,000 features over 13,500 sampled
LIT-PCBA conformers): perceiving BaseFeatures on the stored H-stripped graph
with hydrogens re-added, **no feature references a hydrogen**, every feature
count matches, and the integer centroid of the stored int16 heavy-atom
coordinates reproduces the stored pseudo-atoms exactly in 91.2% of
(conformer, type) sets and within **one quantum (0.001 A)** in the rest --
Aromatic sets 49% inexact, the ionizables ~1.6%, single-atom types <= 0.2% (a
float32 intermediate in today's builder). Measured per set, not per feature. The builder already computes the per-molecule atom-index plan
(`pharmacophore.make_feature_plan`); this design stores it instead of
discarding it. Store each molecule's features once,
as `(type, atom indices)`, and derive the pseudo-atom positions per conformer
at load time from the decoded heavy-atom coordinates.

* **No SMARTS matching at screen time.** Perception runs once per molecule at
  build time, exactly as it does today, and its result -- the atom-index table --
  is what is stored. Loading a block does an integer gather and, for centroid
  features, a sum and a rounded divide: a few integer operations per feature,
  fused into the native decode that already writes the kernel layout. Queries
  are perceived once per query, as today.
* Feature perception depends only on the graph, so the table is per molecule;
  only positions are per conformer, and they are a function of the heavy atoms.
* 87% of features are a single atom, so the position *is* that atom's stored
  coordinate -- exact, no arithmetic. The rest (aromatic rings, carboxylates) are
  centroids; defined as **integer mean of the stored int16 coordinates, rounded
  half-away-from-zero**, they are exact and platform-independent.
* Gains: the payload loses the color slots -- **43% of occupied slots, 33% of all
  slots on LIT-PCBA** (382.6 M color pseudo-atoms against 514.3 M heavy atoms) --
  so ~40% fewer raw bytes to decode per conformer. Counts become per-molecule
  (derived from the run table and feature table; the producer builds the
  per-conformer count word the kernel reads). The corpus becomes literally "graph + definition + heavy
  coordinates", which is the self-describing claim.
* **With bit packing it is also a large disk gain**: a fixed-width packer cannot
  find the duplicated coordinates the way zstd-19's match finder did, so stored
  color would cost full width for the 43% of values that are pseudo-atoms.
  Deriving them removes those values from the payload entirely.
* Costs: **a declared numerics change** for centroid features (the centroid of
  quantized atoms differs from the quantized centroid by < 0.0005 A) -- under
  NUMERICS_POLICY this lands as a declared change, and it is exactly the case
  T270's oracle family exists for. And **producer work**: a gather plus a few
  adds per feature, on the stage that is the wall at small panels.
  *Amended 2026-10-17 (T283 review):* "< 0.0005 A" (half a step) disagreed with
  the measurement this design point cites. The bound is **at most one step**
  (measured: exact in 91.2% of sets, <= 1 quantum otherwise;
  `results/T281/derive_h.py`, output recorded in `results/T281/README.md`): each
  stored atom is within half a step of its prepared value, so their mean is too,
  and rounding the integer mean adds up to another half. The text above is kept
  as written; D034 item 4 carries the corrected bound.
* **Two widths.** The disk record becomes heavy-atom-only, padded to
  `L_heavy = pad(max n_real)`, while the kernel still takes the merged layout
  padded to `max(n_real + n_color)`. The group table records both `L_heavy` and
  the device width (and `L_field_width`, which is a property of the device
  layout and changes numerics), so the producer does not have to rederive them.
* Gate (WP-4): producer throughput and one-query end-to-end with derived color
  against stored color, under the GPU lock. If the producer loses more than a
  few percent after prefetch retuning, store coordinates as today and keep only
  the per-molecule feature table for self-description.

### 4. The molecule table replaces per-conformer ids

`(mol_id u64, n_conf u16, n_real u8)` per molecule in run order. There is no
stored per-conformer counts array: a conformer's count vector is derived from
its molecule's `n_real` and feature table, and the producer builds the device's
per-conformer count word. `mol_id` of a conformer
is a searchsorted over run starts; `conf_idx` is the offset within the run.

* On LIT-PCBA: 4.1 MB instead of 176 MB. Cost per conformer falls from 9 B to
  ~0.2 B, so **`mol_id` stays a full 64-bit id with no varint** -- the run table
  makes the width irrelevant, and it stays safe for any corpus size. (A varint
  would save ~4 bytes per *molecule* while making the table unseekable.)
* `n_conf` becomes u16: the 256-conformer cap that u8 `conf_idx` imposes
  (`build.py:94-95`) lifts to 65,535 for free.
* The device needs `mol_id` per conformer for molecule-level top-K; the producer
  expands runs per launch, as it already copies sidecars into pinned buffers.

### 5. Corpus order is a function of content

Define corpus order as **(bucket, `n_real`, `mol_id`, `conf_idx`)**, and the
global conformer id as the position in that order.

* Two builds of the same molecules -- any input order, any worker count, resumed
  or not -- produce identical files and identical gids.
* The ranking tie-break (ascending gid) becomes (n_real, mol_id, conf_idx)
  within a bucket, close to the `canonical_ids(mol_id, conf_idx)` tie-break the
  metrics already use (`metrics/ranking.py:47`).
* Merging two corpora is a merge-sort of runs, not a renumbering problem.
* Results that must outlive the corpus (`hits.json`, gold sets) key on
  `(mol_id, conf_idx)`; gid is a corpus-local index.
* This is a declared ranking change at the moment of the break -- ties resolve
  differently from today. That belongs with the other declared changes in WP-6.

### 6. Structures: the SMILES is the graph

Drop `structures.sqlite` (2.34 GB on LIT-PCBA) and make `molecules.parquet`'s
`smiles` column load-bearing:

* At build time, **reorder each molecule's heavy atoms into the canonical SMILES
  output order** (`_smilesAtomOutputOrder`), and store coordinates in that order.
  Then slot *i* is atom *i* of `Chem.MolFromSmiles(smiles)`, and the overlay
  needs nothing but the SMILES and the coordinates it already decodes.
* The SMILES is computed after `RemoveAllHs` (today's meta column uses
  `RemoveHs`, which keeps deuterium and can disagree with `n_real`), and
  validated at build time: parse, compare element by element against the stored
  slots.
* Stereo comes from 3D, as the overlay already does
  (`AssignStereochemistryFrom3D(replaceExistingTags=True)`); the SMILES is
  written without stereo or with the first conformer's, and either is harmless.
* **Per-conformer graph variants** that differ in more than stereo (protonation
  or charge states under one source id) are **refused at build**, naming the id
  and asking the user to give each state its own id (the author, 2026-10-17: unlikely
  in practice). Stereo-only differences are accepted and ignored.
* The SMILES also makes the color feature table checkable: re-perceiving
  features from the SMILES with the stored definition must reproduce it --
  **but only after `AddHs`**. Perceived on the H-stripped graph, BaseFeatures
  finds 13,183 of 13,500 sampled conformers' Hydrophobe sets wrong (its SMARTS
  depend on explicit hydrogens); with `AddHs` every set matches
  (`results/T281/derive.py` vs `derive_h.py`). The same rule binds "featurize
  the query from the corpus definition": the spec must state the H handling
  the definition is applied under, and the reader must apply it.
* What is lost: nothing the overlay uses. Explicit H positions were never
  stored; re-adding H with `AddHs(addCoords=True)` becomes an option.
* `web/structures.py`'s external index, `web/topology.py`, `format/topology.py`
  and `index-structures` go (~1,100 lines). Size: ~0 bytes beyond a column that
  exists already, against 170 B/conformer.

### 7. The coordinate encoding: fixed-width bit packing, no compressor

Design goal: **decode may not cost throughput at 1-8 queries**, where the GPU is
the expensive resource. zstd-19 did (`results/T281/producer/`: -15% end to end at one query
against LZ4 even after prefetch retuning; nothing at 32 queries). So the payload
carries **no general-purpose compressor**:

* **Frame-of-reference fixed-width bit packing** per (block, axis): an int16
  minimum and a bit width, then every *real* atom's `v - min` at that width.
  Padding slots are not stored. Values are in units of the grid step (design
  point 8), which is what makes the widths small.
* **Vertical SIMD layout (BP256-16)**: each axis stream is cut into groups of
  256 values held as 16 lanes x 16 positions in `w` 256-bit words, so 16 outputs
  unpack with one constant shift/or/mask. A scalar reference decoder is a few
  dozen lines; the layout maps onto AVX2, AVX-512 and NEON alike.
* Measured (`results/T281/bitpack/`, compiled, single thread, decode to the
  padded kernel layout, bucket-weighted, advisory):

  | | LZ4 today | zstd-19 + split | **bit packing** |
  |---|---|---|---|
  | D5 (PubChem), 0.005 A | 153 B, 13.9 ns | 98 B, 129 ns | **107 B, 11.2 ns** |

  Faster than LZ4 on D5; ~30% smaller than LZ4; 9% larger than zstd-19.
  Per-conformer widths would recover part of that gap (est. 105 B on D5) and
  are a WP-4 option, not the default.
* What this removes: codec choice, codec dependencies and versions, the byte
  split flag, decompression bombs (output size is a pure function of header
  counts), and the prefetch-retuning question.
* Object storage over 10 GbE (~10 M conformers/s at ~120 B) stays a large-panel
  option: one query consumes 25-30 M conformers/s.
* Distribution tarballs may still be zstd-compressed as a whole; that is
  transport, not format.

### 8. Quantize up front at 2^-8 A, stored in units of the step

The author, 2026-10-17: **quantize up front.** The int16 grid is the one geometry:
coordinates are quantized at build; self-overlaps (D033), color positions
(design point 3) and the snapped query (T208 item 9) are computed from the
quantized values; no float coordinate is stored or trusted.

**Chosen step: 2^-8 A = 0.00390625 A** (the author, 2026-10-17). The sweep
(`results/T281/quant-sweep/`, pre-registered, each arm rebuilt from source)
found 0.005 A the coarsest step passing all three deciding checks against a
half-quantum grid-phase control. 2^-8 lies between the passing 0.002 and 0.005
arms, costs ~3% more coordinate bytes than 0.005, and is **exactly
representable in float32**, so dequantizing an int16 is exact and T87's
round-trip precondition holds by construction. The sweep never changed the
device constants (its values stayed in 0.001 units), and the same constants also
drive `r3_quantize`, which re-quantizes the rotated query on rotating starts
(`backend/_cuda_src/kernels.cu:279-281`). T283 therefore runs one confirming
arm at 2^-8 with the device constants changed; if rotated-query staging at
2^-8 measurably hurts, the macro is split (library dequantization at 2^-8,
query staging keeps its own constant) and D034 records it.

*Outcome (T283, 2026-10-17):* no split. The premise above was wrong for the shipped
path: `r3_quantize` of a rotated query runs only in the analytic kernel's
`start_mode_transform`; the shipped `PoseSearch.FIELD` stages the query unrotated, so
shipped screens never re-quantize a rotated query, and on the analytic path the
re-quantization reproduced the permuted integers exactly at 2^-8. D034 item 8 keeps one
constant pair (`results/T283/REPORT.md`, "The rotated-query question";
`results/T283/PROTOCOL_ADDENDUM.md`; `results/T283/rotated_query_check.json`).

| step | heavy-atom bytes | shape recall@1000 vs 0.001 | DUDE-Z shape RBO | enrichment (12 targets x 2 modes) |
|---|---|---|---|---|
| control (0.001, shifted) | 1.00x | 0.9988 | 0.966 | unchanged |
| 0.002 | 0.92x | 0.9985 | 0.971 | unchanged |
| **0.005** | **0.83x** | **0.9973** | **0.968** | **unchanged** |
| 0.01 | 0.76x | 0.9947 | 0.938 (fails >= 0.950) | unchanged |

* Every coordinate within 0.0025 A of its prepared value; p99 score error on the
  top 1,000 is 4.8e-4, a quarter of D013's ~2e-3.
* **The int16 is stored in units of the step**, not 0.001 A: a coarse grid left
  in 0.001 units does not compress (0.995x). So the device's dequantization
  constant (`numerics.WIRE_QUANT_STEP`, `ROSHAMBO3_STAGE_INV_Q_XYZ`) becomes 2^-8
  -- a declared NUMERICS_POLICY change, with the self-overlaps and query snap
  moving with it. Range is no constraint (int16 at 2^-8 A covers +-128 A).
* **T150 is already done.** T87 put the corpus's int16 on the wire and the
  kernel dequantizes at the point of use (`engine/buffers.py`); D021's "host
  prep 33%" is stale. Today's 1-query wall is kernel 39%, H2D 23%, producer wait
  13%, launch path 15%; at 32 queries the kernel is 90%
  (`results/T281/producer/`). T150 closes into T87.

### 9. One unit of work for GPU launches and CPU workers

The format is already blocked: the GPU producer coalesces consecutive blocks
into launches, and CPU workers claim one block each (`engine.py:1590`). Format 3
makes the block self-sufficient:

* **The block table is the work list.** Each entry: first row, row count, byte
  range, a hash, and the molecule range `[m0, m1)`. Per-row sections slice by row
  range, the feature table by molecule range; no per-block metadata files, no
  coordinator pass that opens every reader.
* **Blocks never split a molecule**: boundaries fall on molecule boundaries, at
  most ~4,096 rows.
* **Block size stays ~4,096 rows** (`results/T281/cpublock/`, tachi, advisory --
  the host was not exclusive): no L2-footprint effect at any width
  (blocks up to 17 MB were no slower per worker); 512-2,048 rows lose 3-35% to
  Python per-block self-overlap binding, which serializes on the GIL at 56
  workers; 16,384 rows lose 11-28% of wall to tail imbalance. The byte-target
  idea is dropped. Re-measure 1,024-2,048 once the per-block path is native.
* **A corpus-wide block directory**, expensive-first for CPU schedulers (the
  tail-imbalance fix), in order for the GPU producer.
* **One native, GIL-released decode per block** for both paths: read, unpack,
  derive color, bind stored self-overlaps, write the caller's layout.
* `L_ALIGN` 8 vs 16 was not measured (needs builder changes); WP-4.

### 10. What deliberately does not change

* **Bucketing and padding to `L` in the kernel layout.** The disk payload is
  ragged (bit packing stores real atoms only); padding happens in the decode.
* **Self-overlaps in the corpus** (D033), and `color_self` at f64 (T208's
  precision contract). Whether the GPU reads them is design point 11.
* **Groups**: the 2 M-conformer cap is a builder parallelism and file-size knob.

### 11. Hostile files

Storing the color definition and featurizing queries from it moves the format
beyond array parsing. Threat model and measurements:
`results/T281/security/THREAT_MODEL.md`. What it puts into the design:

* **Nothing in a corpus is executed.** RDKit's fdef grammar has no include or
  file directive, so the definition text is a denial-of-service surface, not
  code execution -- but a real one: a 543-byte fdef took 26 s and 1.2 GB to
  build; a 165-byte pattern costs 13 s per query molecule; a 500 KB nested
  SMARTS took 29 s to reject.
* **A limits table and a pure-Python validator in the spec** (WP-2), run before
  native code sees a byte: `open` (header), `scan` (counts, widths, feature atom
  indices, strings), opt-in `deep` (full recompute). Duplicate JSON keys and NaN
  rejected; header sizes capped; the group table carries no file paths.
* **The native decoder is bounds-checked on its own**, validated or not: input
  length and output capacity passed in, every width (<= 16) and count checked,
  overflow-checked sizes, feature atom indices checked against `n_real`, a
  sanitizer CI build, and fuzzing. The prototype in `results/T281/bitpack/`
  shows why: an unchecked width byte indexes a 17-entry function table.
* **Definitions: shipped by hash, custom by explicit opt-in** (the author,
  2026-10-17). Hashes of BaseFeatures for each supported RDKit release ship with
  the tool; a corpus whose definition matches one is used with no prompt.
  Custom definitions are a supported feature but require an explicit runtime
  flag, whose message tells the user they must vet definitions beyond the RDKit
  defaults. Recommended shape: the flag names the definition's sha256
  (repeatable), so opting in to one definition does not trust every corpus; and
  the RDKit-free size/complexity limits plus a time and memory limit on
  perception stay on even when opted in, so a bad definition is a bounded
  failure rather than a hang.
* **Out of scope for hardening** (the author, 2026-10-17): corpora altered to give
  wrong answers without hanging or executing anything -- e.g. a forged, lowered
  stored self-overlap. Whether the GPU reads stored self-overlaps is therefore a
  performance choice only (recomputing them costs at most ~3.6% of a one-query
  screen and ~0.7% at 32 queries, `results/T281/producer/`). The web app is a
  local demonstration tool and is not intended for exposure on untrusted networks.
* **Integrity**: per-block hashes in the block table and group header hashes in
  `corpus.json`; this is also what makes object-storage range reads verifiable.
  **Signatures are deferred past release** (the author, 2026-10-17); the spec
  reserves a place for a detached signature file.
* **RDKit version**: recorded in `corpus.json`; a mismatch at screen time warns,
  it does not refuse (the author, 2026-10-17). Allow-list hashes cover each
  supported RDKit release.
* **Trust UX** (the author, 2026-10-17): a custom definition is refused with a
  summary (hash, families, what differs from the nearest default, size) and the
  commands to vet and trust it: `roshambo3 definitions show <corpus> [--diff]`
  (RDKit-free), `roshambo3 definitions trust <hash>` (per-user trust file),
  or `--trust-definition <hash>` for one run (repeatable; >= 12-hex prefix
  accepted if unambiguous). Building a corpus from your own definition needs
  no flag and prints its hash. Shape-only screens never need a definition.
* Format 3 drops the serialized RDKit `Mol` binaries in `structures.sqlite`
  from the load path. No Python pickle is in the load path.

## Work packages

Each becomes a ticket. WP-1 and WP-2 come first.

* **WP-1 -- Decisions recorded as D034**: the step (2^-8 A), bit
  packing, block size, the hardening defaults, with this ticket's measurements.
* **WP-2 -- `doc/FORMAT.md`, the spec**: byte layout (BP256-16 included),
  descriptor schema, fingerprint canonicalization, corpus order, versioning
  policy, **limits table and validator spec**, and a small conformance corpus
  (shape and color) with expected fingerprint and decoded arrays. Written before
  the code; the code is tested against it.
* **WP-3 -- Writer, reader, validator** (`format/`): group file, descriptor,
  fingerprint, molecule runs, bit packing with a bounds-checked native decoder
  -- **AVX2 and NEON kernels both required** (the author, 2026-10-17), plus the
  scalar reference -- and the three-tier validator. The unpack routine is
  selected by a checked switch, never by indexing a table with a file byte.
  Deletes the legacy read paths (~1,100 lines).
* **WP-4 -- Gating measurements**, GPU lock: native decode in the producer at 1
  and 8 queries against today's LZ4 path; derived vs stored color; per-block vs
  per-conformer widths; `L_ALIGN` 8 vs 16; CPU block size 1,024-4,096 once the
  per-block path is native; an object-storage range-read screen on one cloud
  host.
* **WP-5 -- Builder** (`prep/`): content order, SMILES-order atoms, variant
  refusal, molecule-aligned blocks, feature table, definition capture,
  provenance into `build.json`. Folds in T273, T274, T275.
* **WP-6 -- Engine and web app**: one native GIL-released block decode for both
  paths, step constant 2^-8, molecule-run expansion, derived color, native
  self-overlap binding, expensive-first CPU scheduling; overlay from SMILES +
  coordinates; results keyed on `(mol_id, conf_idx)`. The web app remains a local demonstration tool. Declared changes (step, tie order, centroid features)
  handled under NUMERICS_POLICY, with T270 if landed.
* **WP-7 -- Delete the legacy**: `prep/convert.py`, the legacy self-overlap
  route, `format/topology.py`, `web/topology.py`, the external structure index.
* **WP-8 -- Definitions**: the allow-list of shipped definition hashes, the
  RDKit-free limit checker, time/memory-limited perception, and the opt-in flag
  for custom definitions with its vetting warning.
* **WP-9 -- Fuzzing and sanitizers**: libFuzzer/atheris over validator and
  decoder, seeded from the conformance corpus; ASan/UBSan CI build.
* **WP-10 -- Rebuild every corpus from source** and re-run the paper's numbers on
  the rebuilds; old corpora read-only until then.

Tickets this absorbs or changes: **T115** (superseded by design point 2),
**T273, T274, T275** (WP-5), **T143** (answered: quantize up front at the
measured step), **T150** (already delivered by T87; close), **T208** remainder
(the 3CR build waits for format 3), **T278** (convention stands).

## Dependencies

WP-2 (spec) precedes WP-3 (writer, reader, validator and decoder, alongside
WP-4); WP-5 (builder) follows, then WP-6 (engine and web app, alongside WP-7),
then WP-10. WP-8 and WP-9 are independent of that chain. The paper's
benchmarks, and the corpus built from the LIT-PCBA source files on 2026-10-16,
are format 2, so WP-10 includes re-running the paper's numbers on the rebuilt
corpora, with the declared changes accounted for.

## Decisions (the author, 2026-10-17)

1. Derived color: accepted. Perception stays at build time (design point 3).
2. Corpus order by content: accepted, with the one-time change in tie order.
3. Charge/protonation variants under one id: refused at build.
4. Variant `mol_id`: moot given 3; T278's convention stands.
5. Quantize up front; settle the step now (design point 8). (T150 turned out
   to be delivered already by T87.)
6. Every repository takes the format break.
7. zstd level 19 by default -- superseded the same day: a 15% one-query loss
   is not acceptable when the GPU is the expensive resource and 1-8 queries is
   the common case; bit packing instead (design point 7).
8. Parquet for the molecule table.
9. The format must suit CPU independent workers as well as the GPU producer
   (design point 9).
10. Bit packing (design point 7), with AVX2 and NEON kernels.
11. Custom color definitions: supported, behind an explicit runtime opt-in that
    warns the user to vet them; shipped RDKit definitions need no opt-in.
12. Hardening covers hangs, resource exhaustion and code execution, not corpora
    altered to give wrong answers. The web app is a local demonstration tool and is not intended for exposure on untrusted networks.

## Decisions added in planning (the author, 2026-10-17)

13. Step 2^-8 A (exact float32 dequantization), confirmed by one T283 arm.
14. Signatures deferred past release; spec reserves room.
15. RDKit version recorded; mismatch warns.
16. Custom definitions trusted by hash (UX above).
17. **T270 (oracle numerics test family) is a prerequisite.** Its practical
    regression delivery (items 1-4 and qualified real-molecule CUDA/CPU
    end-to-end checks) gates T296; native Apple/Metal validation is a manual
    follow-up for T300. Visible coverage reporting accompanies both gates.
    T282-T290 are additive, change no numerics and do not wait on T270
    (approved by the author on 2026-10-17); T291-T302 do. T270's regression
    delivery was approved by the author on 2026-10-18: it satisfies the CPU/CUDA
    prerequisite and does not claim native Apple validation or universal
    numerical certification.

## Implementation tickets

The work packages above are specified as tickets T282-T302 (see each file and
`tickets/INDEX.md`): T282 bookkeeping and test-migration matrix; T283 D034; T284
spec, reference codec and conformance corpus; T285 native codec; T286 Python
writer/reader/validator; T287 descriptor and fingerprint; T288 definitions and
trust; T289 fuzzing, sanitizers, aarch64 CI; T290 gating measurements; T291-T293
builder; T294-T297 engine, CPU workers, step constants, results; T298 the switch;
T299 test fixtures and attribution corpora; T302 the remaining rebuilds; T300
paper re-verification; T301 release ports. Order on the
integration branch (`ticket/T281-format3-switch`, created by T282): T296 (step
constants) lands first, before T291, T294 and T295.

## Open questions

None. Running the `deep` validator tier on release tarballs is part of
T299/T301 by default.

## Traps

* **Pitfall 22**: never convert in place, never into a worktree. Rebuilds write
  new directories; old corpora stay read-only until retired.
* **A fingerprint over an unsorted dict or a float repr is noise.** Canonicalize;
  hash pinned-dtype bytes; test the digest across processes and machines.
* **The failure mode is silence.** Every acceptance test for the descriptor is a
  refusal: wrong numbering, wrong definition text, wrong matrix, separated group
  file, truncated section, flipped byte in a frame.
* **Do not quote the codec throughputs above as decision numbers.** They were
  taken unlocked under host contention. WP-4 takes the real ones.
* **The paper's numbers were measured on the old format.** The rebuild must
  reproduce them within the declared changes, and that comparison is part of
  WP-10's acceptance, not an afterthought.
