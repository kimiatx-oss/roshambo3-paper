#!/usr/bin/env python3
"""Render the cross-backend portability table from screen_smiles.py records.

Every row screens the same LIT-PCBA corpus with the same PANEL-8 queries in
shape, rescore, and combo modes, from one source commit. Throughput is
conformer-query pair evaluations per second of end-to-end screen-call wall
time (median of timed repeats). Recall@K compares each backend's molecule-level
top-K against the reference device's, query by query and mode by mode.

The script refuses, rather than reports, a table whose rows are not
comparable: a different corpus, query panel, top-K, or ranking level, a
source or tool commit other than the one the device list assigns that device,
a dirty tree, an unheld lock, or too few timed repeats. Devices run the list's
default_commit unless they name another of its declared commits; the caption
names every commit the table draws on.

Each device directory also holds the env.json that portability_campaign.sh
writes. Only the CUDA extension stamps a commit, so a CPU-only or Metal record
says tool.git_sha "unknown"; for those rows the tool commit is the clean,
non-editable checkout env.json says the tool was installed from. env.json also
carries the query panel's sha256, which must match the committed PANEL-8.sdf,
and the CPU kernel target the backend selected at run time.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path

DEFAULT_DEVICES = Path("data/portability-devices.json")
# The runs write their own outputs inside the checkout, so a tree whose only
# changes are these directories is still the frozen source.
RUN_OUTPUT_PREFIXES = ("publication/runs/portability/", "publication/runs/portability-smoke/")
# bench.gitinfo truncates its path lists at this length.
GIT_PATH_LIST_LIMIT = 20
DEFAULT_RUNS = Path("runs/portability")
DEFAULT_PANEL = Path("data/queries/PANEL-8.sdf")
PENDING = r"\textbf{??}"
ISA_LABEL = {"AVX512F": "AVX-512", "X86_64_V3": "AVX2", "NEON": "NEON"}


def load_run(directory: Path, mode: str) -> tuple[dict, dict[str, list[str]]]:
    report = json.loads((directory / f"panel8-{mode}.json").read_text(encoding="utf-8"))
    ranked: dict[str, list[tuple[int, str]]] = {}
    with (directory / f"panel8-{mode}.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            ranked.setdefault(row["query"], []).append((int(row["rank"]), row["mol_id"]))
    hits = {query: [mol for _, mol in sorted(rows)] for query, rows in ranked.items()}
    return report, hits


def load_env(directory: Path) -> dict:
    path = directory / "env.json"
    if not path.is_file():
        raise ValueError(f"{directory.name}: no env.json (run portability_campaign.sh env)")
    return json.loads(path.read_text(encoding="utf-8"))


def tool_commit(report: dict, env: dict) -> str:
    """The installed tool's commit: the CUDA stamp, else the clean install's checkout."""
    stamped = report["tool"]["git_sha"]
    if stamped != "unknown":
        return stamped
    install = env["install"]
    if install["checkout_status"].strip() or install["editable"]:
        raise ValueError("tool has no commit stamp and its install checkout was dirty or editable")
    return install["checkout_head"]


def compute_record(report: dict) -> dict:
    """The block describing where a run executed: `gpu` for CUDA, `host_compute` otherwise."""
    return report.get("gpu") or report.get("host_compute") or {}


def device_detail(device: dict, report: dict, env: dict | None = None) -> str:
    """Core counts read from the run record; the CPU kernel target from env.json."""
    compute = compute_record(report)
    if device["backend"] == "cpu":
        cpu = compute["cpu"]
        if cpu.get("performance_cores") is not None:
            cores = f"{cpu['performance_cores']}P+{cpu['efficiency_cores']}E cores"
        else:
            cores = f"{cpu['physical_cores']}C/{cpu['logical_cpus']}T"
        target = ((env or {}).get("tool_stamps", {}).get("cpu") or {}).get("selected_target")
        return f"{cores}, {ISA_LABEL.get(target, target)}" if target else cores
    if device["backend"] == "metal":
        hardware = (compute.get("metal") or {}).get("hardware") or []
        cores = [gpu.get("sppci_cores") for gpu in hardware if isinstance(gpu, dict)]
        cores = [c for c in cores if c]
        return f"{cores[0]} cores" if cores else "core count not recorded"
    return ""


def source_was_dirty(git: dict) -> bool:
    """Dirty beyond the portability runs' own output directories."""
    if not git.get("dirty"):
        return False
    paths = git.get("source_dirty_paths")
    if paths is None or len(paths) >= GIT_PATH_LIST_LIMIT:
        return True   # cannot show that every change is a run output
    return any(not path.startswith(RUN_OUTPUT_PREFIXES) for path in paths)


