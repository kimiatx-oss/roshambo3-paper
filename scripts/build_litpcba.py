#!/usr/bin/env python3
"""Regenerate the LIT-PCBA screening corpus and the PANEL-8 queries from source.

    python scripts/build_litpcba.py all --out <dir> --tool-python <venv>/bin/python

Steps, each resumable and runnable alone (``fetch``, ``index``, ``queries``,
``panel``, ``conformers``, ``corpus``):

1. fetch       download full_data.tgz from the LIT-PCBA site and check it
               against the sha256 recorded when the paper's corpus was built.
2. index       one row per unique compound (keyed on PubChem CID) across the
               15 targets' actives/inactives, and the (target, label, CID) join.
3. queries     each target's PDB template ligands as 3D SDF, at their crystal
               coordinates; RDKit's mol2 reader first, Open Babel's mol2 -> PDB
               round trip for the files RDKit cannot read. Also writes the mask
               of templates that are actives of their own target.
4. panel       PANEL-8 (and SWEEP-8) by make_query_panels.py's fixed rule, and
               a comparison with the committed data/queries/PANEL-8.sdf.
5. conformers  50 ETKDGv3 conformers per compound on the GPU with nvMolKit,
               seed 65017, each minimized with MMFF94s (200 iterations).
6. corpus      ``roshambo3 prepare --color`` over the conformers: a format-3
               corpus with the paper corpus's (default) build parameters.

Steps 2-5 run in a generation environment (scripts/litpcba-requirements.txt:
nvMolKit 0.6.0, which pins RDKit 2026.03.5, plus Open Babel). Step 6 runs in
the tool's own environment, named by --tool-python.

Regeneration is not expected to be byte-identical to the paper's corpus.
nvMolKit embeds from random coordinates on the GPU, and whether that is
bitwise reproducible across GPU models and drivers has not been tested. The
compound set, CID identities and per-molecule conformer budget are
deterministic. The screening workload is fixed by them, since every pair runs
the same optimizer steps; only field-caching behavior can vary.

``--limit N`` keeps the first N compounds, for a smoke test.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

SOURCE_URL = "https://drugdesign.unistra.fr/LIT-PCBA/Files/full_data.tgz"
# Recorded at the paper corpus's acquisition, 2026-08-21.
SOURCE_SHA256 = "93467a5b2a51d303ae7a5e84aa66aae7f371e0502adb006d24aa68905b2b9a7d"
SCRIPTS = Path(__file__).resolve().parent
COMMITTED_PANEL = SCRIPTS.parent / "data" / "queries" / "PANEL-8.sdf"
PROTOCOL = {"embedding": "ETKDGv3", "use_random_coords": True, "minimization": "MMFF94s",
            "n_confs_per_compound": 50, "max_iters": 200, "seed": 65017,
            "engine": "nvmolkit"}
CORPUS_NAME = "LIT-PCBA"  # the format-3 build: shape and color in one corpus


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


# 1. fetch --------------------------------------------------------------------

def fetch(out: Path, args) -> None:
    raw = out / "raw" / "full_data.tgz"
    raw.parent.mkdir(parents=True, exist_ok=True)
    if not raw.exists():
        print(f"downloading {SOURCE_URL}")
        part = raw.with_suffix(".part")
        with urllib.request.urlopen(SOURCE_URL, timeout=600) as response, part.open("wb") as handle:
            shutil.copyfileobj(response, handle)
        part.replace(raw)
    digest = sha256(raw)
    record = {"url": SOURCE_URL, "bytes": raw.stat().st_size, "sha256": digest,
              "matches_paper_source": digest == SOURCE_SHA256,
              "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    write_json(out / "raw" / "retrieval_record.json", record)
    if digest != SOURCE_SHA256:
        message = (f"full_data.tgz sha256 {digest} differs from the paper's source "
                   f"{SOURCE_SHA256}: the upstream archive has changed")
        if not args.allow_source_change:
            raise SystemExit(message + " (pass --allow-source-change to continue)")
        print("WARNING: " + message)
    print(f"full_data.tgz: {record['bytes']} bytes, sha256 {digest[:16]}... "
          f"{'matches' if record['matches_paper_source'] else 'DIFFERS FROM'} the paper's source")


# 2. index --------------------------------------------------------------------

def _tar_members(tgz: Path):
    """Yield ("smi", target, label, cid, smiles) for every actives/inactives line
    and ("mol2", target, pdb_id, bytes, None) for every template ligand."""
    with tarfile.open(tgz, "r:gz") as archive:
        for member in archive.getmembers():
            parts = member.name.split("/")
            if not member.isfile() or len(parts) != 2:
                continue
            target, name = parts
            if name in ("actives.smi", "inactives.smi"):
                label = "active" if name == "actives.smi" else "inactive"
                text = archive.extractfile(member).read().decode("utf-8", "replace")
                for line in text.splitlines():
                    tokens = line.split()
                    if not tokens:
                        continue
                    if len(tokens) != 2:
                        raise ValueError(f"{member.name}: expected 'SMILES CID', got {tokens!r}")
                    smiles, cid = tokens
                    yield ("smi", target, label, cid, smiles)
            elif name.endswith("_ligand.mol2"):
                yield ("mol2", target, name[:-len("_ligand.mol2")],
                       archive.extractfile(member).read(), None)


def _canonical(item):
    cid, smiles = item
    from rdkit import Chem
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return cid, smiles, None, None
    return cid, smiles, Chem.MolToSmiles(mol), len(Chem.GetMolFrags(mol))


def index(out: Path, args) -> None:
    done = out / "index" / "summary.json"
    if done.exists():
        print(f"index already built: {done}")
        return
    smiles_by_cid: dict[str, str] = {}
    labels: list[tuple[str, str, str]] = []
    conflicts = []
    for kind, target, label, cid, smiles in _tar_members(out / "raw" / "full_data.tgz"):
        if kind != "smi":
            continue
        prior = smiles_by_cid.setdefault(cid, smiles)
        if prior != smiles:
            conflicts.append((cid, prior, smiles))
        labels.append((target, label, cid))
    if conflicts:
        raise ValueError(f"{len(conflicts)} CIDs map to more than one SMILES; first: {conflicts[0]}")
    with multiprocessing.Pool(args.workers or os.cpu_count() or 1) as pool:
        rows = pool.map(_canonical, list(smiles_by_cid.items()), chunksize=2000)
    directory = out / "index"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "compounds.jsonl").open("w") as handle:
        for cid, smiles, canonical, fragments in rows:
            handle.write(json.dumps({"cid": cid, "smiles": smiles, "canonical_smiles": canonical,
                                     "n_fragments": fragments, "ext_id": f"CID{cid}"}) + "\n")
    with (directory / "labels.jsonl").open("w") as handle:
        for target, label, cid in labels:
            handle.write(json.dumps({"target": target, "label": label, "cid": cid,
                                     "ext_id": f"CID{cid}"}) + "\n")
    summary = {"n_unique_compounds": len(rows), "n_label_rows": len(labels),
               "n_unparsed_compounds": sum(1 for r in rows if r[2] is None),
               "n_multi_fragment_compounds": sum(1 for r in rows if r[3] and r[3] > 1)}
    write_json(done, summary)
    print(json.dumps(summary))


# 3. queries ------------------------------------------------------------------

def _mol2_via_obabel(obabel: str, data: bytes):
    from rdkit import Chem
    with tempfile.TemporaryDirectory() as tmp:
        mol2, pdb = Path(tmp, "ligand.mol2"), Path(tmp, "ligand.pdb")
        mol2.write_bytes(data)
        result = subprocess.run([obabel, str(mol2), "-O", str(pdb)], capture_output=True, text=True)
        if result.returncode != 0 or not pdb.exists():
            return None, f"obabel failed: {result.stderr.strip()[:200]}"
        mol = Chem.MolFromPDBFile(str(pdb), sanitize=True, removeHs=False)
        return (mol, None) if mol is not None else (None, "RDKit could not read obabel's PDB")


def queries(out: Path, args) -> None:
    from rdkit import Chem
    directory = out / "queries"
    done = directory / "summary.json"
    if done.exists():
        print(f"queries already extracted: {done}")
        return
    obabel = args.obabel or shutil.which("obabel")
    if obabel is None:
        raise SystemExit("Open Babel's obabel is required (pip install openbabel-wheel, or --obabel)")
    canonical = {}
    with (out / "index" / "compounds.jsonl").open() as handle:
        for line in handle:
            row = json.loads(line)
            if row["canonical_smiles"] is not None:
                canonical[row["cid"]] = row["canonical_smiles"]
    by_target = defaultdict(dict)
    with (out / "index" / "labels.jsonl").open() as handle:
        for line in handle:
            row = json.loads(line)
            if row["cid"] in canonical:
                by_target[row["target"]][canonical[row["cid"]]] = (row["label"], row["cid"])
    templates = defaultdict(dict)
    for kind, target, pdb_id, data, _ in _tar_members(out / "raw" / "full_data.tgz"):
        if kind == "mol2":
            templates[target][pdb_id] = data
    directory.mkdir(parents=True, exist_ok=True)
    counts = {"rdkit_direct": 0, "obabel_roundtrip": 0, "unparseable": 0}
    unparseable, mask = [], []
    for target, ligands in sorted(templates.items()):
        writer = None
        for pdb_id, data in sorted(ligands.items()):
            mol = Chem.MolFromMol2Block(data.decode("latin-1"), sanitize=True, removeHs=False)
            if mol is not None:
                counts["rdkit_direct"] += 1
            else:
                mol, reason = _mol2_via_obabel(obabel, data)
                if mol is None:
                    counts["unparseable"] += 1
                    unparseable.append({"target": target, "pdb_id": pdb_id, "reason": reason})
                    continue
                counts["obabel_roundtrip"] += 1
            name = f"{target}_{pdb_id}_query"
            mol.SetProp("_Name", name)
            if writer is None:
                writer = Chem.SDWriter(str(directory / f"{target}.sdf"))
            writer.write(mol)
            hit = by_target[target].get(Chem.MolToSmiles(Chem.RemoveHs(mol)))
            if hit is not None:
                mask.append({"target": target, "pdb_id": pdb_id, "ext_id": name,
                             "matched_label": hit[0], "matched_cid": hit[1]})
        if writer is not None:
            writer.close()
    with (directory / "query_exclusion_mask.jsonl").open("w") as handle:
        for row in mask:
            handle.write(json.dumps(row) + "\n")
    summary = {**counts, "templates": sum(len(v) for v in templates.values()),
               "unparseable_rows": unparseable,
               "active_self_matches": sum(1 for r in mask if r["matched_label"] == "active")}
    write_json(done, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "unparseable_rows"}))


# 4. panel --------------------------------------------------------------------

def panel(out: Path, args) -> None:
    directory = out / "panels"
    subprocess.run([sys.executable, str(SCRIPTS / "make_query_panels.py"),
                    "--queries", str(out / "queries"), "--out", str(directory),
                    "--mask", str(out / "queries" / "query_exclusion_mask.jsonl")],
                   check=True, stdout=subprocess.DEVNULL)
    built = directory / "PANEL-8.sdf"
    same = COMMITTED_PANEL.is_file() and built.read_bytes() == COMMITTED_PANEL.read_bytes()
    record = {"panel_sha256": sha256(built), "committed_sha256":
              sha256(COMMITTED_PANEL) if COMMITTED_PANEL.is_file() else None,
              "identical_to_committed": same}
    write_json(directory / "comparison.json", record)
    print(f"PANEL-8 {record['panel_sha256'][:16]}... "
          f"{'identical to' if same else 'DIFFERS FROM'} the committed data/queries/PANEL-8.sdf")


# 5. conformers ---------------------------------------------------------------

def _conformer_shard(index_: int, rows: list[dict], directory: Path, args) -> dict | None:
    from rdkit import Chem
    from rdkit.Chem import AllChem, rdForceFieldHelpers
    from nvmolkit.embedMolecules import EmbedMolecules
    from nvmolkit.mmffOptimization import MMFFOptimizeMoleculesConfs
    from nvmolkit.types import HardwareOptions

    stem = directory / f"shard_{index_:05d}"
    if stem.with_suffix(".done").exists():
        return None
    mols, records, position = [], [], []
    for row in rows:
        record = {"ext_id": row["ext_id"], "cid": row["cid"]}
        mol = Chem.MolFromSmiles(row["smiles"]) if row["smiles"] else None
        if mol is None:
            record.update(status="failed", stage="parse")
            position.append(None)
        else:
            position.append(len(mols))
            mols.append(Chem.AddHs(mol))
        records.append(record)

    params = AllChem.ETKDGv3()
    params.randomSeed = PROTOCOL["seed"]
    params.useRandomCoords = True  # nvMolKit's ETKDG supports nothing else
    hardware = HardwareOptions(gpuIds=args.gpu_ids, batchSize=-1, batchesPerGpu=-1)
    failed: set[int] = set()

    def failed_from(exc: ValueError) -> set[int]:
        detail = exc.args[1] if len(exc.args) > 1 else {}
        return set(detail.get("none", [])) | set(detail.get("no_params", []))

    try:
        EmbedMolecules(mols, params, confsPerMolecule=PROTOCOL["n_confs_per_compound"],
                       hardwareOptions=hardware)
    except ValueError as exc:
        failed |= failed_from(exc)
    properties = [None] * len(mols)
    for i, mol in enumerate(mols):
        if i not in failed:
            properties[i] = rdForceFieldHelpers.MMFFGetMoleculeProperties(mol, mmffVariant="MMFF94s")
            if properties[i] is None:
                failed.add(i)
    energies = [None] * len(mols)
    if len(mols) > len(failed):
        try:
            energies = list(MMFFOptimizeMoleculesConfs(mols, maxIters=PROTOCOL["max_iters"],
                                                       properties=properties,
                                                       hardwareOptions=hardware))
        except ValueError as exc:
            failed |= failed_from(exc)

    n_ok = n_conformers = 0
    with gzip.open(stem.with_suffix(".sdf.gz"), "wt", compresslevel=1) as sdf, \
            stem.with_suffix(".status.jsonl").open("w") as status:
        writer = Chem.SDWriter(sdf)  # one writer per shard: close() closes the stream
        for record, i in zip(records, position):
            if i is not None and (i in failed or energies[i] is None):
                record.update(status="failed", stage="embed_or_minimize")
            elif i is not None:
                mol = mols[i]
                mol.SetProp("_Name", record["ext_id"])
                record.update(status="ok", n_confs=mol.GetNumConformers())
                for conformer in mol.GetConformers():
                    writer.write(mol, confId=conformer.GetId())
                n_ok += 1
                n_conformers += mol.GetNumConformers()
            status.write(json.dumps(record) + "\n")
        writer.close()
    summary = {"n_compounds": len(rows), "n_ok": n_ok, "n_conformers": n_conformers}
    write_json(stem.with_suffix(".done"), summary)
    return summary


def conformers(out: Path, args) -> None:
    import nvmolkit
    import rdkit
    directory = out / "conformers"
    directory.mkdir(parents=True, exist_ok=True)
    rows = []
    with (out / "index" / "compounds.jsonl").open() as handle:
        for line in handle:
            row = json.loads(line)
            rows.append({"ext_id": row["ext_id"], "cid": row["cid"], "smiles": row["canonical_smiles"]})
    if args.limit:
        rows = rows[:args.limit]
    write_json(directory / "protocol.json",
               {**PROTOCOL, "rdkit_version": rdkit.__version__,
                "nvmolkit_version": getattr(nvmolkit, "__version__", "unknown"),
                "n_compounds": len(rows), "limit": args.limit or None,
                "shard_size": args.shard_size})
    start = time.perf_counter()
    shards = [rows[i:i + args.shard_size] for i in range(0, len(rows), args.shard_size)]
    for index_, shard in enumerate(shards):
        t0 = time.perf_counter()
        summary = _conformer_shard(index_, shard, directory, args)
        state = "already done" if summary is None else (
            f"{summary['n_ok']}/{summary['n_compounds']} ok, {summary['n_conformers']} conformers, "
            f"{time.perf_counter() - t0:.0f} s")
        print(f"shard {index_ + 1}/{len(shards)}: {state}", flush=True)
    print(f"conformers done in {time.perf_counter() - start:.0f} s")


# 6. corpus -------------------------------------------------------------------

def corpus(out: Path, args) -> None:
    if not args.tool_python:
        raise SystemExit("--tool-python must name the python of an environment with roshambo3 installed")
    target = out / "corpus" / CORPUS_NAME
    if (target / "corpus.json").exists():
        print(f"corpus already built: {target}")
        return
    shards = sorted((out / "conformers").glob("shard_*.sdf.gz"))
    if not shards:
        raise SystemExit("no conformer shards; run the conformers step first")
    # prepare reads plain SDF; decompress beside the output (79 GB for the full set).
    sdf_dir = out / "sdf"
    sdf_dir.mkdir(parents=True, exist_ok=True)
    plain = []
    for shard in shards:
        sdf = sdf_dir / shard.name[:-len(".gz")]
        if not sdf.exists():
            part = sdf.with_suffix(".part")
            with gzip.open(shard, "rb") as src, part.open("wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 22)
            part.replace(sdf)
        plain.append(str(sdf))
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([args.tool_python, "-m", "roshambo3.cli", "prepare", *plain, "-o", str(target),
                    "--name", CORPUS_NAME, "--color",
                    "--workers", str(args.prepare_workers)], check=True)
    if not args.keep_sdf:
        shutil.rmtree(sdf_dir)
    descriptor = json.loads((target / "corpus.json").read_text())
    print(f"corpus {target}: {descriptor['n_mol']} molecules, {descriptor['n_conf']} conformers, "
          f"ids_sha256 {descriptor['ids_sha256'][:16]}...")


STEPS = {"fetch": fetch, "index": index, "queries": queries, "panel": panel,
         "conformers": conformers, "corpus": corpus}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=[*STEPS, "all"])
    parser.add_argument("--out", type=Path, required=True, help="working and output directory")
    parser.add_argument("--limit", type=int, default=0, help="first N compounds only (smoke test)")
    parser.add_argument("--workers", type=int, default=0, help="index workers; 0 = all CPUs")
    parser.add_argument("--gpu-ids", default="0", help="comma-separated GPU ids for nvMolKit")
    parser.add_argument("--shard-size", type=int, default=20000)
    parser.add_argument("--obabel", help="path to obabel (default: on PATH)")
    parser.add_argument("--tool-python", help="python with roshambo3 installed (corpus step)")
    parser.add_argument("--prepare-workers", type=int, default=16)
    parser.add_argument("--keep-sdf", action="store_true", help="keep the decompressed SDF")
    parser.add_argument("--allow-source-change", action="store_true")
    args = parser.parse_args()
    args.gpu_ids = [int(x) for x in args.gpu_ids.split(",") if x]
    args.out.mkdir(parents=True, exist_ok=True)
    for name in (STEPS if args.step == "all" else [args.step]):
        print(f"== {name}", flush=True)
        STEPS[name](args.out, args)


if __name__ == "__main__":
    main()
