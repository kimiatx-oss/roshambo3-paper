#!/usr/bin/env python3
"""Render the CPU thread-scaling table from portability_campaign.sh scaling runs.

Each host screened the first PANEL-8 query in shape, rescore, and combo modes
on a ladder of placements: every vCPU unpinned (`all`), and `NxS` arms pinned
by taskset to S hardware threads on each of N physical cores. Where affinity
cannot be set (macOS) the arms are `t<N>`: N workers, placed by the OS.
Throughput is conformer-query pair evaluations per second of screen-call wall
time (median of timed repeats); speedup and parallel efficiency are against the
host's fewest-thread arm (1x1 where the ladder has one).
On SMT hosts three contrasts isolate the second hardware thread: 4x2 vs 4x1 and
all (8x2) vs 8x1 on the same cores, and 4x2 vs 8x1 at the same thread count.

The script refuses arms that are not comparable (different commit, corpus,
query, or mode; an unheld lock; a dirty tree; a worker count or affinity that
does not match the arm) and reports whether every arm on a host returned the
same top-K molecules in the same order, which the pinned arithmetic predicts.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

MODES = ("shape", "rescore", "combo")
ARM_ORDER = ("1x1", "2x1", "4x1", "4x2", "8x1", "all")
DEFAULT_RUNS = Path("runs/portability-scaling")
DEFAULT_DEVICES = Path("data/portability-devices.json")
PENDING = r"\textbf{??}"


def arm_shape(arm: str) -> tuple[int, int] | None:
    """(cores, threads per core) for a pinned arm; None for an unpinned one."""
    if arm == "all" or arm.startswith("t"):
        return None
    cores, threads = arm.split("x")
    return int(cores), int(threads)


def load_arm(directory: Path, mode: str) -> tuple[dict, dict, list[str]]:
    prefix = directory / f"panel1-{mode}"
    report = json.loads(prefix.with_suffix(".json").read_text(encoding="utf-8"))
    run = json.loads(Path(f"{prefix}.run.json").read_text(encoding="utf-8"))
    with prefix.with_suffix(".csv").open(encoding="utf-8", newline="") as handle:
        rows = sorted((int(r["rank"]), r["mol_id"]) for r in csv.DictReader(handle))
    return report, run, [mol for _, mol in rows]


def check_arm(where: str, arm: str, mode: str, report: dict, run: dict) -> int:
    """Validate one arm's record and return its worker count."""
    screen, host = report["screen"], report.get("host_compute") or {}
    if screen.get("backend") != "cpu" or screen["mode"] != mode:
        raise ValueError(f"{where}: record is {screen.get('backend')}/{screen['mode']}")
    if not host.get("lock_held"):
        raise ValueError(f"{where}: the CPU lock was not held")
    if report["git"].get("dirty"):
        raise ValueError(f"{where}: source tree was dirty")
    if screen["cache_mode"] != "warm":
        raise ValueError(f"{where}: cache mode {screen['cache_mode']}")
    workers = int(screen["workers_resolved"])
    shape = arm_shape(arm)
    if arm.startswith("t") and workers != int(arm[1:]):
        raise ValueError(f"{where}: {workers} workers on a {arm} arm")
    if shape is not None:
        cores, threads = shape
        if workers != cores * threads:
            raise ValueError(f"{where}: {workers} workers on a {arm} arm")
        if run.get("affinity") is not None and len(run["affinity"]) != workers:
            raise ValueError(f"{where}: affinity {run['affinity']} does not hold {workers} CPUs")
    return workers


def placement(arm: str, cpu: dict) -> tuple[str, str | None]:
    """The arm's label, and the arm without its extra threads (SMT siblings or
    efficiency cores) when it has any. Pinned arms are NxS; the unpinned
    default is labeled from the host's own core counts. Worker-count arms on a
    hybrid CPU are labeled P+E on the assumption that the OS fills performance
    cores first, which it cannot be made to do."""
    performance = cpu.get("performance_cores")
    if arm.startswith("t"):
        n = int(arm[1:])
        if not performance:
            return f"{n} (OS)", None
        p_cores = min(n, performance)
        label = f"{p_cores}+{n - p_cores}"
        return label, (f"{p_cores}+0" if n > p_cores else None)
    if arm == "all":
        physical, logical = cpu.get("physical_cores"), cpu.get("logical_cpus")
        if not physical or not logical:
            return "all", None
        arm = f"{physical}x{logical // physical}"
    cores, threads = arm.split("x")
    return arm, (f"{cores}x1" if int(threads) > 1 else None)


