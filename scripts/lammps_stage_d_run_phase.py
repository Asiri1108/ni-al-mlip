#!/usr/bin/env python3
"""Stage D worker: ONE phase's NVT->NPT MD stability run (pair_style mliap
unified, Kokkos build). Single-phase, single-process, launched fresh per
phase by the driver (scripts/lammps_stage_d_run_all.py) -- lmp.finalize()
is still dropped (Kokkos::Cuda::finalize() vs torch+cupy's live CUDA
contexts, Stage A), so process exit is what reclaims CUDA/Kokkos state.

Sequence, all within ONE lammps.lammps() instance/process:
  1. read_data (DFT-relaxed starting geometry, force_skew=True)
  2. Python-side mliap unified model load (the ONLY verified working path --
     confirmed empirically 2026-08-19 that a bare `lmp -in` on a script
     containing "pair_style mliap unified EXISTS" fails with "ValueError:
     No unified model loaded" before any Python-side load call happens; see
     scripts/in.nvt_stability's header for the exact error)
  3. pair_style/pair_coeff/neighbor (setup_pair(), same helper as Stage B/C)
  4. box/relax tri pre-equilibration to THIS model's own zero-stress cell
     (relax_full(), same recipe as Stage B/C -- MD should start from the
     model's own PES minimum, not the raw DFT cell, so anything seen below
     is thermal/dynamical behavior, not a cold-start artifact)
  5. NVT production: scripts/in.nvt_stability via lmp.file()
  6. NPT production, continuing in-memory from NVT's final state (no
     re-read_data, no re-velocity-create): scripts/in.npt_stability via
     lmp.file()

Writes results/lammps_stage_d/<phase>_summary.json on success (pre-MD
relaxed state, post-NVT state, post-NPT state, each phase's own
alpha/beta/gamma so this file alone flags gross problems without needing
the log). The full per-step thermo trace (incl. box tilt, from which
alpha/beta/gamma are derived) lives in logs/lammps_stage_d/<phase>.log;
scripts/analyze_md_stability.py parses it for the real stability
assessment (drift, fluctuation, NaN/lost-atoms detection).

Writing nothing (rather than a partial/error summary) on failure is
deliberate, same convention as Stage B/C: a missing summary JSON means this
phase did not complete, unambiguous regardless of how it failed (LAMMPS
lost-atoms error, Python exception, segfault, OOM). The log file (flushed
every thermo line via thermo_modify flush yes) survives any crash for
post-mortem.
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
RESULTS_DIR = f"{ROOT}/results/lammps_stage_d"
LOG_DIR = f"{ROOT}/logs/lammps_stage_d"
SCRIPT_DIR = os.path.dirname(__file__)

# MD protocol parameters -- see module docstring / in.*_stability headers.
TEMP_K = 300.0
SEED = 20260819
TDAMP_PS = 0.1          # Nose-Hoover thermostat damping, ~100x timestep
PDAMP_PS = 1.0           # barostat damping, ~1000x timestep
PRESSURE_BAR = 0.0       # ambient
TIMESTEP_PS = 0.001      # 1 fs
NVT_PS = 15.0
NPT_PS = 15.0
NVT_STEPS = round(NVT_PS / TIMESTEP_PS)
NPT_STEPS = round(NPT_PS / TIMESTEP_PS)
THERMO_EVERY = 25        # -> 600 samples per 15 ps stage


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


def relax_full(lmp, atoms0, phase, unified):
    """tri box/relax + positions, same recipe as Stage B/C, to get THIS
    model's own zero-stress reference cell as the MD starting point."""
    data_file = f"/tmp/stage_d_{phase}_base.data"
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
    """Snapshot cellpar/volume/spacegroup/thermo from the current live state."""
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
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    atoms0 = load_dft_relaxed(phase)
    natoms = len(atoms0)
    log_file = f"{LOG_DIR}/{phase}.log"

    lmp = lammps.lammps(cmdargs=[
        "-k", "on", "g", "1", "-sf", "kk", "-pk", "kokkos", "neigh", "half", "newton", "on",
        "-log", log_file, "-screen", "none",
    ])
    lammps.mliap.activate_mliappy_kokkos(lmp)
    unified = torch.load(MLIAP_MODEL, map_location="cpu")

    relaxed, relax_fmax = relax_full(lmp, atoms0, phase, unified)
    relaxed_cellpar, relaxed_vpa = cellpar_and_vpa(relaxed)
    relaxed_sg_symbol, relaxed_sg_number = spacegroup_of(relaxed)
    print(f"[{phase}] pre-MD relax: fmax={relax_fmax:.3e} eV/A  "
          f"cellpar={relaxed_cellpar.tolist()}", flush=True)

    # LAMMPS variables consumed by in.nvt_stability / in.npt_stability.
    lmp.commands_string(f"""
variable temp equal {TEMP_K}
variable seed equal {SEED}
variable tdamp equal {TDAMP_PS}
variable pdamp equal {PDAMP_PS}
variable pressure equal {PRESSURE_BAR}
variable nvt_steps equal {NVT_STEPS}
variable npt_steps equal {NPT_STEPS}
variable thermo_every equal {THERMO_EVERY}
variable final_data string {RESULTS_DIR}/{phase}_post_nvt.data
""")

    nvt_in = f"{SCRIPT_DIR}/in.nvt_stability"
    npt_in = f"{SCRIPT_DIR}/in.npt_stability"

    lmp.file(nvt_in)
    post_nvt = extract_state(lmp, natoms)
    print(f"[{phase}] post-NVT: T={post_nvt['temp_K']:.1f} K  "
          f"cellpar={post_nvt['cellpar']}", flush=True)

    lmp.command(f"variable final_data delete")
    lmp.command(f"variable final_data string {RESULTS_DIR}/{phase}_post_npt.data")
    lmp.file(npt_in)
    post_npt = extract_state(lmp, natoms)
    print(f"[{phase}] post-NPT: T={post_npt['temp_K']:.1f} K  "
          f"cellpar={post_npt['cellpar']}", flush=True)

    lmp.close()
    # deliberately no lmp.finalize() -- see module docstring

    result = {
        "phase": phase,
        "natoms": natoms,
        "protocol": {
            "temp_K": TEMP_K,
            "seed": SEED,
            "tdamp_ps": TDAMP_PS,
            "pdamp_ps": PDAMP_PS,
            "pressure_bar": PRESSURE_BAR,
            "timestep_ps": TIMESTEP_PS,
            "nvt_steps": NVT_STEPS,
            "npt_steps": NPT_STEPS,
            "thermo_every": THERMO_EVERY,
        },
        "pre_md_relax": {
            "fmax_eV_per_A": relax_fmax,
            "cellpar": relaxed_cellpar.tolist(),
            "volume_per_atom_A3": relaxed_vpa,
            "spacegroup_symbol": relaxed_sg_symbol,
            "spacegroup_number": relaxed_sg_number,
        },
        "post_nvt": post_nvt,
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
