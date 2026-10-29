# D034 — Corpus format 3: one hard break before release, at 2^-8 A, bit-packed, self-describing

**Date:** 2026-10-17 (revised 2026-10-18, 2026-10-20, 2026-10-21, 2026-10-22)
**Status:** accepted (the author, 2026-10-18)
**Source:** T281 (design, measurements, the author's decisions of 2026-10-17 and 2026-10-18); T283 (the 2^-8 step check, `results/T283/`); T284 (`doc/FORMAT.md`)
**Constrains:** every format-3 ticket (T284-T303); `numerics.WIRE_QUANT_STEP`, `rsb3.COORD_SCALE` and the device stage macros `ROSHAMBO3_STAGE_Q_XYZ` / `ROSHAMBO3_STAGE_INV_Q_XYZ`; the corpus builder (`prep/`), readers (`format/`, `engine/source.py`), the CPU worker route and the web app's structure overlay; any ticket that proposes a codec, a corpus layout, a coordinate step, a corpus order, a hydrogen convention or a definition-trust policy

This record states what is settled about the release corpus format ("format 3"),
the evidence for each decision, and when to reopen it. The byte-level
specification is `doc/FORMAT.md`; the design discussion is
`tickets/T281-corpus-format-3.md`. Where this record and the spec disagree, fix
the spec.

**Relation to standing decisions.** D021 (local reads are not the bottleneck)
stands: format 3 is motivated by bytes at rest and over a network, by
self-description and by a clean break before release, not by local read
bandwidth. D033 stands: self-overlaps stay in the corpus and must describe the
scored (quantized) coordinates; item 8 makes that true by construction. D013 is
the acceptance criterion for every declared numerics change below.

**Terms.** A *conformer row* is one conformer of one molecule. *Real atoms* are
a molecule's heavy (non-hydrogen) atoms; `n_real` is their count. A *color
feature* (pharmacophore feature: donor, acceptor, ring, hydrophobe, ...) is
placed at a *pseudo-atom*: one position per feature per conformer. A *slot* is
one atom position in a conformer row of the kernel layout: real atoms first,
then pseudo-atoms, then zero padding up to the bucket width `L`.

## Decision

**1. Hard compatibility break; nothing old stays readable.** At release no
earlier corpus format is readable, today's included. Every legacy read path,
`prep/convert.py`, the version-3 refusal trick and the manifest-or-version
double guard are deleted, and every corpus is rebuilt from source (T298, T302).
*Evidence:* `results/T281/inventory.md` -- ten files per group; two sidecars that
duplicate a third (`.n_real.u8`, `.n_color_by_type.u8`, 137 MB on LIT-PCBA, kept
only for pre-T86 readers); a structures store of 2.34 GB beside 4.55 GB of
coordinates; color definitions recorded only as an absolute venv path.

**2. A corpus is a descriptor, a molecule table and one file per group; a
fingerprint replaces version steps.** The files are `corpus.json` (the
descriptor: everything that changes what a score means, plus the group table),
`molecules.parquet`, `build.json` (provenance; never fingerprinted, never
distributed) and one self-contained `groups/bNN_gNNNN.r3g` per group. The
descriptor records the full color definition text, the positioning rule, the
type numbering, the interaction matrices as values, the step and the RDKit
version. **The semantic fingerprint** -- sha256 over a canonical serialization
of the descriptor's `format`, `frame`, `color` and `prep.conventions` -- replaces
`PERMUTED_COLOR_ORDER_VERSION`, `READABLE_VERSIONS` and `version_for`; the major
version number covers the byte layout only. A reader refuses a group whose
fingerprint differs from its descriptor's, and compares the corpus `color`
section with the query's generator **by content**, refusing a mismatch and
naming the first difference. A query can be featurized from the corpus's own
definition text. **The group table carries no file paths**: a group file's name
is derived from its index. *Evidence:* policy (T281 design points 1-2), closing
the format-2 reader's trust in manifest paths; supersedes T115.

**3. Hydrogens: shape uses heavy atoms only; color perception sees the
hydrogens.** Two conventions, each fixed by the spec:

* **Shape points and atom order: heavy atoms only, `Chem.RemoveAllHs`**
  (`prep/conformer.py::strip_hydrogens`). Every hydrogen is removed, isotopic
  ones included -- `Chem.RemoveHs` keeps isotopically labelled hydrogens, which
  the kernel would then score as carbon (T127). The stored coordinates,
  `n_real`, the canonical SMILES and the atom order (item 6) are all of this
  hydrogen-free molecule.
* **Color perception: on the molecule with explicit hydrogens.** Every
  perception -- at build, the `deep` validator re-checking the stored feature
  table, and a query featurized from the corpus's definition -- runs on
  `Chem.AddHs(Chem.MolFromSmiles(stored SMILES))` (CXSMILES disabled): the
  hydrogen-free graph item 6 stores, hydrogens added. At build this happens
  once per molecule, after item 6's SMILES round-trip check has passed, so
  build and verify agree by construction and library and query perceive
  under one aromaticity model whatever model the input carried (amended
  2026-10-22, below). Hydrogens only affect *which* features match;
  positions come from heavy atoms alone, so a feature that would reference a
  hydrogen is refused at build (none does under BaseFeatures).
  *Why:* RDKit's BaseFeatures Hydrophobe patterns test explicit connectivity --
  `ThreeWayAttach [D3,D4;...]`, `ChainTwoWayAttach [R0;D2;...]` -- and `D` counts
  explicit hydrogen atoms. On the hydrogen-free graph a methyl carbon has `D1`
  instead of `D4` and stops matching. *Evidence:* re-perceiving 13,500 sampled
  LIT-PCBA conformers on the hydrogen-free graph gave a different Hydrophobe
  count from the stored one for 13,183 of them, while every other feature type
  matched; with `AddHs` first, every count matched (`results/T281/derive.py`,
  `derive_h.py`, output in `results/T281/README.md`). T58 measured the same
  effect at build: perceiving after hydrogen removal loses a mean of 7.0
  Hydrophobe features per molecule.
  *Amended 2026-10-22 (the author, option A; T314):* build perceived on the
  input molecule as read, with its hydrogens, so the stored feature table could
  depend on how the input was encoded (an input that is not re-sanitized at
  read keeps the aromaticity model it was written with). One internal corpus
  failed `deep` with `layout.features` for this reason, while a survey of
  LIT-PCBA (407,664), all 43 DUD-Z targets and an internal analog corpus
  found 0. Build now perceives on the stored SMILES as above, and
  the round-trip check compares radical electrons as well. No coordinate
  passes through the SMILES; SDF-built corpora are byte-identical
  (`results/T314/`); `prep.conventions` and the fingerprint are unchanged.

**4. Color positions are derived at load from a per-molecule feature table.**
Each molecule stores its features once, as `(type, heavy-atom indices)`.
Perception (SMARTS matching) runs only at build, or once per query as today.
For each conformer, a feature's pseudo-atom position is derived from the
decoded int16 heavy-atom coordinates: a single-atom feature (87% of them) takes
that atom's coordinate exactly; a multi-atom feature (aromatic ring,
carboxylate, ...) takes the **integer mean of its atoms' int16 coordinates,
rounded half away from zero**, with equal weights (a selected family's blocks
must declare `Weights` of all 1.0; anything else is refused at build). Within a molecule, features are
stored sorted by `(type, atom tuple)` with atoms ascending, so the table is a
pure function of the graph and the definition, independent of the order in
which RDKit enumerates matches.
*Why:* pseudo-atoms are 43% of the occupied slots on LIT-PCBA (382.6 M
pseudo-atoms against 514.3 M heavy atoms; 33% of all slots counting padding).
A fixed-width packer (item 7) cannot exploit their redundancy, so storing them
would cost full width; deriving them removes them from the file.
*Evidence:* over the 13,500 LIT-PCBA conformers of item 3, the derived positions
reproduce the stored pseudo-atoms exactly for 91.2% of (conformer, type) sets
and within one quantum in the rest (`results/T281/README.md`).
*Declared numerics changes (T298; NUMERICS_POLICY 4g, to be written):*
(a) a multi-atom feature's position moves by at most one step -- each stored
atom is within half a step of its prepared value, so their mean is too, and the
integer rounding adds at most another half; (b) the within-type sort changes
the order in which color terms are accumulated. T298 attributes the two
separately.
*Settled on whole-system cost (the author, 2026-10-20): derived color is the release
layout; stored pseudo-atom coordinates are not an option.* T290's isolated
producer test ran derived color at 0.60x the stored producer, failing the
original 3% producer gate, but the producer is not the bottleneck: on a matched
1,200,435-conformer workload, derived/stored end-to-end throughput was 0.999
(GPU, 1 query), 0.988 (GPU, 8 queries), 0.998 (CPU shape) and 0.998 (CPU
combo), with identical outputs (`results/wave1/ACCEPTANCE.md`,
`results/T290/`). GPU clocks were unlocked and the CPU arms had five repeats,
not eleven; these are accepted screening measurements, not a formal gate
certification.

