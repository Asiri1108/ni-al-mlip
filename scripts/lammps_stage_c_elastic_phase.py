#!/usr/bin/env python3
"""Stage C worker: elastic constants for ONE phase via finite-difference
stress-strain, at that phase's OWN LAMMPS zero-stress relaxed cell (NOT the
DFT cell -- residual stress at the DFT cell would contaminate the Cij).

Method: relax (tri, same as Stage B) to get the zero-stress reference cell,
then for each of the 6 Voigt strain modes, apply +/-delta homogeneous strain
to (cell AND atoms), relax internal positions ONLY at fixed (strained) cell,
read off the resulting stress tensor. Central difference over +/-delta gives
one column of Cij per mode: C[i,j] = (sigma_i(+delta_j) - sigma_i(-delta_j))
/ (2*delta). A separate 0-strain evaluation is used only to check how much
of the +/- response is symmetric (linear, used) vs a nonzero mean (nonlinear
or residual-stress artifact, reported as a diagnostic).

Process isolation: one subprocess per phase (launched by
lammps_stage_c_run_all.py), matching Stage B -- lmp.finalize() is still
dropped (Kokkos::Cuda::finalize() segfault, Stage A). A single
lammps.lammps() instance is reused for all ~13 strain states within this
one process via `clear` + re-`read_data`, which is safe (no repeated
construction/teardown of the Kokkos-backed LAMMPS object).
"""
import json
import os
import sys

os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

import numpy as np
import torch
from ase import Atoms
from ase.io import write

sys.path.insert(0, os.path.dirname(__file__))
from lattice_compare_utils import load_dft_relaxed, cellpar_and_vpa, spacegroup_of, ELEMENT_ORDER

import lammps
import lammps.mliap

ROOT = "/workspace/ni_al"
MLIAP_MODEL = f"{ROOT}/models/al3ni_combined227_lora_v1/al3ni_combined227_lora_v1.model-mliap_lammps.pt"
RESULTS_DIR = f"{ROOT}/results/lammps_stage_c"
LOG_DIR = f"{ROOT}/logs/lammps_stage_c"
DELTA = 0.0075  # Voigt strain magnitude used for all finite differences (0.75%)

VOIGT_MODES = [1, 2, 3, 4, 5, 6]  # 1=xx 2=yy 3=zz 4=yz 5=xz 6=xy
BAR_TO_GPA = 1.0e-4


def owned_slice(arr, ids, natoms):
    expected = np.arange(1, natoms + 1)
    if not np.array_equal(ids[:natoms], expected):
        raise RuntimeError(f"owned-atom id layout unexpected: ids[:{natoms}]={ids[:natoms]}")
    return arr[:natoms]


def strain_matrix(mode, delta):
    eps = np.zeros((3, 3))
    if mode == 1:
        eps[0, 0] = delta
    elif mode == 2:
        eps[1, 1] = delta
    elif mode == 3:
        eps[2, 2] = delta
    elif mode == 4:
        eps[1, 2] = eps[2, 1] = delta / 2.0
    elif mode == 5:
        eps[0, 2] = eps[2, 0] = delta / 2.0
    elif mode == 6:
        eps[0, 1] = eps[1, 0] = delta / 2.0
    else:
        raise ValueError(mode)
    return eps


def apply_strain(atoms, eps):
    F = np.eye(3) + eps
    new_cell = atoms.cell.array @ F
    new_pos = atoms.get_positions() @ F
    out = Atoms(symbols=atoms.get_chemical_symbols(), positions=new_pos, cell=new_cell, pbc=True)
    return out


def setup_pair(lmp, unified):
    lammps.mliap.load_unified_kokkos(unified)
    lmp.commands_string(f"""
pair_style mliap unified EXISTS
pair_coeff * * {' '.join(ELEMENT_ORDER)}
neighbor 2.0 bin
neigh_modify every 1 delay 0 check yes
thermo 20
thermo_style custom step pe fmax pxx pyy pzz pxy pxz pyz
""")


def read_data_file(lmp, atoms, path):
    write(path, atoms, format="lammps-data", specorder=ELEMENT_ORDER, masses=True,
          atom_style="atomic", force_skew=True)
    lmp.commands_string(f"""
units metal
atom_style atomic
atom_modify sort 0 0.0
boundary p p p
read_data {path}
""")


