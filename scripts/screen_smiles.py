#!/usr/bin/env python3
"""Screen a reproducible query panel against a format-3 ROSHAMBO3 corpus.

Queries may be generated from SMILES or read with their deposited coordinates
from an SDF.  Query preparation is performed once, followed by optional warmup
and timed screens.  ``--backend`` selects CUDA (the default), the native CPU
backend, or the experimental Metal backend.  CUDA screens carry 1 Hz GPU
telemetry under the per-device GPU lock; CPU and Metal screens hold the
installed package's CPU (and Metal device) lock and record the host's CPU
identity, contention, and, on Linux, achieved core frequency.  Timed runs also
carry cache state, build, and source provenance.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import csv
import gc
import json
import math
import os
import platform
import resource
import socket
import statistics
import sys
import time
from pathlib import Path
from typing import Any


SEED = 0xC0FFEE
MODES = ("shape", "rescore", "combo")
BACKENDS = ("cuda", "cpu", "metal")
# The CUDA decode pool the paper's GPU campaign used; CPU and Metal default to
# their backend's own worker policy.
CUDA_DEFAULT_WORKERS = 8


def configure_fd_limit(minimum: int = 4096) -> dict[str, int]:
    """Raise this process's descriptor soft limit when the host permits it.

    Large corpora have many groups, and each screen source retains mmap-backed
    sidecars for the groups it visits.  A completed source also forms a short
    cycle through its prefetcher callbacks, so repeat screens must not rely on
    the interpreter's eventual cyclic-GC schedule to free those mappings.
    """
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    target = min(int(hard), max(int(soft), int(minimum)))
    if target > soft:
        resource.setrlimit(resource.RLIMIT_NOFILE, (target, hard))
        soft = target
    return {"soft": int(soft), "hard": int(hard)}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    query = parser.add_mutually_exclusive_group(required=True)
    query.add_argument("--smiles-file",
                       help="text file containing one SMILES per nonblank line")
    query.add_argument("--query-sdf",
                       help="SDF query panel; deposited 3D coordinates are retained")
    parser.add_argument("--query-limit", type=int,
                        help="use only the first N queries from the input")
    parser.add_argument("--corpus", required=True, help="format-3 corpus directory (corpus.json)")
    parser.add_argument("--source-tree",
                        default=os.environ.get("ROSHAMBO3_SOURCE_TREE"),
                        help="ROSHAMBO3 checkout containing the benchmark harness "
                             "(default: $ROSHAMBO3_SOURCE_TREE; one of the two is required)")
    parser.add_argument("--mode", required=True, choices=MODES)
    parser.add_argument("-k", "--top-k", type=int, required=True,
                        help="number of top molecules retained per query")
    parser.add_argument("--output-prefix", required=True,
                        help="write <prefix>.json and <prefix>.csv")
    parser.add_argument("--repeats", type=int, default=1,
                        help="number of timed screens after one query preparation")
    parser.add_argument("--warmups", type=int, default=0,
                        help="untimed warmup screens before timed repeats (default: 0)")
    parser.add_argument("--query-conformers", type=int, default=1,
                        help="ETKDGv3/MMFF conformers to generate per input SMILES "
                             "(default: 1)")
    parser.add_argument("--mixing", type=float, default=0.5,
                        help="color weight for rescore/combo (default: 0.5)")
    parser.add_argument("--backend", choices=BACKENDS, default="cuda",
                        help="scoring backend (default: cuda)")
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--workers", type=int,
                        help=f"decode/scoring workers; default {CUDA_DEFAULT_WORKERS} "
                             "for CUDA and the backend's own policy otherwise")
    parser.add_argument("--prefetch", type=int, default=3,
                        help="producer queue depth (default: 3)")
    parser.add_argument("--launch-conformers", type=int,
                        help="conformers per CUDA launch; default uses ROSHAMBO3's "
                             "top-K-aware 65,536-conformer policy")
    parser.add_argument("--cache-mode", choices=("warm", "cold"), default="warm",
                        help="cold drops and verifies corpus pages before every timed "
                             "repeat; warm leaves page cache untouched (default: warm)")
    parser.add_argument("--telemetry-interval", type=float, default=1.0,
                        help="nvidia-smi sampling interval in seconds (default: 1)")
    parser.add_argument("--lock-timeout", type=float, default=0.0,
                        help="seconds to wait for the per-device GPU lock; 0 fails fast")
    parser.add_argument("--force", action="store_true",
                        help="replace an existing report/hits/telemetry output set")
    parser.add_argument("--skip-existing", action="store_true",
                        help="return successfully when the complete output set exists")
    args = parser.parse_args(argv)
    if args.top_k <= 0:
        parser.error("--top-k must be positive")
    if args.repeats <= 0:
        parser.error("--repeats must be positive")
    if args.warmups < 0:
        parser.error("--warmups must be non-negative")
    if args.query_limit is not None and args.query_limit <= 0:
        parser.error("--query-limit must be positive")
    if args.query_conformers <= 0:
        parser.error("--query-conformers must be positive")
    if args.workers is not None and args.workers <= 0:
        parser.error("--workers must be positive")
    if args.workers is None and args.backend == "cuda":
        args.workers = CUDA_DEFAULT_WORKERS
    if args.prefetch < 0:
        parser.error("--prefetch must be non-negative")
    if args.launch_conformers is not None and args.launch_conformers <= 0:
        parser.error("--launch-conformers must be positive")
    if args.telemetry_interval <= 0:
        parser.error("--telemetry-interval must be positive")
    if args.lock_timeout < 0:
        parser.error("--lock-timeout must be non-negative")
    if args.query_sdf and args.query_conformers != 1:
        parser.error("--query-conformers only applies to --smiles-file")
    if args.force and args.skip_existing:
        parser.error("--force and --skip-existing are mutually exclusive")
    if not 0.0 <= args.mixing <= 1.0:
        parser.error("--mixing must be in [0, 1]")
    return args


def read_smiles(path: str | Path) -> list[tuple[int, str]]:
    """Return (one-based line number, SMILES) tuples for nonblank lines."""
    rows: list[tuple[int, str]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            smiles = line.strip()
            if smiles:
                rows.append((line_no, smiles))
    if not rows:
        raise ValueError(f"{path} contains no nonblank SMILES lines")
    return rows


def _single_conformer_copy(mol, conformer_id: int):
    """Copy an RDKit molecule while retaining exactly one named conformer."""
    from rdkit import Chem

    out = Chem.Mol(mol)
    conformer = Chem.Conformer(mol.GetConformer(conformer_id))
    out.RemoveAllConformers()
    out.AddConformer(conformer, assignId=True)
    return out


def build_query_molecules(rows: list[tuple[int, str]], *, n_conformers: int = 1):
    """Parse, embed, and MMFF-optimize query conformers for every input line."""
    from rdkit import Chem
    from rdkit.Chem import AllChem

    molecules, metadata = [], []
    for line_no, smiles in rows:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(f"invalid SMILES on line {line_no}: {smiles!r}")
        canonical_smiles = Chem.MolToSmiles(mol, canonical=True)
        mol = Chem.AddHs(mol)
        params = AllChem.ETKDGv3()
        params.randomSeed = SEED
        if n_conformers == 1:
            conformer_ids = [AllChem.EmbedMolecule(mol, params)]
        else:
            conformer_ids = list(AllChem.EmbedMultipleConfs(
                mol, numConfs=n_conformers, params=params))
        if len(conformer_ids) != n_conformers or any(cid < 0 for cid in conformer_ids):
            raise RuntimeError(
                f"ETKDGv3 generated {len(conformer_ids)} of {n_conformers} requested "
                f"conformers for line {line_no}: {smiles!r}")
        if not AllChem.MMFFHasAllMoleculeParams(mol):
            raise RuntimeError(
                f"MMFF parameters are unavailable for line {line_no}: {smiles!r}")
        optimized = AllChem.MMFFOptimizeMoleculeConfs(mol, maxIters=200)
        for conformer_index, (conformer_id, result) in enumerate(
                zip(conformer_ids, optimized), start=1):
            status, energy = result
            if status < 0:
                raise RuntimeError(
                    f"MMFF optimization failed for line {line_no}, conformer "
                    f"{conformer_index}: {smiles!r}")
            name = f"line_{line_no}_conf_{conformer_index:03d}"
            one = _single_conformer_copy(mol, conformer_id)
            one.SetProp("_Name", name)
            molecules.append(one)
            metadata.append({
                "line": line_no,
                "name": name,
                "query_conformer": conformer_index,
                "input_smiles": smiles,
                "canonical_smiles": canonical_smiles,
                "embed_conformer_id": int(conformer_id),
                "mmff_status": int(status),
                "mmff_energy": float(energy),
            })
    return molecules, metadata


def read_query_sdf(path: str | Path, *, limit: int | None = None):
    """Read an exact-coordinate SDF panel and attach stable query metadata."""
    from rdkit import Chem

    molecules, metadata = [], []
    supplier = Chem.SDMolSupplier(str(path), removeHs=False)
    for record_index, mol in enumerate(supplier, start=1):
        if mol is None:
            raise ValueError(f"could not parse SDF record {record_index} in {path}")
        if mol.GetNumConformers() != 1 or not mol.GetConformer().Is3D():
            raise ValueError(f"SDF record {record_index} must have one 3D conformer")
        name = (mol.GetProp("_Name").strip() if mol.HasProp("_Name") else "")
        if not name:
            name = f"record_{record_index:03d}"
            mol.SetProp("_Name", name)
        elif any(item["name"] == name for item in metadata):
            name = f"{name}_record_{record_index:03d}"
            mol.SetProp("_Name", name)
        molecules.append(mol)
        metadata.append({
            "line": None,
            "record": record_index,
            "name": name,
            "query_conformer": 1,
            "input_smiles": None,
            "canonical_smiles": Chem.MolToSmiles(Chem.RemoveHs(mol), canonical=True),
            "heavy_atoms": int(mol.GetNumHeavyAtoms()),
            "coordinate_source": "input_sdf",
        })
        if limit is not None and len(molecules) == limit:
            break
    if not molecules:
        raise ValueError(f"{path} contains no readable molecules")
    return molecules, metadata


def corpus_identity(corpus) -> dict[str, Any]:
    """What the run screened. corpus.json's sha256 pins the content (it carries
    every group file's header hash, which carries every section's hash); its
    ids_sha256 fixes the conformer ids and order; the fingerprint pins the
    build configuration (color definition, prepare version), not the content.
    The name comes from build.json."""
    import hashlib
    root = Path(corpus.root)
    descriptor = corpus.descriptor
    try:
        name = json.loads((root / "build.json").read_text(encoding="utf-8")).get("name")
    except (OSError, ValueError):
        name = None
    return {
        "path": str(root),
        "name": name or root.name,
        "conformers": int(corpus.n_conformers),
        "molecules": int(corpus.n_molecules),
        "has_color": bool(corpus.has_color),
        "ids_sha256": descriptor.get("ids_sha256"),
        "molecules_sha256": descriptor.get("molecules_sha256"),
        "descriptor_sha256": hashlib.sha256((root / "corpus.json").read_bytes()).hexdigest(),
        "fingerprint": corpus.fingerprint,
        "format": descriptor.get("format"),
    }


def corpus_files(root: str | Path) -> list[Path]:
    """Return regular corpus files in deterministic order."""
    root = Path(root)
    return [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())


def _resident_fraction(path: Path) -> float:
    """Fraction of a file resident according to mincore(2)."""
    size = path.stat().st_size
    if not size:
        return 0.0
    libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    libc.mmap.restype = ctypes.c_void_p
    libc.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int,
                          ctypes.c_int, ctypes.c_int, ctypes.c_long]
    libc.mincore.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                             ctypes.POINTER(ctypes.c_ubyte)]
    libc.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    fd = os.open(path, os.O_RDONLY)
    try:
        addr = libc.mmap(None, ctypes.c_size_t(size), 1, 1,
                         ctypes.c_int(fd), ctypes.c_long(0))
    finally:
        os.close(fd)
    if addr == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_errno(), f"mmap failed on {path}")
    try:
        pages = (size + 4095) // 4096
        vector = (ctypes.c_ubyte * pages)()
        if libc.mincore(ctypes.c_void_p(addr), ctypes.c_size_t(size), vector) != 0:
            raise OSError(ctypes.get_errno(), f"mincore failed on {path}")
        return sum(bool(value & 1) for value in vector) / pages
    finally:
        libc.munmap(ctypes.c_void_p(addr), ctypes.c_size_t(size))


def drop_corpus_cache(root: str | Path) -> dict[str, Any]:
    """Evict clean corpus pages with posix_fadvise and verify with mincore."""
    files = corpus_files(root)
    observations = []
    for path in files:
        try:
            observations.append((path, path.stat().st_size, _resident_fraction(path)))
        except OSError:
            continue
    for path, _size, _before in observations:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)
    after = [(path, size, _resident_fraction(path))
             for path, size, _before in observations]
    total = sum(size for _path, size, _fraction in observations)
    weighted = lambda rows: (sum(size * fraction for _path, size, fraction in rows) /
                             total if total else 0.0)
    return {
        "method": "posix_fadvise(POSIX_FADV_DONTNEED), verified with mincore",
        "n_files": len(observations),
        "bytes": total,
        "resident_fraction_before": weighted(observations),
        "resident_fraction_after_drop": weighted(after),
    }


def write_telemetry_csv(records: list[dict[str, Any]], path: Path) -> None:
    fields = ["phase", "repeat", "t_rel_s", "clocks_sm_mhz", "clocks_mem_mhz",
              "power_draw_w", "temperature_gpu_c", "utilization_gpu_pct",
              "throttle_reasons_active", "sw_power_cap_active"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            for sample in record.pop("telemetry_samples"):
                writer.writerow({"phase": record["phase"],
                                 "repeat": record["repeat"], **sample})


def screen_config(mode: str, mixing: float):
    """Return the benchmark-defined configuration for one screening arm."""
    # spec, not cuda: the enums are backend-neutral and importable without CUDA.
    from roshambo3.backend.spec import ColorPlacement, PoseSearch
    from roshambo3.engine import ScreenConfig

    base = dict(pose_search=PoseSearch.FIELD, steps=25, lr_t=0.4,
                lr_q=0.1, start_mode=1)
    if mode == "shape":
        return ScreenConfig(**base, color=False, mixing=0.0), "tanimoto_shape"
    if mode == "rescore":
        return (ScreenConfig(**base, color=True, mixing=mixing,
                             color_placement=ColorPlacement.AT_POSE),
                "tanimoto_combination")
    if mode == "combo":
        return (ScreenConfig(**base, color=True, mixing=mixing,
                             color_placement=ColorPlacement.IN_GRADIENT),
                "tanimoto_combination")
    raise ValueError(f"unknown mode {mode!r}")


def needs_color_query(mode: str, corpus_has_color: bool) -> bool:
    """Whether query preparation needs the corpus's multi-type schema.

    Only color modes do. The August 2026 CUDA build streamed a color corpus's
    full count vector even to shape screens, and so needed color-typed queries
    there too; the release streams a shape-only count vector for shape screens
    and rejects a 7x7 query interaction matrix against it, while the CPU
    backend accepts either. Shape queries are therefore shape-only on every
    backend. ``corpus_has_color`` is kept so the August call sites still read.
    """
    return mode != "shape"


def json_value(value: Any) -> Any:
    """Convert extension/numpy values into JSON's small value vocabulary."""
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    return value


