#!/usr/bin/env python3
"""Fills the OVITO-bundle structure-file gap for the MACE-MATPES-PBE-0
zero-shot Stage B relaxation: that run (scripts/lammps_stage_b_relax_phase_matpes0_zeroshot.py)
saved cellpar/vpa/spacegroup JSON summaries to results/lammps_stage_b_matpes_pbe0_zeroshot/
but never wrote the relaxed atomic structures to disk. Re-relaxes all 5
phases (same recipe, same model, deterministic minimize -- reproduces the
same cellpar/energy already on record) and writes PRIMITIVE-cell
extxyz+data pairs to results/ovito_export/lammps_0K_zeroshot/, all 5
directly atom-count-comparable to dft/ (unlike the fine-tuned lammps_0K/,
where only Al3Ni/Al3Ni5 are primitive).

One LAMMPS process, clear+read_data per phase (Stage C/D2/resave pattern --
activate_mliappy_kokkos is per-process, not per phase).
"""
import os
import sys

os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

import numpy as np
import torch
from ase import Atoms
from ase.io import write

sys.path.insert(0, os.path.dirname(__file__))
from lattice_compare_utils import load_dft_relaxed, cellpar_and_vpa, spacegroup_of, ELEMENT_ORDER, PHASES

import lammps
import lammps.mliap

ROOT = "/workspace/ni_al"
MLIAP_MODEL = f"{ROOT}/models/mace_matpes_pbe_0_zeroshot-mliap_lammps.pt"
OUT_DIR = f"{ROOT}/results/ovito_export/lammps_0K_zeroshot"
LOG_DIR = f"{ROOT}/logs/lammps_stage_b_matpes_pbe0_zeroshot"


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
    data_file = f"/tmp/save_0K_zeroshot_{phase}.data"
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
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    log_file = f"{LOG_DIR}/resave_zeroshot_5phase.log"
    lmp = lammps.lammps(cmdargs=[
        "-k", "on", "g", "1", "-sf", "kk", "-pk", "kokkos", "neigh", "half", "newton", "on",
        "-log", log_file, "-screen", "none",
    ])
    lammps.mliap.activate_mliappy_kokkos(lmp)
    unified = torch.load(MLIAP_MODEL, map_location="cpu")

    for i, phase in enumerate(PHASES):
        if i > 0:
            lmp.command("clear")
        atoms0 = load_dft_relaxed(phase)
        relaxed, fmax = relax_primitive(lmp, atoms0, phase, unified)
        cellpar, vpa = cellpar_and_vpa(relaxed)
        sg_symbol, sg_number = spacegroup_of(relaxed)
        print(f"[{phase}] primitive relax: fmax={fmax:.3e} eV/A  cellpar={cellpar.tolist()}  "
              f"vpa={vpa:.5f} A^3  spacegroup={sg_symbol} (#{sg_number})", flush=True)

        data_path = f"{OUT_DIR}/{phase}_lammps_0K_zeroshot_primitive.data"
        extxyz_path = f"{OUT_DIR}/{phase}_lammps_0K_zeroshot_primitive.extxyz"
        write(data_path, relaxed, format="lammps-data", specorder=ELEMENT_ORDER,
              masses=True, atom_style="atomic", force_skew=True)
        relaxed_out = relaxed.copy()
        relaxed_out.info["config_id"] = f"{phase}_lammps_0K_zeroshot_primitive"
        relaxed_out.info["phase"] = phase
        relaxed_out.info["source"] = ("LAMMPS mliap unified (Kokkos), box/relax tri + minimize, "
                                       "MACE-MATPES-PBE-0 ZERO-SHOT foundation checkpoint, PRIMITIVE cell, "
                                       "directly atom-count-comparable to the dft/ entry for this phase")
        write(extxyz_path, relaxed_out, format="extxyz")
        print(f"  Wrote {data_path}\n  Wrote {extxyz_path}", flush=True)

    lmp.close()
    # deliberately no lmp.finalize() -- Kokkos::Cuda::finalize() teardown segfault, see Stage A


if __name__ == "__main__":
    main()