def relax_full(lmp, atoms0, phase, unified):
    """tri box/relax + positions, same recipe as Stage B, to get the
    zero-stress reference cell. Returns the relaxed Atoms."""
    data_file = f"/tmp/stage_c_{phase}_base.data"
    read_data_file(lmp, atoms0, data_file)
    setup_pair(lmp, unified)
    lmp.commands_string("""
min_style cg
fix boxrelax all box/relax tri 0.0 vmax 0.001
minimize 0.0 1.0e-8 10000 100000
unfix boxrelax
""")
    natoms = len(atoms0)
    boxlo, boxhi, xy, yz, xz, *_ = lmp.extract_box()
    lx, ly, lz = boxhi[0] - boxlo[0], boxhi[1] - boxlo[1], boxhi[2] - boxlo[2]
    cell = np.array([[lx, 0.0, 0.0], [xy, ly, 0.0], [xz, yz, lz]])
    x_flat = np.array(lmp.numpy.extract_atom("x"), copy=True)
    ids = np.array(lmp.numpy.extract_atom("id"), copy=True)
    types = np.array(lmp.numpy.extract_atom("type"), copy=True)
    positions = owned_slice(x_flat, ids, natoms)
    atom_types = owned_slice(types, ids, natoms)
    symbols = [ELEMENT_ORDER[int(t) - 1] for t in atom_types]
    return Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)


def relax_positions_get_stress(lmp, atoms, phase, tag, unified):
    """Fixed cell (no box/relax), relax internal positions only, return the
    6 stress components in Voigt order (GPa, tension-positive: sigma=-P)."""
    data_file = f"/tmp/stage_c_{phase}_{tag}.data"
    lmp.command("clear")
    read_data_file(lmp, atoms, data_file)
    setup_pair(lmp, unified)
    lmp.commands_string("""
min_style cg
minimize 0.0 1.0e-10 10000 100000
""")
    fmax = lmp.get_thermo("fmax")
    p = np.array([lmp.get_thermo(k) for k in ("pxx", "pyy", "pzz", "pyz", "pxz", "pxy")])
    sigma = -p * BAR_TO_GPA  # Voigt order: 1=xx 2=yy 3=zz 4=yz 5=xz 6=xy
    return sigma, float(fmax)


def voigt_reuss_hill(C):
    C11, C22, C33 = C[0, 0], C[1, 1], C[2, 2]
    C12, C13, C23 = C[0, 1], C[0, 2], C[1, 2]
    C44, C55, C66 = C[3, 3], C[4, 4], C[5, 5]
    Kv = ((C11 + C22 + C33) + 2 * (C12 + C13 + C23)) / 9.0
    Gv = ((C11 + C22 + C33) - (C12 + C13 + C23) + 3 * (C44 + C55 + C66)) / 15.0
    S = np.linalg.inv(C)
    S11, S22, S33 = S[0, 0], S[1, 1], S[2, 2]
    S12, S13, S23 = S[0, 1], S[0, 2], S[1, 2]
    S44, S55, S66 = S[3, 3], S[4, 4], S[5, 5]
    Kr = 1.0 / ((S11 + S22 + S33) + 2 * (S12 + S13 + S23))
    Gr = 15.0 / (4 * (S11 + S22 + S33) - 4 * (S12 + S13 + S23) + 3 * (S44 + S55 + S66))
    K = (Kv + Kr) / 2.0
    G = (Gv + Gr) / 2.0
    E = 9 * K * G / (3 * K + G)
    nu = (3 * K - 2 * G) / (2 * (3 * K + G))
    AU = 5 * Gv / Gr + Kv / Kr - 6.0  # universal (log-free) anisotropy index, any symmetry
    return dict(Kv=Kv, Kr=Kr, K=K, Gv=Gv, Gr=Gr, G=G, E=E, nu=nu, universal_anisotropy_index=AU)


