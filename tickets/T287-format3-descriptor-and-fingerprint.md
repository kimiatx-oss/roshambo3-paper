---
id: T287
title: Format 3 descriptor and semantic fingerprint -- name the color definition by content, refuse a mismatch by name
phase: 3
lane: data
status: closed
model: luna
reviewer: sol
depends_on: [T284, T286]
priority: high
branch: ticket/T287-format3-descriptor-and-fingerprint
worktree: <worktree>
artifacts: results/T287/
---

## Context

**Gate.** None outstanding. T284 (spec, reference) and T286 (writer, reader,
validator) are closed, as is T303 (their fix round). The ticket is additive
(new module and methods; no change to main's numerics or to any existing call
site), so T270 never gated it.

**Sources of truth.** `doc/FORMAT.md` sections 10.1-10.5 (as T303 left it on
main at 8869694d) define the descriptor schema, the definition hash and the
fingerprint; `decisions/D034-corpus-format-3.md` items 2, 3, 4 and 10 decide
them. Where this ticket and either disagree, they win; report the
disagreement to the author rather than editing them.

A color corpus and a query can agree on every array shape and still disagree
on what the color type numbers mean: the canonical interaction matrix is
diagonal, so a permuted numbering scores hydrophobes against donors and gives
plausible wrong Tanimotos. On format 2 the only guards are a manifest check of
the `{name: id}` mapping (`Corpus.require_color_features_enum`,
`format/dataset.py:655`) and an rsb3 version step; the definitions themselves
are recorded only as an absolute venv path (`results/T281/inventory.md`,
"Provenance recorded today"). Format 3's `corpus.json` carries the full
definition text, the type list (numbering and selection at once), the
positioning rule, the interaction matrices as values and the RDKit version,
plus a semantic fingerprint over them (D034 item 2).

**What already exists on main** (all paths under `src/roshambo3/format/r3g/`):

| Piece | Where | This ticket |
|---|---|---|
| Fingerprint (section 10.5) | `reference.fingerprint(descriptor)` | reuse; do not reimplement |
| Definition hash (10.3) | `reference.definition_hash`, `reference.normalize_definition` | reuse |
| Canonical JSON (10.5.1) | `reference.canonical_json`; strict parse/serialize in `jsonstrict.loads` / `jsonstrict.dumps` | reuse |
| `color` object builder | `reference.color_descriptor(generator=, definition=, types=, r=, p=, rdkit_version=)` | reuse |
| Closed-schema parse of `corpus.json` | `validate.read_descriptor(root)` -> `validate.Descriptor` (`data`, `fingerprint`, `sha256`, `path`); `validate._check_color` | reuse |
| Group binding: a group whose header fingerprint differs from `corpus.json`'s is refused | `validate._open_group_file`, code `integrity.fingerprint`; seed `tests/data/format3/adversarial/fingerprint_mismatch/` | **verify only** |
| Fingerprint byte-stable across processes | `tests/test_format3_reference.py::test_fingerprint_is_identical_in_a_separate_process`, run by CI's `cpu` (ubuntu x86) and `cpu-macos` (macos-15 arm64) jobs | **verify only** |
| Hook for this ticket's module | `validate.corpus_fingerprint` imports `fingerprint` from **`roshambo3.format.r3g.descriptor`** if that module exists, else uses the reference's | the module name is fixed by this hook |

What is missing, and is this ticket's work: the descriptor module that the
hook names, the query-side `color` object (`descriptor_color()` on the
generator classes), the content comparison that refuses a mismatch by name,
and a generator built from stored text.

## Scope

New module **`src/roshambo3/format/r3g/descriptor.py`** (the name
`validate.corpus_fingerprint` looks for), new methods in
`src/roshambo3/pharmacophore.py`, and the test file
`tests/test_format3_descriptor.py`. **Do not change any existing call site**
of `require_color_features_enum` (`api.py:98`, `api.py:113`,
`engine/source.py:539`, `engine/source.py:552`, `engine/engine.py:593`,
`web/screening.py:57`, and the direct enum comparison at
`engine/cpu_self.py:214`): **T297** replaces them with this ticket's
`compare` followed by T288's trust gate.

1. **`descriptor.fingerprint(descriptor) -> str`** and
   **`descriptor.definition_hash(definition) -> str`**: thin re-exports of
   `reference.fingerprint` and `reference.definition_hash` (one
   implementation; the reference is the definition, FORMAT.md section 10.5).
   Once `descriptor.py` exists, `validate.corpus_fingerprint` routes through
   it; the conformance fingerprints in `tests/data/format3/EXPECTED.json` must
   not change. T288's allow-list and trust store use `definition_hash`.
