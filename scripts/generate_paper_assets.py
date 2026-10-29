#!/usr/bin/env python3
"""Generate paper constants and table fragments from benchmark reports."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
import re
import shutil
import statistics
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Timing:
    machine: str
    mode: str
    source: Path
    queries: int
    conformers: int
    repeats: int
    median_wall_s: float
    median_kernel_s: float
    evaluations_per_s: float


PUBLIC_REPORTS = {
    ("Blackwell", mode): Path(
        f"public-3bb39f69/blackwell/litpcba/panel8-{mode}-extended.json"
    )
    for mode in ("shape", "rescore", "combo")
} | {
    ("TITAN V", mode): Path(
        f"public-3bb39f69/titanv/litpcba/panel8-{mode}-extended.json"
    )
    for mode in ("shape", "rescore", "combo")
}

FIELD_REPORT = Path("field-accuracy-3bb39f69/summary.json")
LITPCBA_CONFORMER_COUNTS = Path("litpcba-corpus-3bb39f69/conformer-counts.json")
# The Field* cells report the shipped default update rule on the declared subset.
FIELD_ROW = {"population": "first300k", "update_rule": "ADAGRAD_EXP"}
VOLTA_HEADLINE = Path(
    "archive/volta-production-headtohead-t114/results/summary_headline.json"
)
VOLTA_COMBINATION = Path(
    "archive/volta-production-headtohead-t114/results/summary_combination.json"
)
VOLTA_STEP_BUDGET = Path(
    "archive/volta-production-headtohead-t114/results/summary_step_budget.json"
)
DUDEZ_PARITY = Path(
    "archive/dudez-roshambo2-parity-t91/results/summary.json"
)
ARCHIVE_INDEX = Path("ARCHIVE_INDEX.md")
DEVELOPMENT_RECORD = Path("archive/agent-development-record")
D5_REPORT = Path("public-3bb39f69/blackwell/d5/panel4-shape.json")
SATURATION_REPORTS = {
    1: Path("rtx-pro-6000-3cr-3bb39f69/3cr/stability-combo-q1.json"),
    2: Path("rtx-pro-6000-3cr-3bb39f69/3cr/saturation-combo-q2.json"),
    4: Path("rtx-pro-6000-3cr-3bb39f69/3cr/stability-combo-q4.json"),
    8: Path("rtx-pro-6000-3cr-3bb39f69/3cr/saturation-combo-q8.json"),
    16: Path("rtx-pro-6000-3cr-3bb39f69/3cr/saturation-combo-q16.json"),
}


def read_timing(machine: str, mode: str, source: Path) -> Timing:
    report = json.loads(source.read_text(encoding="utf-8"))
    screen = report["screen"]
    repeats = screen["repeats"]
    if screen["mode"] != mode:
        raise ValueError(f"{source}: expected mode {mode!r}, got {screen['mode']!r}")
    if len(repeats) != screen["timed_repeats_requested"]:
        raise ValueError(f"{source}: timed repeat count is incomplete")
    if any(item.get("phase") != "timed" for item in repeats):
        raise ValueError(f"{source}: warm-up was mixed into measured repeats")

    wall = [float(item["screen_call_wall_s"]) for item in repeats]
    kernel = [float(item["kernel_s"]) for item in repeats]
    queries = int(report["query_preparation"]["n_queries"])
    conformers = int(report["corpus"]["conformers"])
    pairs = int(report["screen_size"]["conformer_pairs_per_repeat"])
    if pairs != queries * conformers:
        raise ValueError(f"{source}: conformer-query pair count is inconsistent")
    median_wall = statistics.median(wall)
    return Timing(
        machine=machine,
        mode=mode,
        source=source,
        queries=queries,
        conformers=conformers,
        repeats=len(repeats),
        median_wall_s=median_wall,
        median_kernel_s=statistics.median(kernel),
        evaluations_per_s=pairs / median_wall,
    )


def atomic_write(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(contents, encoding="utf-8")
    temporary.replace(path)


def find_ratio(report: dict, baseline: str, data_mode: str, roshambo3: Timing) -> dict:
    """Archived ROSHAMBO2 wall over this paper's ROSHAMBO3 wall on the same workload.
    The ROSHAMBO2 side is T114's session; the ROSHAMBO3 side is the public TITAN V run."""
    matches = [
        row for row in report["ratios"]
        if row["baseline"] == baseline and row["baseline_data_mode"] == data_mode
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one ratio for baseline={baseline}, data_mode={data_mode}"
        )
    row = matches[0]
    if (int(row["n_conformers"]), int(row["n_query"])) != (roshambo3.conformers, roshambo3.queries):
        raise ValueError(f"{baseline}: ROSHAMBO2 baseline and ROSHAMBO3 run screen different workloads")
    wall = float(row["roshambo2_wall_s"])
    return {"baseline": baseline, "roshambo2_wall_s": wall,
            "roshambo3_wall_s": roshambo3.median_wall_s,
            "ratio_search_only": wall / roshambo3.median_wall_s}


def unique_row(rows: list[dict], description: str, **selectors) -> dict:
    matches = [
        row for row in rows
        if all(row.get(key) == value for key, value in selectors.items())
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one {description} row matching {selectors}, got {len(matches)}"
        )
    return matches[0]


def development_tickets(runs: Path) -> list[dict[str, str]]:
    path = runs / DEVELOPMENT_RECORD / "tickets.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        tickets = list(csv.DictReader(handle))
    ids = {ticket["id"] for ticket in tickets}
    if len(ids) != len(tickets):
        raise ValueError(f"{path}: duplicate ticket ids")
    for ticket in tickets:
        if ticket["status"] not in {"open", "claimed", "in-review", "closed"}:
            raise ValueError(f"{path}: {ticket['id']} has unknown status {ticket['status']!r}")
        if (ticket["status"] == "closed") != bool(ticket["closed"]):
            raise ValueError(f"{path}: {ticket['id']} closed date disagrees with its status")
        if not set(ticket["depends_on"].split()) <= ids:
            raise ValueError(f"{path}: {ticket['id']} depends on an unknown ticket")
    return tickets


def longest_dependency_chain(tickets: list[dict[str, str]]) -> int:
    """Tickets on the longest depends_on path; the export guarantees no cycles."""
    depends = {ticket["id"]: ticket["depends_on"].split() for ticket in tickets}
    length: dict[str, int] = {}

    def chain(ticket: str, visiting: frozenset = frozenset()) -> int:
        if ticket in visiting:
            raise ValueError(f"dependency cycle through {ticket}")
        if ticket not in length:
            length[ticket] = 1 + max(
                (chain(d, visiting | {ticket}) for d in depends[ticket]), default=0)
        return length[ticket]

    return max(chain(ticket) for ticket in depends)


def development_counts(runs: Path) -> dict[str, int]:
    record = json.loads((runs / DEVELOPMENT_RECORD / "record.json").read_text(encoding="utf-8"))
    tickets = development_tickets(runs)
    with (runs / DEVELOPMENT_RECORD / "commit-days.csv").open(encoding="utf-8", newline="") as handle:
        days = list(csv.DictReader(handle))
    columns = [name for name in days[0] if name != "date"]
    commits_by_day = {day["date"]: sum(int(day[name]) for name in columns) for day in days}
    counts = {
        "tickets": len(tickets),
        "closed_tickets": sum(ticket["status"] == "closed" for ticket in tickets),
        "reviewed_tickets": sum(bool(ticket["reviewer"]) for ticket in tickets),
        "reopened_tickets": sum(ticket["reopened"] == "true" for ticket in tickets),
        "retroactive_tickets": sum(ticket["retroactive"] == "true" for ticket in tickets),
        "dependency_edges": sum(len(ticket["depends_on"].split()) for ticket in tickets),
        "longest_chain": longest_dependency_chain(tickets),
        "decisions": len(record["decisions"]),
        "pitfalls": len(record["pitfalls"]),
        "commits": sum(commits_by_day.values()),
        "active_days": sum(count > 0 for count in commits_by_day.values()),
        # The GPU engine of the submitted paper was built in August.
        "august_active_days": sum(
            count > 0 for day, count in commits_by_day.items() if day < "2026-09-01"),
        "origin_commits": sum(int(day["origin"]) for day in days),
    }
    if record["pitfalls"] != list(range(1, counts["pitfalls"] + 1)):
        raise ValueError("numbered pitfalls are not a contiguous 1..N sequence")
    if min(counts["tickets"], counts["decisions"], counts["pitfalls"]) == 0:
        raise ValueError("development-record count unexpectedly resolved to zero")
    return counts


def litpcba_conformer_counts(runs: Path, report: dict) -> dict:
    """LIT-PCBA's per-molecule conformer counts, for the corpus the benchmarks screened."""
    counts = json.loads((runs / LITPCBA_CONFORMER_COUNTS).read_text(encoding="utf-8"))
    corpus = report["corpus"]
    if counts["corpus"]["descriptor_sha256"] != corpus["descriptor_sha256"]:
        raise ValueError("LIT-PCBA conformer counts describe a different corpus than the benchmarks")
    histogram = {int(k): int(v) for k, v in counts["molecules_by_conformer_count"].items()}
    if (sum(histogram.values()), sum(k * v for k, v in histogram.items())) != (
            int(corpus["molecules"]), int(corpus["conformers"])):
        raise ValueError("LIT-PCBA conformer histogram disagrees with the corpus counts")
    if counts["compounds_without_conformers"] != counts["source_compounds"] - int(corpus["molecules"]):
        raise ValueError("LIT-PCBA compounds without conformers do not reconcile")
    return {**counts, "histogram": histogram}


def coordinate_step_log2(reports) -> int:
    """The on-disk coordinate step, 2**step_log2 A, which every benchmark corpus must share."""
    steps = {int(report["corpus"]["format"]["step_log2"]) for report in reports}
    if len(steps) != 1:
        raise ValueError(f"benchmark corpora use different coordinate steps: {sorted(steps)}")
    return steps.pop()


