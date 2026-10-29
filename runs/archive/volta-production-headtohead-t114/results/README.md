# T114 — the Volta head-to-head at production settings

References to `results/`, `tickets/`, `doc/`, `hosts/` and other files not in this repository point at the internal development record.

**Status: advisory**, carrying exactly the two advisories `results/T83/A2` and
T68's own arm carried, plus the harness conditions that fire on every row of
this family (§7). CUDA 12.9 is not the pinned 13.2 and the build is `70-real`
rather than sm_120. Both are unavoidable and both are the point — CUDA 13.x
dropped sm_70 outright, so a TITAN V build can only be made on 12.x, and the
TITAN V is the GPU the comparison paper benchmarked. Every number here is a
wall-clock ratio between two tools on one card in one session; no score from it
is compared against an sm_120 score.

This document **replaces `results/T83/A2-tachi-headtohead.md`**, whose 57.0×
was measured at `6c68da76`, before T85, T86, T87, T92, T93, T96, T97, T105,
T106, T107, T109 and T111 landed. `results/T101/` licenses the re-run and says
so in its own words: *"The production head-to-head is not this ticket's run and
was not started here."*

`METHOD.md` (in the internal development record) carries the construction — what changed from T68's
harness, what had to be built for the combination arm, and the two data defects
found on the way. `results/T68/METHOD.md` is the parent document and is not
reproduced.

---

## 1. Session A — shape, at production settings

Every cell inside **one** `flock` hold and **one** clock region.
`tickets/T68/run_headtohead.sh headline`, its cell definitions byte-identical to
what T68 ran, driven from this ticket's tree by
`tickets/T114/run_session_a.sh`.

| baseline | mode | ROSHAMBO2 s | ROSHAMBO3 s | **T114** | A2 | T68 |
|---|---|---:|---:|---:|---:|---:|
| `u2`, as released | eager | 1422.04 | 7.526 | **188.9×** | 58.7× | 46.9× |
| `u2`, as released | in_memory | 1386.13 | 7.526 | **184.2×** | 57.0× | 45.5× |
| `u2_color_skip` | eager | 656.30 | 7.526 | **87.2×** | 26.7× | 21.3× |
| `u2_color_skip` | in_memory | 614.40 | 7.526 | **81.6×** | 25.0× | 19.9× |

Including the in-memory preload, the two `in_memory` rows are **192.5×** and
**92.1×**. `u2` is ROSHAMBO2 as released; `u2_color_skip` is the baseline whose
colour-loop defect we fixed ourselves, and **81.6× is the honest comparison**
and the number to lead with.

ROSHAMBO3: 7.5262 s median of 11 repeats, min 7.4957, max 7.7094, page cache
dropped and `mincore`-verified before **each** repeat
(`resident_fraction_after_drop` 0.0277 over 93 files / 3,112,793,785 B).
ROSHAMBO2: 2 repeats per cell, spreads 613.88–614.93, 648.58–664.02,
1384.42–1387.84 and the `u2` eager pair likewise.

### 1.1 Both arms were re-run, and the baseline reproduces

A2 was allowed to reuse T68's ROSHAMBO2 wall times only because the achieved
clock matched to the megahertz, and its own text calls that "a coincidence to
verify rather than a protocol to rely on". Verified:

| arm | T68 | T114 | drift |
|---|---:|---:|---:|
| `u2` eager | 1420.28 | 1422.04 | +0.12% |
| `u2` in_memory | 1379.72 | 1386.13 | +0.46% |
| `u2_color_skip` eager | 646.48 | 656.30 | +1.52% |
| `u2_color_skip` in_memory | 604.27 | 614.40 | +1.68% |

**The baseline has not moved. The whole change is on our side**: 30.297 s →
7.5262 s, **4.025×**, of which A2 had already banked 1.252×.

### 1.2 It is the same answer, bit for bit

`tickets/T114/compare_topk_bitwise.py`, T68's own top-K dump against this
session's, same corpus, same 8 queries, same `k`, same steps, same start mode:

| | |
|---|---|
| score words compared | **800,000** |
| score words moved | **0** |
| gids identical | **yes** — 0 differing |
| bit-differing-but-float-equal | 0 |
| max abs score delta | 0.0 |

Compared on **bit patterns**, not `==`: `-0.0 == 0.0` and `NaN != NaN` would
each make an equality test say the wrong thing (T101 §3.1). So this is **the
engine got faster, not the engine changed** — which is a different claim from a
speedup that is merely close, and it is the one the arithmetic being pinned
rather than toleranced entitles us to make.

### 1.3 Where the 4.025× went, and what binds now

| stage | T68 (30.297 s) | T114 (7.526 s) | factor |
|---|---:|---:|---:|
| `kernel_s` | 19.335 (63.8%) | **6.369 (84.6%)** | 3.04× |
| `precompute_s` | 4.687 (15.5%) | 0.107 (1.4%) | 43.8× |
| `free_s` | 2.184 | 0.0018 | 1,213× |
| `h2d_s` | 2.112 | 0.533 (7.1%) | 3.96× |
| `topk_s` | 0.996 | 0.118 | 8.4× |
| `index_s` | 0.130 | 0.106 | 1.2× |
| `alloc_s` | 0.034 | 0.003 | 11× |
| `producer_wait_s` | 0.020 | **0.019 (0.25%)** | — |
| `sink_s` | 0.005 | 0.0004 | — |
| H2D bytes | 13,614,262,040 | **5,147,360,088** | 2.65× less |
| launches (`n_blocks`) | 4,988 | **321** | 15.5× fewer |
| conformers per launch | 4,086 | 63,493 | — |

