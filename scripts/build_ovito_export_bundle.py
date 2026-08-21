#!/usr/bin/env python3
"""Assembles results/ovito_export/ from existing structure/trajectory
files produced across Stage B/C/D/D2/D3. Read-only w.r.t. LAMMPS/torch --
pure file conversion (ASE) + RDF computation (ASE neighbor_list) + README
generation. No LAMMPS instance is created here.

Layout:
  dft/           5 DFT-relaxed primitive cells (from the combined227 DFT
                 dataset's *_relaxed configs)
  lammps_0K/     5 LAMMPS zero-stress relaxed cells -- Al3Ni/Al3Ni5 as
                 PRIMITIVE cells (this session's structure-gap fill,
                 directly atom-count-comparable to dft/), AlNi/AlNi3/
                 Al3Ni2 as SUPERCELLS (Stage D-2's existing
                 supercell_0K.data -- NOT atom-count-comparable to dft/,
                 filename-tagged `_supercell` to make this unambiguous
                 rather than relying on README prose alone)
  md_endpoints/  Stage D's 5-phase post_nvt/post_npt primitive-cell
                 snapshots + Stage D-2's 3-phase post_npt supercell
                 snapshots (single frames, NOT trajectories -- no dump
                 command was ever issued in Stage D/D-2)
  supercells/    the 4 pre-existing 0 K supercells (Stage D-2's
                 AlNi/AlNi3/Al3Ni2 + this session's new Al3Ni5)
  trajectories/  Stage D-3's dump files (assembled separately once that
                 background run completes -- not handled by this script)
  rdf/           g(r) CSV per phase, computed from the DFT-relaxed
                 primitive cell (ASE neighbor_list, PBC-correct regardless
                 of cutoff vs cell size -- no supercell needed for a
                 methodologically valid RDF)

Every LAMMPS .data structure is also converted to extxyz (real chemical
symbols via this project's fixed ELEMENT_ORDER=["Al","Ni"] Z-of-type
mapping, not just numeric LAMMPS types) -- this is the reliability point
the task called out: raw .data files require exactly this mapping to be
right, extxyz carries it natively once converted.
"""
import csv
import json
import os
import sys

import numpy as np
from ase.io import read, write

sys.path.insert(0, os.path.dirname(__file__))
from lattice_compare_utils import load_dft_relaxed, cellpar_and_vpa, spacegroup_of, PHASES, ELEMENT_ORDER

ROOT = "/workspace/ni_al"
EXPORT_DIR = f"{ROOT}/results/ovito_export"
Z_OF_TYPE = {1: 13, 2: 28}  # Al=13, Ni=28 -- matches ELEMENT_ORDER=["Al","Ni"] everywhere in this project

STAGE_B_DIR = f"{ROOT}/results/lammps_stage_b"
STAGE_D_DIR = f"{ROOT}/results/lammps_stage_d"
STAGE_D2_DIR = f"{ROOT}/results/lammps_stage_d2"

manifest = []  # rows for README table


def read_data_as_atoms(path):
    atoms = read(path, format="lammps-data", Z_of_type=Z_OF_TYPE, style="atomic")
    return atoms


def write_pair(atoms, out_dir, basename, source_note, from_data_path=None):
    """Writes <basename>.extxyz always; also copies/keeps <basename>.data
    if from_data_path is given (i.e. a LAMMPS .data original exists)."""
    os.makedirs(out_dir, exist_ok=True)
    extxyz_path = f"{out_dir}/{basename}.extxyz"
    out_atoms = atoms.copy()
    out_atoms.info["config_id"] = basename
    out_atoms.info["source"] = source_note
    write(extxyz_path, out_atoms, format="extxyz")

    data_path = None
    if from_data_path is not None and os.path.exists(from_data_path):
        data_path = f"{out_dir}/{basename}.data"
        if os.path.abspath(from_data_path) != os.path.abspath(data_path):
            with open(from_data_path, "rb") as src, open(data_path, "wb") as dst:
                dst.write(src.read())
    return extxyz_path, data_path


