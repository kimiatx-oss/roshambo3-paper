# 3CR stability and saturation on roci at 3bb39f69 (2026-10-23)

References to `results/`, `tickets/`, `doc/`, `hosts/` and other files not in this repository point at the internal development record.

3CR is a confidential internal library. Nothing here carries a 3CR SMILES, id or structure, and the query's SMILES are withheld. Only the approved totals, rates and the query file's hash appear.

These are the cells behind `fig:saturation`, `ComboQ*` and `ThreeCr*`. They ran on roci (RTX PRO 6000 Blackwell Max-Q, sm_120) at the frozen benchmark commit 3bb39f69, on the format-3 3CR.

## How it ran

- The command was `FROZEN=3bb39f69… CUDA_SRC_SHA=402af23d… OUT=$EXTERNAL_DATA CORPUS_3CR=[withheld] sh hosts/run-roci.sh stability saturation`.
- The build is `$EXTERNAL_DATA`, the same one the 3bb39f69 rerun staged. Its stamp is `3bb39f69 Release 120-real 402af23d… False`, and the checkout is clean.
- It runs the Makefile `stability`, `saturation` and `saturation-q16` targets. The exact argv is in the internal development record.
- The query is the private 3CR query file (withheld), sha256 `3de7b01e31588f6358dfce93bad77c33715d103abbcaa82ff386f8586fbe5c61`. The script checks it.
- Before each step, preflight required no GPU compute process, utilization of 5 % or less, no ncu, nsys or MPS daemon, and a 1-minute load below 2. Both steps passed (preflight log in the internal development record).
- Each screen held the per-device GPU lock (`gpu.lock_held: true` in every report). The script also held the default-base lock.
- The two steps took 11:28:57 to 12:17:17Z.

## Corpus identity (`corpus-identity.json`)

| field | value |
|---|---|
| corpus.json sha256 | [withheld] |
| fingerprint | [withheld] |
| ids_sha256 | [withheld] |
| molecules_sha256 | [withheld] |
| conformers / molecules | 374,226,435 / 75,157,279 |
| disk bytes | [withheld] (75.2 GB rounded; see `ThreeCrDiskGigabytes`) |

Every report records the same corpus identity (withheld here).

## Results

The rate is pair evaluations divided by the median `screen_call_wall_s`. That is the generator's `read_timing`. The manuscript columns are the submission's format-2 August runs, which this repository does not ship.

| q | repeats | median wall s | manuscript wall s | median kernel s | manuscript kernel s | M eval/s | manuscript M eval/s | Δ rate |
|---|---|---|---|---|---|---|---|---|
| 1 | 5 | 35.505 | 35.234 | 16.120 | 16.880 | 10.54 | 10.62 | −0.8 % |
| 2 | 3 | 51.816 | 53.725 | 32.812 | 34.805 | 14.44 | 13.93 | +3.7 % |
| 4 | 5 | 88.130 | 92.640 | 68.538 | 72.437 | 16.99 | 16.16 | +5.1 % |
| 8 | 3 | 161.293 | 171.701 | 141.236 | 148.750 | 18.56 | 17.44 | +6.5 % |
| 16 | 3 | 307.489 | 330.326 | 286.833 | 301.730 | 19.47 | 18.13 | +7.4 % |

The derived values below use the generator's formulas:

| value | here | manuscript |
|---|---|---|
| `ComboQEightToSixteenGainPercent` | 4.9 | 4.0 |
| `ThreeCrDiskGigabytes` | 75.2 | — |
| `ThreeCrQOneWallSeconds` | 35.51 | 35.23 |
| `ThreeCrStoredGigabytesPerSecond` (disk GB / q1 wall) | 2.12 | — |
| `ComboQSixteenMillionConformersPerSecond` | 1.22 | 1.13 |

Wall-time spread (max − min over median) was 1.11 % at q1, 0.75 % at q2, 0.15 % at q4, 0.39 % at q8 and 0.06 % at q16.

Telemetry, from timed samples with utilization above 50 %:
- At q1 the median SM clock was 2160 MHz, with SW power cap active in 16 % of samples.
- From q4 up, the card sat at its 300 W cap the whole time, and the median SM clock was 1927, 1830 and 1777 MHz at q4, q8 and q16.

## Reading

- **Kernel time is 4.5 to 5.7 % lower at every q.** The scored set is the same (same ids). The cause is not attributed here. Candidates are format 3's real-atom-sorted groups and a different build (3bb39f69 against August's 3960ca81, nvcc 13.2.86 against 13.2.78).
- **The q1 wall is unchanged (+0.8 %).** q1 is host-bound: its wall is 35.5 s against a 16.1 s kernel, with the corpus warm in page cache.
- **`ThreeCrStoredGigabytesPerSecond` is 2.12.** It divides the format-3 disk size (75.2 GB) by the q1 wall. The supplement compares this rate against disk and network bandwidth.
- **Saturation gets steeper at high q.** The q8→q16 gain is 4.9 % against 4.0 %, and q16 reaches 19.47 M eval/s against 18.13.

## Files

- `3cr/<cell>.json`: the screen reports. The query SMILES fields are replaced by the query file's sha256. The redaction step also asserts that no SMILES string remains.
- The 1 s GPU telemetry (`3cr/<cell>.telemetry.csv`) and the sha256 and row count of each hit list (`3cr/hits.sha256`) are in the internal development record. The hit lists hold library ids and are not published.
- `summary-rates.json`: the table above, computed from the reports.
- Preflight and after-step snapshots and make output (`logs/`) are in the internal development record.
- A leak scan of this directory ran before commit. It checked the query SMILES and every mol_id and gid in the five hit lists (22,554 strings), and found 0 matches.