**The binding constraint is still the kernel, and more so than before: 63.8% →
84.6% of wall.** Per-launch overhead collapsed from 10.14 s to 0.87 s — T85's
coalescing (15.5× fewer launches) and T83's query-field cache
(`precompute_s` 4.687 → 0.107, A1's mechanism now worth far more against a
smaller wall) — but the kernel *itself* is 3.04× faster, and that is where most
of the 4.025× lives: the int16 wire, the merged record and the query-record
trim showing up as 2.65× less H2D and a far better amortized per-launch cost.

**A2's honest reading does not transfer.** A2 concluded its 1.252× was
"essentially the field cache"; this one is not. And **it has not become
producer- or I/O-bound**: `producer_wait_s` is 0.019 s of 7.526 with the cache
dropped before every repeat, so a 3.11 GB cold read is entirely hidden behind
the kernel.

### 1.4 The baseline's own stage split, which explains both ratio columns

| arm | mode | wall | read+decode | host prep | device (one pybind call) | host reduce |
|---|---|---:|---:|---:|---:|---:|
| `u2` | eager | 1422.04 | 51.07 | 82.77 | 1027.75 | 268.67 |
| `u2` | in_memory | 1386.13 | 0.00 | 79.15 | 1029.13 | 276.14 |
| `u2_color_skip` | eager | 656.30 | 51.14 | 82.52 | 265.62 | 264.74 |
| `u2_color_skip` | in_memory | 614.40 | 0.00 | 79.67 | 265.85 | 268.35 |

The as-released arm's colour-loop defect is **763 s of its 1386**, which is the
whole distance between the 184.2× column and the 81.6× column. With it fixed
the baseline is **49% host-bound**, which is why the in-memory correction is
only 1.026× and 1.068× — reading is not what that arm is spending its time on.

---

## 2. What the step budget costs — the ratio, decomposed

ROSHAMBO3 ships 25 optimizer steps; the ROSHAMBO2 arms run 100 at their own
shipped default. T46 §1.3 priced that and `results/T68/METHOD.md` §10 item 8
requires it to be "a named line of the ratio rather than something folded into
'the kernel got faster'". A reader who let that pass at 25× will not let it
pass at 81.6×, so it is measured rather than cited.

`tickets/T114/run_step_budget.sh` — its own session, **both arms inside one
`flock` hold and one clock region**, because session A was closed by then and a
decomposition whose denominator came from another invocation is exactly the
pairing D007 forbids:

| steps | resolved `lr_t` (D019) | translation budget | wall s | kernel s |
|---:|---:|---:|---:|---:|
| 25 | 0.4 | 3.456 Å | 7.5416 | 6.369 |
| 100 | 0.2 | 3.718 Å | 24.6800 | 23.492 |

**`R3@100 / R3@25` = 3.273×** (kernel only, 3.689×; the ~1.17 s of
non-kernel wall is fixed and does not scale with the budget).

No `--lr-t` was passed and none could be: D019 makes `steps` and `lr_t` one
knob and `ScreenConfig.lr_t = None` derives it, so running 100 steps at the
25-step `lr_t` — the silent accuracy loss `engine/config.py` warns about — is
not reachable through this harness. The resolved pair is recorded on every row.

**This is a cost decomposition, not an accuracy arm.** The headline stays at
the shipped 25 steps, and the baseline is **not** re-run at 25 — taking the
other tool off its shipped default is the more contentious direction and this
decomposition does not need it. Read as a stated factor: of the 81.6×, **3.27×
is the step budget**, and the remainder is everything else the two tools differ
in (a grid-interpolated query field against an analytic one, the record on the
wire, the launch structure, the sink). The 25-step cell here reproduces session
A's to 0.21%, which is a consistency check and **not** a term in any ratio.

---

## 3. Two things about the data that the ticket did not know

Both are in `METHOD.md` in full; the headlines:

**The ROSHAMBO3 colour corpus is refused by the shipped build, and the refusal
is correct.** `color_rsb3/library` records the historical
`{Donor: 1, …, Hydrophobe: 6}`; the shipped generator numbers work-descending
since T106. Scoring one against the other is silent, so
`require_color_features_enum` raises — confirmed directly before converting.
`roshambo3 convert` re-emits it, and `tickets/T114/assert_color_corpus.py`
checks the result against roci's copy rather than trusting it: `sha256_ids`
`3bf681cc36d25f6a…` and **unchanged by the convert** (the permutation moved
planes, not rows), `n_conformers` 20,381,286, slot efficiency **0.7142 →
0.7686**, record v1 → v2, and `roshambo3 verify` reports the corpus
self-consistent.

**The ROSHAMBO2 colour h5 was two shards short, and nothing had noticed.** It
held **19 shards and 18,985,413 conformers** against the shape corpus's 21 and
20,381,286. T82's build crashed on `shard_00018`'s empty post-loop flush — the
exact-multiple defect `results/T68/METHOD.md` §4.1.1 documents and works around,
which T82's colour builder does not — and the exception took shards 19 and 20
with it. `tickets/T114/build_missing_color_h5.py` built them from the same
conformer archive with the same preparer source, the same `BaseFeatures.fdef`
(`766f9790…28d9784`, 6,794 B) and the same RDKit (2026.03.5), all hashed on
both hosts rather than assumed. 18,985,413 + 999,114 + 396,759 = **20,381,286**,
and the identity was re-checked by the gate rather than left as arithmetic.

---

## 4. The gates