def signed(value: float, digits: int = 3) -> str:
    return f"{value:+.{digits}f}"


def current_results(runs: Path) -> dict:
    field = json.loads((runs / FIELD_REPORT).read_text(encoding="utf-8"))
    field_rows = [
        row for row in field["rows"] + field["alternates"]
        if all(row[key] == value for key, value in FIELD_ROW.items())
    ]
    if len(field_rows) != 1 or not field_rows[0]["gate_pass"]:
        raise ValueError(f"the field operating point {FIELD_ROW} is missing or failed its gate")
    titan = {mode: read_timing("TITAN V", mode, runs / PUBLIC_REPORTS[("TITAN V", mode)])
             for mode in ("shape", "combo")}

    headline = json.loads((runs / VOLTA_HEADLINE).read_text(encoding="utf-8"))
    combination = json.loads((runs / VOLTA_COMBINATION).read_text(encoding="utf-8"))
    step_budget = json.loads((runs / VOLTA_STEP_BUDGET).read_text(encoding="utf-8"))
    dudez = json.loads((runs / DUDEZ_PARITY).read_text(encoding="utf-8"))
    d5_path = runs / D5_REPORT
    d5_raw = json.loads(d5_path.read_text(encoding="utf-8"))
    d5 = read_timing("Blackwell", "shape", d5_path)
    litpcba_raw = json.loads(
        (runs / PUBLIC_REPORTS[("Blackwell", "shape")]).read_text(encoding="utf-8")
    )
    threecr_raw = json.loads(
        (runs / SATURATION_REPORTS[1]).read_text(encoding="utf-8")
    )
    d5_h2d_gb_per_s = statistics.median(
        float(row["device_stages_s"]["h2d_bytes"])
        / float(row["device_stages_s"]["h2d_s"])
        / 1e9
        for row in d5_raw["screen"]["repeats"]
    )
    saturation = {
        queries: read_timing("Blackwell", "combo", runs / path)
        for queries, path in SATURATION_REPORTS.items()
    }
    if any(item.queries != queries for queries, item in saturation.items()):
        raise ValueError("saturation report query count does not match its arm")

    combo_u2 = unique_row(
        combination["rows"], "combination baseline", arm="u2", data_mode="in_memory"
    )
    combo_corrected = unique_row(
        combination["rows"],
        "corrected combination baseline",
        arm="u2_color_skip",
        data_mode="in_memory",
    )
    wall_gap = abs(float(combo_corrected["wall_s"]) - float(combo_u2["wall_s"]))
    device_gap = abs(
        float(combo_corrected["stages_s"]["device_total_s"])
        - float(combo_u2["stages_s"]["device_total_s"])
    )
    if wall_gap == 0:
        raise ValueError("combination baseline wall-time gap is zero")
    for stage in ("host_prep_s", "host_reduce_s"):
        a = float(combo_u2["stages_s"][stage])
        b = float(combo_corrected["stages_s"][stage])
        if abs(a - b) / statistics.mean((a, b)) >= 0.01:
            raise ValueError(f"combination baseline {stage} differs by at least 1%")

    budget = unique_row(
        step_budget["step_budget_costs"], "step-budget comparison",
        steps_low=25, steps_high=100,
    )
    if not budget.get("same_session_same_clock_region"):
        raise ValueError("step-budget cells were not measured in one clock region")
    calculated_budget_ratio = float(budget["wall_s_high"]) / float(budget["wall_s_low"])
    if not math.isclose(calculated_budget_ratio, float(budget["high_over_low"]), rel_tol=1e-12):
        raise ValueError("reported and calculated step-budget ratios disagree")

    shape_ef = unique_row(
        dudez["head_to_head"], "DUDE-Z corrected shape EF1%",
        statistic="EF1%",
        base_arm="roshambo2/u2_numerics/shape",
        cand_arm="roshambo3/T66/shape",
    )
    combo_ef = unique_row(
        dudez["head_to_head"], "DUDE-Z corrected combination EF1%",
        statistic="EF1%",
        base_arm="roshambo2/u2_numerics/combination",
        cand_arm="roshambo3/T71/combination",
    )
    for row in (shape_ef, combo_ef):
        if not math.isclose(
            float(row["cand_mean"]) - float(row["base_mean"]),
            float(row["estimate"]), rel_tol=0, abs_tol=1e-12,
        ):
            raise ValueError("DUDE-Z paired estimate does not equal candidate minus baseline")
        if not float(row["lo"]) <= 0 <= float(row["hi"]):
            raise ValueError("DUDE-Z parity interval does not contain zero")
    if shape_ef["n_targets"] != combo_ef["n_targets"]:
        raise ValueError("DUDE-Z shape and combination target counts differ")
    if shape_ef["delta_min"] != combo_ef["delta_min"]:
        raise ValueError("DUDE-Z shape and combination margins differ")
    return {
        "field": field_rows[0],
        "field_report": field,
        "shape_stock": find_ratio(headline, "u2", "in_memory", titan["shape"]),
        "shape_corrected": find_ratio(headline, "u2_color_skip", "in_memory", titan["shape"]),
        "combo_stock": find_ratio(combination, "u2", "in_memory", titan["combo"]),
        "combo_corrected": find_ratio(
            combination, "u2_color_skip", "in_memory", titan["combo"]
        ),
        "d5": d5,
        "d5_molecules": int(d5_raw["corpus"]["molecules"]),
        "coordinate_step_log2": coordinate_step_log2((d5_raw, litpcba_raw, threecr_raw)),
        "litpcba_counts": litpcba_conformer_counts(runs, litpcba_raw),
        "d5_h2d_gb_per_s": d5_h2d_gb_per_s,
        "litpcba_molecules": int(litpcba_raw["corpus"]["molecules"]),
        "threecr_conformers": int(threecr_raw["corpus"]["conformers"]),
        "threecr_molecules": int(threecr_raw["corpus"]["molecules"]),
        "saturation": saturation,
        "combo_device_share_of_gap_percent": 100 * device_gap / wall_gap,
        "step_budget_ratio": calculated_budget_ratio,
        "dudez_shape": shape_ef,
        "dudez_combo": combo_ef,
        "development_counts": development_counts(runs),
    }


def litpcba_full_molecules(results: dict, context: dict) -> int:
    """Molecules that reached every requested conformer; none may exceed the request."""
    requested = int(context["corpora"]["litpcba"]["conformers_requested"])
    histogram = results["litpcba_counts"]["histogram"]
    if max(histogram) != requested:
        raise ValueError(f"LIT-PCBA conformer counts top out at {max(histogram)}, not {requested}")
    return histogram[requested]


