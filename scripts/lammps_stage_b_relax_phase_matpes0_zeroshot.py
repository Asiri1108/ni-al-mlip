#!/usr/bin/env python3
"""Stage B worker (ZERO-SHOT variant): relax ONE phase in LAMMPS (mliap
unified, Kokkos build) via `minimize` + `fix box/relax tri`, starting from
the DFT relaxed geometry -- using the zero-shot MACE-MATPES-PBE-0 foundation
checkpoint instead of the fine-tuned al3ni_combined227_lora_v1 model.

Exact same procedure as scripts/lammps_stage_b_relax_phase.py (that script's
docstring explains the process-isolation / no-lmp.finalize() rationale --
unchanged here). Only MLIAP_MODEL and output paths differ.
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
MLIAP_MODEL = f"{ROOT}/models/mace_matpes_pbe_0_zeroshot-mliap_lammps.pt"
RESULTS_DIR = f"{ROOT}/results/lammps_stage_b_matpes_pbe0_zeroshot"
LOG_DIR = f"{ROOT}/logs/lammps_stage_b_matpes_pbe0_zeroshot"


def owned_slice(arr, ids, natoms):
    expected = np.arange(1, natoms + 1)
    if not np.array_equal(ids[:natoms], expected):
        raise RuntimeError(f"owned-atom id layout unexpected: ids[:{natoms}]={ids[:natoms]}")
    return arr[:natoms]


def main():
    phase = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "tri"
    assert mode in ("tri", "aniso")
    suffix = "" if mode == "tri" else f"_{mode}"
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    atoms0 = load_dft_relaxed(phase)
    natoms = len(atoms0)
    data_file = f"/tmp/stage_b_matpes0_zeroshot_{phase}{suffix}.data"
    write(data_file, atoms0, format="lammps-data", specorder=ELEMENT_ORDER,
          masses=True, atom_style="atomic", force_skew=True)

    log_file = f"{LOG_DIR}/{phase}{suffix}.log"

    lmp = lammps.lammps(cmdargs=[
        "-k", "on", "g", "1", "-sf", "kk", "-pk", "kokkos", "neigh", "half", "newton", "on",
        "-log", log_file, "-screen", "none",
    ])
    lammps.mliap.activate_mliappy_kokkos(lmp)

    lmp.commands_string(f"""
units metal
atom_style atomic
atom_modify sort 0 0.0
boundary p p p
read_data {data_file}
""")

    unified = torch.load(MLIAP_MODEL, map_location="cpu")
    lammps.mliap.load_unified_kokkos(unified)

    lmp.commands_string(f"""
pair_style mliap unified EXISTS
pair_coeff * * {' '.join(ELEMENT_ORDER)}
neighbor 2.0 bin
neigh_modify every 1 delay 0 check yes
thermo 10
thermo_style custom step pe fmax fnorm press vol
min_style cg
fix boxrelax all box/relax {mode} 0.0 vmax 0.001
minimize 0.0 1.0e-8 10000 100000
""")

    e_final = lmp.get_thermo("pe")
    fmax_final = lmp.get_thermo("fmax")
    press_final = lmp.get_thermo("press")

    boxlo, boxhi, xy, yz, xz, periodicity, box_change = lmp.extract_box()
    lx = boxhi[0] - boxlo[0]
    ly = boxhi[1] - boxlo[1]
    lz = boxhi[2] - boxlo[2]
    cell = np.array([
        [lx, 0.0, 0.0],
        [xy, ly, 0.0],
        [xz, yz, lz],
    ])

    x_flat = np.array(lmp.numpy.extract_atom("x"), copy=True)
    ids = np.array(lmp.numpy.extract_atom("id"), copy=True)
    types = np.array(lmp.numpy.extract_atom("type"), copy=True)
    positions = owned_slice(x_flat, ids, natoms)
    atom_types = owned_slice(types, ids, natoms)
    symbols = [ELEMENT_ORDER[int(t) - 1] for t in atom_types]

    lmp.close()
    # deliberately no lmp.finalize() -- see lammps_stage_b_relax_phase.py docstring

    final_atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
    cellpar, vpa = cellpar_and_vpa(final_atoms)
    sg_symbol, sg_number = spacegroup_of(final_atoms)

    stopping_criterion = "UNKNOWN (not found in log)"
    try:
        with open(log_file) as fh:
            for line in fh:
                if line.strip().startswith("Stopping criterion"):
                    stopping_criterion = line.strip()
                    break
    except FileNotFoundError:
        pass

    result = {
        "phase": phase,
        "mode": mode,
        "model": "MACE-MATPES-PBE-0 (zero-shot foundation checkpoint)",
        "natoms": natoms,
        "energy_eV": float(e_final),
        "fmax_final_eV_per_A": float(fmax_final),
        "press_final_bar": float(press_final),
        "stopping_criterion": stopping_criterion,
        "cellpar": cellpar.tolist(),
        "volume_per_atom_A3": vpa,
        "spacegroup_symbol": sg_symbol,
        "spacegroup_number": sg_number,
    }
    out_path = f"{RESULTS_DIR}/{phase}_lammps{suffix}.json"
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps(result, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