2. **Schema.** No new typed model is required: the descriptor is the dict that
   `validate.read_descriptor` returns after its closed-schema checks. Its
   fields are those of FORMAT.md section 10.1: `format = {major: 3, encoding:
   "bp256-16", step_log2: -8}` (an integer exponent, so no float enters the
   fingerprint); `frame = {center: "heavy_atom_centroid", axes:
   "principal_axes", handedness: "right"}`; `prep.conventions`, exactly the six
   keys and values of section 10.1 (the spec defines them; this ticket defines
   none); `prep.version`, `prep.commit` (string or `null`); `groups`; `n_conf`;
   `n_mol`; `ids_sha256`; `molecules_sha256`. The `color` object (section 10.2)
   is `generator` (`"rdkit_fdef" | "smarts_list"`), `definition`
   (LF-normalized text for `rdkit_fdef`; for `smarts_list` a JSON **object**
   `{family: [smarts, ...]}`, not a string), `types` (an ordered list that is
   both the numbering, `id = index + 1`, and the selected families; there is
   no separate `{name: id}` object), `positioning` (always `"centroid"`, no
   weights field: unequal atom weights are refused at build, D034 item 4),
   `r` and `p` as `{dtype: "f32", shape: [n+1, n+1], values: [[...]]}`, and
   `rdkit_version` (excluded from the fingerprint).
3. **`descriptor_color()` on both generator classes.** The query generators are
   `pharmacophore.RDKitPharmacophoreGenerator` (alias `PharmacophoreGenerator`,
   `pharmacophore.py:592`; fdef from `self.fdefName`, default
   `RDConfig.RDDataDir/BaseFeatures.fdef`; factory built by
   `AllChem.BuildFeatureFactory(self.fdefName)` at `pharmacophore.py:420, 470,
   491`) and `pharmacophore.CustomSMARTSPharmacophoreGenerator`
   (`pharmacophore.py:517`; features as a `{name: [SMARTS]}` dict). Both expose
   `FEATURES_ENUM` and `interaction_matrix_r` / `interaction_matrix_p` (read by
   `engine/query.py:237`; the shape/value check is
   `layout.py::check_interaction_matrices`). Add `descriptor_color()` to both,
   returning exactly the section-10.2 object built with
   `reference.color_descriptor`: `generator` (`"rdkit_fdef"` or
   `"smarts_list"`); `definition` (the text read from `self.fdefName`, or the
   `{name: [SMARTS]}` dict); `types` (the family names ordered by their
   `FEATURES_ENUM` id, which must be exactly `1..n`; refuse otherwise);
   `r`, `p`; and `rdkit.__version__`. Import RDKit lazily (inside the method)
   where the module does not already.
4. **`descriptor.compare(corpus_color, query_color) -> None`**, raising
   `DefinitionMismatch(ValueError)` that names the **first** difference in
   this order: `types`, `generator` + `definition` (compared after
   normalization: the fdef text via `normalize_definition`, a SMARTS list via
   `canonical_json`), `positioning`, `r`, `p` (matrices compared as float32
   little-endian bytes, never as JSON or `repr`). The exception carries the
   field name as an attribute. Either side may be `None` (a shape-only corpus
   or query); `None` against a color object is a mismatch named `color`. An
   `rdkit_version` difference **warns** (`warnings.warn` with a dedicated
   category, e.g. `RDKitVersionWarning(UserWarning)`) and never refuses
   (D034 item 10). Comparison is between two section-10.2 objects, so the
   query side is `generator.descriptor_color()`.
5. **`descriptor.generator_from_descriptor(color)`** builds a query generator
   from stored text: for `rdkit_fdef`, build the factory with
   `rdkit.Chem.ChemicalFeatures.BuildFeatureFactoryFromString` (present in
   RDKit 2026.09.1; `_sandbox.py` already uses it), **never** by writing the
   text to a temporary file and passing a path; for `smarts_list`, construct
   `CustomSMARTSPharmacophoreGenerator` from the dict. Family selection and
   numbering come from `types`; matrices from `r` and `p`. The fdef generator
   takes a factory today only from a path, so add a constructor path that
   accepts a prebuilt factory (or the text) without touching the default
   behaviour. Keep the default feature plan (`self._default_feature_plan`,
   `pharmacophore.py:273`, used by `make_feature_plan` at `:481`) exactly as it
   is: it is enabled only when no `features` and no `fdefName` are passed, and
   T292 owns any widening. **This function must not be called on an untrusted
   definition**: T288 wraps it with the allow-list gate and the limited
   subprocess. Here it is a plain function, the single entry point T288
   wraps, with a docstring saying so.
6. **Shape-only corpora** have no `color` section; nothing in the module
   requires a definition for them.

## Deciding measurement

