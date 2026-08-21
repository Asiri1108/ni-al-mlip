#!/usr/bin/env python3
"""Fills the Stage B structure-file gap for Al3Ni and Al3Ni5: Stage B/C/D
all recomputed this same zero-stress relax in-memory but never saved the
0 K relaxed PRIMITIVE cell to disk (only cellpar/vpa/spacegroup JSON
summaries exist in results/lammps_stage_b/). Also builds an Al3Ni5
supercell (0 K only, NO MD -- explicit instruction) for visual parity
with Stage D-2's AlNi/AlNi3/Al3Ni2 supercells.

Same relax recipe as Stage B/C/D/D2 (box/relax tri + minimize, pair_style
mliap unified, Kokkos build, Python-side model load -- the only
verified-working path; bare `lmp -in` cannot load this model). Both
phases done in ONE process via LAMMPS `clear`+`read_data` reuse (Stage
C/D2's already-proven pattern -- activate_mliappy_kokkos is per-process,
not re-called on `clear`), so lmp.finalize() is dropped once at exit
rather than per phase.
"""
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
STAGE_B_DIR = f"{ROOT}/results/lammps_stage_b"
STAGE_D2_DIR = f"{ROOT}/results/lammps_stage_d2"
LOG_DIR = f"{ROOT}/logs/lammps_stage_b"

# 8*3*3*2 = 144 atoms, target 100-150; (3,3,2) rather than a uniform NxNxN
# cube because 8 atoms has no cube factor landing in range (2^3=64 too
# small, 3^3=216 too big) -- chosen for a reasonably box-like supercell
# shape given Al3Ni5's cellpar (a=3.798, b=c=5.003 at this model's own
# relaxed alpha=98.28 deg).
AL3NI5_SUPER_REPLICATION = (3, 3, 2)


def owned_slice(arr, ids, natoms):
    expected = np.arange(1, natoms + 1)
    if not np.array_equal(ids[:natoms], expected):
        raise RuntimeError(f"owned-atom id layout unexpected: ids[:{natoms}]={ids[:natoms]}")
    return arr[:natoms]


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


def relax_primitive(lmp, atoms0, phase, unified):
    data_file = f"/tmp/stage_b_resave_{phase}.data"
    read_data_file(lmp, atoms0, data_file)
    setup_pair(lmp, unified)
    lmp.commands_string("""
min_style cg
fix boxrelax all box/relax tri 0.0 vmax 0.001
minimize 0.0 1.0e-8 10000 100000
unfix boxrelax
""")
    fmax = lmp.get_thermo("fmax")
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
    relaxed = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
    return relaxed, float(fmax)


def main():
    os.makedirs(STAGE_B_DIR, exist_ok=True)
    os.makedirs(STAGE_D2_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    log_file = f"{LOG_DIR}/resave_al3ni_al3ni5.log"
    lmp = lammps.lammps(cmdargs=[
        "-k", "on", "g", "1", "-sf", "kk", "-pk", "kokkos", "neigh", "half", "newton", "on",
        "-log", log_file, "-screen", "none",
    ])
    lammps.mliap.activate_mliappy_kokkos(lmp)
    unified = torch.load(MLIAP_MODEL, map_location="cpu")

    results = {}
    for i, phase in enumerate(["Al3Ni", "Al3Ni5"]):
        if i > 0:
            lmp.command("clear")  # Stage C/D2 pattern: clear+rebuild within one process
        atoms0 = load_dft_relaxed(phase)
        relaxed, fmax = relax_primitive(lmp, atoms0, phase, unified)
        cellpar, vpa = cellpar_and_vpa(relaxed)
        sg_symbol, sg_number = spacegroup_of(relaxed)
        print(f"[{phase}] primitive relax: fmax={fmax:.3e} eV/A  cellpar={cellpar.tolist()}  "
              f"vpa={vpa:.5f} A^3  spacegroup={sg_symbol} (#{sg_number})", flush=True)

        data_path = f"{STAGE_B_DIR}/{phase}_lammps_0K_primitive.data"
        extxyz_path = f"{STAGE_B_DIR}/{phase}_lammps_0K_primitive.extxyz"
        write(data_path, relaxed, format="lammps-data", specorder=ELEMENT_ORDER,
              masses=True, atom_style="atomic", force_skew=True)
        relaxed_out = relaxed.copy()
        relaxed_out.info["config_id"] = f"{phase}_lammps_0K_primitive"
        relaxed_out.info["source"] = "LAMMPS mliap unified (Kokkos), box/relax tri + minimize, this session"
        write(extxyz_path, relaxed_out, format="extxyz")
        print(f"  Wrote {data_path}\n  Wrote {extxyz_path}", flush=True)
        results[phase] = dict(relaxed=relaxed, fmax=fmax, cellpar=cellpar, vpa=vpa,
                               sg_symbol=sg_symbol, sg_number=sg_number)

    # Al3Ni5 supercell, 0 K only, NO MD -- replicate the just-relaxed
    # zero-stress primitive cell (translational symmetry -> exact
    # zero-stress supercell, same reasoning already used in Stage D-2).
    al3ni5_relaxed = results["Al3Ni5"]["relaxed"]
    nx, ny, nz = AL3NI5_SUPER_REPLICATION
    supercell = al3ni5_relaxed.repeat((nx, ny, nz))
    natoms = len(supercell)
    symbols = supercell.get_chemical_symbols()
    n_al = symbols.count("Al")
    n_ni = symbols.count("Ni")
    print(f"[Al3Ni5] supercell: {nx}x{ny}x{nz} of 8-atom primitive -> {natoms} atoms "
          f"({n_al} Al, {n_ni} Ni)", flush=True)

    super_data_path = f"{STAGE_D2_DIR}/Al3Ni5_supercell_0K.data"
    super_extxyz_path = f"{STAGE_D2_DIR}/Al3Ni5_supercell_0K.extxyz"
    write(super_data_path, supercell, format="lammps-data", specorder=ELEMENT_ORDER,
          masses=True, atom_style="atomic", force_skew=True)
    supercell_out = supercell.copy()
    supercell_out.info["config_id"] = "Al3Ni5_supercell_0K"
    supercell_out.info["source"] = (f"LAMMPS mliap unified (Kokkos) zero-stress primitive cell, "
                                     f"replicated {nx}x{ny}x{nz}, NO MD run on the supercell")
    write(super_extxyz_path, supercell_out, format="extxyz")
    print(f"  Wrote {super_data_path}\n  Wrote {super_extxyz_path}", flush=True)

    lmp.close()
    # deliberately no lmp.finalize() -- Kokkos::Cuda::finalize() teardown
    # segfault, see Stage A


if __name__ == "__main__":
    main()