def recall_at_k(candidate: list[str], reference: list[str], k: int) -> float:
    if len(reference) < k:
        raise ValueError(f"reference holds {len(reference)} hits, fewer than k={k}")
    return len(set(candidate[:k]) & set(reference[:k])) / k


def expected_commit(device: dict, spec: dict) -> str:
    commit = device.get("commit", spec["default_commit"])
    if commit not in spec["commits"]:
        raise ValueError(f"{device['key']}: commit {commit[:10]} is not declared in the device list")
    return commit


def analyze(runs: Path, spec: dict, panel_sha256: str) -> dict:
    modes, k = spec["modes"], int(spec["top_k"])
    references = [d for d in spec["devices"] if d.get("reference")]
    if len(references) != 1:
        raise ValueError("exactly one device must be the recall reference")
    present = [d for d in spec["devices"] if (runs / d["key"]).is_dir()]
    if references[0] not in present:
        raise ValueError(f"reference device {references[0]['key']} has no runs")

    loaded = {d["key"]: {mode: load_run(runs / d["key"], mode) for mode in modes}
              for d in present}
    envs = {d["key"]: load_env(runs / d["key"]) for d in present}
    for key, env in envs.items():
        if env["panel_sha256"] != panel_sha256:
            raise ValueError(f"{key}: query panel {env['panel_sha256'][:12]} is not the committed PANEL-8")
    first = loaded[references[0]["key"]][modes[0]][0]
    identity = {
        "corpus_conformers": first["corpus"]["conformers"],
        "corpus_name": first["corpus"]["name"],
        # Format-3 records also name the corpus by content (corpus.json's hash)
        # and by build configuration (fingerprint).
        "corpus_descriptor": first["corpus"].get("descriptor_sha256"),
        "corpus_ids": first["corpus"].get("ids_sha256"),
        "corpus_fingerprint": first["corpus"].get("fingerprint"),
        "queries": [q["name"] for q in first["query_preparation"]["queries"]],
    }
    for key, by_mode in loaded.items():
        device = next(d for d in present if d["key"] == key)
        for mode, (report, _) in by_mode.items():
            where = f"{key}/{mode}"
            screen = report["screen"]
            checks = {
                "corpus_conformers": report["corpus"]["conformers"],
                "corpus_name": report["corpus"]["name"],
                "corpus_descriptor": report["corpus"].get("descriptor_sha256"),
                "corpus_ids": report["corpus"].get("ids_sha256"),
                "corpus_fingerprint": report["corpus"].get("fingerprint"),
                "queries": [q["name"] for q in report["query_preparation"]["queries"]],
            }
            for field, value in checks.items():
                if value != identity[field]:
                    raise ValueError(f"{where}: {field} {value!r} differs from the reference run")
            commit = expected_commit(device, spec)
            for field, value in (("source commit", report["git"]["sha"]),
                                 ("tool commit", tool_commit(report, envs[key]))):
                if value != commit:
                    raise ValueError(f"{where}: {field} {value[:10]} is not the device's {commit[:10]}")
            if source_was_dirty(report["git"]):
                raise ValueError(f"{where}: source tree was dirty")
            if screen["mode"] != mode or screen.get("backend", "cuda") != device["backend"]:
                raise ValueError(f"{where}: record is {screen.get('backend')}/{screen['mode']}")
            if int(screen["top_k"]) != k or screen["level"] != "molecule":
                raise ValueError(f"{where}: top-{screen['top_k']} {screen['level']} is not top-{k} molecule")
            if screen["cache_mode"] != "warm":
                raise ValueError(f"{where}: cache mode {screen['cache_mode']}")
            if len(screen["repeats"]) < int(spec["min_timed_repeats"][device["backend"]]):
                raise ValueError(f"{where}: only {len(screen['repeats'])} timed repeats")
            if not compute_record(report).get("lock_held"):
                raise ValueError(f"{where}: the compute lock was not held")

    reference_hits = {mode: loaded[references[0]["key"]][mode][1] for mode in modes}
    rows = []
    for device in present:
        rates, recalls = {}, []
        for mode in modes:
            report, hits = loaded[device["key"]][mode]
            median_s = statistics.median(r["screen_call_wall_s"] for r in report["screen"]["repeats"])
            rates[mode] = report["screen_size"]["conformer_pairs_per_repeat"] / median_s
            if not device.get("reference"):
                recalls += [recall_at_k(hits[q], reference_hits[mode][q], k) for q in identity["queries"]]
        first_report = loaded[device["key"]][modes[0]][0]
        rows.append({
            "key": device["key"], "name": device["name"], "kind": device["kind"],
            "backend": device["backend"], "reference": bool(device.get("reference")),
            "detail": device_detail(device, first_report, envs[device["key"]]),
            "vcpus": (compute_record(first_report).get("cpu") or {}).get("logical_cpus")
                     if device["backend"] == "cpu" else None,
            "cloud": bool(device.get("cloud")),
            "commit": expected_commit(device, spec),
            "rates": rates,
            "recall_mean": statistics.fmean(recalls) if recalls else None,
            "recall_min": min(recalls) if recalls else None,
        })
    missing = [d["key"] for d in spec["devices"] if d not in present]
    used = sorted({row["commit"] for row in rows}, key=lambda c: c != spec["default_commit"])
    return {"identity": identity, "rows": rows, "missing": missing, "top_k": k, "modes": modes,
            "commits": {c: spec["commits"][c] for c in used}}


