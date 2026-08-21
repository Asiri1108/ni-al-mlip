#!/usr/bin/env python3
"""Partial RDFs (g_AlAl, g_AlNi, g_NiNi) for all 5 phases, at two states:
  - 0 K DFT-relaxed primitive cell (chemical ground truth -- a 0 K
    geometry relaxation cannot diffuse/reorder atoms, so this IS the
    project's authoritative "correct" chemical order for each phase)
  - 300 K MD endpoint (post_npt), SUPERCELL for all 5 phases (AlNi,
    AlNi3, Al3Ni2 from Stage D-2; Al3Ni5 and Al3Ni from Stage D-3's
    trajectory final frame) for better statistics -- Al3Ni was the last
    phase still on a 16-atom primitive-cell single snapshot; closed by a
    dedicated 128-atom (2x2x2) supercell trajectory run.

Same r-range/bin width as the existing total RDF
(build_ovito_export_bundle.py's compute_rdf: rmax=10.0 A, dr=0.05 A) so
partial and total overlay cleanly.

Partial RDF convention: g_ab(r) = n_ab(r) * V / (N_a * N_b * 4*pi*r^2*dr),
where n_ab(r) is the ordered-pair histogram (type(i)=a, type(j)=b) from
ase.neighborlist.neighbor_list -- PBC-correct regardless of cutoff vs
cell size (no supercell needed for methodological validity; supercells
are used anyway per instruction, for better statistics). g_AlNi(r) as
computed here already equals g_NiAl(r) by construction (each geometric
Al-Ni pair contributes one entry from each side, and the N_a*N_b
denominator is symmetric in a,b) -- so only ONE Al-Ni file is written,
matching the 3-partial (AlAl/AlNi/NiNi) request exactly.

First-shell coordination number: for pair type a->b, walk forward from
the first peak (searched in [1.5, 4.0] A, informed by the existing total
RDF's first peaks at 2.4-2.5 A across all 5 phases) to the first local
minimum in g_ab(r) (fallback: peak_r + 1.0 A if none found), then
CN_ab = (cumulative n_ab(r) up to that shell boundary) / N_a -- the
average number of b-neighbors per a-atom within the first shell.
"""
import csv
import json
import os
import sys

import numpy as np
from ase.io import read

sys.path.insert(0, os.path.dirname(__file__))
from lattice_compare_utils import load_dft_relaxed, PHASES

ROOT = "/workspace/ni_al"
OUT_DIR = f"{ROOT}/results/ovito_export/rdf/partial"
Z_OF_TYPE = {1: 13, 2: 28}  # Al=13, Ni=28 -- matches ELEMENT_ORDER=["Al","Ni"] project-wide

RMAX = 10.0
DR = 0.05
PEAK_SEARCH_MIN = 1.5
PEAK_SEARCH_MAX = 4.0

MD_ENDPOINT = {
    "AlNi": (f"{ROOT}/results/lammps_stage_d2/AlNi_post_npt.data",
              "supercell (128 atoms, Stage D-2)"),
    "AlNi3": (f"{ROOT}/results/lammps_stage_d2/AlNi3_post_npt.data",
              "supercell (108 atoms, Stage D-2)"),
    "Al3Ni2": (f"{ROOT}/results/lammps_stage_d2/Al3Ni2_post_npt.data",
               "supercell (135 atoms, Stage D-2)"),
    "Al3Ni5": (f"{ROOT}/results/lammps_stage_d3/Al3Ni5_post_npt.data",
               "supercell (144 atoms, Stage D-3 trajectory final frame)"),
    "Al3Ni": (f"{ROOT}/results/lammps_stage_d3/Al3Ni_post_npt.data",
              "supercell (128 atoms, Stage D-3 trajectory final frame)"),
}


def read_data_as_atoms(path):
    return read(path, format="lammps-data", Z_of_type=Z_OF_TYPE, atom_style="atomic")