def constants_tex(timings: list[Timing], results: dict, context: dict) -> str:
    by_key = {(item.machine, item.mode): item for item in timings}
    machine_names = {"Blackwell": "Blackwell", "TITAN V": "TitanV"}
    mode_names = {"shape": "Shape", "rescore": "Rescore", "combo": "Combo"}
    lines = [
        "% Generated by scripts/generate_paper_assets.py; do not edit.",
        r"\newcommand{\LitpcbaPanelQueries}{8}",
        rf"\newcommand{{\LitpcbaCorpusConformers}}{{{timings[0].conformers:,}}}",
        rf"\newcommand{{\LitpcbaCorpusMillionConformers}}{{{timings[0].conformers / 1e6:.2f}}}",
        rf"\newcommand{{\LitpcbaCorpusMolecules}}{{{results['litpcba_molecules']:,}}}",
        rf"\newcommand{{\LitpcbaDiskGigabytes}}{{{context['corpora']['litpcba']['disk_gb']:g}}}",
        rf"\newcommand{{\LitpcbaSourceCompounds}}{{{results['litpcba_counts']['source_compounds']:,}}}",
        rf"\newcommand{{\LitpcbaCompoundsWithoutConformers}}{{{results['litpcba_counts']['compounds_without_conformers']:,}}}",
        rf"\newcommand{{\LitpcbaFullConformerMolecules}}{{{litpcba_full_molecules(results, context):,}}}",
        rf"\newcommand{{\LitpcbaSourceSdfGigabytes}}{{{results['litpcba_counts']['source_sdf']['bytes'] / 1e9:.1f}}}",
        rf"\newcommand{{\LitpcbaConformersRequested}}{{{context['corpora']['litpcba']['conformers_requested']}}}",
        rf"\newcommand{{\LitpcbaConformerSeed}}{{{context['corpora']['litpcba']['conformer_seed']}}}",
        rf"\newcommand{{\LitpcbaNvmolkitVersion}}{{{context['corpora']['litpcba']['nvmolkit_version']}}}",
        rf"\newcommand{{\LitpcbaRdkitVersion}}{{{context['corpora']['litpcba']['rdkit_version']}}}",
        rf"\newcommand{{\LitpcbaQueryHeavyAtomRange}}{{{context['corpora']['litpcba']['query_heavy_atoms_min']}--{context['corpora']['litpcba']['query_heavy_atoms_max']}}}",
    ]
    for item in timings:
        stem = machine_names[item.machine] + "Litpcba" + mode_names[item.mode]
        lines.append(rf"\newcommand{{\{stem}WallSeconds}}{{{item.median_wall_s:.3f}}}")
        lines.append(
            rf"\newcommand{{\{stem}MillionEvaluationsPerSecond}}"
            rf"{{{item.evaluations_per_s / 1e6:.2f}}}"
        )
    for mode in mode_names:
        ratio = by_key[("TITAN V", mode)].median_wall_s / by_key[("Blackwell", mode)].median_wall_s
        lines.append(
            rf"\newcommand{{\BlackwellVsTitanV{mode_names[mode]}Speedup}}{{{ratio:.2f}}}"
        )
    field = results["field"]
    lines.extend([
        rf"\newcommand{{\FieldPanelRecallAtThousandPercent}}{{{100 * field['recall_at_1000_panel']:.2f}}}",
        rf"\newcommand{{\FieldWorstRecallAtThousandPercent}}{{{100 * field['recall_at_1000_worst']:.1f}}}",
        rf"\newcommand{{\FieldPanelTopHundredSetPercent}}{{{100 * field['top100_set_panel']:.2f}}}",
        rf"\newcommand{{\FieldMedianPoseRmsdAngstrom}}{{{field['pose_rmsd_median_A']:.3f}}}",
        rf"\newcommand{{\VoltaShapeStockSpeedup}}{{{results['shape_stock']['ratio_search_only']:.1f}}}",
        rf"\newcommand{{\VoltaShapeCorrectedSpeedup}}{{{results['shape_corrected']['ratio_search_only']:.1f}}}",
        rf"\newcommand{{\VoltaComboStockSpeedup}}{{{results['combo_stock']['ratio_search_only']:.1f}}}",
        rf"\newcommand{{\VoltaComboCorrectedSpeedup}}{{{results['combo_corrected']['ratio_search_only']:.1f}}}",
        # The abstract quotes the harder baseline per mode as whole numbers.
        rf"\newcommand{{\VoltaShapeCorrectedSpeedupWhole}}{{{results['shape_corrected']['ratio_search_only']:.0f}}}",
        rf"\newcommand{{\VoltaComboStockSpeedupWhole}}{{{results['combo_stock']['ratio_search_only']:.0f}}}",
        rf"\newcommand{{\FieldQueries}}{{{results['field_report']['config']['n_query']}}}",
        rf"\newcommand{{\FieldSubsetConformers}}{{{field['n_conf']:,}}}",
    ])
    d5 = results["d5"]
    lines.extend([
        rf"\newcommand{{\DfiveQueries}}{{{d5.queries}}}",
        rf"\newcommand{{\DfiveConformers}}{{{d5.conformers:,}}}",
        rf"\newcommand{{\DfiveWallSeconds}}{{{d5.median_wall_s:.2f}}}",
        rf"\newcommand{{\DfiveKernelSeconds}}{{{d5.median_kernel_s:.2f}}}",
        rf"\newcommand{{\DfiveMillionEvaluationsPerSecond}}{{{d5.evaluations_per_s / 1e6:.2f}}}",
        rf"\newcommand{{\DfiveMillionEvaluationsPerSecondWhole}}{{{d5.evaluations_per_s / 1e6:.0f}}}",
        rf"\newcommand{{\DfiveMillionConformersPerSecond}}{{{d5.conformers / d5.median_wall_s / 1e6:.2f}}}",
        rf"\newcommand{{\DfiveHtwoDGigabytesPerSecond}}{{{results['d5_h2d_gb_per_s']:.2f}}}",
        rf"\newcommand{{\DfiveMolecules}}{{{results['d5_molecules']:,}}}",
        rf"\newcommand{{\CoordinateStepLogTwo}}{{{results['coordinate_step_log2']}}}",
        rf"\newcommand{{\DfiveDiskGigabytes}}{{{context['corpora']['d5']['disk_gb']:g}}}",
        rf"\newcommand{{\DfiveMeanConformersPerMolecule}}{{{context['corpora']['d5']['mean_conformers_per_molecule']:.2f}}}",
        rf"\newcommand{{\ThreeCrConformers}}{{{results['threecr_conformers']:,}}}",
        rf"\newcommand{{\ThreeCrMillionConformersWhole}}{{{results['threecr_conformers'] / 1e6:.0f}}}",
        rf"\newcommand{{\ThreeCrMolecules}}{{{results['threecr_molecules']:,}}}",
        rf"\newcommand{{\ThreeCrDiskGigabytes}}{{{context['corpora']['3cr']['disk_gb']:g}}}",
        rf"\newcommand{{\ThreeCrMeanConformersPerMolecule}}{{{context['corpora']['3cr']['mean_conformers_per_molecule']:.2f}}}",
        rf"\newcommand{{\ThreeCrQueryHeavyAtoms}}{{{context['corpora']['3cr']['query_heavy_atoms']}}}",
    ])
    query_names = {1: "One", 2: "Two", 4: "Four", 8: "Eight", 16: "Sixteen"}
    for queries, item in sorted(results["saturation"].items()):
        lines.append(
            rf"\newcommand{{\ComboQ{query_names[queries]}MillionEvaluationsPerSecond}}"
            rf"{{{item.evaluations_per_s / 1e6:.2f}}}"
        )
    q8 = results["saturation"][8].evaluations_per_s
    q16 = results["saturation"][16].evaluations_per_s
    lines.append(
        rf"\newcommand{{\ComboQEightToSixteenGainPercent}}{{{100 * (q16 / q8 - 1):.1f}}}"
    )
    q1_wall = results["saturation"][1].median_wall_s
    stored_rate = context["corpora"]["3cr"]["disk_gb"] / q1_wall
    lines.extend([
        rf"\newcommand{{\ComboBaselineDeviceShareOfGapPercent}}{{{results['combo_device_share_of_gap_percent']:.1f}}}",
        rf"\newcommand{{\StepBudgetRatio}}{{{results['step_budget_ratio']:.3f}}}",
        rf"\newcommand{{\ComboQOneMillionConformersPerSecond}}{{{results['saturation'][1].evaluations_per_s / 1e6:.2f}}}",
        rf"\newcommand{{\ComboQSixteenMillionConformersPerSecond}}{{{results['saturation'][16].evaluations_per_s / 16e6:.2f}}}",
        rf"\newcommand{{\DudezTargets}}{{{results['dudez_shape']['n_targets']}}}",
        rf"\newcommand{{\DudezShapeEfBaseline}}{{{results['dudez_shape']['base_mean']:.3f}}}",
        rf"\newcommand{{\DudezShapeEfMethod}}{{{results['dudez_shape']['cand_mean']:.3f}}}",
        rf"\newcommand{{\DudezShapeEfDelta}}{{\ensuremath{{{signed(results['dudez_shape']['estimate'])}}}}}",
        rf"\newcommand{{\DudezShapeEfDeltaCi}}{{\ensuremath{{[{signed(results['dudez_shape']['lo'])},\,{signed(results['dudez_shape']['hi'])}]}}}}",
        rf"\newcommand{{\DudezComboEfBaseline}}{{{results['dudez_combo']['base_mean']:.3f}}}",
        rf"\newcommand{{\DudezComboEfMethod}}{{{results['dudez_combo']['cand_mean']:.3f}}}",
        rf"\newcommand{{\DudezComboEfDelta}}{{\ensuremath{{{signed(results['dudez_combo']['estimate'])}}}}}",
        rf"\newcommand{{\DudezComboEfDeltaCi}}{{\ensuremath{{[{signed(results['dudez_combo']['lo'])},\,{signed(results['dudez_combo']['hi'])}]}}}}",
        rf"\newcommand{{\DudezEfResolvableDelta}}{{{results['dudez_shape']['resolvable_delta_at_n']:.3f}}}",
        rf"\newcommand{{\DudezEfDeltaMin}}{{{results['dudez_shape']['delta_min']:.1f}}}",
        rf"\newcommand{{\TicketCount}}{{{results['development_counts']['tickets']:,}}}",
        rf"\newcommand{{\ClosedTicketCount}}{{{results['development_counts']['closed_tickets']:,}}}",
        rf"\newcommand{{\ReviewedTicketCount}}{{{results['development_counts']['reviewed_tickets']:,}}}",
        rf"\newcommand{{\ReopenedTicketCount}}{{{results['development_counts']['reopened_tickets']:,}}}",
        rf"\newcommand{{\RetroactiveTicketCount}}{{{results['development_counts']['retroactive_tickets']:,}}}",
        rf"\newcommand{{\TicketDependencyCount}}{{{results['development_counts']['dependency_edges']:,}}}",
        rf"\newcommand{{\LongestTicketChain}}{{{results['development_counts']['longest_chain']:,}}}",
        rf"\newcommand{{\DecisionCount}}{{{results['development_counts']['decisions']:,}}}",
        rf"\newcommand{{\PitfallCount}}{{{results['development_counts']['pitfalls']:,}}}",
        rf"\newcommand{{\DevelopmentCommitCount}}{{{results['development_counts']['commits']:,}}}",
        rf"\newcommand{{\DevelopmentActiveDays}}{{{results['development_counts']['active_days']:,}}}",
        rf"\newcommand{{\AugustActiveDays}}{{{results['development_counts']['august_active_days']:,}}}",
        rf"\newcommand{{\OriginCommitCount}}{{{results['development_counts']['origin_commits']:,}}}",
        rf"\newcommand{{\ThreeCrQOneWallSeconds}}{{{q1_wall:.2f}}}",
        rf"\newcommand{{\ThreeCrQOneWallSecondsWhole}}{{{q1_wall:.0f}}}",
        rf"\newcommand{{\ComboQSixteenWallSecondsPerQueryWhole}}{{{results['saturation'][16].median_wall_s / 16:.0f}}}",
        rf"\newcommand{{\ThreeCrStoredGigabytesPerSecond}}{{{stored_rate:.2f}}}",
        rf"\newcommand{{\ClaudePlan}}{{{context['ai_resources']['claude_plan']}}}",
        rf"\newcommand{{\ClaudePlanUsdPerMonth}}{{{context['ai_resources']['claude_plan_usd_per_month']}}}",
        rf"\newcommand{{\ChatgptPlan}}{{{context['ai_resources']['chatgpt_plan']}}}",
        rf"\newcommand{{\ChatgptPlanUsdPerMonth}}{{{context['ai_resources']['chatgpt_plan_usd_per_month']}}}",
        rf"\newcommand{{\AdditionalCreditUsdBelow}}{{{context['ai_resources']['additional_credit_usd_below']}}}",
        rf"\newcommand{{\BlackwellCpuCores}}{{{context['systems']['blackwell']['cpu_cores']}}}",
        rf"\newcommand{{\BlackwellRamGiB}}{{{context['systems']['blackwell']['ram_gib']}}}",
        rf"\newcommand{{\BlackwellGpuMemoryGiB}}{{{context['systems']['blackwell']['gpu_memory_gib']}}}",
        rf"\newcommand{{\BlackwellGpuPowerWatts}}{{{context['systems']['blackwell']['gpu_power_w']}}}",
        rf"\newcommand{{\VoltaCpuCores}}{{{context['systems']['volta']['cpu_cores']}}}",
        rf"\newcommand{{\VoltaRamGiB}}{{{context['systems']['volta']['ram_gib']}}}",
        rf"\newcommand{{\VoltaGpuMemoryGiB}}{{{context['systems']['volta']['gpu_memory_gib']}}}",
        rf"\newcommand{{\VoltaGpuPowerWatts}}{{{context['systems']['volta']['gpu_power_w']}}}",
        rf"\newcommand{{\AnalyticShapeRegistersPerThread}}{{{context['profiling']['analytic_shape']['registers_per_thread']}}}",
        rf"\newcommand{{\AnalyticShapeActiveWarpsPercent}}{{{context['profiling']['analytic_shape']['active_warps_percent']:.1f}}}",
        rf"\newcommand{{\FieldShapeRegistersPerThread}}{{{context['profiling']['field_shape']['registers_per_thread']}}}",
        rf"\newcommand{{\FieldShapeActiveWarpsPercent}}{{{context['profiling']['field_shape']['active_warps_percent']:.1f}}}",
        rf"\newcommand{{\FieldShapeFmaPercent}}{{{context['profiling']['field_shape']['fma_percent']:.1f}}}",
        rf"\newcommand{{\FieldShapeLoneTexThroughputPercent}}{{{context['profiling']['field_shape']['l1tex_throughput_percent']:.1f}}}",
        rf"\newcommand{{\FieldShapeLtwoThroughputPercent}}{{{context['profiling']['field_shape']['l2_throughput_percent']:.1f}}}",
        r"\newcommand{\TenGigETheoreticalGigabytesPerSecond}{1.25}",
    ])
    return "\n".join(lines) + "\n"


