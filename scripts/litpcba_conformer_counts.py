#!/usr/bin/env python3
"""Record LIT-PCBA's per-molecule conformer counts from the format-3 corpus.

    python scripts/litpcba_conformer_counts.py --corpus <LIT-PCBA corpus dir> \
        --source-index ../results/T65/litpcba_index_summary.json \
        --output runs/litpcba-corpus-3bb39f69/conformer-counts.json

The corpus run tables give each molecule's conformer count; the histogram of
those counts, the number of source compounds that produced no conformer, and
the size of the SDF the corpus was built from (build.json's input byte counts)
go into one small record the paper generator reads. Nothing per-molecule is
written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def conformer_histogram(corpus_dir: Path) -> Counter:
    from roshambo3.format.r3g.reader import open_corpus

    per_molecule: Counter = Counter()
    corpus = open_corpus(str(corpus_dir))
    for group in corpus.groups():
        with group:
            for mol_id, n_conf in zip(group.mol_id.tolist(), group.molecule_n_conf.tolist()):
                per_molecule[int(mol_id)] += int(n_conf)
    return Counter(per_molecule.values())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--source-index", type=Path, required=True,
                        help="T65's litpcba_index_summary.json (unique source compounds)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    descriptor = (args.corpus / "corpus.json").read_bytes()
    corpus_json = json.loads(descriptor)
    build = json.loads((args.corpus / "build.json").read_text(encoding="utf-8"))
    source = json.loads(args.source_index.read_text(encoding="utf-8"))
    histogram = conformer_histogram(args.corpus)

    n_mol = sum(histogram.values())
    n_conf = sum(count * molecules for count, molecules in histogram.items())
    if (n_mol, n_conf) != (int(corpus_json["n_mol"]), int(corpus_json["n_conf"])):
        raise ValueError("run tables disagree with corpus.json's molecule or conformer count")
    inputs = build["identity"]["inputs"]
    record = {
        "generator": "scripts/litpcba_conformer_counts.py",
        "corpus": {
            "name": build["name"],
            "descriptor_sha256": hashlib.sha256(descriptor).hexdigest(),
            "ids_sha256": corpus_json["ids_sha256"],
            "molecules": n_mol,
            "conformers": n_conf,
        },
        "source_compounds": int(source["n_unique_compounds"]),
        "source_compounds_from": "results/T65/litpcba_index_summary.json n_unique_compounds",
        "compounds_without_conformers": int(source["n_unique_compounds"]) - n_mol,
        "molecules_by_conformer_count": {str(k): histogram[k] for k in sorted(histogram)},
        "source_sdf": {"files": len(inputs), "bytes": sum(int(item["bytes"]) for item in inputs),
                       "from": "build.json identity.inputs"},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"{n_mol} molecules, {n_conf} conformers, "
          f"{record['compounds_without_conformers']} source compounds without conformers")


if __name__ == "__main__":
    main()