def partial_rdf(atoms, rmax=RMAX, dr=DR):
    from ase.neighborlist import neighbor_list
    symbols = np.array(atoms.get_chemical_symbols())
    natoms = len(atoms)
    volume = atoms.get_volume()
    n_al = int(np.sum(symbols == "Al"))
    n_ni = int(np.sum(symbols == "Ni"))
    i_idx, j_idx, d = neighbor_list("ijd", atoms, rmax)
    si = symbols[i_idx]
    sj = symbols[j_idx]

    bins = np.arange(0.0, rmax + dr, dr)
    r = 0.5 * (bins[:-1] + bins[1:])
    shell_vol = 4.0 * np.pi * r**2 * dr

    g_out = {}
    counts = {}
    pair_defs = [("AlAl", "Al", "Al", n_al, n_al),
                 ("AlNi", "Al", "Ni", n_al, n_ni),
                 ("NiNi", "Ni", "Ni", n_ni, n_ni)]
    for label, ta, tb, na, nb in pair_defs:
        mask = (si == ta) & (sj == tb)
        hist, _ = np.histogram(d[mask], bins=bins)
        counts[label] = hist
        if na == 0 or nb == 0:
            g = np.zeros_like(r)
        else:
            with np.errstate(divide="ignore", invalid="ignore"):
                g = hist * volume / (na * nb * shell_vol)
            g = np.nan_to_num(g, nan=0.0, posinf=0.0)
        g_out[label] = g
    return r, g_out, counts, dict(n_Al=n_al, n_Ni=n_ni, natoms=natoms)


def first_shell(r, g, counts, n_a, search_min=PEAK_SEARCH_MIN, search_max=PEAK_SEARCH_MAX):
    mask = (r >= search_min) & (r <= search_max)
    if not np.any(mask) or n_a == 0:
        return None
    idxs = np.where(mask)[0]
    sub_g = g[idxs]
    if np.all(sub_g == 0):
        return None
    peak_local = int(np.argmax(sub_g))
    peak_idx = idxs[peak_local]
    peak_r = float(r[peak_idx])
    peak_g = float(g[peak_idx])

    dr_step = r[1] - r[0]
    max_idx = min(len(r) - 2, peak_idx + int(round(1.0 / dr_step)))
    shell_idx = None
    for k in range(peak_idx + 1, max_idx):
        if g[k] <= g[k - 1] and g[k] <= g[k + 1]:
            shell_idx = k
            break
    if shell_idx is None:
        shell_idx = max_idx
    shell_r = float(r[shell_idx])
    cn = float(np.sum(counts[:shell_idx + 1])) / n_a
    return dict(peak_r=peak_r, peak_g=peak_g, shell_r=shell_r, coordination_number=cn)


def process(phase, state, atoms, source_note):
    r, partials, counts, comp = partial_rdf(atoms)
    os.makedirs(OUT_DIR, exist_ok=True)
    shells = {}
    for label, na_key in (("AlAl", "n_Al"), ("AlNi", "n_Al"), ("NiNi", "n_Ni")):
        n_a = comp[na_key]
        shells[label] = first_shell(r, partials[label], counts[label], n_a)

    for label in ("AlAl", "AlNi", "NiNi"):
        csv_path = f"{OUT_DIR}/{phase}_{state}_{label}.csv"
        with open(csv_path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow([f"# Partial RDF g_{label}(r), phase={phase}, state={state}, "
                        f"natoms={comp['natoms']} (Al={comp['n_Al']}, Ni={comp['n_Ni']}), "
                        f"source={source_note}, rmax={RMAX}, dr={DR}"])
            w.writerow(["r_angstrom", "g_r"])
            for ri, gi in zip(r, partials[label]):
                w.writerow([f"{ri:.4f}", f"{gi:.6f}"])
    return comp, shells


def main():
    report = {}
    for phase in PHASES:
        report[phase] = {}
        dft_atoms = load_dft_relaxed(phase)
        comp, shells = process(phase, "0K_dft", dft_atoms,
                                "DFT relaxed primitive cell (chemical ground truth)")
        report[phase]["0K_dft"] = dict(comp=comp, shells=shells)
        print(f"[{phase}] 0K DFT: {comp}")
        for label, s in shells.items():
            print(f"    {label}: {s}")

        md_path, md_note = MD_ENDPOINT[phase]
        if os.path.exists(md_path):
            md_atoms = read_data_as_atoms(md_path)
            comp_md, shells_md = process(phase, "300K_md", md_atoms, md_note)
            report[phase]["300K_md"] = dict(comp=comp_md, shells=shells_md)
            print(f"[{phase}] 300K MD ({md_note}): {comp_md}")
            for label, s in shells_md.items():
                print(f"    {label}: {s}")
        else:
            report[phase]["300K_md"] = None
            print(f"[{phase}] 300K MD: MISSING ({md_path})")

    with open(f"{OUT_DIR}/partial_rdf_shell_report.json", "w") as fh:
        json.dump(report, fh, indent=2)
    print(f"\nWrote {OUT_DIR}/partial_rdf_shell_report.json")


if __name__ == "__main__":
    main()