BACKEND_LABEL = {"cuda": "CUDA", "cpu": "CPU", "metal": "Metal"}


# One unit, M pairs/s; CPU rows carry a third decimal.
SECTIONS = (("gpu", "GPUs", "{:.2f}"), ("cpu", "CPUs", "{:.3f}"))


# Cloud CPUs are billed per vCPU, and two vCPUs are the smallest like-for-like
# unit: one physical core with its SMT sibling on x86, two cores without SMT.
VCPU_UNIT = 2


def per_vcpu(row: dict) -> str:
    """Combo pairs/s (K) per VCPU_UNIT vCPUs of a cloud CPU, from the full-VM run."""
    if row["kind"] != "cpu" or not row["cloud"] or not row["vcpus"]:
        return "---"
    return f"{VCPU_UNIT * row['rates']['combo'] / row['vcpus'] / 1e3:.1f}"


def row_label(device: dict, detail: str) -> str:
    """Name, then cores/ISA (and the backend for GPUs)."""
    name = device["name"]
    if device["kind"] == "gpu":
        return f"{name} ({BACKEND_LABEL[device['backend']]}" + (f", {detail})" if detail else ")")
    return name + (f", {detail}" if detail else "")


def table_tex(result: dict, spec: dict | None = None) -> str:
    """The portability table; devices without runs render as pending rows."""
    k = result["top_k"]
    measured = {row["key"]: row for row in result["rows"]}
    devices = (spec["devices"] if spec is not None else
               [{"key": r["key"], "name": r["name"], "kind": r["kind"], "backend": r["backend"]}
                for r in result["rows"]])
    lines = [
        "% Generated by scripts/analyze_portability.py; do not edit.",
        r"\begin{table}[t]",
        r"  \centering",
        r"  \small",
        r"  \caption{End-to-end LIT-PCBA/PANEL-8 throughput (median of",
        r"  warm repeats), combo throughput per two billed vCPUs on cloud CPUs (a core and its SMT",
        rf"  sibling on x86, two cores on Neoverse V2), and molecule-level recall@{k:,} against the",
        r"  reference, mean (worst query).}",
        r"  \label{tab:portability}",
        r"  \begin{tabular}{@{}lrrrrr@{}}",
        r"    \toprule",
        r"    & \multicolumn{3}{c}{M pairs/s} & Combo/2 vCPU & Recall@" + f"{k:,}" + r" \\",
        r"    \cmidrule(lr){2-4}",
        r"    Device & Shape & Rescore & Combo & (K pairs/s) & (\%) \\",
    ]
    for kind, title, fmt in SECTIONS:
        section = [d for d in devices if d["kind"] == kind]
        if not section:
            continue
        lines.append(r"    \midrule")  # GPUs, then CPUs
        for device in section:
            row = measured.get(device["key"])
            if row is None:
                label = row_label(device, "")  # cores come from the run record
                lines.append(rf"    {label} & \multicolumn{{5}}{{c}}{{\emph{{pending}}}} \\")
                continue
            rates = " & ".join(fmt.format(row["rates"][m] / 1e6) for m in result["modes"])
            recall = ("reference" if row["reference"] else
                      f"{100 * row['recall_mean']:.1f} ({100 * row['recall_min']:.1f})")
            lines.append(f"    {row_label(device, row['detail'])} & {rates} & {per_vcpu(row)} & {recall} \\\\")
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


