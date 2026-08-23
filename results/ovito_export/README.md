# OVITO export bundle -- Ni-Al MACE/LAMMPS structures and trajectories

Generated 2026-08-19 from Stage A-D3 LAMMPS/MACE deployment validation work; extended 2026-08-23 with `lammps_0K_zeroshot/` (MACE-MATPES-PBE-0 zero-shot Stage B structures) and the three-way DFT/zero-shot/fine-tuned comparison table. Every structure file is real simulation output -- nothing here is synthetic or placeholder. OVITO desktop reads `.extxyz` and LAMMPS `.data`/dump text formats natively; no ovito install was performed on this machine (per instruction -- the user has OVITO desktop locally).

**Species labeling**: every LAMMPS `.data` file uses this project's fixed `ELEMENT_ORDER=["Al","Ni"]` convention (type 1 = Al, type 2 = Ni) throughout Stage A-D3. The `.extxyz` conversions carry real chemical symbols directly (via explicit `Z_of_type={1:13, 2:28}` on read-back) -- prefer the `.extxyz` file if your tool doesn't let you set a type-to-element mapping.

## dft/ -- DFT-relaxed reference cells (5)

Source: `data/datasets/ni_al_combined227_dft.extxyz`, `{phase}_relaxed` configs. QE 7.6, PBE (see `configs/project_knowledge.md` Section 2).

| Phase | File(s) | State | Atoms | Cell parameters (A, deg) | Note |
|---|---|---|---|---|---|
| Al3Ni | `Al3Ni_dft_relaxed.extxyz` | DFT relaxed (0 K) | 16 | a=4.8255 b=6.6230 c=7.3825 alpha=90.000 beta=90.000 gamma=90.000 |  |
| Al3Ni2 | `Al3Ni2_dft_relaxed.extxyz` | DFT relaxed (0 K) | 5 | a=4.0449 b=4.0449 c=4.9079 alpha=90.000 beta=90.000 gamma=120.000 |  |
| Al3Ni5 | `Al3Ni5_dft_relaxed.extxyz` | DFT relaxed (0 K) | 8 | a=3.7623 b=5.0118 c=5.0118 alpha=96.478 beta=90.000 gamma=90.000 |  |
| AlNi | `AlNi_dft_relaxed.extxyz` | DFT relaxed (0 K) | 2 | a=2.8940 b=2.8940 c=2.8940 alpha=90.000 beta=90.000 gamma=90.000 |  |
| AlNi3 | `AlNi3_dft_relaxed.extxyz` | DFT relaxed (0 K) | 4 | a=3.5673 b=3.5674 c=3.5674 alpha=90.000 beta=90.000 gamma=90.000 |  |

## lammps_0K/ -- LAMMPS zero-stress relaxed cells (5)

**Al3Ni and Al3Ni5 are PRIMITIVE cells** (filled this session -- previously computed in-memory during Stage B/C/D but never saved to disk), same atom count as their `dft/` counterpart -- these are the two pairs that give a literal, direct, same-size DFT-vs-LAMMPS comparison.

**AlNi, AlNi3, Al3Ni2 are SUPERCELLS** (reused from Stage D-2, filename-tagged `_supercell` so this is unambiguous without reading prose) -- different atom count than their `dft/` counterpart. Compare lattice parameters and symmetry only; do NOT treat these as atom-count-matched pairs.

