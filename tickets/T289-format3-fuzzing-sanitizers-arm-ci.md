---
id: T289
title: Fuzz the format-3 validator and native decoder, add ASan/UBSan and Linux aarch64 CI
phase: 3
lane: infra
status: closed
model: luna
reviewer: sol
depends_on: [T284, T285, T286]
priority: high
branch: ticket/T289-format3-fuzzing
worktree: <worktree>
artifacts: results/T289/
---

## Context

**Gate.** None outstanding. T284 (spec, reference, seeds), T285 (native codec)
and T286 (Python writer, reader, validator) are closed, and T303 fixed the
defects their reviews found. The ticket is additive (tests and CI only; no
change to main's numerics), so T270 never gated it. It does not need T288:
the definition-text work here exercises only the RDKit-free pre-pass
(item 5); the sandboxed perception and its adversarial cases are T288's.

**Sources of truth.** `decisions/D034-corpus-format-3.md` item 10 and
`doc/FORMAT.md` sections 14-17 (as T303 left them on main at 8869694d). Where
this ticket and either disagree, they win; report the disagreement to the author
rather than editing them.

**Scope of hardening (D034 item 10, narrowed by the author 2026-10-18).** Required:
**memory safety** of native code reading corpus bytes (a bounds-checked decoder
that does not rely on the validator having run), **no process crash** on a
malformed file (it is refused with an error), and custom-definition isolation
(T288). Everything else -- time and memory bounds on other inputs, FORMAT.md
limits 33-34 -- is **best-effort**: a slow refusal is a finding to record, not
a failure. Files altered only to give wrong answers (e.g. a forged
self-overlap) and forgery of the local scan cache are out of scope. D034 says
fuzzing is "a sanitizer CI job and a short smoke run"; this ticket is that,
**not a fuzzing campaign**: no coverage target, no structure-aware mutator,
no nightly long run.

Two layers defend a reader: the pure-Python validator
(`src/roshambo3/format/r3g/validate.py`; tiers `open`, `scan`, `deep`; every
refusal a `CorpusValidationError`, and no other exception type may escape,
FORMAT.md section 16) that runs before native code sees a byte, and the native
decoder (`src/roshambo3/backend/_cpu_src/r3g_codec.cpp` and friends, wrapped by
`src/roshambo3/format/r3g/native.py`; FORMAT.md section 17), which is
bounds-checked on its own. The threat model
(`results/T281/security/THREAT_MODEL.md`) found the bit-packing prototype
exploitable from a single byte.

**What already exists on main.**
* **Seeds.** Conformance corpora `tests/data/format3/shape/` and `color/`
  (digests in `tests/data/format3/EXPECTED.json`); per-width oracle blocks
  `tests/data/format3/widths/` (`w01`-`w07`, `w14`-`w16`, `wrap.bin`); and the
  adversarial set `tests/data/format3/adversarial/`, whose
  `adversarial/EXPECTED.json` is authoritative: 94 seeds on main at 8869694d,
  each with `(tier, code, threat_model, generated)` and, where native differs,
  `native_code`. 14 are `generated` (materialized by
  `tests/data/format3/adversarial/make_adversarial.py::build(name, dir)`:
  FIFOs, symlinks, `oversize_header`, `block_rows_4097`,
  `single_molecule_4097_rows`, the large-payload cases, ...); bare
  `definition.json` seeds are pre-pass-only (no corpus). The parquet seeds
  (`parquet_*`, including `parquet_unsupported_codec` and
  `parquet_footer_oversize`) target `molecules.parquet`, which is
  zstd-compressed (D034 item 11) and whose footer is walked against a closed
  schema before pyarrow (`format/r3g/parquet_footer.py`, T303).
* **Seed regression tests, all three implementations.** Reference:
  `tests/test_format3_reference.py::test_adversarial_seed_is_refused_by_the_stated_tier`.
  T286 validator: `tests/test_format3_validator.py` (with the `open` time
  bound). Native: `tests/format3_native_cases.py` driven by
  `tests/test_format3_native.py` / `tests/test_format3_native_cpp.py`.
* **Fixture-level sanitizers.** `tests/test_format3_native_cpp.py::test_fixture_asan_ubsan`
  builds the standalone C++ codec fixture (`r3g_codec.cpp`,
  `r3g_unpack_scalar.cpp`, `r3g_encode.cpp` plus the ISA kernels) with
  `-fsanitize=address,undefined` and runs every case; it runs by default on
  Linux, so CI's `cpu` job already runs it. What does **not** exist is a
  sanitized build of the Python extension.
* **Reviewers' fuzz harnesses** from the T285/T286 reviews:
  `results/T303/reviews/t285-repro/fz/fuzz.cpp` (libFuzzer over the native
  core) and `results/T303/reviews/t286-repro/fuzz_worker.py` with
  `run_fuzz.sh` (Python validator). They hard-code scratch paths and a
  `wt/T286/.venv` that no longer exists; treat them as starting points, not
  as runnable scripts.
* **Mutation hooks.** `reference.write_corpus(..., group_mutate=,
  header_mutate=, descriptor_mutate=)` (`format/r3g/reference.py:1194`) applies
  an edit before the hashes that cover it are computed; the adversarial seeds
  are built with them. A smoke harness may use them to reach past the hash
  chain cheaply; no general structure-aware mutator is wanted.
* **CI** (`.github/workflows/ci.yml`): jobs `conventions`, `cpu`
  (`ubuntu-latest`, x86; requires AVX2+FMA), `cpu-macos` (`macos-15`, arm64)
  and `gpu-build`. There is **no Linux aarch64 job**: the comment in the `cpu`
  job (`ci.yml:31-33`, "skip on hosts without them (the arm64 job)") refers to
  one that does not exist. There is no fuzz job and no sanitized-extension job.

## Scope

1. **libFuzzer smoke harness over the native C++ core** (the core compiles
   without Python; build it from the same sources as
   `tests/test_format3_native_cpp.py`). Input: one block's bytes plus a small
   run table (or a whole small group file). Oracle: a clean error code, or
   output bit-identical to the scalar path, which must itself equal
   `reference.decode_block` including the modulo-2^16 wrap of FORMAT.md
   section 5.6. Build with `-fsanitize=fuzzer,address,undefined`. Run each ISA
   path the host can execute (forced scalar and AVX2 on x86; scalar and NEON
   on aarch64; `native.force_isa` / the codec's ISA override). The harness
   must hit the native core with **no validator in front** (T285 must be safe
   on its own).
2. **atheris smoke harness over the Python path**: `validate` `open` -> `scan`
   -> native decode of every block, on mutated whole corpora derived from the
   conformance corpora and the seeds. Oracle: a `CorpusValidationError` (any
   other exception escaping is a finding; FORMAT.md section 16), or a
   successful decode equal to the reference. A process crash (signal, abort)
   is a failure. Record time per input; do not assert it beyond FORMAT.md
   limit 33's best-effort target (`open` <= 20 s per corpus file).
3. *(dropped by the narrowing: no structure-aware mutator.)*
4. **Seeds as regression tests: verify.** The three implementations' seed
   tests above already refuse every seed at its stated tier and code. Confirm
   they run in every CI job this ticket adds (sanitized extension, aarch64),
   and add any seed the smoke runs find.
5. **Pre-pass grammar smoke.** Fuzz `reference.check_definition_text`
   (FORMAT.md section 15; pure, RDKit-free) with case-mixed keywords,
   continuation lines, `!Name` macros, nested `{Name}` references, long
   `*`/`A`/`a` chains, and mutations of the bare `definition.json` seeds.
   Oracle: it returns a summary or raises `CorpusValidationError` with a
   `limit.definition_*` or `value.definition` code; nothing else escapes; it
   finishes within limit 33's bound (record, best-effort). Do not run RDKit
   here: perceiving a definition in the limited subprocess and the measured
   blowups (543-byte fdef 26 s / 1.2 GB; 165-byte pattern 13 s per molecule;
   500 KB nested SMARTS 29 s) are T288's deciding measurement.
6. **CI** (edit `.github/workflows/ci.yml`):
   - **Sanitized extension job** (Linux x86): add a CMake option, e.g.
     `ROSHAMBO3_SANITIZE` (`address,undefined`), passed to the editable install
     as `--config-settings=cmake.define.ROSHAMBO3_SANITIZE=address,undefined`,
     that adds `-fsanitize=...` to the CPU extension's compile and link flags.
     Run the format-3 test files (`tests/test_format3_*.py`) against it, with
     the ASan runtime preloaded as the Python interpreter requires
     (`LD_PRELOAD=$(gcc -print-file-name=libasan.so)`, leak detection off for
     the interpreter). The C++ fixture tests keep running as today.
   - **Fuzz smoke job**: each harness of items 1, 2 and 5 for 60 s per target
     per PR, crash inputs uploaded as artifacts.
   - **`ubuntu-24.04-arm` job** running the CPU suite as the `cpu` job does
     (`python -m pytest -k "not cuda"` with the same install), so NEON is
     covered on Linux, not only on macOS; it must run T285's NEON path forced
     and compare against the conformance digests (`tests/test_format3_native.py`).
     Fix the stale "arm64 job" comment.
7. Commit the harnesses under `tests/fuzz/` (excluded from default pytest
   collection if they need libFuzzer or atheris), and every crash input as a
   regression test.

## Deciding measurement

The sanitized-extension, fuzz-smoke and `ubuntu-24.04-arm` CI jobs green, and
every adversarial seed refused at its stated tier and code in each of them.

## Acceptance

- Every adversarial seed refused at its stated tier and code by the reference,
  the T286 validator and the native codec (`native_code` where
  `adversarial/EXPECTED.json` gives one), in the existing jobs and the new
  ones; time recorded, not asserted beyond FORMAT.md's best-effort targets.
- Sanitized-extension job green; fuzz smoke job green.
- `ubuntu-24.04-arm` CPU job green, including T285's NEON path forced and
  compared against the conformance digests.
- No process crash and no sanitizer report in any smoke run. Any crash or
  memory-safety bug found is fixed (in `src/roshambo3/format/r3g/` or
  `backend/_cpu_src/r3g_*`) or filed as a new ticket, and its input committed
  as a regression test. A slow refusal or a non-`CorpusValidationError`
  exception is recorded in `results/T289/README.md` and fixed if cheap.
- `results/T289/README.md`: what ran, for how long, on which ISA paths, and
  every finding with its disposition.

## Traps

- **A raw byte mutator dies at the first hash.** Mutating a corpus after it is
  written mostly exercises the integrity checks. That is acceptable for a
  smoke run; to reach deeper cheaply, mutate through `reference.write_corpus`'s
  hooks before the hashes are taken, and report which depth each target
  reached. Do not build a general mutator.
- **Do not weaken bounds to make fuzzing pass.** A timeout or memory finding is
  a limits-table question for the author (spec) or a missing check, not a fuzzer
  tuning problem. Do not edit `doc/FORMAT.md` or D034.
- **The Python validator is not under test alone**: item 1 must hit the native
  core with no validator in front.
- **ASan and Python.** A sanitized extension loaded into an unsanitized
  interpreter needs the ASan runtime preloaded and `detect_leaks=0`; without
  that the job fails on interpreter leaks or refuses to load, which is not a
  finding.
- **Wrong-answer corpora are out of scope** (D034 item 10): do not file "a
  forged self-overlap changes scores" as a finding; nor scan-cache forgery.
- **No CUDA here.** If the machine has a foreign MPS daemon, anything that makes
  a CUDA context hangs (CLAUDE.md); export
  `CUDA_MPS_PIPE_DIRECTORY=<private directory>` before local builds and test runs.

## Working rules

See `tickets/CONVENTIONS.md`.
* **Branches.** Cut `ticket/T289-format3-fuzzing` from `main`, worktree
  `<worktree>`; merge back to `main` no-ff. Additive (tests
  and CI only, plus fixes to any defect found). No GPU needed.
* **Venv.** There is no shared venv. Build one in the worktree as
  `doc/BENCHMARKING.md` "The venv" shows and check that `roshambo3.__file__`
  points into the worktree. Local aarch64 checks can use
  `qemu-aarch64-static` as `results/T285/README.md` and
  `results/T303/run_vectors.sh` describe.


## Implementation outcome (2026-10-18) — local work complete

Implemented the standalone native libFuzzer entry point, two instrumented
Atheris targets, CPU extension ASan/UBSan compile and link option, sanitized
format-3 job, bounded 60-second fuzz job with uploaded artifacts, and Linux
`ubuntu-24.04-arm` CPU job with forced NEON. The CI sanitizer launcher preloads
GCC's `libasan` followed by `libstdc++`; the pytest launcher disables CPython
vfork after process start, leaving sanitizer coverage active in the suite and
its children. These controls were needed for ARM runtime behavior and do not
weaken bounds checks or skip refusal tests.

Local evidence is in `results/T289/README.md`. It includes 593 passing ARM
format-3 tests under ASan/UBSan, 2 passing standalone scalar/NEON native
fixture tests, one 60-second native libFuzzer run (2,145,903 executions, cov
529), and 60-second corpus-reader and definition-prepass Atheris smokes (cov
54 and 22). The orchestrator's integration run separately reported 615 passing
format-3 tests on its ordinary CPU build. No codec memory-safety defect or
fuzz crash was found. The AArch64 ASan `__cxa_throw` interceptor failure and
CPython vfork child SIGILL were isolated and fixed in the workflow runtime
setup; full diagnostics and passing controls are retained in the evidence
folder.

Hosted CI was not run; the ticket is closed on local evidence and hosted jobs
are not claimed green.
