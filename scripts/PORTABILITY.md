# Cross-backend portability runs

These runs fill the camera-ready portability table and the CPU thread-scaling
appendix:
- **The engine:** one engine from one source commit.
- **The corpus:** LIT-PCBA, a format-3 corpus with shape and color in one build (20,381,286
  conformers, about 2.7 GB on disk),
  screened with the eight PANEL-8 queries.
- **Modes:** shape, rescore and combo.
- **Devices:** every device in `../data/portability-devices.json`.

`analyze_portability.py` refuses to put rows in one table if they come from
different commits, corpora or query panels, or from a dirty tree. That makes the
setup below matter more than it looks.

`portability_campaign.sh` drives every run on one machine. It uses the same
`screen_smiles.py` flags as the `portability` make targets. Its configuration comes
from environment variables, and it writes outside the checkout so the source
tree stays clean.

## 1. Every machine

1. **Check out the frozen commit**, the same one everywhere, from a git clone or
   a bundle of it. A source tarball will not do: without `.git` the run records
   say `sha "unknown"` and are refused.

   ```sh
   mkdir -p ~/r3bench && cd ~/r3bench
   git clone -b <branch> <repository or bundle> src
   git -C src rev-parse HEAD          # must print <FROZEN>
   git -C src status --porcelain      # must print nothing
   ```

2. **Build the tool from that checkout** into a venv **outside** it. You need
   Python 3.11+ and a C++ compiler. pip fetches CMake if none is installed.
   Install the pinned RDKit first, because RDKit types the query pharmacophores.

   | Machine | Build flags |
   |---|---|
   | CUDA GPU | `--config-settings=cmake.define.ROSHAMBO3_CUDA=ON --config-settings=cmake.define.CMAKE_CUDA_ARCHITECTURES=<arch>-real` with `<arch>` 120 (RTX PRO 6000), 89 (L4), or 70 (TITAN V; needs a CUDA 12.x toolkit, since 13.x rejects sm_70) |
   | CPU only | `--config-settings=cmake.define.ROSHAMBO3_CUDA=OFF` |
   | Apple Silicon | `--config-settings=cmake.define.ROSHAMBO3_CUDA=OFF --config-settings=cmake.define.ROSHAMBO3_METAL=ON` (Command Line Tools suffice) |

   ```sh
   python3 -m venv venv
   venv/bin/python -m pip install --upgrade pip "rdkit==2026.09.1"
   venv/bin/python -m pip install <flags> ./src
   git -C src status --porcelain      # still nothing
   ```

3. **Stage the data on local disk**, not a network mount:
   - the LIT-PCBA format-3 corpus directory (the one holding `corpus.json`);
   - `PANEL-8.sdf`, which is `../data/queries/PANEL-8.sdf`.

   Both can be rebuilt from public data (`build_litpcba.py`, see `LITPCBA.md`),
   but copying the corpus is faster than rebuilding it.

4. **Set the driver's environment** (the paths are examples):

   ```sh
   export R3_PYTHON=~/r3bench/venv/bin/python R3_SRC=~/r3bench/src \
          R3_CORPUS=~/r3data/LIT-PCBA-color R3_PANEL=~/r3data/PANEL-8.sdf \
          R3_OUT=~/r3bench/out
   export DEVICE_KEY=<key> BACKEND=<cuda|cpu|metal>   # see the table below
   DRIVER=~/r3bench/portability_campaign.sh   # a copy of this directory's script
   ```

   The driver is a copy kept outside the checkout. It postdates the commit the
   camera-ready tool was frozen at, and each run records its sha256.

   `R3_SRC` is the engine checkout the tool was installed from, and the driver
   runs `$R3_SRC/publication/scripts/screen_smiles.py`, which is the layout of
   the development repository the campaign ran from. With the public
   repositories, link this repository into the engine checkout and keep the
   link out of its status, so the tree still records as clean:

   ```sh
   ln -s <this repository> "$R3_SRC/publication"
   echo publication >> "$R3_SRC/.git/info/exclude"
   ```

Every run takes the machine's own lock:
- CUDA takes the per-device GPU lock.
- CPU takes the CPU lock.
- Metal takes both the CPU lock and the Metal device lock.

A run waits up to an hour for a busy lock rather than proceeding unlocked.

## 2. Per device

```sh
sh $DRIVER env       # install provenance, tool build stamps, topology -> $R3_OUT/$DEVICE_KEY/env.json
sh $DRIVER smoke     # one query, one combo pass: proves the backend accepts every bucket
sh $DRIVER table     # 1 warm-up + 5 timed repeats (CPU: 3) per mode, resumable
sh $DRIVER scaling   # Linux CPU hosts only: the pinned thread ladder below, resumable
R3_THREADS="4 8 10 12 14" sh $DRIVER threads   # any CPU host: unpinned worker-count ladder
```

The `env` record matters for CPU-only and Metal builds. Only the CUDA extension
stamps a commit, so for those builds the run records show
`tool.git_sha: "unknown"`. `env.json` holds:
- the checkout and install the tool came from;
- the CPU and Metal build stamps, including the CPU kernel target selected at
  run time;
- the query panel's sha256.