def constants_tex(result: dict, spec: dict) -> str:
    """Prose constants; values that wait on unmeasured devices render as ??."""
    rows = {row["key"]: row for row in result["rows"]}
    others = [row for row in result["rows"] if not row["reference"]]
    reference = next(row for row in result["rows"] if row["reference"])
    cpus = [row for row in result["rows"] if row["kind"] == "cpu"]
    missing = set(result["missing"])
    missing_cpu = any(d["key"] in missing and d["kind"] == "cpu" for d in spec["devices"])
    # Recall minima wait on every device; the reference-over-fastest-CPU ratios
    # only on the CPU rows (the reference itself must have runs to get here).
    values = {
        "PortabilityLowestMeanRecallPercent": (
            PENDING if missing else f"{100 * min(r['recall_mean'] for r in others):.1f}"),
        "PortabilityWorstRecallPercent": (
            PENDING if missing else f"{100 * min(r['recall_min'] for r in others):.1f}"),
    }
    ratios = {}
    for mode in ("shape", "combo"):
        ratios[mode] = reference["rates"][mode] / max(r["rates"][mode] for r in cpus)
        values[f"PortabilityReferenceOverFastestCpu{mode.title()}"] = (
            PENDING if missing_cpu else f"{ratios[mode]:.0f}")
    # The prose quotes the ratios as a range, low to high, whichever mode is which.
    for name, ratio in (("Low", min(ratios.values())), ("High", max(ratios.values()))):
        values[f"PortabilityReferenceOverFastestCpu{name}"] = (
            PENDING if missing_cpu else f"{ratio:.0f}")
    lines = ["% Generated by scripts/analyze_portability.py; do not edit."]
    lines += [rf"\newcommand{{\{name}}}{{{value}}}" for name, value in values.items()]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    parser.add_argument("--devices", type=Path, default=DEFAULT_DEVICES)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--output", type=Path, default=Path("generated"))
    parser.add_argument("--require-all", action="store_true",
                        help="fail unless every listed device has runs")
    args = parser.parse_args()
    spec = json.loads(args.devices.read_text(encoding="utf-8"))
    panel_sha256 = hashlib.sha256(args.panel.read_bytes()).hexdigest()
    result = analyze(args.runs, spec, panel_sha256)
    if result["missing"]:
        message = "no runs for: " + ", ".join(result["missing"])
        if args.require_all:
            raise SystemExit(message)
        print("warning: " + message)
    (args.output / "tables").mkdir(parents=True, exist_ok=True)
    (args.output / "tables" / "portability.tex").write_text(table_tex(result, spec), encoding="utf-8")
    (args.output / "portability-constants.tex").write_text(constants_tex(result, spec), encoding="utf-8")
    (args.output / "portability.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for row in result["rows"]:
        rates = ", ".join(f"{m} {row['rates'][m] / 1e6:.2f}M/s" for m in result["modes"])
        print(f"{row['key']:>14}: {rates}")


if __name__ == "__main__":
    main()