def describe_build_configuration(build, backend: str = "cuda") -> dict[str, Any]:
    """Give the loaded extension both a stable label and readable summary.

    ``arch_profile`` alone says only single- versus multi-SASS.  For the paper
    we also need to distinguish an explicit, quotable ``120-real`` build from
    CMake's unresolved ``native`` development shortcut, and to state whether a
    portable fat binary carries forward-compatible PTX.
    """
    archs = list(build.arch_list)
    requested = str(build.cuda_architectures_requested or "unknown")
    arch_text = ", ".join(archs) if archs else "none verified"
    if backend != "cuda":
        label = backend
        kind = (f"{backend} backend"
                + ("; CUDA extension also present" if build.with_cuda else ""))
    elif not build.with_cuda:
        label = "cpu-only"
        kind = "CPU-only build (no CUDA extension loaded)"
    elif requested.strip() == "native":
        label = "development-native-unresolved"
        kind = ("development native CUDA build (CMake recorded 'native'; "
                f"verified SASS: {arch_text})")
    elif archs == ["sm_120"]:
        label = "blackwell-sm120-explicit"
        kind = ("explicit Blackwell-only CUDA build "
                f"(requested {requested}; SASS: sm_120)")
    elif len(archs) > 1:
        label = "portable-fatbin"
        kind = ("portable CUDA fat binary "
                f"(SASS: {arch_text})")
    elif len(archs) == 1:
        label = f"single-arch-{archs[0]}"
        kind = f"explicit single-architecture CUDA build (SASS: {archs[0]})"
    else:
        label = "cuda-architecture-unverified"
        kind = f"CUDA build with unverified SASS (requested {requested})"

    ptx = ("forward-compatible PTX included" if build.ptx_present
           else "no PTX fallback")
    summary = (f"{build.build_type}; {kind}; {ptx}; "
               f"NVCC {build.nvcc_version}; {build.nthreads} threads/block")
    return {
        "label": label,
        "summary": summary,
        "requested_architectures": requested,
        "verified_sass_architectures": archs,
        "ptx_present": bool(build.ptx_present),
    }