| Device | `BACKEND` | `DEVICE_KEY` | Table duration (estimate) |
|---|---|---|---|
| RTX PRO 6000 Blackwell Max-Q | `cuda` | `rtx-pro-6000` | minutes |
| TITAN V | `cuda` | `titan-v` | ~10 min |
| L4 (cloud, G2, 16 vCPU) | `cuda` | `l4` | ~15 min |
| Xeon Platinum 8581C (cloud, c4-highcpu-16) | `cpu` | `xeon-8581c` | ~45 min |
| EPYC 9B45 (cloud, c4d-highcpu-16) | `cpu` | `epyc-turin` | ~45 min |
| Neoverse V2 (cloud, c4a-highcpu-16) | `cpu` | `neoverse-v2` | ~1.5 h |
| Apple M4 Pro GPU | `metal` | `m4-pro-gpu` | ~30 min |
| Apple M4 Pro CPU | `cpu` | `m4-pro-cpu` | ~2 h |

### CPU thread scaling

`scaling` screens the first PANEL-8 query in all three modes on each of these
placements:
- **No pinning (`all`):** every vCPU, the table's default.
- **`8x1`:** one thread on each of 8 physical cores.
- **`4x2`:** both SMT siblings of 4 cores (only where SMT exists).
- **`4x1`, `2x1`, `1x1`.**

Pinning works by `taskset`, from the topology in
`/sys/devices/system/cpu/*/topology`, with `--workers` set to match. Arms smaller
than the machine skip core 0, which takes the guest's interrupt load.

Most arms get 1 warm-up and 3 timed repeats. `2x1` and `1x1` get 1 warm-up and 1
timed repeat, since single-thread timing varies little and those arms dominate
the cost.

On a 16-vCPU x86 VM (8 cores × 2 SMT), the unpinned run is the 8×2 point. The
SMT contrasts are:
- 4×2 vs. 4×1 (same cores);
- unpinned vs. 8×1 (same cores);
- 4×2 vs. 8×1 (same thread count).

### CUDA machines

Before starting, confirm the card is idle and no profiler holds its clocks:

```sh
nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory --format=csv
ps aux | grep -E "[n]cu|[n]sys"
export CUDA_MPS_PIPE_DIRECTORY=$HOME   # a foreign MPS daemon otherwise hangs context creation
```

On a cloud VM, pick a host shape with at least 16 vCPUs. The end-to-end time
includes host-side decoding, so the smallest shapes measure the host, not the
GPU.

### Cloud CPU machines

By default the CPU backend uses every logical CPU the process may run on, SMT
siblings included, and the record says how many. Leave the VM otherwise idle.
The run records achieved core frequency.

### The Mac (Apple Silicon)

The system `python3` is too old, so install a current one first, for example
`brew install python@3.12`. Then:

1. **Set up** with the steps in section 1, using the Apple Silicon build flags and
   `python3.12 -m venv venv`.

2. **Check the backend:**

   ```sh
   venv/bin/python -c 'from roshambo3.backend import metal; print(metal.available())'   # True
   ```

3. **Prepare the machine:**
   - Plug in the power adapter.
   - Turn off Low Power Mode: `pmset -g | grep lowpowermode` should show 0.
   - Quit other applications.
   - Do not use the machine during a run. `caffeinate` keeps it awake.

4. **Metal GPU** (set `BACKEND=metal` and `DEVICE_KEY=m4-pro-gpu` in the step 4
   environment):

   ```sh
   sh $DRIVER env && caffeinate -dims sh $DRIVER smoke   # stop here and report if this fails
   caffeinate -dims sh $DRIVER table
   ```

5. **CPU:**

   ```sh
   export BACKEND=cpu DEVICE_KEY=m4-pro-cpu
   sh $DRIVER env && caffeinate -dims sh $DRIVER smoke && caffeinate -dims sh $DRIVER table
   ```

6. **CPU thread ladder.** The OS places the workers, since macOS has no affinity
   control. On a 10P+4E M4 Pro, the arms above 10 threads add efficiency cores:

   ```sh
   R3_THREADS="4 8 10 12 14" caffeinate -dims sh $DRIVER threads
   ```

7. **Archive** `~/r3bench/out` and return it to whoever runs the import:
   `tar czf r3bench-out-mac.tgz -C ~/r3bench out`. One tarball holds both
   `m4-pro-gpu/` and `m4-pro-cpu/`.

What the Mac records capture:
- The Metal record captures the GPU core count from `system_profiler`.
- The CPU record captures the performance and efficiency core counts.
- macOS exposes no unprivileged frequency counter, so these rows record power
  settings and thermal state instead of clocks.
- macOS has no CPU affinity control, so the pinned `scaling` ladder is Linux-only.
  `threads` varies only the worker count.

## 3. Bring the results back

The driver writes the following under `$R3_OUT/<DEVICE_KEY>/`:
- `env.json`;
- `smoke/panel1-combo.*`;
- `table/panel8-{shape,rescore,combo}.{json,csv,telemetry.csv,run.json}`;
- `scaling/<arm>/panel1-<mode>.*`.

Copy each device's directories into the paper repository:
- `table/` and `env.json` go to `runs/portability/<DEVICE_KEY>/`;
- `scaling/` goes to `runs/portability-scaling/<DEVICE_KEY>/`;
- `smoke/` goes to `runs/portability-smoke/<DEVICE_KEY>/`.

Then run:

```sh
python scripts/analyze_portability.py --require-all
```

This prints each device's rates and writes `generated/tables/portability.tex`,
or names the first comparability rule a run broke. The run records contain host
names and local paths. Shorten any cloud FQDNs, which embed the project and zone,
before publishing.