**5. Molecules are a run table; per-conformer counts are not stored.** Per
molecule, in corpus order: `(mol_id u64, n_conf u16, n_real u8)`. A conformer's
`mol_id` is found by binary search over run starts and its `conf_idx` is its
offset in the run. Per-conformer counts are derived from the run table and the
feature table; the producer builds the kernel's per-conformer count word.
A molecule has at most 255 heavy atoms and at most **4,096 conformers**
(today's cap is 256).
*Evidence:* 4.1 MB instead of 176 MB on LIT-PCBA (about 0.2 B per conformer
against 9 B), so `mol_id` stays a plain u64 with no varint.

**6. The SMILES is the graph; the structures store is dropped; variants under
one id are refused.** Heavy atoms are stored in the output order of the
canonical, non-isomeric SMILES of the hydrogen-free molecule, so slot *i* is
atom *i* of `MolFromSmiles(smiles)`; the builder checks element, charge,
hydrogen count, radical electrons (since 2026-10-22, T314) and bonds slot by
slot, and perceives color features on that parsed molecule (item 3). Being non-isomeric, the SMILES also
carries no isotope labels: a molecule with isotopically labelled heavy atoms
(e.g. 13C) is stored with its unlabelled graph. Scoring and features ignore
isotopes and `mol_id` comes from the name, so this changes no score or
identity. Stereochemistry lives in the 3D coordinates, as the web overlay
already uses it. Conformers sharing an id whose graphs differ in more than
stereo (charge or protonation states, tautomers, heavy-isotope labels,
fragments) are **refused at build**, naming the id; stereo-only differences,
aromatic vs Kekule forms and deuterium vs protium are accepted (T291's census:
0 refusals in LIT-PCBA's 407,664 and DUD-Z's 133,403 molecules). T278's `mol_id` convention stands.
A molecule whose SMILES fails the slot check (RDKit can write a canonical
SMILES it cannot parse, such as PubChem 12157944's `Cn1ccn(C)[si+]1C`) is
rejected by the builder and recorded in `build.json`'s rejected list rather
than refusing the build (the author, 2026-10-21).
*Declared numerics change (T298, attributed with item 12's):* atoms are
reordered into SMILES order *before* the conformer is prepared, so the
centroid and covariance that align the prepared frame are summed in a new
order; a prepared coordinate can therefore differ at float32 rounding level,
and occasionally quantize one step differently. Reordering first keeps the
prepared frame a function of content alone, up to a graph automorphism:
symmetry-equivalent atoms supplied in another order may occupy each other's
slots. T291 measured 0 of 497,745 stored int16 values changed by the reorder
on one input set (not a bound).
*Evidence:* `structures.sqlite` is 2.34 GB on LIT-PCBA and used only by the web
overlay, which discards its stereo (`web/chemistry.py:10-24`); on PUR2, 57 of
811 molecules had two stored graphs that differed only in stereo.

**7. Coordinates are bit-packed (BP256-16); no general-purpose compressor.**
Per block and axis, frame-of-reference fixed-width packing of the real atoms
only (padding is not stored), in units of the step (item 8), in the vertical
BP256-16 layout (groups of 256 values as 16 lanes x 16 positions). AVX2 and NEON
unpack kernels and a scalar reference are all required and must agree bit for
bit. The decoded size is a function of header counts alone, so there is no
decompression bomb. Whole-file compression of distribution tarballs is
transport, not format.
*Evidence:* `results/T281/bitpack/README.md` (advisory; single thread, decode to
the padded kernel layout; at 0.005 A): D5 107 B and 11.2 ns per conformer,
against LZ4 153 B / 13.9 ns and zstd-19 98 B / 129 ns; an internal
large-molecule set 19.6 ns against 16.9 ns and 175 ns. The native
codec (T285) decodes D5 in 7.55 ns and the internal large-molecule set in 13.15 ns per conformer
(`results/T285/bench.json`). zstd-19 was first chosen and then rejected: about
15% slower end to end at one query even after prefetch retuning, and no faster
at 32 queries (`results/T281/producer/REPORT.md`), when the GPU is the
expensive resource and 1-8 queries is the common case.

**8. The coordinate step is 2^-8 A (0.00390625 A); coordinates are stored as
int16 in units of the step.** Coordinates are quantized once, at build, and
everything downstream -- self-overlaps (D033), derived color positions (item
4), the snapped query -- is computed from the quantized values; no float
coordinate is stored. Rounding is `np.rint` (half to even). The representable
range is exactly [-128, +127.99609375] A; a coordinate outside it is refused at
build, never clipped. One pair of device constants serves every site:
`ROSHAMBO3_STAGE_Q_XYZ = 256.0f` and `ROSHAMBO3_STAGE_INV_Q_XYZ = 0.00390625f`,
matching `numerics.WIRE_QUANT_STEP` and the descriptor's
`format.step_log2 = -8`. Dequantization stays `cscale * (INV_Q * (float)v)`,
two roundings, never folded (NUMERICS_POLICY 4c). The round trip int16 ->
float -> int16 is exact because both constants are powers of two.
*Evidence:* the T281 sweep (`results/T281/quant-sweep/`, pre-registered): 0.005
A is the coarsest step passing R1-R3, and 0.01 A fails R3. T283
(`results/T283/REPORT.md`; GPU lock held, decision grade), with the device
constants actually changed to 2^-8: passes R1, R2 and R3 -- PubChem shape
recall@1000 0.9979 against 0.9988 at 0.001 A (paired difference -0.0009, 95% CI
[-0.0012, -0.0006]); DUDE-Z enrichment no worse in all six (mode, metric)
cells; DUDE-Z ranking agreement 0.969 (shape) and 0.974 (combo); a repeat run is
byte-identical; the round trip has 0 mismatches over all 65,536 int16 values.
**One constant pair suffices** because the only place a query is re-quantized
after rotation is the analytic pose search, whose start rotations are signed
permutations; rotating an on-grid query by them reproduces its integers
exactly (float32 rotation error under 5e-5 A against a half-step of 0.00195 A;
all 27,636 checked values exact, `results/T283/rotated_query_check.json`). The
shipped FIELD search never re-quantizes the query, so R1-R3 above did not
exercise this path; T296 measures the analytic path's screen-level effect.
*Accepted (the author, 2026-10-20):* T296 implemented the step and passes FIELD
R1/R2/R3 and ANALYTIC R2/R3 (`results/T296/analytic/analysis.json`;
ANALYTIC R1 omitted by decision). The step is accepted on that screening recall
and enrichment evidence, with T296's fixture-level diagnostic failures retained
on record: at 2^-8 the prepared-fixture qualifier establishes basin separation
for 2 of 12 cases (failure to establish separation, not an observed wrong
basin), and off-grid comparisons that mix query representations are T305's.
This does not certify every pose basin or waive pinned arithmetic.
*Declared numerics change:* NUMERICS_POLICY 4e, written by T296, which lists
every site the constants touch.

**9. Blocks are molecule-aligned and hold at most 4,096 rows; the block table
is the work list.** A block never splits a molecule. Because a molecule has at
most 4,096 conformers (item 5), every block -- one molecule or many -- has at
most 4,096 rows, and decodes to at most 4,096 x 512 x 6 B = 12.6 MB in the
device layout. Each block-table entry gives the first row, row count, byte
range, a hash and the molecule range. A corpus-wide block directory is ordered
most-expensive-first for CPU schedulers and in file order for the GPU producer;
one native decode per block, releasing the GIL, serves both.
*Evidence:* `results/T281/cpublock/REPORT.md` (tachi, advisory): no cache-size
effect for blocks up to 17 MB; 512-2,048 rows lose 3-35% to per-block Python
overhead; 16,384 rows lose 11-28% to tail imbalance.

**10. Hardening: be careful with custom definitions; do not attempt a full
hardening.** Custom color definitions make corpus files carry text that RDKit
will parse, which is a new risk. The required protections are:
(a) **memory safety** of native code reading corpus bytes -- a bounds-checked
decoder that does not rely on the validator having run (T285);
(b) **no process crash** on a malformed file: it is refused with an error;
(c) **custom definitions isolated**: shipped RDKit definitions are recognized by
hash and need nothing; any other definition needs an explicit opt-in by hash
(`--trust-definition <sha256>`, `roshambo3 definitions trust/show`), passes an
RDKit-free pre-pass, and is perceived in a time- and memory-limited subprocess
(T288).
**Best-effort:** time and memory bounds on other inputs. The limits in
`doc/FORMAT.md` section 14 are engineering targets; a malformed file that makes
a run slow or fail is acceptable. Fuzzing is a sanitizer CI job and a short
smoke run (T289).
**Out of scope:** files altered only to give wrong answers (e.g. a forged
self-overlap); forgery of the local scan cache; the web app, a local demonstration tool not intended for exposure on untrusted
networks. **Signatures are deferred past release**; the format reserves a place
for a detached signature. **The RDKit version is recorded**; a mismatch at
screen time warns and does not refuse.
*Evidence:* `results/T281/security/THREAT_MODEL.md` -- a 543-byte definition
took 26 s and 1.2 GB to build, and a 165-byte pattern cost 13 s per query
molecule; RDKit's definition grammar has no include directive, so definition
text is a denial-of-service risk, not a code-execution one.

**11. The molecule table is Parquet, zstd-compressed.** `molecules.parquet`
holds `mol_id`, `ext_id`, `smiles`, `hac`, `mw`, `rotors`; `ids.i64` goes. It is
written with zstd compression, `PLAIN`-encoded, non-null, in row groups of at
most 2^14 rows; readers accept zstd or uncompressed. Screening never reads it
(only hit resolution and `verify` do), so its cost is bytes at rest, and SMILES
in large libraries often share long substrings that compress well. A
compression bomb is out of scope (item 10); the declared-size checks of the
page walk stay as best-effort bounds. The zstd level is chosen by T303 from a
size and read-time measurement. (the author, 2026-10-18; this replaces an earlier
uncompressed-only rule made to avoid decompression bombs.)

**12. Corpus order is by content.** Rows are ordered `(bucket, n_real, mol_id,
conf_idx)`, and a conformer's global id (gid) is its position. Two builds of
the same records -- in any molecule order, with any worker count, or resumed --
produce identical files. Conformer order within a molecule is not normalized:
`conf_idx` follows the source's conformer order, so reordering one molecule's
conformer records changes the files. Results that outlive a corpus (`hits.json`, gold sets) key on
`(mol_id, conf_idx)`; gid is corpus-local.
*Evidence:* today's order within a bucket is `n_real`, then worker slot, then
shard append order (`build.py:14-17, 733-753`) -- a function of scheduling.
*Declared numerics change (T298; NUMERICS_POLICY 4f, to be written):* the device
breaks score ties by ascending gid, so tied conformers change order once.

**13. Unchanged by format 3.** Bucketing and padding to `L` in the kernel layout
(the file is ragged; padding happens at decode); self-overlaps stored in the
corpus (D033), `color_self` as f64 and present only for canonical interaction
matrices -- identity `p` and unit diagonal `r` on the color types, off-diagonal
`r` ignored because its `p` is 0 (the author, 2026-10-21; FORMAT.md section 10.2.1); groups capped at 2M conformers; the int16 coordinate already sent to
the device (T87; T150 closed into it).

**14. Delivery.** Implemented in this repository first, then ported to
the tool release and the paper release (T301). The paper's numbers, measured on format
2, are re-run on rebuilt corpora with each declared change attributed (T300).
T270 (the oracle numerics test family, built outside this work) items 1-3 gate
the step change (T296); its Metal arms and items 4-5 gate the paper
re-verification (T300). T282-T290 and T303 add code without changing numerics
and are not gated.

## Open

* Whether `verify --tier deep` runs on our release tarballs by default (owned by
  T301; the author may decline).

## Reopen if

1. **Hard break:** someone outside the project holds format-2 corpora that
   cannot be rebuilt from source before release and must stay readable.
2. **Descriptor:** the canonical serialization cannot be made byte-stable across
   processes and machines (T287), or a consumer needs to locate a group file
   other than by its index.
3. **Hydrogens:** a supported definition produces a feature on a hydrogen, or a
   definition's matches depend on hydrogens in a way `AddHs` does not reproduce.
4. **Derived color:** a measured deployment shows derived color costing more
   than 3% end-to-end throughput at 1-8 queries (whole-system, not the isolated
   producer).
5. **Run table:** a real use needs more than 4,096 conformers of one molecule or
   more than 255 heavy atoms.
6. **Variants:** a real corpus refuses a non-negligible share of molecules as
   charge or protonation variants, or the element-by-element SMILES check fails
   on real inputs.
7. **Bit packing:** native decode costs throughput at 1-8 queries against
   format-2 LZ4 (T290), or a deployment target has neither AVX2 nor NEON.
8. **Step:** R1, R2 or R3 fails at 2^-8 on a later panel, including T296's
   analytic-mode run; a real coordinate falls outside the int16 range; or a
   start set that is not a signed permutation ships, or the analytic pose search
   becomes the default -- then measure separate query and library constants.
   (The analytic search is reachable today: `screen --analytic`, a bare `--color`
   without `--mode`, and the FIELD path's refusal of non-canonical matrices.)
9. **Blocks:** a measured GPU end-to-end throughput gain from a different
   block size, or a CPU gain large enough to matter in practice (not a
   within-noise difference). `block_rows` is a builder default, not a format
   property -- readers take any block table of 1-4,096-row blocks -- so changing
   it is a rebuild, never a format change. (A dedicated CPU block-size campaign,
   T307, was dropped on 2026-10-21 for this reason: the per-block path is
   native, so the expected CPU effect is small, and the format is tuned for the
   GPU, where smaller blocks only add per-block overhead.)
10. **Hardening:** slow or failed runs on malformed files prove to matter in
    practice; the web app needs to be exposed on untrusted networks; corpora come from
    parties we do not trust, so wrong-answer files enter scope (then signatures
    and a GPU-side self-overlap check return, D033 item 4); or RDKit's definition
    grammar gains an include directive.
11. **Parquet:** the release tool cannot carry the `pyarrow` dependency.
12. **Corpus order:** T298 measures the tie-order change moving results more than
    D013 accepts, or the content sort becomes a material share of build time.
13. **zstd:** a deployment is large-panel or network-bound only, so the producer
    is off the critical path and bytes at rest dominate -- then a second encoding
    is a new major version, not a flag.

## Traceability to T281's decisions

| T281 decision (`tickets/T281-corpus-format-3.md`) | Item |
|---|---|
| 1 derived color, perception at build | 4 |
| 2 corpus order by content | 12 |
| 3, 4 variants refused; variant `mol_id` moot | 6 |
| 5, 13 quantize up front; step 2^-8 | 8 |
| 6 internal first, then port | 14 |
| 7 zstd-19 (superseded) | 7 |
| 8 Parquet | 11 |
| 9 suits CPU workers and the GPU producer | 9 |
| 10 bit packing, AVX2 and NEON | 7 |
| 11, 12, 14, 15, 16 custom definitions, hardening scope, signatures, RDKit version, trust by hash | 10 |
| 17 T270 gate | 14 |
| the author, 2026-10-18: 4,096 conformers per molecule | 5, 9 |
| the author, 2026-10-18: hardening narrowed | 10 |
| the author, 2026-10-18: equal atom weights only | 4 |
| the author, 2026-10-18: compress `molecules.parquet` | 11 |
| the author, 2026-10-20: derived color settled on whole-system cost; step accepted on screening evidence | 4, 8 |
| the author, 2026-10-21: canonical matrices judged on scoring entries; `Weights` required; unparseable SMARTS refused | 4, 13 |
| the author, 2026-10-21: a molecule whose SMILES does not round-trip is rejected per molecule, not refused for the build | 6 |
| the author, 2026-10-22: build perceives on the stored SMILES (option A); radical electrons in the round-trip check | 3, 6 |