| gate | result |
|---|---|
| **shape pair, same conformers** — re-run, not inherited | 20,381,286 and 407,664 on both sides; 0 molecules on one side only; 0 count mismatches; `identical_population: true` |
| **colour pair, same conformers** — first time ever run | 20,381,286 and 407,664 on both sides; 0 / 0 / 0; `identical_population: true`; h5 `L` ∈ {68, 80, 88, 92, 96, 100, 104} |
| **top-K agreement, shape**, ROSHAMBO3 vs `u2_color_skip` and vs `u2` | mean set overlap **0.925 / 0.968 / 0.954 / 0.961** at k = 10 / 100 / 1,000 / 10,000, identical for both baselines |
| **top-K agreement, combination**, ROSHAMBO3 vs `u2_color_skip` | mean set overlap **0.962 / 0.949 / 0.942 / 0.946** at the same four k. One cell per tool per objective, which is what the ratio being between two tools answering the same question requires. Not dumped for `u2`, whose eager cell was the one not run (§6A.1). |
| **sm_70 SASS embedded, no PTX**, read out of the loaded `.so` | three cubins `kernels/molecule_topk/topk.sm_70`, `embedded_ptx: []`, `.so` sha256 `37198299…`, `numerics.check_build()` OK, `HEAD:src` = the tree the binary was built from |
| **within-tool bit gate** vs T68's top-K | 0 of 800,000 words moved (§1.2) |
| **colour operating point**, T107's lock | 0 of 32,879,200 words moved (§5) |
| **colour plane order / corpus migration** | 0 compounds cross the 1% boundary on any of 8 queries (§6) |

Top-K set agreement is **set agreement between two candidates**, neither a gold
standard — not `R(N, k)`, and not comparable digit for digit with any recall in
`doc/METRICS.md` §1. The two sides read different bytes by design and do not
compute the same thing.

---

## 5. Did locking the colour operating point move a colour score? **No.**

Every accuracy number the submission rests on — `results/T66`, `T71`, `T104`,
and `T91`'s comparison against them — was measured at the **pre-lock** colour
operating point, `color_residency = GLOBAL`, `color_stage = 0`. The tree ships
`SHARED / 48` since T107. §1.2's bit gate covers the *shape* FIELD path and
says nothing about colour; T106's colour-FIELD "identical" is the query trim,
and T111's is the same config under two builds. Neither compares the two
**configurations**, and `color_stage = 48` is a staged path that re-quantizes
coordinates through `ROSHAMBO3_STAGE_INV_Q_XYZ`.

`tickets/T114/color_operating_point_gate.py`: one binary — T111 kept the
`GLOBAL / 0` cells compiled — one corpus, the production PANEL-8, and two
`ScreenConfig`s differing in exactly those two fields, everything else the
shipped combination arm taken by import from
`tickets/T66/screen_panel.py::arm_specs(0.5)["combination"]`.

| group | L | conformers | score words | moved | gids moved | H2D bytes |
|---:|---:|---:|---:|---:|---:|---|
| 0 | 24 | 116,624 | 8,000,000 | **0** | 0 | 25,920,048, identical |
| 6 | 56 | 1,540,787 | 8,000,000 | **0** | 0 | 638,216,856, identical |
| 9 | 56 | 1,802,470 | 8,000,000 | **0** | 0 | 746,612,400, identical |
| 13 | 72 | 1,253,900 | 8,000,000 | **0** | 0 | 639,769,824, identical |
| 17 | 104 | 5,495 | 879,200 | **0** | 0 | 3,876,768, identical |
| | | | **32,879,200** | **0** | **0** | |

Five groups spanning the corpus's whole colour width range, k = 50,000, bit
patterns not `==`, per-group score and gid sha256s equal. The queries carry
**119 colour features** — asserted before the comparison, because a panel that
produced none would make this gate pass having exercised no colour at all.

The likely mechanism, and it is worth stating because it makes the null
expected rather than lucky: the library record has been int16 on the wire since
T87, so re-quantizing an already-quantized coordinate at the same scale is
idempotent — the staged path reads the values the streamed path reads.
**`results/T66`, `T71`, `T104` and `T91`'s comparison describe the binary we
ship.** That was a live exposure until this run and it is now closed.

---

## 6. What migrating a colour corpus does to the ranking

The plane reorder is **not** bit-identical and was never claimed to be:
`results/T106` §2 owes no bit-identity bar, and rests on T105's measured
`|ΔT|` max **4.77e-7** over 320 M pairs. What had never been done is turning
that score-level bound into a **ranking** statement on the corpus the accuracy
campaign used — and T104 screened `color_rsb3/library` in its historical order,
so the exposure was real rather than hypothetical.

Both orders are on disk, and `Rsb3Source(color_features_enum=…)` reads the
refused one deliberately. The historical-order queries come from a generator
built with `pharmacophore.HISTORICAL_FEATURE_ORDER`, whose interaction matrices
are asserted to be the **exact permutation** of the shipped one's under the same
index map, reading the same fdef; and the two corpora's per-type colour counts
agree **exactly by name** on every group checked, with `n_real` equal
element-wise. So the two arms differ in the plane order and the record version
and in nothing else.

### 6.1 The measurement, aligned by conformer

`tickets/T114/color_plane_order_diagnose.py`, `DenseScores` — every conformer in
corpus order, so row *i* is the same conformer in both arms. Group 0, 116,624
conformers × 8 queries:

| arm | column | words moved | max abs Δ | p99 abs Δ | > 1e-3 |
|---|---|---:|---:|---:|---:|
| **shape-only** | all four | **0 / 18,659,840** | **0.0** | 0.0 | 0 |
| combination | `self_overlap_library` | **0 / 932,992** | **0.0** | 0.0 | 0 |
| combination | `self_color_library` | 492,368 | 1.91e-5 | 7.6e-6 | **0** |
| combination | `tanimoto_combination` | 667,921 | 7.70e-3 | **1.84e-5** | 439 |
| combination | `tanimoto_shape` | 632,709 | 1.64e-1 | 5.94e-5 | 904 |
| combination | `tanimoto_color` | 764,744 | 1.64e-1 | 5.77e-5 | 941 |

**`results/T88` §3 is reproduced, not contradicted, and on ground T88 did not
cover.** A shape-only screen across the two records — v1 split against v2
merged, `L` 16 against 24 — moves **0 of 18,659,840 words**, and the
library-intrinsic shape column `self_overlap_library` is 0 moved at max Δ
exactly 0.0 inside the colour screen too. That is T88's bit-identity, on Volta
and on a different corpus.

**T105 is consistent once the two figures are read as what they are.** The
library-intrinsic *colour* column moves by at most **1.91e-5**, nothing above
1e-3 — reassociation of a float32 colour accumulation under the permutation,
T105's own mechanism. T105's 4.77e-7 is a **fixed-pose per-pair** bound;
everything else here is **post-optimization**, and `decisions/D001` / T25
already record that Adagrad turns a fixed-pose null into p99 2.6e-5.

**The amplification is the pose, not the score.** `tanimoto_shape` cannot move
at fixed pose — the shape payload is bit-identical, proved on the row above —
yet it moves by up to 0.16 inside the combination screen. A ~1e-5 colour
perturbation tips a start point or an Adagrad trajectory on **439–941 of
932,992 conformers, 0.05–0.1%**, and those land on a different local optimum.
p99 stays at 2–6e-5.

### 6.2 Does anything cross the cut?

`tickets/T114/color_plane_order_gate.py`, PANEL-8, the shipped combination arm,
`MoleculeTopK` at `k = n_molecules` — a complete 407,664-compound ranking per
query, so a cut boundary is exact:

| cut | n | compounds crossing, all 8 queries |
|---|---:|---:|
| 0.5% | 2,039 | 1 (GBA only) |
| **1%** | **4,077** | **0 — on every one of the 8 queries** |
| 5% | 20,384 | 3 (ESR1_ago, ESR1_ant, GBA — one each) |

**Against what.** `doc/METRICS.md` §6 records the shipped configuration's own
score error on the retrieved list at **1.78e-3**. A p99 of 2–6e-5 is **30–90×
below the error the project already accepts**, and D013 accepts on recall and
ranking rather than on bits in the first place. This sits well inside the
established regime.

**So: the accuracy campaign ran on historical-order corpora; migrating them
moves post-optimization scores by p99 2–6e-5 through 0.05–0.1% of conformers
reposing; and 0 compounds cross the 1% boundary on any of 8 queries.** Bounded,
mechanistically explained, and below accepted noise.

**The honest limit of what that says.** This is a whole-corpus ranking of
PANEL-8 against all 407,664 compounds. It is **not** a per-target EF delta:
`results/T66`, `T71` and `T104` rank against per-target populations with
per-target denominators and the T65 / D002 masks, and whether the four crossing
compounds are actives is a question this measurement does not ask. Whether the
campaign is re-run on migrated corpora is not this ticket's decision.

### 6.3 A defect in this ticket's own first instrument, recorded

The first run of the plane-order gate reported `max |Δ| 4.74e-4` with 68.7% of
words moved. **Both figures are retracted.** It subtracted rank slot *i* of one
ranked list from rank slot *i* of the other, and slot *i* holds a different
compound in the two arms as soon as the ranking moves at all — so it reported
the ranking's movement dressed as the arithmetic's. Neither `results/T88`
(merged record, max Δ exactly 0.0) nor `results/T105` (the reorder alone,
4.77e-7) could account for it, and when both halves of a decomposition are
measured near zero and the whole comes back three orders larger, the instrument
is the first suspect. The gate now joins score deltas **on the compound**, the
defect is written into the source, and the cut-crossing counts above were set
comparisons throughout and are unaffected.

---

## 6A. Session B — combination, which had never been run

Every head-to-head this project has run — T68's five sessions, T83's A2 — is
mode 1. Meanwhile the submission's *accuracy* claim is a combination claim: T71
and T104 report combination EF on both panels and T91 reports ROSHAMBO2's. **The
two programs were compared on retrieval quality with colour in the objective and
on speed without it.** This is the first time anyone has timed them against each
other on the workload the accuracy claim is about.

D025 **mode 3 on both sides** at the paper's λ = 0.5, on the same 8-query panel
and the same 20,381,286 conformers as session A, in one `flock` hold and one
clock region. Neither arm's specification is written down in this ticket's code:
ours is imported from `tickets/T66/screen_panel.py`'s
`arm_specs(0.5)["combination"]` and the baseline's from
`tickets/T91/run_roshambo2_panel.py`'s, which is what keeps the speed lane and
the accuracy lane describing the same arm.

| baseline | mode | ROSHAMBO2 s | ROSHAMBO3 s | **ratio** | incl. preload |
|---|---|---:|---:|---:|---:|
| **`u2`, as released** | **in_memory** | **2936.72** | **19.756** | **148.6×** | **152.7×** |
| `u2_color_skip` | in_memory | 3335.38 | 19.756 | 168.8× | 175.2× |
| `u2_color_skip` | eager | 3394.00 | 19.756 | 171.8× | 171.8× |
| `u2`, as released | eager | **not run — §6A.1** | | | |

