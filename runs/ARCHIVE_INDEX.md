# Run records

These are the run records the paper's build reads. Every ROSHAMBO3 timing in
the paper comes from the frozen benchmark commit
`3bb39f698bfffc1045f585187d30230ba639a758` of the internal development
repository (identical screening kernels to the released ROSHAMBO3 1.0.0), on
format-3 corpora; the ROSHAMBO2 comparator timings come from earlier archived
sessions (`archive/volta-production-headtohead-t114/`). Commit hashes in these records refer to that internal
history, which is not published.

References to `results/`, `tickets/`, `doc/`, `hosts/`, to `runs/archive/` directories
not listed below, and to other files not in this repository point at the internal
development record.

Paths, device serial numbers and UUIDs were redacted when the records were
imported (`scripts/import_portability.py` and the export that produced this
tree); data locations appear as `$EXTERNAL_DATA`. Records of runs on the
private 3CR library carry counts, rates and the query file's hash only: no structures,
molecule ids, query SMILES or hit lists.

| Directory | Paper use |
|---|---|
| `public-3bb39f69/` | Blackwell and TITAN V runs on LIT-PCBA (extended) and PubChem3D: the main results table, large-scale search, scale and roofline tables |
| `rtx-pro-6000-3cr-3bb39f69/` | 3CR stability and saturation (the saturation figure and the `ComboQ*`/`ThreeCr*` constants) |
| `field-accuracy-3bb39f69/` | Field-versus-analytic retrieval on an internal tuning corpus: aggregate and per-query recall, no structures |
| `litpcba-corpus-3bb39f69/` | LIT-PCBA conformers-per-molecule histogram and source size (`scripts/litpcba_conformer_counts.py`) |
| `roofline-ladder-3bb39f69/`, `roofline-ladder-l4-3bb39f69/` | Nsight Compute counter summaries for the roofline model (GB202, AD104) |
| `portability/`, `portability-scaling/` | The portability table and the CPU thread-scaling appendix (`scripts/portability_campaign.sh`, `scripts/import_portability.py`) |
| `archive/volta-production-headtohead-t114/` | The TITAN V head-to-head against ROSHAMBO2 (speedups, step budget, objective cost) |
| `archive/dudez-roshambo2-parity-t91/` | DUDE-Z parity against ROSHAMBO2 |
| `archive/agent-development-record/` | The development-record export behind the ticket figures and Appendix E counts |
