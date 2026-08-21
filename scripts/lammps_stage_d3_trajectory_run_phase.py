#!/usr/bin/env python3
"""Stage D-3 worker: ONE supercell phase's NPT trajectory run WITH dump
output for OVITO animation (pair_style mliap unified, Kokkos build).
Single-phase, single-process, launched fresh per phase by
lammps_stage_d3_trajectory_run_all.py -- lmp.finalize() still dropped
(Kokkos::Cuda::finalize() vs torch+cupy's live CUDA contexts, Stage A).

Starts directly from an existing 0 K relaxed SUPERCELL data file (no
re-relax needed): AlNi's (Stage D-2, results/lammps_stage_d2/
AlNi_supercell_0K.data) and Al3Ni5's (this session's structure-gap fill,
results/lammps_stage_d2/Al3Ni5_supercell_0K.data) are both already this
model's own zero-stress supercell, written by this project's fixed
write()/specorder=["Al","Ni"] convention, so read_data can consume them
directly -- no ASE round-trip needed for the starting structure.

Single-stage 15 ps NPT @ 300 K, 1 fs (same protocol as Stage D-2), full
triclinic barostat, PLUS a `dump ... id element xu yu zu` trajectory
(unwrapped coordinates, real element names) every DUMP_EVERY steps for
OVITO animation -- see scripts/in.npt_trajectory.

Writes results/lammps_stage_d3/<phase>_summary.json and the dump file
results/lammps_stage_d3/<phase>_trajectory.dump on success. A missing
summary JSON means the phase did not complete (same convention as
Stage B/C/D/D2).
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
from lattice_compare_utils import cellpar_and_vpa, spacegroup_of, ELEMENT_ORDER

import lammps
import lammps.mliap

ROOT = "/workspace/ni_al"
MLIAP_MODEL = f"{ROOT}/models/al3ni_combined227_lora_v1/al3ni_combined227_lora_v1.model-mliap_lammps.pt"
STAGE_D2_DIR = f"{ROOT}/results/lammps_stage_d2"
RESULTS_DIR = f"{ROOT}/results/lammps_stage_d3"
LOG_DIR = f"{ROOT}/logs/lammps_stage_d3"
SCRIPT_DIR = os.path.dirname(__file__)

STARTING_DATA = {
    "AlNi": f"{STAGE_D2_DIR}/AlNi_supercell_0K.data",
    "Al3Ni5": f"{STAGE_D2_DIR}/Al3Ni5_supercell_0K.data",
    "Al3Ni": f"{STAGE_D2_DIR}/Al3Ni_supercell_0K.data",
}

TEMP_K = 300.0
SEED = 20260819
TDAMP_PS = 0.1
PDAMP_PS = 1.0
PRESSURE_BAR = 0.0
TIMESTEP_PS = 0.001
NPT_PS = 15.0
NPT_STEPS = round(NPT_PS / TIMESTEP_PS)
THERMO_EVERY = 25
DUMP_EVERY = 100  # -> ~150 frames over 15 ps


def owned_slice(arr, ids, natoms):
    expected = np.arange(1, natoms + 1)
    if not np.array_equal(ids[:natoms], expected):
        raise RuntimeError(f"owned-atom id layout unexpected: ids[:{natoms}]={ids[:natoms]}")
    return arr[:natoms]


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


def extract_state(lmp, natoms):
    boxlo, boxhi, xy, yz, xz, *_ = lmp.extract_box()
    lx, ly, lz = boxhi[0] - boxlo[0], boxhi[1] - boxlo[1], boxhi[2] - boxlo[2]
    cell = np.array([[lx, 0.0, 0.0], [xy, ly, 0.0], [xz, yz, lz]])
    x_flat = np.array(lmp.numpy.extract_atom("x"), copy=True)
    ids = np.array(lmp.numpy.extract_atom("id"), copy=True)
    types = np.array(lmp.numpy.extract_atom("type"), copy=True)
    positions = owned_slice(x_flat, ids, natoms)
    atom_types = owned_slice(types, ids, natoms)
    symbols = [ELEMENT_ORDER[int(t) - 1] for t in atom_types]
    atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
    cellpar, vpa = cellpar_and_vpa(atoms)
    sg_symbol, sg_number = spacegroup_of(atoms)
    return {
        "temp_K": float(lmp.get_thermo("temp")),
        "pe_eV": float(lmp.get_thermo("pe")),
        "press_bar": float(lmp.get_thermo("press")),
        "cellpar": cellpar.tolist(),
        "volume_per_atom_A3": vpa,
        "spacegroup_symbol": sg_symbol,
        "spacegroup_number": sg_number,
    }


def main():
    phase = sys.argv[1]
    if phase not in STARTING_DATA:
        raise SystemExit(f"phase must be one of {list(STARTING_DATA)}, got {phase}")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    starting_data = STARTING_DATA[phase]
    if not os.path.exists(starting_data):
        raise SystemExit(f"missing starting structure {starting_data}")

    log_file = f"{LOG_DIR}/{phase}.log"
    lmp = lammps.lammps(cmdargs=[
        "-k", "on", "g", "1", "-sf", "kk", "-pk", "kokkos", "neigh", "half", "newton", "on",
        "-log", log_file, "-screen", "none",
    ])
    lammps.mliap.activate_mliappy_kokkos(lmp)
    unified = torch.load(MLIAP_MODEL, map_location="cpu")

    lmp.commands_string(f"""