**Lead with 148.6×.** On the shape arm `u2_color_skip` was both the honest
comparison and the smaller ratio, so leading with it cost nothing. **On this arm
the ordering inverts**: the smaller ratio is `u2` **as released**, and quoting
168.8× instead would be quoting the larger number against a baseline we modified
ourselves — which is the exact thing `u2_color_skip` exists to prevent. The
conservative arm is whichever is slower to beat, not whichever carries the
label.

**And 148.6× rather than 152.7×, for the same reason and not by convention.**
Both columns are above, and the choice between them is an argument rather than
an inherited habit. The `in_memory` arm spends **79.27 s** loading 50.86 GB of
corpus into RAM before its search begins, and the leading number **does not
charge ROSHAMBO2 for it** — 79.27 s of their work, excluded. ROSHAMBO3 has no
preload to exclude in return: it drops the page cache and verifies the drop
before every one of its 11 repeats, so its 19.756 s contains its own reading,
every time. Where two defensible readings exist we take theirs, which is the
same principle that makes `in_memory` the row we quote at all
(§6A.1) — and it is the reading a reviewer is actually testing.

ROSHAMBO3: 19.7561 s median of 11 repeats, min 19.7283, max 19.9050, page cache
dropped and `mincore`-verified before **each** repeat — **130 files,
5,116,489,365 B, `resident_fraction_after_drop` 0.0461.** That drop list is
built by `os.walk` over the corpus root rather than a flat glob, so it covered
the colour planes without being told they were there; the shape corpus's was 93
files and 3,112,793,785 B.

ROSHAMBO2: one timed repeat per cell. The probe measured a full combination
screen at roughly an hour, so two replicates on four cells is most of a day;
T68's own `corpus2` session gave its most expensive arm one replicate for the
same reason and said so. Session A measured these same arms' replicate
dispersion on this machine at **0.17%–2.4%** — that is a statement about
dispersion from another session and is not combined with anything here.

### 6A.1 Why `u2 eager` was not run

**It is a decision, not an omission.** `in_memory` is **ROSHAMBO2's most
favourable data mode**, and that is exactly why it is the one to quote: it
preloads the entire corpus into RAM — **50.86 GB resident, 125.91 s of preload
excluded from the search time** — and then never touches the disk again.
**ROSHAMBO3 has no such mode.** Our arm drops the page cache and verifies the
drop before every one of its 11 repeats, so it reads the corpus cold each time.
The `in_memory` row therefore puts our cold-read pipeline against their fully
warm one, and it is the row A2's headline compared against. `eager` mostly
re-measures cold-read cost, which session A already characterized on the shape
arm where the two modes differ by 6% — and the two colour `u2_color_skip` rows
above differ by 1.8%, which is the same statement again.

The session was ended after `combination_u2_inmem` by
`tickets/T114/stop_after_cell.sh`, from outside the worktree: `bash` reads a
script incrementally as it executes, so editing the running
`run_headtohead.sh` could have made it execute garbage from a shifted file
offset. Ending it also dropped the session's last cell,
`combination_uc_eager_b` — a second replicate of `u2_color_skip` eager, which
would have carried this session's own dispersion. That is the price of the
mechanism and it is stated rather than absorbed: **no cell of session B has a
measured spread**, and the dispersion figure quoted above is session A's.

### 6A.2 Where the wall went

| arm | mode | wall | read+decode | host prep | device (one pybind call) | host reduce |
|---|---|---:|---:|---:|---:|---:|
| `u2`, as released | in_memory | 2936.72 | 0.00 | 81.59 | 2575.64 | 279.49 |
| `u2_color_skip` | in_memory | 3335.38 | 0.00 | 81.34 | 2972.33 | 281.72 |
| `u2_color_skip` | eager | 3394.00 | 69.04 | 84.22 | 2966.99 | 273.74 |

Both `in_memory` arms preload to **50.86 GB resident** (53.08 / 53.09 GB at the
end) in 79.27 s and 125.91 s respectively.

ROSHAMBO3's own split: `kernel_s` **17.362 of 19.756 — 87.9%**, `h2d_s` 0.841
over 8,596,396,728 B, `precompute_s` 0.142, `index_s` 0.147, `topk_s` 0.097,
`alloc` + `free` 0.006, 321 launches. **More kernel-bound than the shape arm's
84.6%**, which is what an objective with more arithmetic per pair and the same
bytes on the wire should look like.

### 6A.3 `u2` against `u2_color_skip` on this arm

The ticket predicted the two arms would **converge** here: `fc711a9` skips
colour *evaluation when colour scoring is off*, and on this arm it is on, so the
commit's own subject line should have nothing to do.

**They did not converge, and the gap runs the other way.**

| | session A (shape) | session B (combination) |
|---|---:|---:|
| `u2` in_memory | 1386.13 s | **2936.72 s** |
| `u2_color_skip` in_memory | 614.40 s | 3335.38 s |
| `u2` / `u2_color_skip` | **2.256× slower** | **0.880× — faster** |

On the shape arm the as-released build is 2.26× slower, which is the colour-loop
defect running over the padding region with its results discarded. On the
combination arm the as-released build is **1.136× faster** than the one we
patched. The difference sits in device time — 2575.64 s against 2972.33 s,
**396.69 s, a 1.154× gap on that stage alone** — and not in host prep (81.59
against 81.34) or host reduce (279.49 against 281.72), which are equal to well
under a percent.