def add_manifest_row(directory, basename, phase, state, atoms, extxyz_path, data_path, note=""):
    cellpar, vpa = cellpar_and_vpa(atoms)
    manifest.append({
        "directory": directory, "basename": basename, "phase": phase, "state": state,
        "natoms": len(atoms), "cellpar": cellpar.tolist(), "vol_per_atom_A3": vpa,
        "extxyz": os.path.basename(extxyz_path) if extxyz_path else None,
        "data": os.path.basename(data_path) if data_path else None,
        "note": note,
    })


def build_dft():
    out_dir = f"{EXPORT_DIR}/dft"
    for phase in PHASES:
        atoms = load_dft_relaxed(phase)
        basename = f"{phase}_dft_relaxed"
        extxyz_path, _ = write_pair(atoms, out_dir, basename,
                                     "DFT (QE 7.6, PBE) relaxed reference cell, "
                                     "data/datasets/ni_al_combined227_dft.extxyz")
        add_manifest_row("dft", basename, phase, "DFT relaxed (0 K)", atoms, extxyz_path, None)


def build_lammps_0K():
    out_dir = f"{EXPORT_DIR}/lammps_0K"
    # Al3Ni, Al3Ni5: primitive cells, freshly saved this session, directly
    # atom-count-comparable to dft/.
    for phase in ["Al3Ni", "Al3Ni5"]:
        data_path = f"{STAGE_B_DIR}/{phase}_lammps_0K_primitive.data"
        atoms = read_data_as_atoms(data_path)
        basename = f"{phase}_lammps_0K_primitive"
        extxyz_path, data_out = write_pair(
            atoms, out_dir, basename,
            "LAMMPS mliap unified (Kokkos), box/relax tri + minimize, PRIMITIVE cell, "
            "this session -- directly atom-count-comparable to the dft/ entry for this phase",
            from_data_path=data_path)
        add_manifest_row("lammps_0K", basename, phase, "LAMMPS 0K relaxed (primitive)",
                          atoms, extxyz_path, data_out,
                          note="DIRECTLY comparable to dft/ (same atom count, primitive cell)")
    # AlNi, AlNi3, Al3Ni2: Stage D-2's existing SUPERCELLS -- filename-tagged
    # so the atom-count mismatch vs dft/ is unambiguous, not README-only.
    for phase in ["AlNi", "AlNi3", "Al3Ni2"]:
        data_path = f"{STAGE_D2_DIR}/{phase}_supercell_0K.data"
        atoms = read_data_as_atoms(data_path)
        basename = f"{phase}_lammps_0K_supercell"
        extxyz_path, data_out = write_pair(
            atoms, out_dir, basename,
            "LAMMPS mliap unified (Kokkos), Stage D-2 zero-stress SUPERCELL (0 K, pre-MD) -- "
            "NOT atom-count-comparable to the dft/ entry for this phase (different size); "
            "compare lattice parameters/symmetry only, not a literal side-by-side",
            from_data_path=data_path)
        add_manifest_row("lammps_0K", basename, phase, "LAMMPS 0K relaxed (supercell)",
                          atoms, extxyz_path, data_out,
                          note="NOT directly comparable to dft/ (supercell, different atom count "
                               "-- geometry/symmetry comparison only)")


def build_md_endpoints():
    out_dir = f"{EXPORT_DIR}/md_endpoints"
    for phase in PHASES:
        for stage_tag, fname, state in (
            ("post_nvt", f"{STAGE_D_DIR}/{phase}_post_nvt.data", "300K NVT endpoint (t=15ps, primitive)"),
            ("post_npt", f"{STAGE_D_DIR}/{phase}_post_npt.data", "300K NPT endpoint (t=30ps, primitive)"),
        ):
            if not os.path.exists(fname):
                continue
            atoms = read_data_as_atoms(fname)
            basename = f"{phase}_stageD_{stage_tag}"
            extxyz_path, data_out = write_pair(
                atoms, out_dir, basename,
                f"Stage D primitive-cell MD endpoint ({state}), 300K/1fs, mliap unified Kokkos",
                from_data_path=fname)
            add_manifest_row("md_endpoints", basename, phase, state, atoms, extxyz_path, data_out)

    for phase in ["AlNi", "AlNi3", "Al3Ni2"]:
        fname = f"{STAGE_D2_DIR}/{phase}_post_npt.data"
        if not os.path.exists(fname):
            continue
        atoms = read_data_as_atoms(fname)
        basename = f"{phase}_stageD2_post_npt_supercell"
        extxyz_path, data_out = write_pair(
            atoms, out_dir, basename,
            "Stage D-2 supercell MD endpoint (300K NPT, t=15ps), mliap unified Kokkos",
            from_data_path=fname)
        add_manifest_row("md_endpoints", basename, phase, "300K NPT endpoint (t=15ps, supercell)",
                          atoms, extxyz_path, data_out)