def system_record_checks(runs: Path, key: str, system: dict) -> None:
    """Refuse a systems-table row the machine's own run record contradicts."""
    env = json.loads((runs / "portability" / system["record"] / "env.json").read_text(encoding="utf-8"))
    lscpu = env.get("lscpu") or ""
    if lscpu:
        model = re.search(r"Model name:\s*(.*)", lscpu).group(1)
        if system["cpu"].split()[-1].lower() not in model.lower():
            raise ValueError(f"{key}: CPU {system['cpu']!r} is not the recorded {model!r}")
        threads = int(re.search(r"^CPU\(s\):\s*(\d+)", lscpu, re.MULTILINE).group(1))
        if threads != system["threads"]:
            raise ValueError(f"{key}: {system['threads']} threads, the record has {threads}")
    smi = env.get("nvidia_smi") or ""
    if smi:
        name = re.search(r"Product Name\s*:\s*(.*)", smi).group(1).strip()
        mib = float(re.search(r"FB Memory Usage\s*\n\s*Total\s*:\s*(\d+)", smi).group(1))
        watts = float(re.search(r"Current Power Limit\s*:\s*([\d.]+)", smi).group(1))
        if not name.startswith(system["gpu"]) or abs(mib / 1024 - system["gpu_memory_gib"]) >= 1 \
                or watts != system["gpu_power_w"]:
            raise ValueError(f"{key}: GPU facts disagree with the record ({name}, {mib} MiB, {watts} W)")
    profile = env.get("system_profiler")
    if profile:
        hardware = json.loads(profile)["SPHardwareDataType"][0]
        cores = int(hardware["number_processors"].split()[1].split(":")[0])
        memory = int(hardware["physical_memory"].split()[0])
        if hardware["chip_type"] != system["cpu"] or cores != system["cpu_cores"] or memory != system["ram_gib"]:
            raise ValueError(f"{key}: Mac facts disagree with the record ({hardware['chip_type']}, {cores}, {memory})")


def systems_table(runs: Path, context: dict) -> str:
    """Appendix table of every benchmarked machine."""
    rows = []
    for key in context["systems_order"]:
        system = context["systems"][key]
        system_record_checks(runs, key, system)
        cores = (str(system["cpu_cores"]) if system["threads"] == system["cpu_cores"]
                 else f"{system['cpu_cores']}/{system['threads']}")
        memory = f"{system['gpu_memory_gib']:g}" if "gpu_memory_gib" in system else "--"
        power = str(system["gpu_power_w"]) if "gpu_power_w" in system else "--"
        where = system.get("cloud_shape") or system.get("storage_label") or "--"
        rows.append(rf"    {system['label']} & {system['cpu_label']} & {cores} & {system['ram_gib']:g} & "
                    rf"{system.get('gpu_label', '--')} & {memory} & {power} & {where} \\")
    left = r">{\raggedright\arraybackslash}"
    return "\n".join([
        "% Generated by scripts/generate_paper_assets.py; do not edit.",
        r"\begin{table}[h]",
        r"  \centering",
        r"  \scriptsize",
        r"  \caption{Benchmarked machines. Cores/threads count physical cores and hardware threads"
        r" (vCPUs on cloud VMs); power is the GPU's power limit. CPU, thread, GPU-memory and power-limit"
        r" facts are checked against each machine's run record. The last column is the cloud machine"
        r" type or the local corpus storage.}",
        r"  \label{tab:systems}",
        rf"  \begin{{tabularx}}{{\textwidth}}{{@{{}}{left}p{{1.8cm}}{left}X rr {left}p{{1.8cm}} rr {left}p{{2.1cm}}@{{}}}}",
        r"    \toprule",
        r"    & & Cores/ & RAM & & GPU mem & Power & Instance \\",
        r"    Machine & CPU & threads & (GiB) & GPU & (GiB) & (W) & or storage \\",
        r"    \midrule",
        *rows,
        r"    \bottomrule",
        r"  \end{tabularx}",
        r"\end{table}",
        "",
    ])


def main_results_table(results: dict) -> str:
    return r"""% Generated by scripts/generate_paper_assets.py; do not edit.
\begin{table}[t]
  \centering
  \small
  \caption{Accuracy and matched TITAN V performance. Field recall uses \FieldQueries{}
  queries against \FieldSubsetConformers{} conformers and a corrected analytic reference;
  DUDE-Z reports paired EF1\% differences with 95\% BCa intervals. Speedups
  use identical \LitpcbaPanelQueries-query, \LitpcbaCorpusMillionConformers-million-conformer searches.}
  \label{tab:main-results}
  \begin{tabular}{@{}llr@{}}
    \toprule
    Question & Measure & Result \\
    \midrule
    Field retrieval & mean / worst recall@$1{,}000$ &
      \FieldPanelRecallAtThousandPercent\% / \FieldWorstRecallAtThousandPercent\% \\
    Field retrieval & mean top-$100$ set agreement &
      \FieldPanelTopHundredSetPercent\% \\
    DUDE-Z shape parity & \multirow{2}{*}{paired $\Delta$ EF1\% (95\% CI)} &
      \DudezShapeEfDelta{} \DudezShapeEfDeltaCi{} \\
    DUDE-Z combo parity & &
      \DudezComboEfDelta{} \DudezComboEfDeltaCi{} \\
    Shape speed & \multirow{2}{*}{vs. color-skip / as-released ROSHAMBO2} &
      \VoltaShapeCorrectedSpeedup$\times$ / \VoltaShapeStockSpeedup$\times$ \\
    Combo speed & &
      \VoltaComboCorrectedSpeedup$\times$ / \VoltaComboStockSpeedup$\times$ \\
    \bottomrule
  \end{tabular}
\end{table}
"""


def shipped_kernel_table() -> str:
    return r"""% Generated by scripts/generate_paper_assets.py; do not edit.
\begin{table}[H]
  \centering
  \small
  \caption{Production field-kernel operating points. $W_A$ is the number of
  lanes cooperating on one atom loop; $S$ is the number of such lane groups
  sharing a library row and dividing its starting orientations. ``Shared 48'' stages
  the first 48 library color sites and reads any tail from global memory.}
  \label{tab:shipped-kernel-config}
  \begin{tabular}{@{}p{0.29\linewidth}p{0.31\linewidth}p{0.31\linewidth}@{}}
    \toprule
    Setting & Shape / color rescore & Combo optimization \\
    \midrule
    Threads per block & 256 & 256 \\
    $W_A$ / $S$ & 4 / 1 & 4 / 4 \\
    Query shape objective & fp16 \texttt{half4} texture & fp16 \texttt{half4} texture \\
    Query coordinate record & fp32 \texttt{float4}, shared & fp32 \texttt{float4}, shared \\
    Library shape & three-plane int16, shared & three-plane int16, shared \\
    Library color & global, terminal score only & three-plane int16, shared 48 \\
    Preferred SMEM carveout & 25\% & 25\% \\
    Minimum blocks/SM & 4 & 2 \\
    Update ownership & per-lane & per-lane \\
    Color evaluation & analytic at final pose & analytic at every step \\
    \bottomrule
  \end{tabular}
\end{table}
"""


def svg_to_pdf(svg: str, svg_path: Path, pdf_path: Path) -> None:
    """Write an inspectable SVG source and render it to a vector PDF."""
    mutool = shutil.which("mutool")
    if mutool is None:
        raise RuntimeError("mutool is required to render generated vector figures")
    atomic_write(svg_path, svg)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [mutool, "convert", "-o", str(pdf_path), str(svg_path)],
        check=True,
        capture_output=True,
        text=True,
    )