**Unexplained, but localized — and the localization is a measurement, not a
hedge.** The two arms' host stages are equal to well under a percent: host prep
81.59 s against 81.34 s (0.31%), host reduce 279.49 s against 281.72 s (0.79%),
read+decode 0.00 s on both because both are `in_memory`. **The entire 398.66 s
of wall difference is 396.69 s of device time**, 99.5% of it. That does not say
what the gap is, but it says what it is **not**, and it rules out a whole class
of explanations by measurement rather than by argument: not the environment, not
host scheduling or CPU contention (the host stages would have moved), not the
page cache or the disk (neither arm touches it), and not thermal drift between
cells (§8: busy-only 1335.0 MHz on every cell of this session, zero throttled
busy samples, `sw_power_cap` never active). **Whatever it is, it is inside the
one pybind call**, which is where the next person should look.

**What is left is genuinely unexplained, and at one timed repeat per cell it
cannot be explained here.** Both rows are `advisory`, neither has a replicate,
and session A's
measured replicate dispersion on these same arms was 0.17%–2.4% — smaller than
13.6%, but that is a dispersion from a different session on a different corpus
and it does not license a significance claim about these two. Two things would
settle it and neither is this ticket's to run: **replicates on both arms in one
session**, and a **full diff of `fc711a9` against `7ff8237`** to establish
whether it changes anything beyond the colour-evaluation skip.

**What it is not.** It is not evidence that our fix is a pessimization on the
combination objective, and it is not evidence that it is not. Nothing here is
attributed to `fc711a9` by elimination. The number that gets quoted — 148.6× —
is the one that does not depend on resolving this at all, because it is the
as-released arm.

### 6A.4 Pitfall 8: this is not divisible into session A

The two sessions read different corpora with different padding. The ROSHAMBO2
colour h5's padded width `L` runs **{68, 80, 88, 92, 96, 100, 104}** against the
shape h5's {40, 44, 48, 52, 56}, and the `.rsb3` side moved from
`color_padding_efficiency` 0.590 to slot efficiency 0.7686. **A wall time from
one session is not divisible into a wall time from the other**, and the
combination ratio is a ratio within session B only. That is why the cost of
colour in the objective is measured in its own two-cell session (§6A.5) rather
than by dividing 19.756 s into 7.526 s, which would be a ratio between two data
layouts as much as between two objectives.

### 6A.5 What colour in the objective costs — the first Volta measurement

Its own session, **both cells in one `flock` hold and one clock region**, on the
colour corpus, `tickets/T114/run_objective_cost.sh`:

| arm | wall s | min | max | kernel s | H2D bytes |
|---|---:|---:|---:|---:|---:|
| shape (`color=False`) | **8.2028** | 8.1847 | 8.3746 | 6.5181 | 8,504,681,208 |
| combination (mode 3, λ = 0.5) | **19.8285** | 19.7648 | 19.9676 | 17.3632 | 8,596,396,728 |

**Combination costs 2.417× a shape screen of the same corpus** (kernel only,
2.664×). Both cells 11 repeats with 3 warm-up, 1335.0 MHz min = median = max,
throttle 0.000, `sw_power_cap` 0.000, the page cache dropped and verified before
each repeat over the same 130 files / 5,116,489,365 B.

**Why it is not session A's 7.526 s divided into session B's 19.756 s.** That
quotient would be 2.625×, and it would be wrong for the reason pitfall 8 gives:
the two sessions read different corpora. The same shape screen costs 7.5262 s on
the shape corpus and **8.2028 s on the colour one — 9.0% more for the identical
computation**, because the colour corpus's records are wider. Dividing across
sessions would fold that 9% into the objective's cost and call it arithmetic.
**Both cells here are on one corpus in one invocation**, which is the only form
in which the number means what it says.

**Against T63's Blackwell figure, as a cross-architecture note and nothing
more.** T63 *measured* mode 3 at **2.05×** a shape-only screen on sm_120; this
is **2.417×** on sm_70. `decisions/D025` is explicit that 1.25× was a paper
estimate and **must not be quoted**, and its reopening condition is to be read
against 2.05×. The two are not combined and neither is normalized against the
other: different architecture, different toolkit, different corpus, and T63's
denominator was a `PoseSearch.ANALYTIC` shape screen while this one is FIELD.
What can be said is that **the first Volta measurement of this quantity lands in
the same regime as the Blackwell one** — a little over twice a shape screen,
not the quarter-again the paper estimate suggested — and that the combination
objective is therefore affordable on this card too.

One consistency check, not a term in any ratio: the `combination_again` cell
here came out at 19.8285 s against session B's 19.7561 s, **0.37% apart** across
two sessions on two occasions. The head-to-head's combination wall remains
session B's.



## 6B. A usability defect on the shipped API, found by using it

**A shape-only screen of a colour corpus refuses, and the message names the
symptom rather than the fix.**

```
RuntimeError: roshambo3.cuda: the library count vector is 7 wide and the
interaction matrix is 1x1. Both are indexed by feature type id, so they must
agree.
```

The call that produces it is an ordinary one:

```python
api.screen(panel, color_corpus, config=ScreenConfig(color=False), ...)
```

`config.color` is False, so `_check_color` returns immediately, `Rsb3Source` is
built with `color=False` and reads no colour plane, and nothing colour is
computed anywhere. But the library's **count vector is 7 wide whether or not
colour is scored** — it is a property of the corpus — while
`api.load_queries(panel)` without a `color_generator` produces a **1x1**
interaction matrix, and the extension refuses the pair.