def analyze(runs: Path, commits: dict[str, str]) -> dict:
    """``commits`` maps each host key to the source commit its arms must run."""
    hosts, identity = [], None
    for key, commit in commits.items():
        root = runs / key
        if not root.is_dir():
            continue
        arms = [a for a in ARM_ORDER if (root / a).is_dir()]
        arms += sorted((p.name for p in root.glob("t[0-9]*") if p.is_dir()),
                       key=lambda a: int(a[1:]))
        if not arms:
            raise ValueError(f"{key}: no scaling arms")
        rows, identical = [], {mode: True for mode in MODES}
        first_hits, cpu = {}, None
        for arm in arms:
            rates, workers = {}, None
            for mode in MODES:
                where = f"{key}/{arm}/{mode}"
                report, run, hits = load_arm(root / arm, mode)
                if report["git"]["sha"] != commit:
                    raise ValueError(f"{where}: commit {report['git']['sha'][:10]} is not the host's {commit[:10]}")
                this = (report["corpus"]["conformers"], report["corpus"].get("descriptor_sha256"),
                        report["corpus"].get("fingerprint"),
                        [q["name"] for q in report["query_preparation"]["queries"]])
                if identity is None:
                    identity = this
                elif this != identity:
                    raise ValueError(f"{where}: corpus (count, content or build) or query differs from the first arm read")
                workers = check_arm(where, arm, mode, report, run)
                if cpu is None:
                    cpu = dict((report.get("host_compute") or {}).get("cpu") or {})
                median_s = statistics.median(r["screen_call_wall_s"] for r in report["screen"]["repeats"])
                rates[mode] = report["screen_size"]["conformer_pairs_per_repeat"] / median_s
                if mode not in first_hits:
                    first_hits[mode] = hits
                elif hits != first_hits[mode]:
                    identical[mode] = False
            rows.append({"arm": arm, "workers": workers, "rates": rates})
        for row in rows:
            row["label"], row["without_extra"] = placement(row["arm"], cpu)
        by_label = {row["label"]: row for row in rows}
        for row in rows:
            base_row = by_label.get(row["without_extra"]) if row["without_extra"] else None
            row["extra_gain"] = ({m: row["rates"][m] / base_row["rates"][m] - 1 for m in MODES}
                                 if base_row is not None else None)
        base = min(rows, key=lambda r: r["workers"])
        for row in rows:
            row["speedup"] = {m: row["rates"][m] / base["rates"][m] for m in MODES}
            row["efficiency"] = {m: row["speedup"][m] * base["workers"] / row["workers"]
                                 for m in MODES}
        by_arm = {r["arm"]: r["rates"] for r in rows}
        contrasts = {}
        for name, (num, den) in {"4x2/4x1": ("4x2", "4x1"), "all/8x1": ("all", "8x1"),
                                 "4x2/8x1": ("4x2", "8x1")}.items():
            if num in by_arm and den in by_arm and "4x2" in by_arm:
                contrasts[name] = {m: by_arm[num][m] / by_arm[den][m] for m in MODES}
        hosts.append({"key": key, "commit": commit, "rows": rows, "baseline_arm": base["arm"],
                      "cpu": cpu,
                      "smt_contrasts": contrasts,
                      "identical_topk": identical})
    if not hosts:
        raise ValueError(f"no scaling runs under {runs}")
    present = {host["key"] for host in hosts}
    return {"hosts": hosts, "missing": [key for key in commits if key not in present]}


def table_tex(result: dict, names: dict[str, str]) -> str:
    """Rates in thousands of pairs/s; hosts without runs render as pending rows."""
    lines = [
        "% Generated by scripts/analyze_cpu_scaling.py; do not edit.",
        r"\begin{table}[h]",
        r"  \centering",
        r"  \small",
        r"  \caption{CPU thread scaling on one PANEL-8 query over LIT-PCBA, in thousand",
        r"  conformer-query pair evaluations/s (median of warm timed repeats). $N\times S$ runs $S$",
        r"  hardware threads on each of $N$ physical cores, pinned except for the full machine; on the",
        r"  M4 Pro, $P{+}E$ counts performance and efficiency cores, assuming macOS fills performance cores",
        r"  first (it cannot be pinned). Extra-thread gain is combo throughput over the same physical",
        r"  cores without their SMT siblings ($N\times 2$ vs.\ $N\times 1$) or efficiency cores",
        r"  ($P{+}E$ vs.\ $P{+}0$). $^\dagger$Cloud VM.}",
        r"  \label{tab:cpu-scaling}",
        r"  \begin{tabular}{@{}llrrrrr@{}}",
        r"    \toprule",
        r"    Host & Placement & Threads & Shape & Rescore & Combo & Extra-thread gain \\",
        r"    \midrule",
    ]
    for index, host in enumerate(result["hosts"]):
        if index:
            lines.append(r"    \midrule")
        for i, row in enumerate(host["rows"]):
            name = names.get(host["key"], host["key"]) if i == 0 else ""
            label = row["label"].replace("x", r"$\times$")
            rates = " & ".join(f"{row['rates'][m] / 1e3:.0f}" for m in MODES)
            gain = ("---" if row["extra_gain"] is None else
                    f"$+{100 * row['extra_gain']['combo']:.0f}$\\%")
            lines.append(f"    {name} & {label} & {row['workers']} & {rates} & {gain} \\\\")
    for key in result.get("missing", []):
        lines += [r"    \midrule",
                  rf"    {names.get(key, key)} & \multicolumn{{6}}{{c}}{{\emph{{pending}}}} \\"]
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


