#!/usr/bin/env python3
"""T68: define the query panels, once, by rule -- and hold to them.

    python scripts/make_query_panels.py --queries <dir> --out <dir>

Copied from the development repository (tickets/T68) as run; the committed
output is data/queries/PANEL-8.sdf.

Two panels, and the reason there are two is `decisions/D012`, whose history is
three revisions of quoting a speedup without the query-size range it was
measured over.

**PANEL-8** -- the headline panel, eight query ligands, because the comparison
paper's Table 2 screens "8 query ligands" against the full LIT-PCBA set. The
selection rule is fixed *before* any timing is taken and depends on nothing
measured: the 15 LIT-PCBA targets sorted by name, the first eight taken, and
within each target the PDB template ligand whose record name sorts first. It is
arbitrary; what matters is that it is arbitrary in a way no result could have
influenced.

**SWEEP-8** -- eight ligands drawn across the *whole* heavy-atom range of all
120 LIT-PCBA template ligands at evenly spaced order statistics, so the ratio
can be quoted with a range rather than a panel mean. T28's resolution of D012
found the grid's advantage running from ~1.0x at 10 query atoms to 5-8x at 50,
and PANEL-8's own span (see the manifest) does not cover that on its own.

Heavy atoms, not atoms: hydrogens are removed on both sides before scoring, so
the size that drives the kernel's cost is the heavy-atom count.

The D002 leakage mask is *recorded*, not applied: it changes which hits are
enrichment-eligible (T67's problem) and changes no wall clock, so a speed panel
that excluded a ligand for being an active would be excluding it for a reason
that cannot affect the measurement.
"""
from __future__ import annotations

import argparse
import glob
import json
import os


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", required=True, help="dir of <TARGET>.sdf")
    ap.add_argument("--mask", default="results/T65/litpcba_query_exclusion_mask.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=8)
    a = ap.parse_args()

    from rdkit import Chem

    masked = set()
    if os.path.exists(a.mask):
        for line in open(a.mask):
            masked.add(json.loads(line)["ext_id"])

    # (target, name, heavy_atoms, mol). removeHs=True at read time so the
    # heavy-atom count is the count and not a property of the file.
    rows = []
    for path in sorted(glob.glob(os.path.join(a.queries, "*.sdf"))):
        target = os.path.basename(path)[:-4]
        for mol in Chem.SDMolSupplier(path, removeHs=True, sanitize=True):
            if mol is None:
                continue
            name = mol.GetProp("_Name")
            heavy = sum(1 for at in mol.GetAtoms() if at.GetAtomicNum() > 1)
            rows.append({"target": target, "name": name, "heavy_atoms": heavy,
                         "mol": mol})

    targets = sorted({r["target"] for r in rows})

    # PANEL-8: first n targets by name, first ligand by name inside each.
    panel = []
    for t in targets[:a.n]:
        cand = sorted([r for r in rows if r["target"] == t],
                      key=lambda r: r["name"])
        panel.append(cand[0])

    # SWEEP-8: evenly spaced order statistics of heavy-atom count over ALL
    # ligands. Ties broken by name so the choice is a function of the corpus.
    by_size = sorted(rows, key=lambda r: (r["heavy_atoms"], r["name"]))
    idx = [round(i * (len(by_size) - 1) / (a.n - 1)) for i in range(a.n)]
    sweep = [by_size[i] for i in idx]

    os.makedirs(a.out, exist_ok=True)
    manifest = {"record": "query_panels", "ticket": "T68",
                "source_dir": a.queries,
                "n_template_ligands": len(rows),
                "n_targets": len(targets),
                "heavy_atom_range_all": [by_size[0]["heavy_atoms"],
                                         by_size[-1]["heavy_atoms"]],
                "d002_mask_ext_ids": sorted(masked),
                "panels": {}}

    for label, sel, rule in (
        ("PANEL-8", panel,
         "the 15 targets sorted by name, first 8 taken; within each target the "
         "template ligand whose record name sorts first"),
        ("SWEEP-8", sweep,
         "all template ligands sorted by heavy-atom count (ties by name), 8 "
         "taken at evenly spaced order statistics over the whole range"),
    ):
        out_sdf = os.path.join(a.out, f"{label}.sdf")
        w = Chem.SDWriter(out_sdf)
        for r in sel:
            w.write(r["mol"])
        w.close()
        heavy = [r["heavy_atoms"] for r in sel]
        manifest["panels"][label] = {
            "sdf": out_sdf, "rule": rule, "n_queries": len(sel),
            "queries": [{"name": r["name"], "target": r["target"],
                         "heavy_atoms": r["heavy_atoms"],
                         "in_d002_mask": r["name"] in masked} for r in sel],
            "heavy_atoms": {"min": min(heavy), "max": max(heavy),
                            "mean": sum(heavy) / len(heavy)},
        }

    with open(os.path.join(a.out, "panels.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