The remedy is to pass a `color_generator` to a screen that computes no colour,
which is not a thing a reader would guess from the message. That is what
`tickets/T68/run_roshambo3.py` now does, with the reason written beside it.

**Why it is worth a ticket rather than a footnote.** It is on the shipped path,
not on a harness: a user holding a colour corpus who wants a shape-only screen
of it meets it, and meets it as an error about an interaction matrix they never
asked for. Two fixes suggest themselves and this ticket picks neither — widen
the query's matrix to the corpus's type count when colour is off, since it is
then unused; or say in the message that a `color_generator` is required to
width-match a colour corpus even for a shape screen. It belongs beside **T112**,
whose theme is the legible boundary between what the API refuses and why.

It cost this ticket one cell of session B, which is how it was found: the cell
refused, the session carried on holding its lock (which is the rule working),
and the measurement it was the denominator for moved into its own two-cell
session so its quotient stays inside one clock region.


## 7. The advisories, in full

Every row of this ticket is `advisory`. None of the conditions is a defect in
the measurement, and each is annotated in the record itself rather than left to
be read as one.

1. **CUDA 12.9 is not the pinned 13.2.** Unavoidable: CUDA 13.x dropped sm_70
   outright, so a TITAN V build can only be made on 12.x. Carried verbatim from
   `results/T83/A2` and T68.
2. **The build is `70-real`, not sm_120.** This is the point: the TITAN V is the
   GPU model the comparison paper benchmarked, which is what removes the
   hardware objection from the speed claim rather than arguing around it. No
   score from this ticket is compared against an sm_120 score.
3. **The unsatisfiable pitfall-12 bound.** `bench.rules.check_max_results`
   demands `max_results >= 10 × n_conformers`, i.e. k ≥ 2.04e8 here, which a
   device-resident top-K cannot be asked for. The condition is unsatisfiable,
   not unmet; the pitfall it guards — roshambo2's shipped 10,000 applied *per
   batch before merging* — is addressed by setting `max_results` and `-k`
   explicitly on **both** sides, which every session here does. A known harness
   defect recorded on T69.
4. A quiescent allocation outside this environment was present on GPU 0; utilization and clocks were checked before each timed cell.
5. **`throttle_fraction` above the 0.05 advisory threshold on the ROSHAMBO2
   rows** (0.0705, 0.0714). `bench.clocks`'s raw fraction counts `GpuIdle` as a
   throttle reason, and these arms are ~50% host-bound so they park the card
   while they reduce on the CPU. §8 disambiguates it.
6. **The launch-structure advisory** (T102): `run_roshambo3.py` does not pass
   `RunRequest(launch=LaunchShape.from_screen(...))`, so the launch-size rule
   falls back to the corpus total. New since A2; it is a harness reporting gap,
   not a property of these runs, whose launches are 63,493 conformers each.
7. **Too few timed repeats on the ROSHAMBO2 rows**, against
   `bench.rules.REQUIRED_TIMED_REPEATS = 11`. **Two** per cell in session A and
   **one** per cell in session B. The rule is T04's, written for kernel
   microbenchmarks, and it is satisfiable on the ROSHAMBO3 side — every
   ROSHAMBO3 row here is 11 repeats with 3 warm-up — and not on the baseline's:
   a shape repeat costs 10–24 minutes on this corpus and a combination repeat
   costs **49–57 minutes**. Eleven repeats of session B's four cells would be
   roughly forty hours of one card.

   **What that costs, stated rather than hidden.** Session A's cells carry their
   spread and it is tight — 613.88–614.93, 648.58–664.02, 1384.42–1387.84, and
   the `u2` eager pair likewise, i.e. **0.17%–2.4%**. **Session B's cells have
   no spread at all**: one repeat each, and the replicate cell that would have
   given the session its own dispersion (`combination_uc_eager_b`) was dropped
   when the session was ended early (§6A.1). Session A's dispersion is a figure
   from a different session on a different corpus; it is context, and it is not
   combined with anything in session B nor used to make a significance claim
   about the 1.136× gap in §6A.3.

---

## 8. Clocks — D023's reopening condition did not fire

D023's condition for the headline regime is *"a throttle fraction materially
different between arms"*. `tickets/T68/clock_check.py`, busy-only
(`utilization ≥ 50%`):

| session A cell | samples | busy | clock over busy samples | throttle reasons on busy samples | `sw_power_cap` |
|---|---:|---:|---|---|---:|
| `u2` eager | 2,702 | 1,938 | 1320 / **1335** / 1335, mean 1334.94 | **none, all 1,938** | 0 |
| `u2` in_memory | 2,693 | 1,934 | 1320 / **1335** / 1335, mean 1334.96 | **none, all 1,934** | 0 |
| `u2_color_skip` eager | 1,249 | 494 | 1320 / **1335** / 1335, mean 1334.85 | **none, all 494** | 0 |
| `u2_color_skip` in_memory | 1,246 | 493 | 1320 / **1335** / 1335, mean 1334.94 | **none, all 493** | 0 |
| ROSHAMBO3 | 81 | — | 1335 / **1335** / 1335 | throttle fraction 0.000 | 0 |

**Busy-median spread across cells: 0.0 MHz. `d023_reopening_condition_fired:
false`.** Every sample carrying a throttle reason is `GpuIdle` on an idle sample
(87–96 per cell); **no busy sample on any cell carries any throttle reason at
all**, and `sw_power_cap` is active in **0 samples everywhere**. This is the
same clock region T68 and A2 ran in, to the megahertz — and the fact that it
came out the same on a third occasion is why the arms were re-run rather than
reused.