def field_schematic_svg() -> str:
    matrix = []
    for row in range(5):
        for column in range(6):
            x, y = 94 + 34 * column, 69 + 29 * row
            matrix.append(f'<rect x="{x}" y="{y}" width="30" height="25" fill="#eef3f8" stroke="#aeb9c5" stroke-width="1"/>')
            matrix.append(f'<circle cx="{x + 15}" cy="{y + 12.5}" r="4.2" fill="#707b87"/>')
    matrix_svg = "\n".join(matrix)
    query_labels = "\n".join(
        f'<circle cx="72" cy="{81.5 + 29*row}" r="6" fill="#2866a6" stroke="#173e66" stroke-width="1.2"/>'
        f'<text x="58" y="{86 + 29*row}" text-anchor="end" class="atomlabel">a{row + 1}</text>'
        for row in range(5)
    )
    library_labels = "\n".join(
        f'<circle cx="{109 + 34*column}" cy="53" r="6" fill="#e68a2e" stroke="#8d4e10" stroke-width="1.2"/>'
        f'<text x="{109 + 34*column}" y="40" text-anchor="middle" class="atomlabel">b{column + 1}</text>'
        for column in range(6)
    )
    grid = "\n".join(
        [f'<line x1="{x}" y1="57" x2="{x}" y2="204" stroke="#b9c7d6" stroke-width="1"/>' for x in range(430, 656, 25)]
        + [f'<line x1="430" y1="{y}" x2="655" y2="{y}" stroke="#b9c7d6" stroke-width="1"/>' for y in range(57, 205, 25)]
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="920" height="270" viewBox="0 0 920 270">
<defs>
  <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#333"/></marker>
  <marker id="gradarrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" fill="#b42424"/></marker>
</defs>
<style>
text {{ font-family: Helvetica, Arial, sans-serif; fill:#111; }}
.panel {{ font-size:18px; font-weight:bold; }} .title {{ font-size:16px; font-weight:bold; }}
.label {{ font-size:14px; }} .small {{ font-size:12px; }} .atomlabel {{ font-size:12px; font-style:italic; }}
.cell {{ fill:#eef3f8; stroke:#aeb9c5; stroke-width:1; }} .pairdot {{ fill:#707b87; }}
.query {{ fill:#2866a6; stroke:#173e66; stroke-width:1.2; }} .library {{ fill:#e68a2e; stroke:#8d4e10; stroke-width:1.2; }}
.grid {{ stroke:#b9c7d6; stroke-width:1; }} .box {{ fill:#f7f8fa; stroke:#929da8; stroke-width:1.2; rx:6; }}
</style>
<rect width="920" height="270" fill="white"/>

<text x="18" y="25" class="panel">A</text>
<text x="178" y="25" text-anchor="middle" class="title">Direct analytic atom-pair loop</text>
{matrix_svg}
{query_labels}
{library_labels}
<text x="196" y="224" text-anchor="middle" class="label">library atoms, B</text>
<text x="22" y="139" text-anchor="middle" class="label" transform="rotate(-90 22 139)">query atoms, A</text>
<text x="196" y="249" text-anchor="middle" class="small">evaluate every matrix cell: A × B Gaussians per step</text>

<path d="M325 135 L386 135" stroke="#333" stroke-width="2" marker-end="url(#arrow)"/>
<text x="356" y="118" text-anchor="middle" class="small">transpose</text>
<text x="356" y="153" text-anchor="middle" class="small">query once</text>

<text x="402" y="25" class="panel">B</text>
<text x="654" y="25" text-anchor="middle" class="title">Query field + library-atom lookup loop</text>
{grid}
<circle cx="474" cy="92" r="35" fill="#2866a6" opacity="0.08"/><circle cx="474" cy="92" r="22" fill="#2866a6" opacity="0.13"/><circle cx="474" cy="92" r="6" fill="#2866a6" stroke="#173e66" stroke-width="1.2"/>
<circle cx="536" cy="151" r="39" fill="#2866a6" opacity="0.08"/><circle cx="536" cy="151" r="24" fill="#2866a6" opacity="0.13"/><circle cx="536" cy="151" r="6" fill="#2866a6" stroke="#173e66" stroke-width="1.2"/>
<circle cx="607" cy="96" r="37" fill="#2866a6" opacity="0.08"/><circle cx="607" cy="96" r="23" fill="#2866a6" opacity="0.13"/><circle cx="607" cy="96" r="6" fill="#2866a6" stroke="#173e66" stroke-width="1.2"/>
<text x="448" y="48" class="small" fill="#173e66">query Gaussians rasterized once</text>

<g fill="#e68a2e" stroke="#8d4e10" stroke-width="1.2"><circle cx="462" cy="166" r="7"/><circle cx="512" cy="112" r="7"/><circle cx="580" cy="170" r="7"/><circle cx="630" cy="132" r="7"/></g>
<text x="450" y="184" class="atomlabel">b1</text><text x="518" y="128" class="atomlabel">b2</text>
<text x="568" y="189" class="atomlabel">b3</text><text x="635" y="151" class="atomlabel">b4</text>
<path d="M462 166 l18 -17" stroke="#b42424" stroke-width="2" marker-end="url(#gradarrow)"/>
<path d="M512 112 l-15 -18" stroke="#b42424" stroke-width="2" marker-end="url(#gradarrow)"/>
<path d="M580 170 l17 -16" stroke="#b42424" stroke-width="2" marker-end="url(#gradarrow)"/>
<path d="M630 132 l-13 -18" stroke="#b42424" stroke-width="2" marker-end="url(#gradarrow)"/>

<rect x="688" y="55" width="205" height="38" rx="6" fill="#f7f8fa" stroke="#929da8" stroke-width="1.2"/><text x="790" y="70" text-anchor="middle" class="small">for each library atom</text><text x="790" y="85" text-anchor="middle" class="small">transform: x = Rb + t</text>
<path d="M790 94 L790 108" stroke="#333" stroke-width="1.5" marker-end="url(#arrow)"/>
<rect x="688" y="112" width="205" height="38" rx="6" fill="#f7f8fa" stroke="#929da8" stroke-width="1.2"/><text x="790" y="128" text-anchor="middle" class="small">tex3D(x)</text><text x="790" y="143" text-anchor="middle" class="small">interpolate value + gradient</text>
<path d="M790 151 L790 165" stroke="#333" stroke-width="1.5" marker-end="url(#arrow)"/>
<rect x="688" y="169" width="205" height="38" rx="6" fill="#f7f8fa" stroke="#929da8" stroke-width="1.2"/><text x="790" y="185" text-anchor="middle" class="small">accumulate overlap</text><text x="790" y="200" text-anchor="middle" class="small">and force/torque</text>

<circle cx="445" cy="239" r="6" fill="#2866a6" stroke="#173e66" stroke-width="1.2"/><text x="457" y="244" class="small">query atom / field</text>
<circle cx="570" cy="239" r="6" fill="#e68a2e" stroke="#8d4e10" stroke-width="1.2"/><text x="582" y="244" class="small">library atom</text>
<path d="M683 239 l20 -12" stroke="#b42424" stroke-width="2" marker-end="url(#gradarrow)"/><text x="710" y="244" class="small">interpolated gradient</text>
</svg>'''


def saturation_svg(results: dict) -> str:
    items = sorted(results["saturation"].items())
    # A conventional measured-point plot: query count is logarithmic by design
    # (each arm doubles q), the rate axis starts at zero, and straight segments
    # connect observations without suggesting an inferred asymptote.
    left, right, top, bottom = 66, 474, 20, 218
    ymin, ymax = 0.0, 20.0
    x_at = lambda index: left + index * (right - left) / (len(items) - 1)
    y_at = lambda rate: bottom - (rate - ymin) * (bottom - top) / (ymax - ymin)
    rates = [item.evaluations_per_s / 1e6 for _, item in items]
    points = " ".join(f"{x_at(i):.1f},{y_at(rate):.1f}" for i, rate in enumerate(rates))
    ygrid = "\n".join(
        f'<line x1="{left}" y1="{y_at(y):.1f}" x2="{right}" y2="{y_at(y):.1f}" stroke="#dfe3e8" stroke-width="1"/>'
        f'<text x="{left-9}" y="{y_at(y)+4:.1f}" text-anchor="end" font-size="11">{y}</text>'
        for y in (0, 5, 10, 15, 20)
    )
    marks = "\n".join(
        f'<circle cx="{x_at(i):.1f}" cy="{y_at(rate):.1f}" r="4.5" fill="#2866a6" stroke="white" stroke-width="1.2"/>'
        f'<text x="{x_at(i):.1f}" y="{bottom+20}" text-anchor="middle" font-size="11">{queries}</text>'
        for i, ((queries, _), rate) in enumerate(zip(items, rates))
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="510" height="270" viewBox="0 0 510 270" font-family="Helvetica,Arial,sans-serif" fill="#202124">
<rect width="510" height="270" fill="white"/>{ygrid}
<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#30343b" stroke-width="1.2"/><line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#30343b" stroke-width="1.2"/>
<polyline points="{points}" fill="none" stroke="#2866a6" stroke-width="2.4" stroke-linejoin="round"/>{marks}
<text x="270" y="260" text-anchor="middle" font-size="11">concurrent query conformers (log2 spacing)</text>
<text x="15" y="125" text-anchor="middle" font-size="11" transform="rotate(-90 15 125)">million conformer-query evaluations/s</text>
</svg>'''


def public_performance_table(timings: list[Timing]) -> str:
    rows = []
    for item in timings:
        mode = {"shape": "Shape", "rescore": "Shape + color rescore", "combo": "Joint combo"}[item.mode]
        rows.append(
            f"    {item.machine} & {mode} & {item.median_wall_s:.3f} & "
            f"{item.evaluations_per_s / 1e6:.2f} \\\\"
        )
    body = "\n".join(rows)
    return rf"""% Generated by scripts/generate_paper_assets.py; do not edit.
\begin{{table}}[t]
  \centering
  \small
  \caption{{End-to-end LIT-PCBA panel timing. Each repeat screens eight query
  structures against 20,381,286 conformers; values are medians over measured
  warm-cache repeats.}}
  \label{{tab:public-performance}}
  \begin{{tabular}}{{@{{}}llrr@{{}}}}
    \toprule
    GPU & Mode & Wall time (s) & M eval./s \\
    \midrule
{body}
    \bottomrule
  \end{{tabular}}
\end{{table}}
"""


TICKET_MILESTONES = Path("data/ticket-milestones.json")
TICKET_CALLOUTS = Path("data/ticket-callouts.json")
# Categorical slots 1, 2, 3, 7 of the validated reference palette, assigned to
# tiers in a fixed order.
TIER_STYLE = [
    ("haiku", "Haiku / Luna tier", "#eb6834"),
    ("sonnet", "Sonnet / Terra tier", "#1baf7a"),
    ("opus", "Opus / Sol tier", "#2a78d6"),
    ("fable", "Fable / Astra tier", "#6250d6"),
]


def dashed_vline(x: float, y0: float, y1: float, width: float, dash: float = 3.0, gap: float = 2.0) -> list[str]:
    """A dashed vertical line as explicit segments: mutool's SVG renderer ignores
    stroke-dasharray and would draw it solid."""
    segments, y = [], y0
    while y < y1:
        segments.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{min(y + dash, y1):.1f}" '
                        f'stroke="#30343b" stroke-width="{width}"/>')
        y += dash + gap
    return segments


def ticket_timeline_svg(runs: Path, milestones_path: Path = TICKET_MILESTONES) -> str:
    from datetime import date, datetime, timedelta

    record = json.loads((runs / DEVELOPMENT_RECORD / "record.json").read_text(encoding="utf-8"))
    tickets = sorted(development_tickets(runs), key=lambda t: int(t["number"]))
    with (runs / DEVELOPMENT_RECORD / "commit-days.csv").open(encoding="utf-8", newline="") as handle:
        day_rows = list(csv.DictReader(handle))
    milestones = json.loads(milestones_path.read_text(encoding="utf-8"))["milestones"]
    tiers = {key: (label, color) for key, label, color in TIER_STYLE}
    unknown = {t["model_tier"] for t in tickets} - set(tiers)
    if unknown:
        raise ValueError(f"tickets carry tiers with no style: {sorted(unknown)}")

    def when(stamp: str) -> datetime:
        return datetime.fromisoformat(stamp)

    start = datetime.fromisoformat("2026-08-15T00:00:00+00:00")
    exported = when(record["exported_utc"])
    last = max([exported.date()] + [date.fromisoformat(m["date"]) for m in milestones])
    end = datetime.combine(last + timedelta(days=1), datetime.min.time(), exported.tzinfo)
    left, right, plot_right = 182.0, 800.0, 778.0
    strip_top, strip_bottom = 70.0, 132.0
    top, bottom = 152.0, 682.0
    span_s = (end - start).total_seconds()
    x_at = lambda moment: left + (moment - start).total_seconds() / span_s * (plot_right - left)
    row_h = (bottom - top) / len(tickets)
    row_y = {t["id"]: top + i * row_h for i, t in enumerate(tickets)}

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{right:.0f}" height="740" '
        f'viewBox="0 0 {right:.0f} 740" font-family="Helvetica,Arial,sans-serif" fill="#202124">',
        f'<rect width="{right:.0f}" height="740" fill="white"/>',
    ]

    # Legend, one swatch per tier actually present, with its ticket count.
    counts = Counter(t["model_tier"] for t in tickets)
    x, y = left, 18.0
    for key, label, color in TIER_STYLE:
        if not counts[key]:
            continue
        text = f"{label} ({counts[key]})"
        width = 30 + 7.4 * len(text)
        if x + width > right:
            x, y = left, y + 22
        out.append(f'<rect x="{x:.1f}" y="{y - 10:.1f}" width="16" height="11" rx="2" fill="{color}"/>')
        out.append(f'<text x="{x + 21:.1f}" y="{y:.1f}" font-size="13.5">{text}</text>')
        x += width

    # Commits per day, aligned with the timeline.
    by_day = {
        row["date"]: sum(int(row[name]) for name in row if name != "date") for row in day_rows
    }
    peak = max(by_day.values())
    scale_top = 100 * math.ceil(peak / 100)
    y_strip = lambda n: strip_bottom - n / scale_top * (strip_bottom - strip_top)
    for tick in range(0, scale_top + 1, scale_top // 2):
        out.append(f'<line x1="{left}" y1="{y_strip(tick):.1f}" x2="{plot_right}" y2="{y_strip(tick):.1f}" stroke="#e4e4e0" stroke-width="0.8"/>')
        out.append(f'<text x="{left - 6}" y="{y_strip(tick) + 3.5:.1f}" text-anchor="end" font-size="12.5" fill="#5f6368">{tick}</text>')
    out.append(f'<text x="{left - 44}" y="{(strip_top + strip_bottom) / 2 + 4:.1f}" text-anchor="end" font-size="13.5">commits/day</text>')
    day_w = (plot_right - left) * 86400 / span_s
    for day, n in sorted(by_day.items()):
        moment = datetime.fromisoformat(day + "T00:00:00+00:00")
        out.append(f'<rect x="{x_at(moment) + 1:.1f}" y="{y_strip(n):.1f}" width="{day_w - 2:.1f}" height="{strip_bottom - y_strip(n):.1f}" fill="#7d7d78"/>')

    # The longest commit-free run: shaded through both panels.
    quiet, run = [], []
    day = start.date()
    while day < exported.date():
        if by_day.get(day.isoformat(), 0) == 0:
            run.append(day)
        else:
            quiet = max(quiet, run, key=len)
            run = []
        day += timedelta(days=1)
    quiet = max(quiet, run, key=len)
    if len(quiet) >= 5:
        a = x_at(datetime.combine(quiet[0], datetime.min.time(), start.tzinfo))
        b = x_at(datetime.combine(quiet[-1] + timedelta(days=1), datetime.min.time(), start.tzinfo))
        out.append(f'<rect x="{a:.1f}" y="{strip_top}" width="{b - a:.1f}" height="{bottom - strip_top:.1f}" fill="#f1f1ee"/>')
        out.append(f'<text x="{(a + b) / 2:.1f}" y="{top + 14}" text-anchor="middle" font-size="13" fill="#5f6368">no commits</text>')

    # Epoch bands and their labels, nudged apart where bands are thin.
    epochs = record["epochs"]
    label_y = []
    for index, epoch in enumerate(epochs):
        rows = [row_y[t["id"]] for t in tickets if t["epoch"] == epoch["key"]]
        if not rows:
            continue
        y0, y1 = min(rows), max(rows) + row_h
        if index % 2 == 0:
            out.append(f'<rect x="{left}" y="{y0:.1f}" width="{plot_right - left}" height="{y1 - y0:.1f}" fill="#f6f6f3"/>')
        out.append(f'<line x1="{left}" y1="{y0:.1f}" x2="{plot_right}" y2="{y0:.1f}" stroke="#d9d9d4" stroke-width="0.6"/>')
        y = max((y0 + y1) / 2 + 4, (label_y[-1] + 15) if label_y else 0)
        label_y.append(y)
        out.append(f'<text x="{left - 6}" y="{y:.1f}" text-anchor="end" font-size="13.5">{epoch["label"]}</text>')

    # The workshop's deadlines and notification.
    for index, milestone in enumerate(milestones):
        xm = x_at(datetime.fromisoformat(milestone["date"] + "T00:00:00+00:00"))
        out.extend(dashed_vline(xm, strip_top - 4, bottom, 0.8))
        # Labels sit above the commit strip. A label that would run past the plot sits to the left of its line.
        width = 6.6 * len(milestone["label"])
        anchor, xt = ("end", xm - 3) if xm + 3 + width > plot_right else ("start", xm + 3)
        out.append(f'<text x="{xt:.1f}" y="{strip_top - 7:.1f}" text-anchor="{anchor}" font-size="13" fill="#30343b">{milestone["label"]}</text>')

    # One bar per ticket: created to closed; open tickets run faintly to the export.
    for t in tickets:
        color = tiers[t["model_tier"]][1]
        a = x_at(when(t["created"]))
        closed = bool(t["closed"])
        b = x_at(when(t["closed"])) if closed else x_at(exported)
        width = max(b - a, 2.2)
        opacity = "" if closed else ' fill-opacity="0.32"'
        out.append(f'<rect x="{a:.2f}" y="{row_y[t["id"]] + 0.12 * row_h:.2f}" width="{width:.2f}" height="{0.76 * row_h:.2f}" fill="{color}"{opacity}/>')

    # Axes.
    out.append(f'<line x1="{left}" y1="{bottom}" x2="{plot_right}" y2="{bottom}" stroke="#30343b" stroke-width="1"/>')
    tick = start
    while tick <= end:
        xt = x_at(tick)
        out.append(f'<line x1="{xt:.1f}" y1="{bottom}" x2="{xt:.1f}" y2="{bottom + 4}" stroke="#30343b" stroke-width="1"/>')
        out.append(f'<text x="{xt:.1f}" y="{bottom + 19}" text-anchor="middle" font-size="13">{tick.strftime("%b")} {tick.day}</text>')
        tick += timedelta(days=7)
    out.append(f'<text x="{(left + plot_right) / 2:.1f}" y="{bottom + 42}" text-anchor="middle" font-size="13.5">ticket opened to closed, 2026; one row per ticket, in id order</text>')
    out.append("</svg>")
    return "\n".join(out)


# The main-text strip: one dot per ticket over commits per day, with the largest
# burst of ticket starts in each epoch circled and labeled with the epoch.
BURST_GAP_HOURS = 4
BURST_MIN_TICKETS = 10


def ticket_bursts(tickets: list[dict], spans: dict | None = None) -> list[dict]:
    """Per epoch, its largest run of ticket starts with no gap over BURST_GAP_HOURS.

    ``spans`` maps an epoch to an explicit ``first``..``last`` ticket range that
    replaces its burst: a multi-day wave that overnight gaps split into small runs.
    """
    from datetime import datetime, timedelta

    ordered = sorted(tickets, key=lambda t: (t["created"], int(t["number"])))
    runs, current = [], []
    for ticket in ordered:
        moment = datetime.fromisoformat(ticket["created"])
        if current and moment - datetime.fromisoformat(current[-1]["created"]) > timedelta(hours=BURST_GAP_HOURS):
            runs.append(current)
            current = []
        current.append(ticket)
    runs.append(current)
    best = {}
    for run in runs:
        for epoch in {t["epoch"] for t in run}:
            members = [t for t in run if t["epoch"] == epoch]
            if len(members) >= BURST_MIN_TICKETS and len(members) > len(best.get(epoch, [])):
                best[epoch] = members
    for epoch, span in (spans or {}).items():
        first, last = int(span["first"].lstrip("T")), int(span["last"].lstrip("T"))
        members = [t for t in ordered if t["epoch"] == epoch and first <= int(t["number"]) <= last]
        if not members:
            raise ValueError(f"callout span for {epoch} holds no ticket of that epoch")
        best[epoch] = members
    return [{"epoch": epoch, "members": members} for epoch, members in best.items()]


def ticket_strip_svg(runs: Path, milestones_path: Path = TICKET_MILESTONES,
                     callouts_path: Path = TICKET_CALLOUTS) -> str:
    from datetime import datetime, timedelta

    record = json.loads((runs / DEVELOPMENT_RECORD / "record.json").read_text(encoding="utf-8"))
    tickets = sorted(development_tickets(runs), key=lambda t: int(t["number"]))
    with (runs / DEVELOPMENT_RECORD / "commit-days.csv").open(encoding="utf-8", newline="") as handle:
        day_rows = list(csv.DictReader(handle))
    milestones = json.loads(milestones_path.read_text(encoding="utf-8"))["milestones"]
    tiers = {key: (label, color) for key, label, color in TIER_STYLE}
    labels = {epoch["key"]: epoch["label"] for epoch in record["epochs"]}
    callouts = json.loads(callouts_path.read_text(encoding="utf-8"))
    sides, spans = callouts["sides"], callouts.get("spans", {})

    when = datetime.fromisoformat
    start = when("2026-08-15T00:00:00+00:00")
    exported = when(record["exported_utc"])
    last = max([exported.date()] + [datetime.fromisoformat(m["date"]).date() for m in milestones])
    end = datetime.combine(last + timedelta(days=1), datetime.min.time(), exported.tzinfo)
    width, height = 800.0, 336.0
    left, right = 92.0, 790.0
    strip_top, strip_bottom, top, bottom = 60.0, 94.0, 110.0, 292.0
    x_at = lambda moment: left + (moment - start).total_seconds() / (end - start).total_seconds() * (right - left)
    y_at = {t["id"]: top + i / (len(tickets) - 1) * (bottom - top) for i, t in enumerate(tickets)}

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" font-family="Helvetica,Arial,sans-serif" fill="#202124">',
        f'<rect width="{width:.0f}" height="{height:.0f}" fill="white"/>',
    ]
    counts = Counter(t["model_tier"] for t in tickets)
    x = left
    for key, label, color in TIER_STYLE:
        if counts[key]:
            text = f"{label.removesuffix(' tier')} ({counts[key]})"
            out.append(f'<circle cx="{x + 5:.1f}" cy="18" r="5.5" fill="{color}"/>')
            out.append(f'<text x="{x + 14:.1f}" y="23.5" font-size="16">{text}</text>')
            x += 26 + 7.6 * len(text)

    by_day = {row["date"]: sum(int(row[k]) for k in row if k != "date") for row in day_rows}
    peak = 100 * math.ceil(max(by_day.values()) / 100)
    day_w = (right - left) * 86400 / (end - start).total_seconds()
    for day, n in sorted(by_day.items()):
        xd = x_at(when(day + "T00:00:00+00:00"))
        h = n / peak * (strip_bottom - strip_top)
        out.append(f'<rect x="{xd + 0.4:.1f}" y="{strip_bottom - h:.1f}" width="{day_w - 0.8:.1f}" height="{h:.1f}" fill="#9a9a95"/>')
    out.append(f'<text x="{left - 6}" y="{strip_bottom - 6}" text-anchor="end" font-size="15" fill="#5f6368">commits/day</text>')
    out.append(f'<text x="{left - 6}" y="{(top + bottom) / 2 + 4:.1f}" text-anchor="end" font-size="15" fill="#5f6368">tickets</text>')

    for milestone in milestones:
        xm = x_at(when(milestone["date"] + "T00:00:00+00:00"))
        out.extend(dashed_vline(xm, strip_top - 4, bottom + 4, 0.7))
        anchor, xt = ("end", xm - 3) if xm + 3 + 7.9 * len(milestone["label"]) > right else ("start", xm + 3)
        out.append(f'<text x="{xt:.1f}" y="{strip_top - 7}" text-anchor="{anchor}" font-size="15" fill="#30343b">{milestone["label"]}</text>')

    for t in tickets:
        color = tiers[t["model_tier"]][1]
        xo, yo = x_at(when(t["created"])), y_at[t["id"]]
        if t["closed"] and x_at(when(t["closed"])) - xo > 1.5:
            out.append(f'<line x1="{xo:.1f}" y1="{yo:.1f}" x2="{x_at(when(t["closed"])):.1f}" y2="{yo:.1f}" stroke="{color}" stroke-width="0.6" stroke-opacity="0.4"/>')
        out.append(f'<circle cx="{xo:.1f}" cy="{yo:.1f}" r="1.9" fill="{color}"/>')

    # Callouts: an ellipse around each burst, labeled with its epoch. Each label
    # takes the first candidate position that stays in the plot and clear of dots,
    # ellipses, date lines and earlier labels.
    dots = [(x_at(when(t["created"])), y_at[t["id"]]) for t in tickets]
    bursts = []
    for burst in ticket_bursts(tickets, spans):
        xs = [x_at(when(t["created"])) for t in burst["members"]]
        ys = [y_at[t["id"]] for t in burst["members"]]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        rx, ry = (max(xs) - min(xs)) / 2 + 7, (max(ys) - min(ys)) / 2 + 5
        bursts.append((cx, cy, rx, ry, labels[burst["epoch"]], sides.get(burst["epoch"])))
    boxes = [(cx - rx, cy - ry, cx + rx, cy + ry) for cx, cy, rx, ry, _, _ in bursts]
    milestone_x = [x_at(when(m["date"] + "T00:00:00+00:00")) for m in milestones]
    # A chosen side may cross a dashed date line (the label has a white backing);
    # the automatic fallback may not.
    clear = lambda box, chosen=False: ((chosen or not any(box[0] - 2 < xm < box[2] + 2 for xm in milestone_x))
                         and left + 2 <= box[0] and box[2] <= right - 2 and strip_bottom + 3 <= box[1] and box[3] <= bottom
                         and not any(box[0] - 3 < x < box[2] + 3 and box[1] - 3 < y < box[3] + 3 for x, y in dots)
                         and not any(box[0] < b[2] and b[0] < box[2] and box[1] < b[3] and b[1] < box[3] for b in boxes))
    for cx, cy, rx, ry, text, side in sorted(bursts, key=lambda b: b[1]):
        text_w, text_h = 7.8 * len(text), 13.5
        # Below first: left of the staircase, or right of it under the wave's closure
        # lines; then beside or above the wave.
        below = [(x, cy + ry + drop) for drop in (14, 28, 42, 56, 70, 84)
                 for x in (cx - rx - 2 - text_w, cx - text_w * 0.75, cx - text_w / 2)]
        below_right = [(cx + rx + shift, cy + ry + drop) for drop in (14, 28, 42)
                       for shift in range(0, 241, 20)]
        level = [(cx - rx - 4 - text_w, cy + 4)] + [(cx + rx + 4 + shift, cy + 4) for shift in range(0, 181, 20)]
        above = [(x, cy - ry - drop) for drop in (6, 20, 34, 48)
                 for x in (cx + rx - text_w, cx - text_w / 2, cx + rx)]
        steps = range(0, 121, 10)
        preferred = {
            "left": [(cx - rx - 4 - text_w - s, cy + 4) for s in steps],
            "right": [(cx + rx + 4 + s, cy + 4) for s in range(0, 181, 10)],
            "above-left": [(cx - rx - text_w - s, cy - ry - d) for d in (4, 14, 24, 34) for s in (0, 10, 20, 30)],
            "above-right": [(cx + rx + s, cy - ry - d) for d in (4, 14, 24, 34) for s in (0, 10, 20, 30)],
            "below": [(cx - text_w / 2 + s, cy + ry + d) for d in (14, 28, 42) for s in (0, -30, 30, -60)],
            # Straight down to the lowest clear row: later tickets sit to the right,
            # so the column under a wave is free for a vertical leader.
            "down": [(x, y) for y in range(int(bottom) - 2, int(cy + ry + 14), -7)
                     for x in (cx - 10, cx - text_w / 3, cx - text_w / 2)],
            "below-left": [(cx - rx - text_w - s, cy + ry + d) for d in (14, 28, 42, 56) for s in (0, 20, 40)],
            "below-right": [(cx + rx + s, cy + ry + d) for d in (14, 28, 42) for s in range(0, 241, 20)],
        }
        if side is not None and side not in preferred:
            raise ValueError(f"unknown callout side {side!r}")
        candidates = (preferred[side] if side else []) + below + below_right + level + above
        chosen = len(preferred[side]) if side else 0
        for index, (lx, ly) in enumerate(candidates):
            box = (lx, ly - text_h, lx + text_w, ly + 2)
            if clear(box, index < chosen):
                break
        else:
            def why(lx, ly):
                box = (lx, ly - text_h, lx + text_w, ly + 2)
                reasons = []
                if any(box[0] - 2 < xm < box[2] + 2 for xm in milestone_x): reasons.append("date line")
                if not (left + 2 <= box[0] and box[2] <= right - 2 and strip_bottom + 3 <= box[1] and box[3] <= bottom):
                    reasons.append("outside plot")
                if any(box[0] - 3 < x < box[2] + 3 and box[1] - 3 < y < box[3] + 3 for x, y in dots): reasons.append("dots")
                if any(box[0] < b[2] and b[0] < box[2] and box[1] < b[3] and b[1] < box[3] for b in boxes): reasons.append("label")
                return f"({lx:.0f},{ly:.0f}) {'/'.join(reasons)}"
            raise ValueError(f"no clear place for the {text!r} callout: " + "; ".join(why(*c) for c in candidates))
        boxes.append(box)
        out.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="none" stroke="#30343b" stroke-width="0.9"/>')
        # Elbow leader. A label to the right is reached along the wave's own row (later
        # tickets sit lower), then vertically; one to the left drops from the ellipse first.
        if box[0] > cx + rx:
            knee = box[0] + 8
            end_y = box[1] if box[1] > cy else box[3] if box[3] < cy else (box[1] + box[3]) / 2
            points = [(cx + rx, cy), (knee, cy), (knee, end_y)] if end_y != (box[1] + box[3]) / 2 \
                else [(cx + rx, cy), (box[0] - 1, cy)]
        elif box[2] < cx - rx:
            mid = (box[1] + box[3]) / 2
            if box[1] - 2 <= cy <= box[3] + 2:      # level with the wave: straight across
                points = [(cx - rx, cy), (box[2] + 1, cy)]
            else:
                points = [(cx, cy + ry if mid > cy else cy - ry), (cx, mid), (box[2] + 1, mid)]
        else:
            px = min(max(cx, box[0] + 4), box[2] - 4)
            points = [(px, cy + ry if box[1] > cy else cy - ry), (px, box[1] if box[1] > cy else box[3])]
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        out.append(f'<polyline points="{path}" fill="none" stroke="#30343b" stroke-width="0.7"/>')
        out.append(f'<rect x="{box[0] - 1:.1f}" y="{box[1]:.1f}" width="{text_w + 2:.1f}" height="{text_h + 3:.1f}" fill="white" fill-opacity="0.85"/>')
        out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="15">{text}</text>')

    out.append(f'<line x1="{left}" y1="{bottom + 4}" x2="{right}" y2="{bottom + 4}" stroke="#30343b" stroke-width="0.8"/>')
    tick = start
    while tick <= end:
        xt = x_at(tick)
        out.append(f'<line x1="{xt:.1f}" y1="{bottom + 4}" x2="{xt:.1f}" y2="{bottom + 7}" stroke="#30343b" stroke-width="0.8"/>')
        out.append(f'<text x="{xt:.1f}" y="{bottom + 23}" text-anchor="middle" font-size="15" fill="#5f6368">{tick.strftime("%b")} {tick.day}</text>')
        tick += timedelta(days=14)
    out.append("</svg>")
    return "\n".join(out)


PITFALL_CLASSES = Path("data/pitfall-classes.json")
DEVELOPMENT_INCIDENTS = Path("data/development-incidents.json")


def development_constants_tex(incidents_path: Path = DEVELOPMENT_INCIDENTS) -> str:
    incidents = json.loads(incidents_path.read_text(encoding="utf-8"))["incidents"]
    lines = [
        "% Generated by scripts/generate_paper_assets.py from "
        f"{incidents_path.as_posix()}; do not edit.",
    ]
    seen = set()
    for item in incidents:
        command, value = item["command"], item["value"]
        if not re.fullmatch(r"[A-Za-z]+", command) or command in seen:
            raise ValueError(f"bad or duplicate incident command {command!r}")
        if not item.get("source"):
            raise ValueError(f"incident {command} has no source")
        if not re.fullmatch(r"[+-]?[0-9]+(?:\{,\}[0-9]{3})*(?:\.[0-9]+)?", value):
            raise ValueError(f"incident {command} value {value!r} is not a number")
        seen.add(command)
        lines.append(rf"\newcommand{{\{command}}}{{{value}}}")
    return "\n".join(lines) + "\n"


def pitfall_classes_table(runs: Path, classes_path: Path = PITFALL_CLASSES) -> str:
    record = json.loads((runs / DEVELOPMENT_RECORD / "record.json").read_text(encoding="utf-8"))
    classes = json.loads(classes_path.read_text(encoding="utf-8"))["classes"]
    assigned = [number for item in classes for number in item["pitfalls"]]
    if sorted(assigned) != record["pitfalls"]:
        raise ValueError("pitfall classes must assign every recorded pitfall exactly once")
    for item in classes:
        if item["example_pitfall"] not in item["pitfalls"]:
            raise ValueError(f"class {item['label']!r} cites an example outside the class")
    rows = [
        f"    {item['label']} & {len(item['pitfalls'])} & {item['example']} ({item['example_pitfall']}) \\\\"
        for item in classes
    ]
    return "\n".join([
        "% Generated by scripts/generate_paper_assets.py; do not edit.",
        r"\begin{table}[t]",
        r"  \centering",
        r"  \small",
        rf"  \caption{{The {len(assigned)} numbered pitfalls of the development record, by the kind of",
        r"  failure each guards against. Each was added after the failure it describes had happened",
        r"  at least once; the example's pitfall number is in parentheses.}",
        r"  \label{tab:pitfall-classes}",
        r"  \begin{tabular}{@{}p{0.27\linewidth}rp{0.6\linewidth}@{}}",
        r"    \toprule",
        r"    Failure class & $n$ & Example \\",
        r"    \midrule",
        *rows,
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
        "",
    ])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def generate(runs: Path, output: Path) -> None:
    timings = [
        read_timing(machine, mode, runs / relative)
        for (machine, mode), relative in PUBLIC_REPORTS.items()
    ]
    results = current_results(runs)
    context_path = Path("data/experimental-context.json")
    context = json.loads(context_path.read_text(encoding="utf-8"))
    atomic_write(output / "constants.tex", constants_tex(timings, results, context))
    atomic_write(output / "tables" / "public-performance.tex", public_performance_table(timings))
    atomic_write(output / "tables" / "main-results.tex", main_results_table(results))
    atomic_write(output / "tables" / "systems.tex", systems_table(runs, context))
    atomic_write(output / "tables" / "shipped-kernel-config.tex", shipped_kernel_table())
    svg_to_pdf(
        field_schematic_svg(),
        output / "figures" / "field-schematic.svg",
        output / "figures" / "field-schematic.pdf",
    )
    svg_to_pdf(
        saturation_svg(results),
        output / "figures" / "blackwell-saturation.svg",
        output / "figures" / "blackwell-saturation.pdf",
    )
    atomic_write(output / "development-constants.tex", development_constants_tex())
    atomic_write(output / "tables" / "pitfall-classes.tex", pitfall_classes_table(runs))
    svg_to_pdf(
        ticket_timeline_svg(runs),
        output / "figures" / "ticket-timeline.svg",
        output / "figures" / "ticket-timeline.pdf",
    )
    svg_to_pdf(
        ticket_strip_svg(runs),
        output / "figures" / "ticket-strip.svg",
        output / "figures" / "ticket-strip.pdf",
    )

    sources = sorted(
        {item.source for item in timings}
        | {
            context_path,
            TICKET_MILESTONES,
            PITFALL_CLASSES,
            DEVELOPMENT_INCIDENTS,
            runs / FIELD_REPORT,
            runs / VOLTA_HEADLINE,
            runs / VOLTA_COMBINATION,
            runs / VOLTA_STEP_BUDGET,
            runs / DUDEZ_PARITY,
            runs / ARCHIVE_INDEX,
            runs / DEVELOPMENT_RECORD / "record.json",
            runs / DEVELOPMENT_RECORD / "tickets.csv",
            runs / DEVELOPMENT_RECORD / "commit-days.csv",
            runs / D5_REPORT,
            runs / LITPCBA_CONFORMER_COUNTS,
            *(runs / path for path in SATURATION_REPORTS.values()),
        }
    )
    manifest = {
        "generator": "scripts/generate_paper_assets.py",
        "sources": [
            {"path": path.as_posix(), "sha256": sha256(path)} for path in sources
        ],
        "outputs": [
            "constants.tex",
            "development-constants.tex",
            "tables/pitfall-classes.tex",
            "tables/main-results.tex",
            "tables/systems.tex",
            "tables/public-performance.tex",
            "tables/shipped-kernel-config.tex",
            "figures/field-schematic.pdf",
            "figures/field-schematic.svg",
            "figures/blackwell-saturation.pdf",
            "figures/blackwell-saturation.svg",
            "figures/ticket-timeline.pdf",
            "figures/ticket-timeline.svg",
            "figures/ticket-strip.pdf",
            "figures/ticket-strip.svg",
        ],
        "statistic": "median of measured repeats",
    }
    atomic_write(output / "manifest.json", json.dumps(manifest, indent=2) + "\n")
    atomic_write(output / ".stamp", "generated\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, default=Path("runs"))
    parser.add_argument("--output", type=Path, default=Path("generated"))
    args = parser.parse_args()
    generate(args.runs, args.output)


if __name__ == "__main__":
    main()
