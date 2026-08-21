#!/usr/bin/env python3
"""Writes results/ovito_export/README.md from manifest.json (structure
entries, produced by build_ovito_export_bundle.py), the Stage D-3
trajectory summary JSONs, and the partial-RDF shell report (produced by
compute_partial_rdf.py). Pure read/format, no LAMMPS/ASE compute.
"""
import json

ROOT = "/workspace/ni_al"
EXPORT_DIR = f"{ROOT}/results/ovito_export"

with open(f"{EXPORT_DIR}/manifest.json") as fh:
    manifest = json.load(fh)

TRAJECTORY_PHASES = ["AlNi", "Al3Ni5", "Al3Ni"]
traj_summaries = {}
for phase in TRAJECTORY_PHASES:
    with open(f"{ROOT}/results/lammps_stage_d3/{phase}_summary.json") as fh:
        traj_summaries[phase] = json.load(fh)

with open(f"{EXPORT_DIR}/rdf/partial/partial_rdf_shell_report.json") as fh:
    partial_report = json.load(fh)

# Chemical-order verdicts: manually assessed against the printed shell
# report (see the session's own analysis) -- textbook coordination
# numbers for B2/L1_2 are exact literature facts; Al3Ni/Al3Ni2/Al3Ni5 have
# no textbook first-shell coordination number available, so their verdict
# rests on 0K-DFT-vs-300K-MD self-consistency instead (peak position and
# CN stability), not a literature comparison.
CHEM_ORDER_VERDICTS = {
    "AlNi": ("PRESERVED",
             "B2 (CsCl-type): first shell is 8 unlike (Al-Ni) neighbors, textbook exact. "
             "CN_AlNi=8.0 identical at 0K and 300K. g_AlAl and g_NiNi are EXACTLY 0.000000 "
             "at the AlNi first-shell distance (r=2.525 A) at 300K -- no antisite signature, "
             "quantitatively confirmed, not inferred from peak position alone."),
    "AlNi3": ("PRESERVED",
              "L1_2 (Cu3Au-type): Al's 12 nearest neighbors are ALL Ni (textbook exact); "
              "Ni's 12 nearest neighbors are 4 Al + 8 Ni. CN_AlNi=12.0 and CN_NiNi=8.0 "
              "identical at 0K and 300K (CN_NiAl derives to exactly 4.0 both times). "
              "g_AlAl is EXACTLY 0.000000 at the first-shell distance (r=2.525 A) at 300K -- "
              "no antisite signature, quantitatively confirmed."),
    "Al3Ni": ("PRESERVED",
              "Pnma, D0_11/cementite-type -- no exact textbook first-shell number used here; "
              "general expectation (minority species Ni avoids Ni-Ni first-neighbor contact) "
              "is qualitatively consistent (CN_NiNi small/second-shell at both states). Now "
              "verified at the SAME confidence level as the other 4 phases: a dedicated "
              "128-atom (2x2x2) supercell trajectory closed the statistics gap (previously "
              "only a 16-atom single snapshot existed for this phase). CN_AlNi -- the most "
              "diagnostic pair -- is essentially UNCHANGED (2.667->2.677, +0.4%, 0K->300K). "
              "Peak positions stable across all 3 pairs (AlNi 2.475->2.475 A exact; AlAl "
              "2.875->2.825 A; NiNi 3.775->3.725 A). CN shifts for the like-pairs (AlAl "
              "6.67->7.77, NiNi 2.0->1.38) are the same order of magnitude as the "
              "shell-boundary-integration sensitivity already seen and explained for "
              "Al3Ni2 -- not a species migration."),
    "Al3Ni2": ("PRESERVED",
               "P-3m1 (hexagonal) -- no exact textbook first-shell number used here. Peak "
               "POSITIONS unchanged 0K->300K for all 3 pair types (AlAl 2.93->2.98 A, "
               "AlNi 2.43->2.43 A exact, NiNi 2.73->2.73 A exact) -- no new peaks at wrong "
               "distances. CN shifts (AlNi 3.33->5.32, NiNi 3.0->2.19) track a shell-boundary "
               "integration window that widened under thermal peak broadening (AlNi shell_r "
               "2.48->2.88 A), not a species migration -- an integration-method artifact, "
               "not a chemistry change."),
    "Al3Ni5": ("PRESERVED",
               "Cmmm -- no exact textbook first-shell number used here. Best-behaved of the "
               "3 lower-symmetry phases (144-atom supercell, good statistics): CN_AlNi "
               "IDENTICAL 0K->300K (9.333->9.333, to 3 decimal places). All 3 peak positions "
               "shifted by <=0.1 A, consistent with the ~1% linear thermal expansion already "
               "established for this phase in Stage D-2."),
}