units metal
atom_style atomic
atom_modify sort 0 0.0
boundary p p p
read_data {starting_data}
""")
    natoms = lmp.get_natoms()
    setup_pair(lmp, unified)
    print(f"[{phase}] loaded {starting_data}: {natoms} atoms", flush=True)

    dump_file = f"{RESULTS_DIR}/{phase}_trajectory.dump"
    final_data = f"{RESULTS_DIR}/{phase}_post_npt.data"
    lmp.commands_string(f"""
variable temp equal {TEMP_K}
variable seed equal {SEED}
variable tdamp equal {TDAMP_PS}
variable pdamp equal {PDAMP_PS}
variable pressure equal {PRESSURE_BAR}
variable npt_steps equal {NPT_STEPS}
variable thermo_every equal {THERMO_EVERY}
variable dump_every equal {DUMP_EVERY}
variable dump_file string {dump_file}
variable final_data string {final_data}
""")

    traj_in = f"{SCRIPT_DIR}/in.npt_trajectory"
    lmp.file(traj_in)
    post_npt = extract_state(lmp, natoms)
    print(f"[{phase}] post-NPT: T={post_npt['temp_K']:.1f} K  cellpar={post_npt['cellpar']}", flush=True)

    lmp.close()
    # deliberately no lmp.finalize() -- see Stage A

    n_frames_expected = NPT_STEPS // DUMP_EVERY + 1  # +1 for step 0
    dump_size_bytes = os.path.getsize(dump_file) if os.path.exists(dump_file) else None

    result = {
        "phase": phase, "natoms": natoms, "starting_data": starting_data,
        "protocol": {
            "temp_K": TEMP_K, "seed": SEED, "tdamp_ps": TDAMP_PS, "pdamp_ps": PDAMP_PS,
            "pressure_bar": PRESSURE_BAR, "timestep_ps": TIMESTEP_PS,
            "npt_steps": NPT_STEPS, "thermo_every": THERMO_EVERY, "dump_every": DUMP_EVERY,
        },
        "n_frames_expected": n_frames_expected,
        "dump_file": dump_file,
        "dump_size_bytes": dump_size_bytes,
        "post_npt": post_npt,
        "log_file": log_file,
    }
    out_path = f"{RESULTS_DIR}/{phase}_summary.json"
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps(result, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
