#!/usr/bin/env python3
"""Stage D-2 worker: ONE small-cell phase's supercell NPT MD (pair_style
mliap unified, Kokkos build). Single-phase, single-process, launched fresh
per phase by lammps_stage_d2_run_all.py -- lmp.finalize() still dropped
(Kokkos::Cuda::finalize() vs torch+cupy's live CUDA contexts, Stage A).

Why a supercell: Stage D found AlNi (2 atoms), AlNi3 (4), and Al3Ni2 (5)
too small for the per-phase beta/gamma drift numbers to carry real
statistical weight -- AlNi's instantaneous NVT temperature swung ~1-1140 K
sample-to-sample at only 3 degrees of freedom (see
configs/LAMMPS_STAGE_D_MD_STABILITY_STATUS.txt and Section 8 of
configs/project_knowledge.md). Building ~100-200 atom supercells brings
these 3 phases to the same statistical footing as Al3Ni5 (8 atoms, Stage
D's only phase deemed to already give a meaningful shear number).

Sequence, all within ONE lammps.lammps() instance/process:
  1. relax the PRIMITIVE cell to this model's own zero-stress reference
     (relax_primitive(), identical recipe to Stage B/C/D) -- NOT the
     supercell itself: a zero-stress primitive cell replicates to an
     exact zero-stress supercell by translational symmetry, so relaxing
     at supercell scale would be redundant and give an identical answer
     up to floating-point noise, at much higher cost.
  2. build the supercell via ASE Atoms.repeat() using REPLICATION[phase]
  3. `clear` + fresh read_data + pair setup on the SUPERCELL -- the
     primitive-cell LAMMPS state from step 1 cannot be resized in place.
     This clear-then-rebuild-within-the-same-process pattern is exactly
     Stage C's already-verified-working pattern (13 strained states per
     phase, all via clear+read_data+setup_pair, no re-call of
     activate_mliappy_kokkos needed -- that registration is per-process,
     not per-box).
  4. single-stage 15 ps NPT @ 300 K (no separate NVT stage -- explicit
     Stage D-2 instruction), full triclinic barostat (`tri`), with
     per-species (Al vs Ni) MSD tracked via `compute msd` so a rising MSD
     (diffusion/melting) can be told apart from ordinary vibration --
     see scripts/in.npt_stability_supercell.

Writes results/lammps_stage_d2/<phase>_summary.json on success. Writing
nothing on failure is deliberate, same convention as Stage B/C/D: a
missing summary JSON means this phase did not complete, unambiguous
regardless of how it failed. The log (flushed every thermo line) survives
any crash for post-mortem.
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
RESULTS_DIR = f"{ROOT}/results/lammps_stage_d2"
LOG_DIR = f"{ROOT}/logs/lammps_stage_d2"
SCRIPT_DIR = os.path.dirname(__file__)

# Replication factors, chosen to land each supercell's atom count in
# [100, 200]: AlNi 2*4^3=128, AlNi3 4*3^3=108, Al3Ni2 5*3^3=135.
REPLICATION = {"AlNi": (4, 4, 4), "AlNi3": (3, 3, 3), "Al3Ni2": (3, 3, 3)}

TEMP_K = 300.0
SEED = 20260819
TDAMP_PS = 0.1
PDAMP_PS = 1.0
PRESSURE_BAR = 0.0
TIMESTEP_PS = 0.001
NPT_PS = 15.0
NPT_STEPS = round(NPT_PS / TIMESTEP_PS)
THERMO_EVERY = 25


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
    """Same recipe as Stage B/C/D: tri box/relax + positions on the
    PRIMITIVE cell to get this model's own zero-stress reference."""
    data_file = f"/tmp/stage_d2_{phase}_primitive.data"
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
    if phase not in REPLICATION:
        raise SystemExit(f"phase must be one of {list(REPLICATION)}, got {phase}")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    atoms0 = load_dft_relaxed(phase)
    n_primitive = len(atoms0)
    nx, ny, nz = REPLICATION[phase]

    log_file = f"{LOG_DIR}/{phase}.log"
    lmp = lammps.lammps(cmdargs=[
        "-k", "on", "g", "1", "-sf", "kk", "-pk", "kokkos", "neigh", "half", "newton", "on",
        "-log", log_file, "-screen", "none",
    ])
    lammps.mliap.activate_mliappy_kokkos(lmp)
    unified = torch.load(MLIAP_MODEL, map_location="cpu")

    relaxed_primitive, relax_fmax = relax_primitive(lmp, atoms0, phase, unified)
    primitive_cellpar, primitive_vpa = cellpar_and_vpa(relaxed_primitive)
    print(f"[{phase}] primitive relax: fmax={relax_fmax:.3e} eV/A  "
          f"cellpar={primitive_cellpar.tolist()}  vpa={primitive_vpa:.5f} A^3", flush=True)

    supercell = relaxed_primitive.repeat((nx, ny, nz))
    natoms = len(supercell)
    symbols = supercell.get_chemical_symbols()
    n_al0 = symbols.count("Al")
    n_ni0 = symbols.count("Ni")
    print(f"[{phase}] supercell: {nx}x{ny}x{nz} of {n_primitive}-atom primitive -> "
          f"{natoms} atoms ({n_al0} Al, {n_ni0} Ni)", flush=True)

    supercell_cellpar, supercell_vpa = cellpar_and_vpa(supercell)

    # fresh state for the supercell -- Stage C's proven clear+rebuild
    # pattern; activate_mliappy_kokkos is per-process, not re-called here.
    lmp.command("clear")
    supercell_data = f"{RESULTS_DIR}/{phase}_supercell_0K.data"
    read_data_file(lmp, supercell, supercell_data)
    setup_pair(lmp, unified)

    lmp.commands_string(f"""
variable temp equal {TEMP_K}
variable seed equal {SEED}
variable tdamp equal {TDAMP_PS}
variable pdamp equal {PDAMP_PS}
variable pressure equal {PRESSURE_BAR}
variable npt_steps equal {NPT_STEPS}
variable thermo_every equal {THERMO_EVERY}
variable final_data string {RESULTS_DIR}/{phase}_post_npt.data
""")

    npt_in = f"{SCRIPT_DIR}/in.npt_stability_supercell"
    lmp.file(npt_in)
    post_npt = extract_state(lmp, natoms)
    print(f"[{phase}] post-NPT: T={post_npt['temp_K']:.1f} K  "
          f"cellpar={post_npt['cellpar']}", flush=True)

    lmp.close()
    # deliberately no lmp.finalize() -- see module docstring

    result = {
        "phase": phase,
        "n_primitive_atoms": n_primitive,
        "replication": [nx, ny, nz],
        "natoms": natoms,
        "n_Al": n_al0,
        "n_Ni": n_ni0,
        "protocol": {
            "temp_K": TEMP_K, "seed": SEED, "tdamp_ps": TDAMP_PS, "pdamp_ps": PDAMP_PS,
            "pressure_bar": PRESSURE_BAR, "timestep_ps": TIMESTEP_PS,
            "npt_steps": NPT_STEPS, "thermo_every": THERMO_EVERY,
        },
        "primitive_relax": {
            "fmax_eV_per_A": relax_fmax,
            "cellpar": primitive_cellpar.tolist(),
            "volume_per_atom_A3": primitive_vpa,
        },
        "supercell_0K": {
            "cellpar": supercell_cellpar.tolist(),
            "volume_per_atom_A3": supercell_vpa,
        },
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