**Not a profiler holding the clock** (D007's trap): `profilers.txt` is written
from `ps aux | grep -E "[n]cu|[n]sys"` before each session takes the flock and
is empty for every session; every record's `profiler_control` is clear at both
ends; and the raw traces are not steady — they read 135 MHz whenever the card
goes idle between launches, which is a card boosting rather than a tool holding.

**Session B, the same check, and it did not fire either:**

| session B cell | samples | busy | clock over busy samples | throttle reasons on busy samples | `sw_power_cap` |
|---|---:|---:|---|---|---:|
| `u2` in_memory | 2,864 | 2,426 | 1320 / **1335** / 1335 | **none, all 2,426** | 0 |
| `u2_color_skip` in_memory | 3,288 | 2,806 | 1320 / **1335** / 1335 | **none, all 2,806** | 0 |
| `u2_color_skip` eager | 3,223 | 2,808 | 1200 / **1335** / 1335 | **none, all 2,808** | 0 |
| ROSHAMBO3 combination | — | — | 1335 / **1335** / 1335 | throttle fraction 0.000 | 0 |

Busy-median spread across cells **0.0 MHz**, `d023_reopening_condition_fired:
false` (`clock_check_combination.json`). One cell touched 1200 MHz on a single
busy sample against a median of 1335 with no throttle reason attached — a
boost-clock transition, not a throttle, and it moves no median.

The step-budget session's two cells and the objective-cost session's two cells
all report min = median = max = **1335.0 MHz** with throttle 0.000 and
`sw_power_cap` 0.000, so both internal quotients are one clock region as well.

**Every ratio in this document therefore sits at the same achieved clock — 1335
MHz — as T68's and as A2's**, across five sessions and three separate days of
measurement.

---

## 9. What this is, and is not

**It is** a wall-clock ratio between two tools, on one card, in one session, at
each tool's own shipped configuration, on the same 20,381,286 conformers and
the same 8 queries, with the population equality proved on both pairs and the
answers shown to agree.

**It is not** an absolute throughput number. D023 licenses tachi to produce a
quotable *comparison ratio* and continues to forbid a quotable absolute
pairs/s; nothing here grounds a projection to 1e9 or 1e11 (D006, unchanged).

**The change from 57.0× is 4.025× of engine, and nothing else.** The baseline
reproduces to within 1.7% (§1.1); the corpus, panel, `k`, step count, workers,
prefetch depth and clock region are the same as A2's; and the answer is
bit-identical to the one A2's predecessor produced (§1.2). The 4.025× spans
every change since `da498d94` — T85's launch coalescing, T86's count vector,
T87's int16 wire, T88's merged record, T92's staging policy, T93, T96, T97,
T105's query-record trim, T106, T107's locked operating point, T109 and T111 —
and §1.3 attributes it: about 3.04× in the kernel and the rest in per-launch
overhead that has essentially vanished.

**The two tools still do not compute the same thing**, and that is T68's §10
item 8 unchanged and still the most important caveat. 25 steps at `lr_t` 0.4
against 100 at 0.1; a grid-interpolated query field against an analytic one.
§2 measures the step-budget half of that at **3.273×** so a reader can subtract
it rather than take it on trust; the pose-search half is not separable and is
not claimed to be.

**This build is 2.25% slower on Volta than the pre-lock one, deliberately.**
T107 measured staging colour at `color_stage = 48` at +4.3% on sm_120 and
−2.25% on sm_70, and the operating point was locked for Blackwell with that
loss accepted. Session B's numbers carry that recorded trade; it is not a
regression to chase.

**Still not measured**: ROSHAMBO2's enrichment against ours on LIT-PCBA at
matched populations (T91 did DUDE-Z); block coalescing, which A1 puts at a
further 1.7–2.7× and which is not implemented; and any Blackwell head-to-head,
which would be a different card and a different bottleneck margin.

---

## 10. Files

| file | what |
|---|---|
| `summary_headline.json` (its `TABLES_headline.md` rendering is in the internal record) | session A's rows, ratios, stage split and in-memory correction, generated by `tickets/T68/summarize.py` |
| `summary_combination.json` | session B — §6A |
| `summary_step_budget.json` | §2 |
| `summary_objective_cost.json` | §6A.5 |
| `headline/`, `combination/`, `step_budget/`, `objective_cost/`, `combination_probe/` | every run record and clock trace, per session (GPU-state files and `profilers.txt` are in the internal record) |
| `clock_check_headline.json`, `clock_check_combination.json` | §8, busy-only clock distributions and D023's verdict on both timed sessions |
| `build_check.json` | the loaded `.so`: embedded ELF, absence of PTX, sha256, `HEAD:src` |
| `gates/topk_bitwise_vs_T68.json` | §1.2 |
| `gates/color_operating_point_gate.json` | §5 |
| `gates/color_plane_order_gate.json`, `color_plane_order_diagnose.json` | §6 |
| `gates/shape/`, `gates/combination/` | the same-conformers and top-K agreement gates |
| `gates/color_build_env_*.json` | fdef, RDKit and preparer hashes on all three interpreters |
| `color_corpus_check.json`, `convert_color_rsb3.log` | §3, the convert checked against roci's copy |
| `color_h5_backfill.json`, `color_h5_backfill.log` | §3, the two rebuilt shards and their provenance |
| `METHOD.md` (internal record) | the construction, and the two data defects in full |

Scripts: `tickets/T114/` and the T68 harness it drives. Every one was committed
before it ran.