def constants_tex(result: dict, macros: dict[str, str]) -> str:
    """Prose constants per host; a host without runs gets ?? for the pinned-ladder set."""
    lines = ["% Generated by scripts/analyze_cpu_scaling.py; do not edit."]
    emit = lambda name, value: lines.append(rf"\newcommand{{\Scaling{name}}}{{{value}}}")
    for host in result["hosts"]:
        stem, rows = macros[host["key"]], {r["arm"]: r for r in host["rows"]}
        if "8x1" in rows:
            emit(f"{stem}EightCoreEfficiencyPercent", f"{100 * rows['8x1']['efficiency']['combo']:.0f}")
        if "all" in rows and "1x1" in rows:
            emit(f"{stem}AllEfficiencyPercent", f"{100 * rows['all']['efficiency']['combo']:.0f}")
        contrasts = host["smt_contrasts"]
        if "all/8x1" in contrasts:
            emit(f"{stem}SmtGainPercent", f"{100 * (contrasts['all/8x1']['combo'] - 1):.0f}")
            emit(f"{stem}SmtGainFourCorePercent", f"{100 * (contrasts['4x2/4x1']['combo'] - 1):.0f}")
        hybrid = [r for r in host["rows"] if r["extra_gain"] is not None and "+" in r["label"]]
        if hybrid:
            full = max(hybrid, key=lambda r: r["workers"])
            base = next(r for r in host["rows"] if r["label"] == full["without_extra"])
            p_cores, e_cores = (int(x) for x in full["label"].split("+"))
            emit(f"{stem}EcoreGainPercent", f"{100 * full['extra_gain']['combo']:.0f}")
            emit(f"{stem}ShapePerPcoreThousand", f"{base['rates']['shape'] / p_cores / 1e3:.0f}")
            emit(f"{stem}ShapePerEcoreThousand",
                 f"{(full['rates']['shape'] - base['rates']['shape']) / e_cores / 1e3:.0f}")
    for key in result.get("missing", []):
        emit(f"{macros[key]}EightCoreEfficiencyPercent", PENDING)
        emit(f"{macros[key]}AllEfficiencyPercent", PENDING)
    identical = sum(all(h["identical_topk"].values()) for h in result["hosts"])
    emit("IdenticalTopKHostCount", PENDING if result.get("missing") else str(identical))
    emit("HostCount", str(len(result["hosts"]) + len(result.get("missing", []))))
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    parser.add_argument("--devices", type=Path, default=DEFAULT_DEVICES)
    parser.add_argument("--output", type=Path, default=Path("generated"))
    args = parser.parse_args()
    spec = json.loads(args.devices.read_text(encoding="utf-8"))
    cpus = [d for d in spec["devices"] if d["backend"] == "cpu"]
    result = analyze(args.runs, {d["key"]: d.get("commit", spec["default_commit"]) for d in cpus})
    (args.output / "tables").mkdir(parents=True, exist_ok=True)
    names = {d["key"]: d["name"] + (r"$^\dagger$" if d.get("cloud") else "") for d in cpus}
    (args.output / "tables" / "cpu-scaling.tex").write_text(table_tex(result, names), encoding="utf-8")
    (args.output / "cpu-scaling.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    macros = {d["key"]: d["macro"] for d in cpus}
    (args.output / "cpu-scaling-constants.tex").write_text(constants_tex(result, macros), encoding="utf-8")
    for host in result["hosts"]:
        same = ", ".join(m for m, ok in host["identical_topk"].items() if not ok) or "all modes"
        print(f"{host['key']}: identical top-K across arms: "
              f"{'yes' if same == 'all modes' else 'NO for ' + same}")
        for row in host["rows"]:
            rates = ", ".join(f"{m} {row['rates'][m] / 1e6:.2f}M/s" for m in MODES)
            print(f"  {row['arm']:>4} ({row['workers']:>2} threads): {rates}; "
                  f"combo eff {100 * row['efficiency']['combo']:.0f}%")
        for name, values in host["smt_contrasts"].items():
            print(f"  SMT {name}: " + ", ".join(f"{m} {v:.2f}x" for m, v in values.items()))


if __name__ == "__main__":
    main()