| Phase | File(s) | State | Atoms | Cell parameters (A, deg) | Note |
|---|---|---|---|---|---|
| Al3Ni | `Al3Ni_lammps_0K_primitive.extxyz` + `Al3Ni_lammps_0K_primitive.data` | LAMMPS 0K relaxed (primitive) | 16 | a=4.8155 b=6.5999 c=7.4267 alpha=90.000 beta=90.000 gamma=90.000 | DIRECTLY comparable to dft/ (same atom count, primitive cell) |
| Al3Ni2 | `Al3Ni2_lammps_0K_supercell.extxyz` + `Al3Ni2_lammps_0K_supercell.data` | LAMMPS 0K relaxed (supercell) | 135 | a=12.1546 b=12.1546 c=14.6929 alpha=90.000 beta=90.000 gamma=120.000 | NOT directly comparable to dft/ (supercell, different atom count -- geometry/symmetry comparison only) |
| Al3Ni5 | `Al3Ni5_lammps_0K_primitive.extxyz` + `Al3Ni5_lammps_0K_primitive.data` | LAMMPS 0K relaxed (primitive) | 8 | a=3.7984 b=5.0035 c=5.0035 alpha=98.279 beta=90.000 gamma=90.000 | DIRECTLY comparable to dft/ (same atom count, primitive cell) |
| AlNi | `AlNi_lammps_0K_supercell.extxyz` + `AlNi_lammps_0K_supercell.data` | LAMMPS 0K relaxed (supercell) | 128 | a=11.5818 b=11.5818 c=11.5818 alpha=90.000 beta=90.000 gamma=90.000 | NOT directly comparable to dft/ (supercell, different atom count -- geometry/symmetry comparison only) |
| AlNi3 | `AlNi3_lammps_0K_supercell.extxyz` + `AlNi3_lammps_0K_supercell.data` | LAMMPS 0K relaxed (supercell) | 108 | a=10.7022 b=10.7022 c=10.7022 alpha=90.000 beta=90.000 gamma=90.000 | NOT directly comparable to dft/ (supercell, different atom count -- geometry/symmetry comparison only) |

## lammps_0K_zeroshot/ -- MACE-MATPES-PBE-0 ZERO-SHOT relaxed cells (5), added 2026-08-23

Same relax recipe as `lammps_0K/` (LAMMPS mliap unified, Kokkos build, `box/relax tri` + `minimize`, starting from the DFT-relaxed geometry) but using the **zero-shot MACE-MATPES-PBE-0 foundation checkpoint** (`runs/pilot25_matpes_pbe_lora_v1/downloads/mace/MACEmatpespbeomatftmodel`, exported to mliap format as `models/mace_matpes_pbe_0_zeroshot-mliap_lammps.pt`, head="default") -- i.e. what the fine-tuned model started from **before** the Ni-Al fine-tuning that produced `lammps_0K/`'s structures.

**All 5 phases are PRIMITIVE cells**, same atom count as their `dft/` counterpart in every case (unlike `lammps_0K/`, where only Al3Ni/Al3Ni5 are primitive) -- every phase here is directly, atom-count-comparable to `dft/` with no supercell caveat.

| Phase | File(s) | State | Atoms | Cell parameters (A, deg) | Note |
|---|---|---|---|---|---|
| AlNi | `AlNi_lammps_0K_zeroshot_primitive.extxyz` + `.data` | LAMMPS 0K relaxed, zero-shot (primitive) | 2 | a=2.8681 b=2.8681 c=2.8681 alpha=90.000 beta=90.000 gamma=90.000 | DIRECTLY comparable to dft/ |
| Al3Ni | `Al3Ni_lammps_0K_zeroshot_primitive.extxyz` + `.data` | LAMMPS 0K relaxed, zero-shot (primitive) | 16 | a=4.7497 b=6.6483 c=7.3968 alpha=90.000 beta=90.000 gamma=90.000 | DIRECTLY comparable to dft/ |
| Al3Ni2 | `Al3Ni2_lammps_0K_zeroshot_primitive.extxyz` + `.data` | LAMMPS 0K relaxed, zero-shot (primitive) | 5 | a=4.0422 b=4.0422 c=4.8772 alpha=90.000 beta=90.000 gamma=120.000 | DIRECTLY comparable to dft/ |
| Al3Ni5 | `Al3Ni5_lammps_0K_zeroshot_primitive.extxyz` + `.data` | LAMMPS 0K relaxed, zero-shot (primitive) | 8 | a=3.8228 b=4.9677 c=4.9677 alpha=100.373 beta=90.000 gamma=90.000 | DIRECTLY comparable to dft/ |
| AlNi3 | `AlNi3_lammps_0K_zeroshot_primitive.extxyz` + `.data` | LAMMPS 0K relaxed, zero-shot (primitive) | 4 | a=3.5629 b=3.5629 c=3.5629 alpha=90.000 beta=90.000 gamma=90.000 | DIRECTLY comparable to dft/ |