def timing_record(result, outer_wall_s: float) -> dict[str, Any]:
    stats = result.stats
    stages = json_value(dict(stats.device_stages))
    kernel_s = stages.get("kernel_s", stages.get("kernel"))
    return {
        "screen_call_wall_s": outer_wall_s,
        "engine_wall_s": float(stats.wall_s),
        "producer_wait_s": float(stats.producer_wait_s),
        "launch_enqueue_s": float(stats.launch_s),
        "sink_s": float(stats.sink_s),
        "device_stages_s": stages,
        "kernel_s": kernel_s,
        "conformers_screened": int(stats.n_conformers),
        "conformer_pairs_screened": int(stats.n_rows),
        "launches": int(stats.n_blocks),
    }


def stability(values: list[float]) -> dict[str, float]:
    median = statistics.median(values)
    return {
        "min_s": min(values),
        "median_s": median,
        "max_s": max(values),
        "pstdev_s": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "relative_spread": ((max(values) - min(values)) / median
                            if median else 0.0),
    }


def write_hits_csv(result, query_metadata: dict[str, dict], path: Path) -> None:
    fields = ["query", "input_line", "query_conformer", "rank", "gid", "mol_id",
              "tanimoto_shape", "tanimoto_color", "tanimoto_combination"]
    catalog = result.catalog
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for hits in result:
            query = query_metadata[hits.query_name]
            # Recall is compared by molecule: two backends can pick different
            # winning conformers of one molecule.
            mol_ids = catalog.mol_ids(hits.gids) if len(hits.gids) else []
            for rank, (gid, mol_id) in enumerate(zip(hits.gids, mol_ids), start=1):
                writer.writerow({
                    "query": hits.query_name,
                    "input_line": query["line"],
                    "query_conformer": query["query_conformer"],
                    "rank": rank,
                    "gid": int(gid),
                    "mol_id": int(mol_id),
                    "tanimoto_shape": float(hits.tanimoto_shape[rank - 1]),
                    "tanimoto_color": float(hits.tanimoto_color[rank - 1]),
                    "tanimoto_combination": float(hits.tanimoto_combination[rank - 1]),
                })


