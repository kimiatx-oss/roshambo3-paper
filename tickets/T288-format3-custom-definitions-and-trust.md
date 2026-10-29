---
id: T288
title: Custom color definitions -- shipped defaults by hash, everything else behind an explicit, bounded opt-in
phase: 3
lane: infra
status: closed
model: sonnet
depends_on: [T287]
priority: high
branch: ticket/T288-format3-custom-definitions-and-trust
worktree: <worktree>
artifacts: results/T288/
---

## Context

**Gate.** T287 is done and merged into the integration branch
`ticket/T281-format3-switch` (not main); it provides
`roshambo3.format.r3g.descriptor` with `definition_hash`, `compare` and
`generator_from_descriptor` (check `git log ticket/T281-format3-switch -- src/roshambo3/format/r3g/descriptor.py`).
Nothing else gates it: T284, T286 and T303 are closed, and the ticket is
additive (no change to main's numerics), so T270 never gated it.

**Sources of truth.** `decisions/D034-corpus-format-3.md` item 10 (accepted
2026-10-18) and `doc/FORMAT.md` sections 10.2-10.3, 14 (limits 24-30) and 15
(the pre-pass), as T303 left them on main at 8869694d. Where this ticket and
either disagree, they win; report the disagreement to the author rather than
editing them.

Format 3 stores each color corpus's full feature-definition text (an RDKit
`.fdef` file, or a SMARTS-list object) in `corpus.json`, and queries are
featurized with that definition (D034 item 2). Compiling definition text that
came from a downloaded file is a denial-of-service surface: it cannot execute
code (RDKit's fdef grammar has no include or file directive) but it can hang a
reader. Measured on RDKit 2026.09.1 (`results/T281/security/THREAT_MODEL.md`,
section 2.1 and appendix):

* a 543-byte fdef with doubling `AtomType` macros expands to 3.4 MB and takes
  **26.5 s and 1.2 GB** to build;
* a 165-byte `DefineFeature` of 18 chained `*` atoms takes **13.1 s per query
  molecule** to match (14 atoms: 4.9 s);
* a 500 KB nested SMARTS takes **29 s** just to be rejected.

**Scope of hardening (D034 item 10, narrowed 2026-10-18).** Three protections
are *required*: memory safety of native code, no process crash on a malformed
file, and **custom-definition isolation** -- which is this ticket: shipped
RDKit definitions are recognized by hash and need nothing; any other
definition needs an explicit opt-in by hash (`--trust-definition <sha256>`,
`roshambo3 definitions trust/show`), passes the RDKit-free pre-pass, and is
perceived in a time- and memory-limited subprocess. Limits stay on even when
trusted. Time and memory bounds on *other* inputs are best-effort. The web app reads
the same trust file; it is a local demonstration tool and is not intended for
exposure on untrusted networks.

**What already exists on the integration branch** (paths under `src/roshambo3/format/r3g/`):

* **The pre-pass**: `reference.check_definition_text(definition, generator,
  types=None) -> dict` (FORMAT.md section 15): pure, RDKit-free, bounded, the
  closed grammar. It returns a summary (`rdkit_fdef`: `atomtype_lines`,
  `definefeature_lines`, `expanded_total`, `expanded_longest`, `families`;
  `smarts_list`: `patterns`, `families`) and raises `CorpusValidationError`
  with `code` one of `limit.definition_size`, `limit.definition_lines`,
  `limit.definition_line_count`, `limit.definition_expansion`,
  `limit.definition_depth`, `limit.definition_atoms`,
  `limit.definition_patterns` or `value.definition` (FORMAT.md section 16.5).
  T286's `scan` tier calls it. **Reuse it; do not write a second one.**
* **The limited subprocess, as a placeholder**: `_sandbox.py`. Its docstring
  says "Placeholder for T288 ... `run_child` is the one function T288
  replaces". `run_child(request, timeout=)` runs an isolated interpreter
  (`python -I`, no roshambo3 import, `CUDA_VISIBLE_DEVICES=""`) with
  `RLIMIT_AS` 2 GiB, `RLIMIT_CPU` 30 s and a 60 s wall kill, builds the
  factory with `BuildFeatureFactoryFromString` (or compiles a SMARTS list),
  perceives on `Chem.AddHs(MolFromSmiles(smiles))`, and returns integers
  only. `deep_rdkit_checks` (the `deep` tier's re-perception, FORMAT.md
  section 16.4) is its caller.
* **The definition hash**: `reference.definition_hash` (re-exported by T287 as
  `descriptor.definition_hash`). The shipped `BaseFeatures.fdef` of RDKit
  2026.09.1 hashes to
  `766f9790513f8f94c67ec6d1c8b6d5bede59b81f6da8c2081f57e49fb28d9784` -- the
  raw file's SHA-256, since the spec normalizes line endings only (section
  10.3).