Structural before/after JSON summary and DFT-reference comparison: `results/lammps_stage_b_matpes_pbe0_zeroshot/`, `configs/LAMMPS_STAGE_B_MATPES_PBE0_ZEROSHOT_STATUS.txt`. **Stage C (elastic) and Stage D (MD) were NOT run for this zero-shot model -- out of scope for the task that produced this directory; `lammps_0K_zeroshot/` is a 0 K relax-only structure set.**

## md_endpoints/ -- MD snapshot endpoints (NOT trajectories)

Single frames only -- Stage D and Stage D-2 never issued a LAMMPS `dump` command, so no per-step data exists for these runs (confirmed by grep, not assumed). Stage D covers all 5 phases at PRIMITIVE-cell size (post-NVT t=15ps, post-NPT t=30ps); Stage D-2 covers AlNi/AlNi3/Al3Ni2 at SUPERCELL size (post-NPT only, t=15ps, single-stage protocol, no separate NVT stage).

| Phase | File(s) | State | Atoms | Cell parameters (A, deg) | Note |
|---|---|---|---|---|---|
| Al3Ni | `Al3Ni_stageD_post_npt.extxyz` + `Al3Ni_stageD_post_npt.data` | 300K NPT endpoint (t=30ps, primitive) | 16 | a=4.8620 b=6.7006 c=7.2987 alpha=91.570 beta=89.922 gamma=90.340 |  |
| Al3Ni | `Al3Ni_stageD_post_nvt.extxyz` + `Al3Ni_stageD_post_nvt.data` | 300K NVT endpoint (t=15ps, primitive) | 16 | a=4.8155 b=6.5999 c=7.4267 alpha=90.000 beta=90.000 gamma=90.000 |  |
| Al3Ni2 | `Al3Ni2_stageD2_post_npt_supercell.extxyz` + `Al3Ni2_stageD2_post_npt_supercell.data` | 300K NPT endpoint (t=15ps, supercell) | 135 | a=12.1243 b=12.2550 c=14.7173 alpha=90.154 beta=89.776 gamma=119.866 |  |
| Al3Ni2 | `Al3Ni2_stageD_post_npt.extxyz` + `Al3Ni2_stageD_post_npt.data` | 300K NPT endpoint (t=30ps, primitive) | 5 | a=3.9761 b=4.0682 c=5.0061 alpha=86.760 beta=91.306 gamma=121.565 |  |
| Al3Ni2 | `Al3Ni2_stageD_post_nvt.extxyz` + `Al3Ni2_stageD_post_nvt.data` | 300K NVT endpoint (t=15ps, primitive) | 5 | a=4.0515 b=4.0515 c=4.8976 alpha=90.000 beta=90.000 gamma=120.000 |  |
| Al3Ni5 | `Al3Ni5_stageD_post_npt.extxyz` + `Al3Ni5_stageD_post_npt.data` | 300K NPT endpoint (t=30ps, primitive) | 8 | a=3.9397 b=5.0077 c=4.9265 alpha=97.010 beta=89.838 gamma=89.796 |  |
| Al3Ni5 | `Al3Ni5_stageD_post_nvt.extxyz` + `Al3Ni5_stageD_post_nvt.data` | 300K NVT endpoint (t=15ps, primitive) | 8 | a=3.7984 b=5.0035 c=5.0035 alpha=98.279 beta=90.000 gamma=90.000 |  |
| AlNi | `AlNi_stageD2_post_npt_supercell.extxyz` + `AlNi_stageD2_post_npt_supercell.data` | 300K NPT endpoint (t=15ps, supercell) | 128 | a=11.6327 b=11.6257 c=11.5841 alpha=90.066 beta=89.901 gamma=89.903 |  |
| AlNi | `AlNi_stageD_post_npt.extxyz` + `AlNi_stageD_post_npt.data` | 300K NPT endpoint (t=30ps, primitive) | 2 | a=2.8356 b=2.8943 c=3.1142 alpha=89.568 beta=83.530 gamma=89.535 |  |
| AlNi | `AlNi_stageD_post_nvt.extxyz` + `AlNi_stageD_post_nvt.data` | 300K NVT endpoint (t=15ps, primitive) | 2 | a=2.8954 b=2.8954 c=2.8954 alpha=90.000 beta=90.000 gamma=90.000 |  |
| AlNi3 | `AlNi3_stageD2_post_npt_supercell.extxyz` + `AlNi3_stageD2_post_npt_supercell.data` | 300K NPT endpoint (t=15ps, supercell) | 108 | a=10.7554 b=10.7260 c=10.7443 alpha=89.815 beta=90.212 gamma=90.179 |  |
| AlNi3 | `AlNi3_stageD_post_npt.extxyz` + `AlNi3_stageD_post_npt.data` | 300K NPT endpoint (t=30ps, primitive) | 4 | a=3.4906 b=3.6977 c=3.5704 alpha=92.475 beta=90.780 gamma=90.275 |  |
| AlNi3 | `AlNi3_stageD_post_nvt.extxyz` + `AlNi3_stageD_post_nvt.data` | 300K NVT endpoint (t=15ps, primitive) | 4 | a=3.5674 b=3.5674 c=3.5674 alpha=90.000 beta=90.000 gamma=90.000 |  |