def main():
    phase = sys.argv[1]
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    atoms0 = load_dft_relaxed(phase)
    log_file = f"{LOG_DIR}/{phase}.log"

    lmp = lammps.lammps(cmdargs=[
        "-k", "on", "g", "1", "-sf", "kk", "-pk", "kokkos", "neigh", "half", "newton", "on",
        "-log", log_file, "-screen", "none",
    ])
    lammps.mliap.activate_mliappy_kokkos(lmp)
    unified = torch.load(MLIAP_MODEL, map_location="cpu")

    relaxed = relax_full(lmp, atoms0, phase, unified)
    base_cellpar, base_vpa = cellpar_and_vpa(relaxed)
    base_sg_symbol, base_sg_number = spacegroup_of(relaxed)

    ref_sigma, ref_fmax = relax_positions_get_stress(lmp, relaxed, phase, "ref", unified)

    sigma_plus = {}
    sigma_minus = {}
    fmax_by_state = {"ref": ref_fmax}
    for mode in VOIGT_MODES:
        for sign, bucket, tag in ((+1, sigma_plus, f"m{mode}p"), (-1, sigma_minus, f"m{mode}m")):
            eps = strain_matrix(mode, sign * DELTA)
            strained = apply_strain(relaxed, eps)
            sigma, fmax = relax_positions_get_stress(lmp, strained, phase, tag, unified)
            bucket[mode] = sigma
            fmax_by_state[tag] = fmax

    lmp.close()
    # deliberately no lmp.finalize() -- see module docstring

    C = np.zeros((6, 6))
    nonlinear_residual = np.zeros((6, 6))
    for j in VOIGT_MODES:
        col = (sigma_plus[j] - sigma_minus[j]) / (2 * DELTA)
        C[:, j - 1] = col
        nonlinear_residual[:, j - 1] = (sigma_plus[j] + sigma_minus[j]) / 2.0 - ref_sigma

    asymmetry = float(np.max(np.abs(C - C.T)))
    C_sym = (C + C.T) / 2.0
    eigvals = np.linalg.eigvalsh(C_sym)
    born_general_stable = bool(np.all(eigvals > 0))

    cubic = None
    if phase in ("AlNi", "AlNi3"):
        C11 = (C_sym[0, 0] + C_sym[1, 1] + C_sym[2, 2]) / 3.0
        C12 = (C_sym[0, 1] + C_sym[0, 2] + C_sym[1, 2]) / 3.0
        C44 = (C_sym[3, 3] + C_sym[4, 4] + C_sym[5, 5]) / 3.0
        cubic_spread_C11 = float(np.std([C_sym[0, 0], C_sym[1, 1], C_sym[2, 2]]))
        cubic_spread_C12 = float(np.std([C_sym[0, 1], C_sym[0, 2], C_sym[1, 2]]))
        cubic_spread_C44 = float(np.std([C_sym[3, 3], C_sym[4, 4], C_sym[5, 5]]))
        cond1 = C11 - C12 > 0
        cond2 = C11 + 2 * C12 > 0
        cond3 = C44 > 0
        zener = 2 * C44 / (C11 - C12) if (C11 - C12) != 0 else None
        cubic = dict(C11=C11, C12=C12, C44=C44,
                     symmetry_spread=dict(C11=cubic_spread_C11, C12=cubic_spread_C12, C44=cubic_spread_C44),
                     born_cubic_stable=bool(cond1 and cond2 and cond3),
                     cond_C11_minus_C12_gt0=bool(cond1), cond_C11_plus_2C12_gt0=bool(cond2), cond_C44_gt0=bool(cond3),
                     zener_ratio=zener)

    moduli = voigt_reuss_hill(C_sym)

    result = {
        "phase": phase,
        "natoms": len(relaxed),
        "delta_strain": DELTA,
        "base_relaxed_cellpar": base_cellpar.tolist(),
        "base_relaxed_volume_per_atom_A3": base_vpa,
        "base_relaxed_spacegroup": [base_sg_symbol, base_sg_number],
        "ref_state_stress_GPa": ref_sigma.tolist(),
        "ref_state_fmax_eV_per_A": ref_fmax,
        "fmax_by_state_eV_per_A": fmax_by_state,
        "Cij_GPa": C.tolist(),
        "Cij_symmetrized_GPa": C_sym.tolist(),
        "Cij_asymmetry_max_GPa": asymmetry,
        "nonlinear_residual_GPa": nonlinear_residual.tolist(),
        "nonlinear_residual_max_GPa": float(np.max(np.abs(nonlinear_residual))),
        "eigenvalues_GPa": eigvals.tolist(),
        "born_general_stable": born_general_stable,
        "cubic": cubic,
        "moduli_GPa": moduli,
        "geometry_note": (
            "Al3Ni5: computed at this model's OWN relaxed alpha=%.3f deg, NOT the DFT "
            "value (96.478 deg, see Stage B). Structurally different cell -- no direct "
            "apples-to-apples comparison exists against any DFT/literature Al3Ni5 elastic "
            "reference at the DFT geometry." % base_cellpar[3]
        ) if phase == "Al3Ni5" else None,
    }
    out_path = f"{RESULTS_DIR}/{phase}_elastic.json"
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k not in ("Cij_GPa",)}, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
