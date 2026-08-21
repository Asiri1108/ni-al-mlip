"""Shared helpers for Stage B: lattice parameters, volume/atom, spacegroup."""
import numpy as np
import spglib
from ase.io import read

DFT_PATH = "/workspace/ni_al/data/datasets/ni_al_combined227_dft.extxyz"
PHASES = ["AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3"]
ELEMENT_ORDER = ["Al", "Ni"]
SYMPREC = 1e-2  # loose enough to tolerate numerical relaxation noise, tight enough to distinguish real symmetry breaks


def load_dft_relaxed(phase):
    frames = read(DFT_PATH, index=":")
    by = {a.info.get("config_id"): a for a in frames}
    return by[f"{phase}_relaxed"].copy()


def cellpar_and_vpa(atoms):
    cellpar = np.asarray(atoms.cell.cellpar(), dtype=float)
    vpa = float(atoms.get_volume() / len(atoms))
    return cellpar, vpa


def spacegroup_of(atoms, symprec=SYMPREC):
    cell = (atoms.cell.array, atoms.get_scaled_positions(), atoms.get_atomic_numbers())
    ds = spglib.get_symmetry_dataset(cell, symprec=symprec)
    if ds is None:
        return None, None
    # spglib >= 2.0 returns an attribute-style dataset
    return str(ds.international), int(ds.number)


def pct_diff(pred, ref):
    return (np.asarray(pred, dtype=float) - np.asarray(ref, dtype=float)) / np.asarray(ref, dtype=float) * 100.0
