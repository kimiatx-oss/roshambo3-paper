#!/usr/bin/env python3
"""Small production-path target for analytic/field Nsight Compute profiles."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("field", "analytic"), required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--queries", type=int, default=4)
    parser.add_argument("--groups", default="6")
    parser.add_argument("--steps", type=int, default=25)
    parser.add_argument("--device", type=int, default=0)
    args = parser.parse_args()

    from rdkit import Chem
    from roshambo3 import api
    from roshambo3.backend import PoseSearch
    from roshambo3.engine import ScreenConfig
    from roshambo3.format import Corpus

    with tempfile.TemporaryDirectory(prefix="roshambo3-roofline-") as temporary:
        query_path = Path(temporary) / "queries.sdf"
        writer = Chem.SDWriter(str(query_path))
        count = 0
        for molecule in Chem.SDMolSupplier(str(args.panel), removeHs=False):
            if molecule is not None and count < args.queries:
                writer.write(molecule)
                count += 1
        writer.close()
        if count != args.queries:
            raise ValueError(f"requested {args.queries} queries but found {count}")
        groups = None if args.groups == "all" else [int(value) for value in args.groups.split(",")]
        config = ScreenConfig(
            pose_search=PoseSearch.FIELD if args.arm == "field" else PoseSearch.ANALYTIC,
            color=False, steps=args.steps, lr_t=0.4, lr_q=0.1, start_mode=1)
        result = api.screen(
            str(query_path), Corpus(args.corpus), k=1000, config=config,
            device_id=args.device, groups=groups, workers=2, prefetch_depth=1,
            level="conformer", stage_timing=False)
        print(f"arm={args.arm} conformers={result.stats.n_conformers} "
              f"blocks={result.stats.n_blocks} pair_rows={result.stats.n_rows}")


if __name__ == "__main__":
    main()
