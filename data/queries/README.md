# Query panels

## PANEL-8

`PANEL-8.sdf` holds the eight query ligands behind every LIT-PCBA screen in the
paper: Tables 2–3, the roofline runs, and the portability table. They are
LIT-PCBA's PDB template ligands, with crystal-pose 3D coordinates as distributed
with the benchmark, and the screens use those coordinates as they are.

sha256: `b27df200f284769fa0c5229bb2c33ecb2c5e037da028bad57dd3e7c13c2515ea`

| Query | Target | PDB | Heavy atoms |
|---|---|---|---|
| `ADRB2_3p0g_query` | ADRB2 | 3P0G | 27 |
| `ALDH1_4wp7_query` | ALDH1 | 4WP7 | 32 |
| `ESR1_ago_1l2i_query` | ESR1 (agonist) | 1L2I | 24 |
| `ESR1_ant_1xp1_query` | ESR1 (antagonist) | 1XP1 | 34 |
| `FEN1_5fv7_query` | FEN1 | 5FV7 | 23 |
| `GBA_2v3d_query` | GBA | 2V3D | 15 |
| `IDH1_4i3k_query` | IDH1 | 4I3K | 17 |
| `KAT2A_5h86_query` | KAT2A | 5H86 | 53 |

**Selection rule.** The rule was fixed before any timing was taken, and nothing
measured could have influenced it:
1. Sort LIT-PCBA's 15 targets by name and take the first eight.
2. Within each, take the template ligand whose record name sorts first.

`scripts/make_query_panels.py` applies the rule. Its input is one SDF per target,
holding that target's template ligands as parsed by RDKit. The mol2 templates
that RDKit could not read directly were recovered by an Open Babel round trip
through PDB, and a few remained unreadable. Applying the rule to a different
parse could therefore pick a different ligand for a target, so this file, not
the rule, is the reference.

`scripts/build_litpcba.py` (see `scripts/LITPCBA.md`) rebuilds that input from
the public LIT-PCBA release with the pinned RDKit and Open Babel, applies the
rule, and checks the result against this file. It reproduces this file byte for
byte.

Two LIT-PCBA templates are also actives of their own target (both PKM2). Neither
is in this panel, and the panel is used for throughput, where that overlap
cannot affect a timing.