def resolved_workers(args: argparse.Namespace) -> int:
    """The worker count ``roshambo3.screen`` actually uses for these arguments."""
    if args.workers is not None:
        return int(args.workers)
    if args.backend == "cpu":
        from roshambo3.engine.config import _default_cpu_workers
        return int(_default_cpu_workers())
    return CUDA_DEFAULT_WORKERS


class CudaHarness:
    """GPU lock, contention, and clock/power telemetry for the CUDA backend."""

    report_key = "gpu"
    stage_timing = True

    def __init__(self, args: argparse.Namespace):
        from bench.clocks import ClockPowerSampler, detect_profiler_clock_control
        from bench.gpu_lock import GpuLock, query_gpu_state, resolve_device

        self._sampler_class = ClockPowerSampler
        self._detect_profiler = detect_profiler_clock_control
        self._query = query_gpu_state
        self.interval_s = args.telemetry_interval
        # Device resolution and flock happen through nvidia-smi and the
        # filesystem, before importing roshambo3 can create a CUDA context.
        self.device = resolve_device(args.device)
        self.lock = GpuLock("paper-roshambo3", device=self.device,
                            blocking=args.lock_timeout > 0,
                            timeout_s=args.lock_timeout if args.lock_timeout > 0 else None)

    def __enter__(self) -> "CudaHarness":
        self.lock.__enter__()
        self.initial = self._query(device=self.device)
        self.profiler = self._detect_profiler()
        return self

    def __exit__(self, *exc):
        return self.lock.__exit__(*exc)

    def contention(self) -> dict[str, Any]:
        return self._query(device=self.device).as_dict()

    def sampler(self):
        return self._sampler_class(device=self.device, interval_s=self.interval_s)

    def describe(self) -> dict[str, Any]:
        return {"device": self.device.as_dict(), "lock_path": str(self.lock.lock_path),
                "lock_held": self.lock.was_held, "initial_state": self.initial.as_dict(),
                "profiler_clock_control": self.profiler.as_dict()}