## Scope

New module **`src/roshambo3/definitions.py`** (the public name
`roshambo3.definitions` used below), plus CLI and API wiring. The screen paths
do not read format 3 yet; **T297 wires this gate into them** (API, CLI, web)
on the integration branch. This ticket provides the gate as a library
function, the CLI and the flags.

1. **Allow-list and shipped default texts.** Ship the text of RDKit's
   `BaseFeatures.fdef` as package data,
   `src/roshambo3/data/definitions/<rdkit-version>/BaseFeatures.fdef`, at least
   for RDKit 2026.09.1, the version this repository is developed against
   (`pyproject.toml` does not pin RDKit). Each directory carries a
   `PROVENANCE` file naming the RDKit version, the source path and the
   sha256. `src/roshambo3/data/` does not exist yet; the wheel packages
   `src/roshambo3` (`pyproject.toml`, `wheel.packages`), so confirm the data
   files are present in a built wheel (`pip wheel . && unzip -l`). The
   allow-list is a committed data file listing each shipped text's
   `definition_hash` with its RDKit version and the date added, plus
   `scripts/definition_allowlist.py`, which reads
   `RDConfig.RDDataDir/BaseFeatures.fdef` from the installed RDKit and prints
   the entry and the text to add. `show --diff` and the refusal summary use
   only the shipped texts, so neither needs RDKit.
2. **Pre-pass.** Call `reference.check_definition_text(definition, generator,
   types)` before RDKit sees any text, for trusted and untrusted definitions
   alike. A definition file passed directly (T293's builder, a user's file) is
   pre-passed too; that is where limit 24 (64 KiB) is reachable, since in
   `corpus.json` limit 4 refuses first. **"n patterns"** in messages is the
   summary's `definefeature_lines` (fdef) or `patterns` (SMARTS list).