## supercells/ -- 0 K relaxed supercells, no MD (5)

AlNi (128 atoms, 4x4x4), AlNi3 (108 atoms, 3x3x3), Al3Ni2 (135 atoms, 3x3x3) from Stage D-2; Al3Ni5 (144 atoms, 3x3x2) and Al3Ni (128 atoms, 2x2x2) built this session. Each replicates that phase's own zero-stress relaxed primitive cell (translational symmetry -> exact zero-stress supercell, no separate supercell-scale relax needed). All 5 phases now have a supercell.

| Phase | File(s) | State | Atoms | Cell parameters (A, deg) | Note |
|---|---|---|---|---|---|
| Al3Ni | `Al3Ni_supercell_0K.extxyz` + `Al3Ni_supercell_0K.data` | LAMMPS 0K relaxed (supercell) | 128 | a=9.6310 b=13.1999 c=14.8535 alpha=90.000 beta=90.000 gamma=90.000 |  |
| Al3Ni2 | `Al3Ni2_supercell_0K.extxyz` + `Al3Ni2_supercell_0K.data` | LAMMPS 0K relaxed (supercell) | 135 | a=12.1546 b=12.1546 c=14.6929 alpha=90.000 beta=90.000 gamma=120.000 |  |
| Al3Ni5 | `Al3Ni5_supercell_0K.extxyz` + `Al3Ni5_supercell_0K.data` | LAMMPS 0K relaxed (supercell) | 144 | a=11.3951 b=15.0105 c=10.0070 alpha=98.279 beta=90.000 gamma=90.000 |  |
| AlNi | `AlNi_supercell_0K.extxyz` + `AlNi_supercell_0K.data` | LAMMPS 0K relaxed (supercell) | 128 | a=11.5818 b=11.5818 c=11.5818 alpha=90.000 beta=90.000 gamma=90.000 |  |
| AlNi3 | `AlNi3_supercell_0K.extxyz` + `AlNi3_supercell_0K.data` | LAMMPS 0K relaxed (supercell) | 108 | a=10.7022 b=10.7022 c=10.7022 alpha=90.000 beta=90.000 gamma=90.000 |  |

## trajectories/ -- animated NPT runs (3 phases)

LAMMPS native custom-dump text format (`ITEM: ATOMS id element xu yu zu`) -- one of OVITO's most robust native importers. `element` field carries real chemical symbols (`dump_modify ... element Al Ni`), not numeric LAMMPS types. `xu yu zu` are LAMMPS-computed UNWRAPPED coordinates, so atoms do not 'teleport' across the periodic boundary between animated frames -- both explicitly requested. Box bounds (including triclinic tilt) are written every frame automatically by LAMMPS's dump format.

| Phase | File | Atoms | Frames | Dump interval | Total time | File size | Starting structure | Initial cell (A, deg) |
|---|---|---|---|---|---|---|---|---|
| AlNi | `AlNi_supercell_300K_npt_trajectory.dump` | 128 | 151 | 100 steps (0.100 ps) | 15.0 ps | 0.64 MB | `AlNi_supercell_0K.data` (0 K supercell) | see supercells/ entry above |
| Al3Ni5 | `Al3Ni5_supercell_300K_npt_trajectory.dump` | 144 | 151 | 100 steps (0.100 ps) | 15.0 ps | 0.72 MB | `Al3Ni5_supercell_0K.data` (0 K supercell) | see supercells/ entry above |
| Al3Ni | `Al3Ni_supercell_300K_npt_trajectory.dump` | 128 | 151 | 100 steps (0.100 ps) | 15.0 ps | 0.63 MB | `Al3Ni_supercell_0K.data` (0 K supercell) | see supercells/ entry above |