class _HostSampler:
    """Achieved-frequency sampling for a host-scored screen.

    Linux samples per-core frequency; macOS has no unprivileged equivalent, so
    the sampler records nothing there and the report says so.
    """

    def __init__(self):
        from bench.cpu import CpuFrequencySampler
        self._sampler = CpuFrequencySampler()

    def __enter__(self) -> "_HostSampler":
        self._sampler.__enter__()
        return self

    def __exit__(self, *exc):
        return self._sampler.__exit__(*exc)

    def summary(self) -> dict[str, Any]:
        return self._sampler.summary()

    def to_csv_rows(self) -> list[dict[str, Any]]:
        return []


def apple_gpu_hardware() -> Any:
    """``system_profiler``'s display record, which carries the GPU core count."""
    import subprocess
    try:
        out = subprocess.run(["system_profiler", "SPDisplaysDataType", "-json"],
                             capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": str(exc)}
    if out.returncode != 0:
        return {"error": out.stderr.strip()}
    gpus = json.loads(out.stdout).get("SPDisplaysDataType", [])
    keep = ("sppci_model", "sppci_cores", "sppci_device_type", "spdisplays_mtlgpufamilysupport")
    return [{key: gpu.get(key) for key in keep} for gpu in gpus]


class HostHarness:
    """CPU (and Metal device) locks plus host identity for CPU and Metal runs.

    Metal screens decode the corpus on the CPU, so a Metal run holds the CPU
    lock as well as its device lock, as the Metal release-candidate timing did.
    """

    report_key = "host_compute"
    stage_timing = False   # stage timing forces the CPU backend off its worker route

    def __init__(self, args: argparse.Namespace):
        self.backend = args.backend
        self.device = args.device
        self.lock_timeout = args.lock_timeout
        self._stack = None
        self.locks: list[dict[str, Any]] = []

    def __enter__(self) -> "HostHarness":
        from contextlib import ExitStack

        from bench.cpu import cpu_identity, query_cpu_state
        from roshambo3.web.gpu import resource_lock

        deadline = time.monotonic() + max(self.lock_timeout, 0.5)
        canceled = lambda: time.monotonic() > deadline
        self._stack = ExitStack()
        try:
            for backend, device in [("cpu", 0)] + ([("metal", self.device)]
                                                   if self.backend == "metal" else []):
                identity = self._stack.enter_context(resource_lock(backend, device, canceled))
                self.locks.append({"backend": backend, "identity": str(identity)})
        except BaseException:
            self._stack.close()
            raise
        self._query = query_cpu_state
        self.cpu = cpu_identity().as_dict()
        self.initial = query_cpu_state().as_dict()
        self.power_before = None
        if sys.platform == "darwin":
            from bench.cpu_darwin import power_state
            self.power_before = power_state()
        self.metal = None
        if self.backend == "metal":
            from roshambo3.backend import metal
            self.metal = {"device": dict(metal.extension().device_info(self.device)),
                          "build_stamp": json_value(metal.build_stamp()),
                          "hardware": apple_gpu_hardware()}
        return self

    def __exit__(self, *exc):
        return self._stack.__exit__(*exc)

    def contention(self) -> dict[str, Any]:
        return self._query().as_dict()

    def sampler(self) -> _HostSampler:
        return _HostSampler()

    def describe(self) -> dict[str, Any]:
        return {"backend": self.backend, "locks": self.locks,
                "lock_held": bool(self.locks), "cpu": self.cpu,
                "initial_state": self.initial, "power_before": self.power_before,
                "metal": self.metal}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    prefix = Path(args.output_prefix)
    csv_path = prefix.with_suffix(".csv")
    json_path = prefix.with_suffix(".json")
    telemetry_path = Path(f"{prefix}.telemetry.csv")
    existing = [path for path in (csv_path, json_path, telemetry_path) if path.exists()]
    if args.skip_existing and len(existing) == 3:
        print(f"complete output set already exists for {prefix}; skipping")
        return 0
    if existing and not args.force:
        detail = "complete" if len(existing) == 3 else "partial"
        raise FileExistsError(f"refusing to overwrite {detail} output set: " +
                              ", ".join(map(str, existing)))
    prefix.parent.mkdir(parents=True, exist_ok=True)
    fd_limit = configure_fd_limit()

    if args.source_tree is None:
        raise SystemExit("set --source-tree or ROSHAMBO3_SOURCE_TREE to a ROSHAMBO3 checkout")
    source_tree = Path(args.source_tree).resolve()
    if not (source_tree / "bench").is_dir():
        raise FileNotFoundError(f"benchmark harness not found under {source_tree}")
    sys.path.insert(0, str(source_tree))
    from bench.build_check import verify_build
    from bench.gitinfo import get_git_info

    harness = CudaHarness(args) if args.backend == "cuda" else HostHarness(args)
    with harness:
        build = verify_build()
        build_description = describe_build_configuration(build, args.backend)
        print(f"build: {build_description['summary']}")

        import roshambo3 as r3
        from roshambo3.pharmacophore import PharmacophoreGenerator

        # The installed tool's own commit: the checkout above supplies only
        # the harness, and a machine can have one at a different commit.
        tool = {"git_sha": r3.get_build_info().git_sha,
                "version": getattr(r3, "__version__", None),
                "package_path": str(Path(r3.__file__).resolve().parent)}

        corpus = r3.open_corpus(args.corpus)
        prep_start = time.perf_counter()
        if args.smiles_file:
            rows = read_smiles(args.smiles_file)
            if args.query_limit is not None:
                rows = rows[:args.query_limit]
            molecules, query_metadata = build_query_molecules(
                rows, n_conformers=args.query_conformers)
            query_input_count = len(rows)
            query_process = ("AddHs -> ETKDGv3(seed=0xC0FFEE) -> "
                             "MMFFOptimizeMoleculeConfs(maxIters=200)")
        else:
            molecules, query_metadata = read_query_sdf(
                args.query_sdf, limit=args.query_limit)
            query_input_count = len(molecules)
            query_process = "exact 3D coordinates from input SDF"
        generator = (PharmacophoreGenerator()
                     if needs_color_query(args.mode, corpus.has_color) else None)
        queries = r3.load_queries(molecules, color_generator=generator)
        query_prep_s = time.perf_counter() - prep_start

        config, rank_column = screen_config(args.mode, args.mixing)
        records, timed, final_result = [], [], None
        total_screens = args.warmups + args.repeats
        for screen_index in range(total_screens):
            is_warmup = screen_index < args.warmups
            repeat_index = (screen_index + 1 if is_warmup
                            else screen_index - args.warmups + 1)
            cache = None
            contention = None
            if not is_warmup:
                if args.cache_mode == "cold":
                    cache = drop_corpus_cache(corpus.root)
                contention = harness.contention()
            sampler = harness.sampler()
            start = time.perf_counter()
            with sampler:
                result = r3.screen(
                    queries, corpus, k=args.top_k, config=config,
                    device_id=args.device, workers=args.workers,
                    prefetch_depth=args.prefetch,
                    launch_conformers=args.launch_conformers,
                    color_generator=generator, level="molecule",
                    stage_timing=harness.stage_timing, backend=args.backend)
            record = timing_record(result, time.perf_counter() - start)
            record.update({
                "phase": "warmup" if is_warmup else "timed",
                "repeat": repeat_index,
                "cache": cache,
                "contention_before": contention,
                "telemetry": sampler.summary(),
                "telemetry_samples": sampler.to_csv_rows(),
            })
            records.append(record)
            if not is_warmup:
                timed.append(record)
                final_result = result
            if screen_index + 1 < total_screens:
                del result
                gc.collect()

        assert final_result is not None
        write_hits_csv(final_result, {q["name"]: q for q in query_metadata}, csv_path)
        compute_description = harness.describe()

    screen_wall = [record["screen_call_wall_s"] for record in timed]
    kernel = [float(record["kernel_s"]) for record in timed
              if isinstance(record["kernel_s"], (int, float))]
    expected_pairs = len(query_metadata) * int(corpus.n_conformers)
    write_telemetry_csv(records, telemetry_path)

    report = {
        "script": "screen_smiles.py",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": {"hostname": socket.gethostname(), "platform": platform.platform()},
        "git": get_git_info(str(source_tree)).as_dict(),
        "tool": tool,
        "build": {**build.as_dict(),
                  "configuration": build_description},
        harness.report_key: compute_description,
        "query_preparation": {
            "wall_s": query_prep_s,
            "n_queries": len(query_metadata),
            "input": args.smiles_file or args.query_sdf,
            "input_records": query_input_count,
            "conformers_per_smiles": args.query_conformers if args.smiles_file else None,
            "process": query_process,
            "queries": query_metadata,
        },
        "screen": {
            "mode": args.mode,
            "backend": args.backend,
            "ranking_column": rank_column,
            "level": "molecule",
            "top_k": args.top_k,
            "mixing": args.mixing if args.mode != "shape" else 0.0,
            "device": args.device,
            "workers": args.workers,
            "workers_resolved": resolved_workers(args),
            "prefetch_depth": args.prefetch,
            "launch_conformers_requested": args.launch_conformers,
            "fd_limit": fd_limit,
            "warmups_requested": args.warmups,
            "timed_repeats_requested": args.repeats,
            "cache_mode": args.cache_mode,
            "warmups": [record for record in records if record["phase"] == "warmup"],
            "repeats": timed,
            "stability": {"screen_call_wall_s": stability(screen_wall)},
            "host_timing_note": (
                "producer_wait_s, launch_enqueue_s, and sink_s are overlapping "
                "host-side diagnostics, not an additive partition of wall time."),
        },
        "corpus": corpus_identity(corpus),
        "screen_size": {
            "conformer_pairs_per_repeat": expected_pairs,
            "conformer_pairs_all_repeats": expected_pairs * args.repeats,
            "actual_conformer_pairs_final_repeat": timed[-1]["conformer_pairs_screened"],
        },
        "outputs": {"hits_csv": str(csv_path), "report_json": str(json_path),
                    "telemetry_csv": str(telemetry_path)},
    }
    if kernel:
        report["screen"]["stability"]["kernel_s"] = stability(kernel)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(json_value(report), handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"prepared {len(query_metadata)} queries in {query_prep_s:.3f}s")
    print(f"screened {expected_pairs:,} conformer pairs per repeat; "
          f"median wall {statistics.median(screen_wall):.3f}s over {args.repeats} repeat(s)")
    print(f"wrote {csv_path}, {json_path}, and {telemetry_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
