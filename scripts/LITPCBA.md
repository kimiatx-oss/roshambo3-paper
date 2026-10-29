# Rebuilding the LIT-PCBA corpus and PANEL-8

`build_litpcba.py` regenerates, from the public LIT-PCBA release, the two
inputs every LIT-PCBA screen in the paper uses:
- the 407,983-compound format-3 corpus, with shape and color in one build;
- the eight PANEL-8 query ligands.

```sh
python3 -m venv genvenv && genvenv/bin/pip install -r scripts/litpcba-requirements.txt
PATH=$PWD/genvenv/bin:$PATH genvenv/bin/python scripts/build_litpcba.py all \
    --out <work dir> --tool-python <roshambo3 venv>/bin/python --gpu-ids 0
```

The result is `<work dir>/corpus/LIT-PCBA` and
`<work dir>/panels/PANEL-8.sdf`. Each step resumes where it stopped and can run
alone: `fetch`, `index`, `queries`, `panel`, `conformers`, `corpus`.

| Step | What it does | Cost |
|---|---|---|
| fetch | Downloads `full_data.tgz` (54 MB) from the LIT-PCBA site and refuses it unless its sha256 matches the paper's source. | seconds |
| index | Deduplicates the 15 targets' actives and inactives by PubChem CID: 407,983 compounds and 2,808,770 (target, label, CID) rows. | about 1 min on 24 cores |
| queries | Writes each target's PDB template ligands at crystal coordinates. RDKit reads 105 of the 129 templates directly, Open Babel's mol2-to-PDB round trip recovers 15, and 9 stay unreadable. Two templates are actives of their own target and are recorded in a mask. | seconds |
| panel | Applies `make_query_panels.py`'s fixed rule and checks the result against the committed `data/queries/PANEL-8.sdf`. | seconds |
| conformers | Runs nvMolKit 0.6.0 on the GPU: 50 ETKDGv3 conformers per compound, seed 65017, MMFF94s minimization (200 iterations). | about 5.6 h on two TITAN V GPUs for the paper's corpus |
| corpus | Runs `roshambo3 prepare --color` in the tool's own environment, producing a format-3 corpus (`corpus.json`, `molecules.parquet`, `groups/`). It first decompresses the conformer shards (79 GB of SDF), which it deletes afterward unless given `--keep-sdf`. | about 50 min on 16 workers |

**What reproduces exactly:**
- the compound set and CIDs, which fix the corpus's molecule identities;
- the query panel. The panel step reports whether the rebuilt file is
  byte-identical to the committed one.

**What may differ:** the conformer coordinates. nvMolKit embeds from random
coordinates on the GPU, and nobody has tested whether that is bitwise
reproducible across GPU models or drivers. So a rebuilt corpus is the same
screening workload, the same molecules and conformer budget under the same
fixed optimizer steps, but not the same bytes. Throughput can differ only
through field-caching behavior.

**Smoke test:** `--limit 300` keeps the first 300 compounds. On a shared RTX
PRO 6000 that produced 15,000 conformers in under a minute. The corpus step was
checked separately on format 3, on 2,000 of the paper's conformers (40
molecules): it writes `corpus.json`, `molecules.parquet` and `groups/`, and the
benchmark runner screens the result in every mode.