The refusal matrix in `tests/test_format3_descriptor.py`: for each of the five
compared fields (`types`, definition text, `positioning`, `r`, `p`), a test
that perturbs that one field (a) on the corpus side and (b) on the query side
and asserts `DefinitionMismatch` naming that field -- 10 cases. `positioning`
has one legal value, so perturb it in a dict that bypasses the schema check;
the comparison must still name it. Plus the group binding, already enforced:
one test that opens `tests/data/format3/adversarial/fingerprint_mismatch/`
through `reader.open_corpus` and asserts `integrity.fingerprint` -- 11 cases.
Commit the matrix output (test ids and outcomes) to `results/T287/`.

## Acceptance

* `pytest tests/test_format3_descriptor.py` green; it runs in CI's `cpu` and
  `cpu-macos` jobs (no CI change needed: both run `pytest -k "not cuda"`).
* All 11 refusal cases pass; an RDKit-version-only difference emits exactly one
  warning and no refusal.
* `descriptor.fingerprint` equals `EXPECTED.json`'s fingerprints for both
  conformance corpora (`tests/data/format3/{shape,color}/corpus.json`), and
  `tests/test_format3_reference.py` and `tests/test_format3_validator.py` still
  pass with `descriptor.py` present (the hook now routes through it).
* `fingerprint` is invariant to dict insertion order and JSON key order, and to
  `\r\n` vs `\n` in an fdef definition (FORMAT.md section 10.3 normalizes line
  endings); a matrix perturbed by one float32 ulp changes it; `rdkit_version`
  does not.
* `PharmacophoreGenerator().descriptor_color()` has `definition_hash` equal to
  `766f9790513f8f94c67ec6d1c8b6d5bede59b81f6da8c2081f57e49fb28d9784` on RDKit
  2026.09.1 (FORMAT.md section 10.3), passes `validate`'s color schema check
  (`validate._check_color`), and `types` equals the family names (first
  elements) of `pharmacophore.WORK_DESCENDING_FEATURE_ORDER`, in order.
* `generator_from_descriptor` on the shipped BaseFeatures text produces a
  generator whose `FEATURES_ENUM`, matrices and features on a few test
  molecules (perceived with `Chem.AddHs` first) equal `PharmacophoreGenerator()`'s
  with the same families and interactions; the same for a `smarts_list`
  round trip of a `CustomSMARTSPharmacophoreGenerator`.
* No file is written by `generator_from_descriptor` (assert with a patched
  `tempfile` / `builtins.open` in the test).
* No existing test changes behaviour; no existing call site changes.

## Traps

* **A digest over an unsorted dict or a float repr is noise.** Never hash
  anything yourself: call `reference.fingerprint`. If you need a new digest,
  canonicalize with `reference.canonical_json` and hash pinned bytes.
* **The numbering is the shipped work-descending order** (Hydrophobe=1,
  Acceptor=2, Aromatic=3, Donor=4, PosIonizable=5, NegIonizable=6), not the
  historical Donor=1 order. `format/rsb3.py:494-499`'s error message still
  lists the historical order as "this build's numbering"; it is stale. Take the
  order from `pharmacophore.WORK_DESCENDING_FEATURE_ORDER` and the generator,
  never from that message.
* **Interaction matrices are compared as values**, not as "canonical: true"
  (format 2's `manifest.interaction_matrix` is only `{canonical, reasons}`).
* **Do not featurize anything here from untrusted text.** RDKit's fdef builder
  can be made to take 26 s and 1.2 GB from a 543-byte file, and matching can
  take 13 s per query molecule from a 165-byte pattern
  (`results/T281/security/THREAT_MODEL.md`, appendix). T288 owns the gate; keep
  `generator_from_descriptor` the one entry point it wraps. Tests here use only
  the shipped BaseFeatures text and small hand-written SMARTS lists.
* **Features are perceived on the hydrogen-bearing molecule** (D034 item 3).
  Re-perceiving BaseFeatures on an H-stripped graph gets Hydrophobe wrong for
  most molecules (`results/T281/derive.py` vs `derive_h.py`); any test that
  perceives must call `Chem.AddHs` first.
* **Two hash functions, two purposes.** `definition_hash` names the definition
  text alone (trust, allow-list); `fingerprint` names the whole meaning
  (`format`, `frame`, `prep.conventions`, `color`). Do not use one for the
  other.

## Working rules

See `tickets/CONVENTIONS.md`.
* **Branches.** Cut `ticket/T287-format3-descriptor-and-fingerprint` from
  `main`, worktree `<worktree>`; merge back to `main` no-ff.
  Additive: no existing behaviour changes.
* **Venv.** There is no shared venv. Build one in the worktree as
  `doc/BENCHMARKING.md` "The venv" shows and check that `roshambo3.__file__`
  points into the worktree.
* No GPU is needed. If an unrelated CUDA MPS daemon is running, export
  `CUDA_MPS_PIPE_DIRECTORY=<scratch>` before running pytest or a build.