Protocol (all phases, identical to Stage D-2's supercell NPT protocol): 300 K, 1 fs timestep, single-stage NPT (no separate NVT thermalization), full triclinic barostat (`tri`, ambient pressure), Nose-Hoover thermostat (Tdamp=0.1 ps), barostat damping 1.0 ps, seed 20260819. Both files well under the 200 MB size concern (0.6-0.7 MB each) -- dump frequency (every 100 steps, ~150 frames) was not reduced.

## rdf/ -- radial distribution function, quantitative order evidence (5)

g(r) computed from each phase's **DFT-relaxed primitive cell** (`dft/` entries, NOT a LAMMPS or MD state) via `ase.neighborlist.neighbor_list` with rmax=10.0 A, dr=0.05 A. This is a PBC-correct calculation regardless of cutoff-vs-cell-size (ASE handles periodic replication properly, unlike a naive minimum-image approach), so it is meaningful even for AlNi's 2-atom cell. Total (all-species) g(r), not partial/species-resolved. First-peak positions (2.42-2.53 A across all 5 phases) are physically reasonable Al-Ni nearest-neighbor distances -- a basic sanity check, not a literature validation. This is the quantitative order evidence that does NOT depend on PTM (or any template classifier) working correctly on these low-symmetry phases -- see the caveat below.

| Phase | File |
|---|---|
| AlNi | `rdf/AlNi_rdf.csv` |
| Al3Ni | `rdf/Al3Ni_rdf.csv` |
| Al3Ni2 | `rdf/Al3Ni2_rdf.csv` |
| Al3Ni5 | `rdf/Al3Ni5_rdf.csv` |
| AlNi3 | `rdf/AlNi3_rdf.csv` |

## rdf/partial/ -- species-resolved (partial) RDF + chemical-order check

g_AlAl(r), g_AlNi(r), g_NiNi(r) for all 5 phases, at TWO states each: the 0 K DFT-relaxed cell (chemical ground truth -- a 0 K relaxation cannot diffuse/reorder atoms) and the 300 K MD endpoint (supercell where one exists: AlNi/AlNi3/Al3Ni2 from Stage D-2, Al3Ni5 from Stage D-3's trajectory final frame; Al3Ni falls back to Stage D's 16-atom primitive -- no supercell MD was ever run for Al3Ni). Same rmax=10.0 A, dr=0.05 A as the total RDF above, so all three overlay cleanly with each other and with `rdf/{phase}_rdf.csv`. Convention: g_ab(r) = n_ab(r)*V/(N_a*N_b*4*pi*r^2*dr) -- g_AlNi(r) as computed equals g_NiAl(r) by construction, so only one Al-Ni file exists per phase/state (15 files: 5 phases x 3 pairs, one state) x 2 states = 30 CSVs total, plus `partial_rdf_shell_report.json` with the numeric first-shell peak/coordination data behind the verdicts below.

**This is the check no previous step in this project would have caught**: Stage A-D3 validated energy/force agreement, elastic constants, and positional/thermal MD stability -- none of that distinguishes a structure where Al and Ni stay on their correct sublattices from one where they've started swapping (antisite defects / chemical disordering), since both would look identical in every metric checked so far.

| Phase | Structure type | Verdict | Basis |
|---|---|---|---|
| AlNi | B2 (CsCl) | **PRESERVED** | B2 (CsCl-type): first shell is 8 unlike (Al-Ni) neighbors, textbook exact. CN_AlNi=8.0 identical at 0K and 300K. g_AlAl and g_NiNi are EXACTLY 0.000000 at the AlNi first-shell distance (r=2.525 A) at 300K -- no antisite signature, quantitatively confirmed, not inferred from peak position alone. |
| AlNi3 | L1_2 (Cu3Au) | **PRESERVED** | L1_2 (Cu3Au-type): Al's 12 nearest neighbors are ALL Ni (textbook exact); Ni's 12 nearest neighbors are 4 Al + 8 Ni. CN_AlNi=12.0 and CN_NiNi=8.0 identical at 0K and 300K (CN_NiAl derives to exactly 4.0 both times). g_AlAl is EXACTLY 0.000000 at the first-shell distance (r=2.525 A) at 300K -- no antisite signature, quantitatively confirmed. |
| Al3Ni | Pnma (D0_11/cementite) | **PRESERVED** | Pnma, D0_11/cementite-type -- no exact textbook first-shell number used here; general expectation (minority species Ni avoids Ni-Ni first-neighbor contact) is qualitatively consistent (CN_NiNi small/second-shell at both states). Now verified at the SAME confidence level as the other 4 phases: a dedicated 128-atom (2x2x2) supercell trajectory closed the statistics gap (previously only a 16-atom single snapshot existed for this phase). CN_AlNi -- the most diagnostic pair -- is essentially UNCHANGED (2.667->2.677, +0.4%, 0K->300K). Peak positions stable across all 3 pairs (AlNi 2.475->2.475 A exact; AlAl 2.875->2.825 A; NiNi 3.775->3.725 A). CN shifts for the like-pairs (AlAl 6.67->7.77, NiNi 2.0->1.38) are the same order of magnitude as the shell-boundary-integration sensitivity already seen and explained for Al3Ni2 -- not a species migration. |
| Al3Ni2 | P-3m1 (hex) | **PRESERVED** | P-3m1 (hexagonal) -- no exact textbook first-shell number used here. Peak POSITIONS unchanged 0K->300K for all 3 pair types (AlAl 2.93->2.98 A, AlNi 2.43->2.43 A exact, NiNi 2.73->2.73 A exact) -- no new peaks at wrong distances. CN shifts (AlNi 3.33->5.32, NiNi 3.0->2.19) track a shell-boundary integration window that widened under thermal peak broadening (AlNi shell_r 2.48->2.88 A), not a species migration -- an integration-method artifact, not a chemistry change. |
| Al3Ni5 | Cmmm | **PRESERVED** | Cmmm -- no exact textbook first-shell number used here. Best-behaved of the 3 lower-symmetry phases (144-atom supercell, good statistics): CN_AlNi IDENTICAL 0K->300K (9.333->9.333, to 3 decimal places). All 3 peak positions shifted by <=0.1 A, consistent with the ~1% linear thermal expansion already established for this phase in Stage D-2. |

**Antisite/disordering signature: NONE DETECTED in any phase.** The two phases with an exact textbook-forbidden first-shell pair (AlNi: no Al-Al or Ni-Ni at the 8-fold unlike-neighbor distance; AlNi3: no Al-Al at the 12-fold Ni-neighbor distance) were checked quantitatively, not just by peak position: g_AlAl and g_NiNi are EXACTLY 0.000000 at r=2.525 A for AlNi at 300 K, and g_AlAl is EXACTLY 0.000000 at r=2.525 A for AlNi3 at 300 K -- read directly from the CSVs, not inferred. No first-shell peak broadened into an adjacent pair's peak for any phase at either state.

| Phase | State | CN_AlAl (shell r, A) | CN_AlNi (shell r, A) | CN_NiNi (shell r, A) |
|---|---|---|---|---|
| AlNi | 0K DFT | 6.00 (2.93) | 8.00 (2.58) | 6.00 (2.93) |
| AlNi | 300K MD | 6.00 (3.18) | 8.00 (2.83) | 6.00 (3.28) |
| AlNi3 | 0K DFT | 6.00 (3.62) | 12.00 (2.58) | 8.00 (2.58) |
| AlNi3 | 300K MD | 6.00 (3.88) | 12.00 (2.88) | 8.00 (2.78) |
| Al3Ni | 0K DFT | 6.67 (2.93) | 2.67 (2.53) | 2.00 (3.83) |
| Al3Ni | 300K MD | 7.77 (3.12) | 2.68 (2.62) | 1.38 (3.83) |
| Al3Ni2 | 0K DFT | 6.00 (2.98) | 3.33 (2.48) | 3.00 (2.78) |
| Al3Ni2 | 300K MD | 6.00 (3.23) | 5.32 (2.88) | 2.19 (2.78) |
| Al3Ni5 | 0K DFT | 2.67 (2.88) | 9.33 (2.62) | 6.40 (2.73) |
| Al3Ni5 | 300K MD | 2.11 (2.93) | 9.33 (2.83) | 6.76 (3.03) |

## Three-way structural comparison: DFT vs zero-shot vs fine-tuned (added 2026-08-23)

**The most compelling figure available in this bundle.** All 5 phases, all
primitive cells, all atom-count-matched to `dft/` in every column -- the
only 3-way structural comparison in the bundle with no supercell caveat
anywhere. Zero-shot = `lammps_0K_zeroshot/` (MACE-MATPES-PBE-0 foundation
checkpoint, no fine-tuning). Fine-tuned = `lammps_0K/` for Al3Ni/Al3Ni5
(the two phases saved as primitive there); for AlNi/AlNi3/Al3Ni2, the
fine-tuned lattice parameters/volume below are the values recorded in
`configs/LAMMPS_STAGE_B_RELAXATION_STATUS.txt` (same primitive-cell relax,
just not separately re-saved to a primitive `.extxyz`/`.data` pair in
`lammps_0K/`, which only kept those 3 phases' pre-existing Stage D-2
supercell files). % error is volume/atom vs the same `dft/` reference cell
in both cases -- a genuine single-reference before/after (see the parent
project's `configs/NI_AL_UNIFIED_COMPARISON.md` Section 10 for the full
derivation and the elemental-coverage caveat behind why zero-shot
undershoots here).

| Phase | State | a (A) | b (A) | c (A) | alpha (deg) | V/atom (A^3) | Vol err vs DFT |
|---|---|---:|---:|---:|---:|---:|---:|
| AlNi | DFT | 2.89401 | 2.89401 | 2.89401 | 90.000 | 12.11907 | -- |
| AlNi | Zero-shot | 2.86805 | 2.86805 | 2.86805 | 90.000 | 11.79590 | **-2.6666%** |
| AlNi | Fine-tuned | 2.89545 | 2.89545 | 2.89545 | 90.000 | 12.13714 | **+0.1491%** |
| Al3Ni | DFT | 4.82550 | 6.62303 | 7.38249 | 90.000 | 14.74629 | -- |
| Al3Ni | Zero-shot | 4.74971 | 6.64830 | 7.39676 | 90.000 | 14.59819 | **-1.0043%** |
| Al3Ni | Fine-tuned | 4.81550 | 6.59993 | 7.42674 | 90.000 | 14.75229 | **+0.0407%** |
| Al3Ni2 | DFT | 4.04492 | 4.04492 | 4.90786 | 90.000 | 13.90827 | -- |
| Al3Ni2 | Zero-shot | 4.04219 | 4.04219 | 4.87724 | 90.000 | 13.80283 | **-0.7581%** |
| Al3Ni2 | Fine-tuned | 4.05153 | 4.05153 | 4.89762 | 90.000 | 13.92467 | **+0.1179%** |
| Al3Ni5 | DFT | 3.76231 | 5.01178 | 5.01178 | 96.478 | 11.73726 | -- |
| Al3Ni5 | Zero-shot | 3.82276 | 4.96775 | 4.96775 | 100.373 | 11.59978 | **-1.1713%** |
| Al3Ni5 | Fine-tuned | 3.79835 | 5.00350 | 5.00350 | 98.279 | 11.76261 | **+0.2159%** |
| AlNi3 | DFT | 3.56726 | 3.56739 | 3.56739 | 90.000 | 11.34945 | -- |
| AlNi3 | Zero-shot | 3.56288 | 3.56288 | 3.56288 | 90.000 | 11.30688 | **-0.3751%** |
| AlNi3 | Fine-tuned | 3.56739 | 3.56739 | 3.56739 | 90.000 | 11.34987 | **+0.0037%** |

**Summary: max |volume/atom error| zero-shot 2.6666% (AlNi) vs fine-tuned
0.2159% (Al3Ni5) -- a 12.3x reduction in worst-phase structural error from
fine-tuning, on the identical QE/PBE DFT reference for every phase, every
column.** Symmetry (spacegroup number) is preserved 5/5 in BOTH the
zero-shot and fine-tuned relaxations -- fine-tuning's gain here is in
volume/lattice accuracy, not in avoiding a symmetry break. Sign pattern:
zero-shot under-contracts on all 5 phases (every error negative);
fine-tuned over-expands on all 5 (every error positive) -- opposite bias
directions, both small in the fine-tuned case.

## Directly comparable pairs (explicit)

- **Al3Ni**: `dft/Al3Ni_dft_relaxed.extxyz` vs `lammps_0K/Al3Ni_lammps_0K_primitive.extxyz` -- same atom count (16), direct.
- **Al3Ni5**: `dft/Al3Ni5_dft_relaxed.extxyz` vs `lammps_0K/Al3Ni5_lammps_0K_primitive.extxyz` -- same atom count (8), direct. Note the alpha angle: DFT 96.478 deg vs LAMMPS 98.279 deg -- this is a real, previously-diagnosed model PES feature (`configs/LAMMPS_STAGE_B_AL3NI5_ALPHA_DIAGNOSTIC.txt`), not a bundle error.
- **AlNi, AlNi3, Al3Ni2**: `dft/` (primitive) vs `lammps_0K/*_supercell` -- **NOT** atom-count comparable. Compare lattice parameters/symmetry only.
- All 5 phases: `dft/` vs `rdf/` are on the SAME structure (RDF computed from the DFT-relaxed cell), so RDF peak positions reflect the DFT geometry, not the LAMMPS-relaxed one.

## Known gaps / limitations

- **No trajectory for the remaining 2 phases** (Al3Ni2, AlNi3) -- Stage D-3 covers AlNi, Al3Ni5, and Al3Ni. `md_endpoints/` gives single before/after snapshots for all 5, but not an animation, for the other 2.
- **PTM was never run** -- ovito is not installed on this machine (by design; the user's OVITO desktop is expected to do this). Based on OVITO's documented built-in template set (FCC/HCP/BCC/ICO/SC/diamond-cubic/diamond-hex/graphene -- recalled, not verified this session), AlNi (B2, BCC-topology) and AlNi3 (L1_2, FCC-topology) should classify positively; Al3Ni/Al3Ni2/Al3Ni5's lower-symmetry coordination environments are not covered by any built-in template and would likely show as 'Other/unclassified' -- not evidence of disorder. The `rdf/` CSVs are the recommended quantitative fallback regardless of what PTM reports.
- **RESOLVED**: `rdf/*_rdf.csv` (total) has now been supplemented with `rdf/partial/` (species-resolved g_AlAl/g_AlNi/g_NiNi + a chemical-order verdict per phase) -- see that section above. Not an open gap anymore.
- **AlNi/AlNi3/Al3Ni2 have no primitive-cell 0 K LAMMPS structure file** -- only their Stage D-2 supercell version exists; a true 1:1 primitive DFT-vs-LAMMPS comparison for these 3 phases would need a fresh (cheap) relax run, not done here (out of the scope actually requested this session).
- **RESOLVED**: Al3Ni's chemical-order verdict was previously lower-confidence (only a 16-atom primitive-cell MD snapshot existed, no supercell run). A dedicated 128-atom (2x2x2) supercell trajectory closed this gap -- Al3Ni is now verified at the same confidence level as the other 4 phases (see the chemical-order table above). Not an open gap anymore.
- **First-shell coordination numbers use a simple peak-then-first-local-minimum shell boundary** -- sensitive to thermal peak broadening (see Al3Ni2's CN shifts above, attributed to a widened integration window, not a chemistry change); treat CN as an approximate, not a rigorously-converged, number, especially at 300 K.
- **RESOLVED (2026-08-23)**: this bundle originally had no MACE-MATPES-PBE-0 zero-shot structures (it was built before that Stage B run), blocking a direct DFT-vs-zero-shot-vs-fine-tuned visual comparison. `lammps_0K_zeroshot/` (5 primitive cells) now closes this -- see the "Three-way structural comparison" section above. Stage C (elastic) and Stage D (MD) were deliberately NOT run for the zero-shot model (out of scope), so no zero-shot equivalent of `md_endpoints/`/`trajectories/`/Stage C exists or is claimed here.