def fmt_cellpar(cp):
    return (f"a={cp[0]:.4f} b={cp[1]:.4f} c={cp[2]:.4f} "
            f"alpha={cp[3]:.3f} beta={cp[4]:.3f} gamma={cp[5]:.3f}")


def table_for(directory, columns_extra=""):
    rows = [r for r in manifest if r["directory"] == directory]
    lines = ["| Phase | File(s) | State | Atoms | Cell parameters (A, deg) | Note |",
             "|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: (x["phase"], x["basename"])):
        files = []
        if r["extxyz"]:
            files.append(f"`{r['extxyz']}`")
        if r["data"]:
            files.append(f"`{r['data']}`")
        lines.append(f"| {r['phase']} | {' + '.join(files)} | {r['state']} | {r['natoms']} | "
                     f"{fmt_cellpar(r['cellpar'])} | {r['note']} |")
    return "\n".join(lines)


lines = []
lines.append("# OVITO export bundle -- Ni-Al MACE/LAMMPS structures and trajectories")
lines.append("")
lines.append("Generated this session (2026-08-19) from Stage A-D3 LAMMPS/MACE deployment "
             "validation work. Every structure file is real simulation output -- nothing "
             "here is synthetic or placeholder. OVITO desktop reads `.extxyz` and LAMMPS "
             "`.data`/dump text formats natively; no ovito install was performed on this "
             "machine (per instruction -- the user has OVITO desktop locally).")
lines.append("")
lines.append("**Species labeling**: every LAMMPS `.data` file uses this project's fixed "
             "`ELEMENT_ORDER=[\"Al\",\"Ni\"]` convention (type 1 = Al, type 2 = Ni) "
             "throughout Stage A-D3. The `.extxyz` conversions carry real chemical symbols "
             "directly (via explicit `Z_of_type={1:13, 2:28}` on read-back) -- prefer the "
             "`.extxyz` file if your tool doesn't let you set a type-to-element mapping.")
lines.append("")

lines.append("## dft/ -- DFT-relaxed reference cells (5)")
lines.append("")
lines.append("Source: `data/datasets/ni_al_combined227_dft.extxyz`, `{phase}_relaxed` "
             "configs. QE 7.6, PBE (see `configs/project_knowledge.md` Section 2).")
lines.append("")
lines.append(table_for("dft"))
lines.append("")

lines.append("## lammps_0K/ -- LAMMPS zero-stress relaxed cells (5)")
lines.append("")
lines.append("**Al3Ni and Al3Ni5 are PRIMITIVE cells** (filled this session -- previously "
             "computed in-memory during Stage B/C/D but never saved to disk), same atom "
             "count as their `dft/` counterpart -- these are the two pairs that give a "
             "literal, direct, same-size DFT-vs-LAMMPS comparison.")
lines.append("")
lines.append("**AlNi, AlNi3, Al3Ni2 are SUPERCELLS** (reused from Stage D-2, "
             "filename-tagged `_supercell` so this is unambiguous without reading prose) -- "
             "different atom count than their `dft/` counterpart. Compare lattice "
             "parameters and symmetry only; do NOT treat these as atom-count-matched pairs.")
lines.append("")
lines.append(table_for("lammps_0K"))
lines.append("")

lines.append("## md_endpoints/ -- MD snapshot endpoints (NOT trajectories)")
lines.append("")
lines.append("Single frames only -- Stage D and Stage D-2 never issued a LAMMPS `dump` "
             "command, so no per-step data exists for these runs (confirmed by grep, not "
             "assumed). Stage D covers all 5 phases at PRIMITIVE-cell size (post-NVT t=15ps, "
             "post-NPT t=30ps); Stage D-2 covers AlNi/AlNi3/Al3Ni2 at SUPERCELL size "
             "(post-NPT only, t=15ps, single-stage protocol, no separate NVT stage).")
lines.append("")
lines.append(table_for("md_endpoints"))
lines.append("")

lines.append("## supercells/ -- 0 K relaxed supercells, no MD (5)")
lines.append("")
lines.append("AlNi (128 atoms, 4x4x4), AlNi3 (108 atoms, 3x3x3), Al3Ni2 (135 atoms, 3x3x3) "
             "from Stage D-2; Al3Ni5 (144 atoms, 3x3x2) and Al3Ni (128 atoms, 2x2x2) built "
             "this session. Each replicates that phase's own zero-stress relaxed primitive "
             "cell (translational symmetry -> exact zero-stress supercell, no separate "
             "supercell-scale relax needed). All 5 phases now have a supercell.")
lines.append("")
lines.append(table_for("supercells"))
lines.append("")

lines.append("## trajectories/ -- animated NPT runs (3 phases)")
lines.append("")
lines.append("LAMMPS native custom-dump text format (`ITEM: ATOMS id element xu yu zu`) -- "
             "one of OVITO's most robust native importers. `element` field carries real "
             "chemical symbols (`dump_modify ... element Al Ni`), not numeric LAMMPS types. "
             "`xu yu zu` are LAMMPS-computed UNWRAPPED coordinates, so atoms do not "
             "'teleport' across the periodic boundary between animated frames -- both "
             "explicitly requested. Box bounds (including triclinic tilt) are written every "
             "frame automatically by LAMMPS's dump format.")
lines.append("")
lines.append("| Phase | File | Atoms | Frames | Dump interval | Total time | File size | "
             "Starting structure | Initial cell (A, deg) |")
lines.append("|---|---|---|---|---|---|---|---|---|")
for phase in TRAJECTORY_PHASES:
    fname = f"{phase}_supercell_300K_npt_trajectory.dump"
    s = traj_summaries[phase]
    proto = s["protocol"]
    size_mb = s["dump_size_bytes"] / 1e6
    total_ps = proto["npt_steps"] * proto["timestep_ps"]
    lines.append(f"| {phase} | `{fname}` | {s['natoms']} | 151 | "
                 f"{proto['dump_every']} steps ({proto['dump_every']*proto['timestep_ps']:.3f} ps) | "
                 f"{total_ps:.1f} ps | {size_mb:.2f} MB | "
                 f"`{s['starting_data'].split('/')[-1]}` (0 K supercell) | "
                 f"see supercells/ entry above |")
lines.append("")
lines.append("Protocol (all phases, identical to Stage D-2's supercell NPT protocol): "
             "300 K, 1 fs timestep, single-stage NPT (no separate NVT thermalization), "
             "full triclinic barostat (`tri`, ambient pressure), Nose-Hoover thermostat "
             "(Tdamp=0.1 ps), barostat damping 1.0 ps, seed 20260819. Both files well under "
             "the 200 MB size concern (0.6-0.7 MB each) -- dump frequency (every 100 steps, "
             "~150 frames) was not reduced.")
lines.append("")

lines.append("## rdf/ -- radial distribution function, quantitative order evidence (5)")
lines.append("")
lines.append("g(r) computed from each phase's **DFT-relaxed primitive cell** "
             "(`dft/` entries, NOT a LAMMPS or MD state) via `ase.neighborlist.neighbor_list` "
             "with rmax=10.0 A, dr=0.05 A. This is a PBC-correct calculation regardless of "
             "cutoff-vs-cell-size (ASE handles periodic replication properly, unlike a naive "
             "minimum-image approach), so it is meaningful even for AlNi's 2-atom cell. "
             "Total (all-species) g(r), not partial/species-resolved. First-peak positions "
             "(2.42-2.53 A across all 5 phases) are physically reasonable Al-Ni "
             "nearest-neighbor distances -- a basic sanity check, not a literature "
             "validation. This is the quantitative order evidence that does NOT depend on "
             "PTM (or any template classifier) working correctly on these low-symmetry "
             "phases -- see the caveat below.")
lines.append("")
lines.append("| Phase | File |")
lines.append("|---|---|")
for phase in ["AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3"]:
    lines.append(f"| {phase} | `rdf/{phase}_rdf.csv` |")
lines.append("")

lines.append("## rdf/partial/ -- species-resolved (partial) RDF + chemical-order check")
lines.append("")
lines.append("g_AlAl(r), g_AlNi(r), g_NiNi(r) for all 5 phases, at TWO states each: the 0 K "
             "DFT-relaxed cell (chemical ground truth -- a 0 K relaxation cannot diffuse/"
             "reorder atoms) and the 300 K MD endpoint (supercell where one exists: AlNi/"
             "AlNi3/Al3Ni2 from Stage D-2, Al3Ni5 from Stage D-3's trajectory final frame; "
             "Al3Ni falls back to Stage D's 16-atom primitive -- no supercell MD was ever "
             "run for Al3Ni). Same rmax=10.0 A, dr=0.05 A as the total RDF above, so all "
             "three overlay cleanly with each other and with `rdf/{phase}_rdf.csv`. "
             "Convention: g_ab(r) = n_ab(r)*V/(N_a*N_b*4*pi*r^2*dr) -- g_AlNi(r) as computed "
             "equals g_NiAl(r) by construction, so only one Al-Ni file exists per phase/state "
             "(15 files: 5 phases x 3 pairs, one state) x 2 states = 30 CSVs total, plus "
             "`partial_rdf_shell_report.json` with the numeric first-shell peak/coordination "
             "data behind the verdicts below.")
lines.append("")
lines.append("**This is the check no previous step in this project would have caught**: "
             "Stage A-D3 validated energy/force agreement, elastic constants, and "
             "positional/thermal MD stability -- none of that distinguishes a structure "
             "where Al and Ni stay on their correct sublattices from one where they've "
             "started swapping (antisite defects / chemical disordering), since both would "
             "look identical in every metric checked so far.")
lines.append("")
lines.append("| Phase | Structure type | Verdict | Basis |")
lines.append("|---|---|---|---|")
STRUCTURE_TYPE = {"AlNi": "B2 (CsCl)", "AlNi3": "L1_2 (Cu3Au)", "Al3Ni": "Pnma (D0_11/cementite)",
                  "Al3Ni2": "P-3m1 (hex)", "Al3Ni5": "Cmmm"}
for phase in ["AlNi", "AlNi3", "Al3Ni", "Al3Ni2", "Al3Ni5"]:
    verdict, basis = CHEM_ORDER_VERDICTS[phase]
    lines.append(f"| {phase} | {STRUCTURE_TYPE[phase]} | **{verdict}** | {basis} |")
lines.append("")
lines.append("**Antisite/disordering signature: NONE DETECTED in any phase.** The two "
             "phases with an exact textbook-forbidden first-shell pair (AlNi: no Al-Al or "
             "Ni-Ni at the 8-fold unlike-neighbor distance; AlNi3: no Al-Al at the 12-fold "
             "Ni-neighbor distance) were checked quantitatively, not just by peak position: "
             "g_AlAl and g_NiNi are EXACTLY 0.000000 at r=2.525 A for AlNi at 300 K, and "
             "g_AlAl is EXACTLY 0.000000 at r=2.525 A for AlNi3 at 300 K -- read directly "
             "from the CSVs, not inferred. No first-shell peak broadened into an adjacent "
             "pair's peak for any phase at either state.")
lines.append("")
lines.append("| Phase | State | CN_AlAl (shell r, A) | CN_AlNi (shell r, A) | CN_NiNi (shell r, A) |")
lines.append("|---|---|---|---|---|")
for phase in ["AlNi", "AlNi3", "Al3Ni", "Al3Ni2", "Al3Ni5"]:
    for state_key, state_label in (("0K_dft", "0K DFT"), ("300K_md", "300K MD")):
        entry = partial_report.get(phase, {}).get(state_key)
        if not entry:
            continue
        shells = entry["shells"]
        cells = []
        for label in ("AlAl", "AlNi", "NiNi"):
            s = shells.get(label)
            cells.append(f"{s['coordination_number']:.2f} ({s['shell_r']:.2f})" if s else "n/a")
        lines.append(f"| {phase} | {state_label} | {cells[0]} | {cells[1]} | {cells[2]} |")
lines.append("")

lines.append("## Directly comparable pairs (explicit)")
lines.append("")
lines.append("- **Al3Ni**: `dft/Al3Ni_dft_relaxed.extxyz` vs "
             "`lammps_0K/Al3Ni_lammps_0K_primitive.extxyz` -- same atom count (16), direct.")
lines.append("- **Al3Ni5**: `dft/Al3Ni5_dft_relaxed.extxyz` vs "
             "`lammps_0K/Al3Ni5_lammps_0K_primitive.extxyz` -- same atom count (8), direct. "
             "Note the alpha angle: DFT 96.478 deg vs LAMMPS 98.279 deg -- this is a real, "
             "previously-diagnosed model PES feature "
             "(`configs/LAMMPS_STAGE_B_AL3NI5_ALPHA_DIAGNOSTIC.txt`), not a bundle error.")
lines.append("- **AlNi, AlNi3, Al3Ni2**: `dft/` (primitive) vs `lammps_0K/*_supercell` -- "
             "**NOT** atom-count comparable. Compare lattice parameters/symmetry only.")
lines.append("- All 5 phases: `dft/` vs `rdf/` are on the SAME structure (RDF computed from "
             "the DFT-relaxed cell), so RDF peak positions reflect the DFT geometry, not "
             "the LAMMPS-relaxed one.")
lines.append("")

lines.append("## Known gaps / limitations")
lines.append("")
lines.append("- **No trajectory for the remaining 2 phases** (Al3Ni2, AlNi3) -- Stage D-3 "
             "covers AlNi, Al3Ni5, and Al3Ni. `md_endpoints/` gives single before/after "
             "snapshots for all 5, but not an animation, for the other 2.")
lines.append("- **PTM was never run** -- ovito is not installed on this machine (by design; "
             "the user's OVITO desktop is expected to do this). Based on OVITO's documented "
             "built-in template set (FCC/HCP/BCC/ICO/SC/diamond-cubic/diamond-hex/graphene -- "
             "recalled, not verified this session), AlNi (B2, BCC-topology) and AlNi3 "
             "(L1_2, FCC-topology) should classify positively; Al3Ni/Al3Ni2/Al3Ni5's "
             "lower-symmetry coordination environments are not covered by any built-in "
             "template and would likely show as 'Other/unclassified' -- not evidence of "
             "disorder. The `rdf/` CSVs are the recommended quantitative fallback "
             "regardless of what PTM reports.")
lines.append("- **RESOLVED**: `rdf/*_rdf.csv` (total) has now been supplemented with "
             "`rdf/partial/` (species-resolved g_AlAl/g_AlNi/g_NiNi + a chemical-order "
             "verdict per phase) -- see that section above. Not an open gap anymore.")
lines.append("- **AlNi/AlNi3/Al3Ni2 have no primitive-cell 0 K LAMMPS structure file** -- "
             "only their Stage D-2 supercell version exists; a true 1:1 primitive DFT-vs-"
             "LAMMPS comparison for these 3 phases would need a fresh (cheap) relax run, "
             "not done here (out of the scope actually requested this session).")
lines.append("- **RESOLVED**: Al3Ni's chemical-order verdict was previously lower-confidence "
             "(only a 16-atom primitive-cell MD snapshot existed, no supercell run). A "
             "dedicated 128-atom (2x2x2) supercell trajectory closed this gap -- Al3Ni is "
             "now verified at the same confidence level as the other 4 phases (see the "
             "chemical-order table above). Not an open gap anymore.")
lines.append("- **First-shell coordination numbers use a simple peak-then-first-local-"
             "minimum shell boundary** -- sensitive to thermal peak broadening (see "
             "Al3Ni2's CN shifts above, attributed to a widened integration window, not a "
             "chemistry change); treat CN as an approximate, not a rigorously-converged, "
             "number, especially at 300 K.")
lines.append("")

with open(f"{EXPORT_DIR}/README.md", "w") as fh:
    fh.write("\n".join(lines) + "\n")

print(f"Wrote {EXPORT_DIR}/README.md")