def build_supercells():
    out_dir = f"{EXPORT_DIR}/supercells"
    sources = {
        "AlNi": f"{STAGE_D2_DIR}/AlNi_supercell_0K.data",
        "AlNi3": f"{STAGE_D2_DIR}/AlNi3_supercell_0K.data",
        "Al3Ni2": f"{STAGE_D2_DIR}/Al3Ni2_supercell_0K.data",
        "Al3Ni5": f"{STAGE_D2_DIR}/Al3Ni5_supercell_0K.data",
        "Al3Ni": f"{STAGE_D2_DIR}/Al3Ni_supercell_0K.data",
    }
    for phase, fname in sources.items():
        if not os.path.exists(fname):
            print(f"WARNING: missing {fname}, skipping supercells/{phase}", file=sys.stderr)
            continue
        atoms = read_data_as_atoms(fname)
        basename = f"{phase}_supercell_0K"
        extxyz_path, data_out = write_pair(
            atoms, out_dir, basename,
            "LAMMPS mliap unified (Kokkos) zero-stress supercell, 0 K, NO MD run",
            from_data_path=fname)
        add_manifest_row("supercells", basename, phase, "LAMMPS 0K relaxed (supercell)",
                          atoms, extxyz_path, data_out)


def compute_rdf(atoms, rmax=10.0, dr=0.05):
    from ase.neighborlist import neighbor_list
    natoms = len(atoms)
    volume = atoms.get_volume()
    density = natoms / volume
    i_idx, j_idx, d = neighbor_list("ijd", atoms, rmax)
    bins = np.arange(0.0, rmax + dr, dr)
    hist, edges = np.histogram(d, bins=bins)
    r = 0.5 * (edges[:-1] + edges[1:])
    shell_vol = 4.0 * np.pi * r**2 * dr
    with np.errstate(divide="ignore", invalid="ignore"):
        g = hist / (shell_vol * density * natoms)
    g = np.nan_to_num(g, nan=0.0, posinf=0.0)
    return r, g


def build_rdf():
    out_dir = f"{EXPORT_DIR}/rdf"
    os.makedirs(out_dir, exist_ok=True)
    for phase in PHASES:
        atoms = load_dft_relaxed(phase)
        r, g = compute_rdf(atoms)
        csv_path = f"{out_dir}/{phase}_rdf.csv"
        with open(csv_path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["# RDF computed from DFT-relaxed primitive cell (data/datasets/"
                        "ni_al_combined227_dft.extxyz, config_id={}_relaxed), total "
                        "(all-species) g(r), rmax=10.0 A, dr=0.05 A, "
                        "ASE neighbor_list (PBC-correct regardless of cutoff vs cell size)".format(phase)])
            w.writerow(["r_angstrom", "g_r"])
            for ri, gi in zip(r, g):
                w.writerow([f"{ri:.4f}", f"{gi:.6f}"])
        print(f"Wrote {csv_path}  ({len(atoms)} atoms, first peak near "
              f"r={r[np.argmax(g[:100])]:.3f} A)")


def write_manifest_json():
    with open(f"{EXPORT_DIR}/manifest.json", "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"Wrote {EXPORT_DIR}/manifest.json ({len(manifest)} entries)")


def main():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    build_dft()
    build_lammps_0K()
    build_md_endpoints()
    build_supercells()
    build_rdf()
    write_manifest_json()
    print(f"\n{len(manifest)} structure entries assembled (trajectories/ handled separately)")


if __name__ == "__main__":
    main()