3. **Bounded perception: own the subprocess.** Replace the placeholder
   `_sandbox.run_child` with this ticket's implementation (keep the function
   name and its request/response contract, or update `deep_rdkit_checks` in
   the same commit so `verify --tier deep` keeps passing on both conformance
   corpora). Expose a public "build factory and perceive" call from
   `roshambo3.definitions` that both query featurization and the `deep` tier
   use -- the one place corpus text becomes an RDKit factory. Requirements:
   `RLIMIT_AS` 2 GiB, `RLIMIT_CPU` 30 s, wall-clock kill at 60 s (all three
   configurable; these defaults, which are `_sandbox`'s today); no CUDA
   context in the child and no GPU lock taken; only integer feature tables
   (type, atom indices) and positions return, validated like a corpus table
   (types in `1..n_types`, indices `< n_atoms`). Allow-listed definitions may
   run in-process. **Limits apply to trusted definitions too**: trust removes
   the refusal, not the bounds.
4. **Trust store.** Per-user file `~/.config/roshambo3/trusted-definitions`
   (respect `$XDG_CONFIG_HOME`). One entry per line,
   `<64-hex sha256>\t<ISO-8601 date>\t<note>` (note may be empty; tabs in a
   note become spaces on write); lines starting with `#` and blank lines are
   ignored; a malformed line is reported with its line number and skipped,
   never silently trusted. Atomic writes (temp file + `os.replace`).
5. **CLI** (`src/roshambo3/cli.py`).
   * New subcommand group `roshambo3 definitions`:
     * `show <corpus> [--diff]`: prints the stored definition, RDKit-free
       (read `corpus.json` with `roshambo3.format.r3g.validate.read_descriptor`;
       a `smarts_list` definition is printed as its canonical JSON,
       `reference.canonical_json`). `--diff` prints a unified diff against the
       **nearest shipped default**: the shipped `BaseFeatures.fdef` text (any
       shipped RDKit release) with the fewest changed lines (`difflib`; ties
       to the newest RDKit version). Escape control characters when printing.
     * `trust <hash> [--note TEXT] [--corpus PATH]`: a **full** 64-hex hash,
       or a prefix of at least 12 hex characters together with `--corpus
       <path>`, resolved against that corpus's definition hash; a prefix
       without `--corpus` is refused. `untrust <hash>` (full hash or an
       unambiguous prefix of an entry already in the trust file). `list`.
   * On `screen` (`cli.py:596`, `s = sub.add_parser("screen", ...)`) and any
     other command that featurizes queries: `--trust-definition <hash>`,
     repeatable. A prefix of at least 12 hex characters is accepted if it is
     unambiguous against the corpus being opened; the trust file stores full
     hashes only. Until T297 wires the gate, the flag has no effect on any
     screen; say so in its help text.
   * The `differs` line summarizes the diff against the nearest shipped
     default in one line: families added/removed, then the number of changed
     patterns per family (e.g. `adds family "Halogen"; changes Acceptor (2
     patterns)`). For a `smarts_list`, compare its families and patterns with
     the shipped fdef's `DefineFeature` families and patterns.
   * **Refusal message** (exact shape, from T281's "Trust UX"):
     ```
     error: <corpus> uses a custom color definition that is not one of RDKit's defaults.
       definition  sha256 <first 12>…<last 4>
       families    <comma-separated family names>
       differs     <one-line summary vs the nearest shipped default>
       size        <KB>, <n> patterns  (within limits | exceeds <limit>)

     Custom definitions are compiled and run by RDKit on your queries. Vet it before
     trusting it:
       roshambo3 definitions show <corpus>            # full text
       roshambo3 definitions trust <first 12> --corpus <corpus>   # trust it from now on
     or for this run only:
       roshambo3 screen ... --trust-definition <first 12>
     ```
     (`trust` with a prefix needs `--corpus`, item 5, so the hint includes
     it.) A definition that fails the pre-pass is refused with the limit or
     rule named (the `CorpusValidationError` code), even if trusted.
6. **Python API.** `roshambo3.definitions.trust(hash, note=)`, `untrust`,
   `list_trusted`, `show`, and the gate function
   `check_definition(color, *, trusted=(), corpus_path=None)` (or a similarly
   named function; document it, T297 calls it), where `color` is the corpus's
   section-10.2 object: returns normally for a shipped or trusted, in-limits
   definition; raises `UntrustedDefinitionError(ValueError)` whose
   attributes carry the summary fields of the message above; raises
   `CorpusValidationError` for a pre-pass refusal. Add the keyword
   `trust_definitions=()` to `api.screen` (`api.py:131`) and
   `api.score_matrix` (`api.py:284`); it is accepted and documented, and
   T297 makes it effective.
7. **Builder.** Building a corpus from the user's own definition file needs
   no flag (the file is the user's); the build prints the definition hash so
   it can be handed to colleagues. **T293 implements the print** (it owns the
   builder), with `descriptor.definition_hash`.
8. **Shape-only screens never need a definition** and never consult the trust
   store.
9. **Web demo.** The gate must be usable by the web app: today's color gate
   compares the manifest's `features_enum` with `PharmacophoreGenerator()` in
   `web/config.py` (`public()`, `:24`); T297 replaces that comparison with the
   gate's verdict (an untrusted custom definition disables color modes for
   that corpus, with a message pointing at the CLI). No web changes here.

## Deciding measurement

Four adversarial definitions, each **refused or killed with a clean error
naming the limit, within the stated bound, while trusted**:

* the macro bomb (the threat model appendix's doubling `AtomType` levels,
  n=18, 543 bytes) -- refused by the pre-pass (limit 28, recursion depth);
* the 18-`*` chained `DefineFeature` -- refused by the pre-pass (limit 29,
  top-level atoms);
* the 500 KB nested SMARTS (`"[$(" * d + "C" + ")]" * d`) as a `DefineFeature`
  pattern -- refused by the pre-pass (limit 24, `limit.definition_size`,
  checked first);
* **a definition that passes the pre-pass but is slow to match**: a
  `DefineFeature` of a 16-atom `*~*~...~*` chain (FORMAT.md section 15 says
  it is within the limits and still costs seconds per molecule), perceived on
  imatinib with hydrogens (68 atoms) repeated until the CPU limit is crossed --
  **killed in the subprocess** by `RLIMIT_CPU` or the wall clock, with the
  limit named and the child reaped. This is the case that tests the sandbox;
  the first three never reach it. The test may lower the configurable limits
  (e.g. 2 s CPU, 5 s wall) to stay fast; also run it once at the defaults and
  record the time.

Generator code for the first three is in the threat model's appendix.
Commit the timing table (case, stage that refused, code, wall time, peak RSS)
to `results/T288/`.

## Acceptance

* `pytest tests/test_definitions.py` green; CI's `cpu` (x86 Linux) and
  `cpu-macos` (macOS arm64) jobs run it.
* The allow-listed BaseFeatures definition passes `check_definition` with no
  trust entry, no prompt, and runs in-process.
* An untrusted custom definition is refused with the documented message
  (golden-text test with the hash substituted).
* `--trust-definition <12-hex prefix>` / `trusted=` lets it pass; an ambiguous
  or too-short prefix is refused; `definitions trust` persists across
  processes; `untrust` removes it.
* The four adversarial definitions fail bounded even when trusted; the
  subprocess is reaped (no zombie, no orphan) on every failure path.
* `verify --tier deep --all` still accepts `tests/data/format3/color/`, now
  through this ticket's subprocess.
* `roshambo3 definitions show` never imports RDKit (a subprocess runs it and
  asserts `"rdkit" not in sys.modules`).
* A shape-only corpus with a custom definition needs no flag (test the gate
  function with `color=None`).

## Traps

* **Trust names one exact text.** Never offer an "allow any custom definition"
  switch; a user who vetted one definition must be refused again for a
  tampered one.
* **Restricting the grammar does not bound matching.** The 13 s case is plain
  `*~*`; the subprocess limits are the defence for matching, not a SMARTS
  subset. That is why the fourth deciding case exists.
* **The threat model's flag name differs.** It proposes
  `--trust-corpus-definition`; T281's trust UX settled on `--trust-definition`
  plus the `definitions` subcommand. Use T281's.
* **Child processes and CUDA.** Keep `_sandbox`'s approach: a fresh
  interpreter via `subprocess` (never `fork` of a process that may hold a CUDA
  context), `CUDA_VISIBLE_DEVICES=""`, nothing of roshambo3 imported in the
  child. If a foreign MPS daemon is running, the child must not touch CUDA at
  all (CLAUDE.md, MPS trap).
* **`definitions.py` must not import RDKit, or `pharmacophore` (which imports
  RDKit), at module top level.** Import them lazily inside the functions that
  build factories; otherwise the RDKit-free `show` test fails. `import
  roshambo3` does not import RDKit today (`pharmacophore` is imported lazily);
  keep it that way.
* **RDKit logs raw bytes to stderr** (the threat model found an ESC byte echoed
  from a bad SMILES). Escape anything definition-derived before printing, and
  keep `RDLogger.DisableLog` in the child.
* **Do not re-perceive on H-stripped molecules** (D034 item 3). Query
  featurization adds hydrogens first (`Chem.AddHs`), as `_sandbox` does.
* **Do not edit `doc/FORMAT.md` or D034.** If the pre-pass or the limits look
  wrong, report it to the author.

## Working rules

See `tickets/CONVENTIONS.md`.
* **Branches.** Cut `ticket/T288-format3-custom-definitions-and-trust` from
  the integration branch `ticket/T281-format3-switch` (where T287 landed),
  worktree `<worktree>`; merge back into the integration
  branch no-ff, never into main. Additive.
* **Venv.** There is no shared venv. Build one in the worktree as
  `doc/BENCHMARKING.md` "The venv" shows and check that `roshambo3.__file__`
  points into the worktree.
* No GPU work. Export `CUDA_MPS_PIPE_DIRECTORY=<private directory>` and check
  `pgrep -a nvidia-cuda-mps` before running pytest or a build (CLAUDE.md).
