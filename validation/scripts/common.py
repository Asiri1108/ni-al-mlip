"""Shared paths, constants and helpers for the Ni-Al MACE validation."""
import os, json, hashlib
import numpy as np
from ase.io import read

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH = os.path.join(ROOT, "work", "archive", "ni_al")
DATA = os.path.join(ARCH, "data", "datasets")
MODELS = os.path.join(ARCH, "models")
RESULTS = os.path.join(ROOT, "results")
BASE_MODEL = os.path.join(ROOT, "work", "base", "MACE-matpes-pbe-omat-ft.model")

# QE/PBE elemental chemical potentials (configs/STEPB_ELEMENTAL_REFERENCES_STATUS.txt).
# These are the ONLY admissible references for formation energy in this project.
MU_AL = -537.46115182   # eV/atom, nspin=1, k=(24,24,24), relaxed a=4.038351 A
MU_NI = -4670.57345642  # eV/atom, nspin=2, start_mag=0.60, k=(22,22,22), relaxed a=3.517938 A

PHASES = ["Al3Ni", "Al3Ni2", "AlNi", "Al3Ni5", "AlNi3"]
X_NI = {"Al3Ni": 0.25, "Al3Ni2": 0.40, "AlNi": 0.50, "Al3Ni5": 0.625, "AlNi3": 0.75}

# Pre-registered thresholds, locked before any Phase 3 number was computed.
THRESHOLDS = {
    "seed_noise_floor_meV_atom": 0.43,
    "locked_acceptance_bar_meV_atom": 2.6183,
    "zero_shot_reference_meV_atom": 21.23,
    "force_mae_target_eV_A": 0.05,
    "relax_dabc_A": 0.05,
    "relax_dV_frac": 0.02,
}

FAMILY_ORDER = ["relaxed", "iso", "uniaxial", "biaxial", "ortho",
                "shear", "shear_rattle", "rattle", "volume_rattle"]


def family(config_type):
    """Map a config_type string onto one of the 9 deformation families."""
    c = config_type.lower()
    # order matters: the compound families must be tested before their substrings
    for f in ["volume_rattle", "shear_rattle", "biaxial", "uniaxial",
              "ortho", "shear", "rattle", "iso", "relaxed"]:
        if f in c:
            return f
    return c


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_dataset(tag="combined227"):
    """Return (atoms_list, split_map) for a dataset generation."""
    import glob
    allf = os.path.join(DATA, f"ni_al_{tag}_dft.extxyz")
    atoms = read(allf, ":")
    trf = glob.glob(os.path.join(DATA, f"ni_al_{tag}_train_*.extxyz"))
    vaf = glob.glob(os.path.join(DATA, f"ni_al_{tag}_validation_*.extxyz"))
    tr = {a.info["config_id"] for a in read(trf[0], ":")} if trf else set()
    va = {a.info["config_id"] for a in read(vaf[0], ":")} if vaf else set()
    split = {}
    for a in atoms:
        cid = a.info["config_id"]
        split[cid] = "TRAIN" if cid in tr else ("VALIDATION" if cid in va else "RESERVED")
    return atoms, split


def calc(model_path, dtype="float64"):
    from mace.calculators import MACECalculator
    return MACECalculator(model_paths=model_path, device="cpu", default_dtype=dtype)


def model_path(name):
    return os.path.join(MODELS, name, name + ".model")


def formation_energy(energy, symbols):
    """E_f per atom in eV, using QE elemental chemical potentials only."""
    n_al = sum(1 for s in symbols if s == "Al")
    n_ni = sum(1 for s in symbols if s == "Ni")
    n = n_al + n_ni
    return (energy - n_al * MU_AL - n_ni * MU_NI) / n
