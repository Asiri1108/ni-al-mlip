#!/usr/bin/env python3
"""Stage B, ASE/MACE-direct reference: relax all 5 phases with the plain ASE
MACECalculator (no LAMMPS) + FrechetCellFilter, for comparison against the
LAMMPS relaxation. No Kokkos/LAMMPS involved -- safe to run all 5 in one
process (only torch CUDA, which doesn't have the finalize-teardown issue
Stage A hit).
"""
import json
import os

os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

from ase.filters import FrechetCellFilter
from ase.optimize import LBFGS
from mace.calculators import MACECalculator

from lattice_compare_utils import load_dft_relaxed, cellpar_and_vpa, spacegroup_of, PHASES

ROOT = "/workspace/ni_al"
RAW_MODEL = f"{ROOT}/models/al3ni_combined227_lora_v1/al3ni_combined227_lora_v1.model"
RESULTS_DIR = f"{ROOT}/results/lammps_stage_b"
FMAX_TOL = 1e-8  # eV/Angstrom, matches the ftol used on the LAMMPS side as closely as ASE's convergence criterion allows


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    calc = MACECalculator(model_paths=RAW_MODEL, device="cpu", default_dtype="float64")

    for phase in PHASES:
        atoms = load_dft_relaxed(phase)
        atoms.calc = calc
        ecf = FrechetCellFilter(atoms)
        opt = LBFGS(ecf, logfile=f"{ROOT}/logs/lammps_stage_b/{phase}_ase.log")
        converged = opt.run(fmax=FMAX_TOL, steps=2000)

        e_final = float(atoms.get_potential_energy())
        fmax_final = float(max((atoms.get_forces() ** 2).sum(axis=1) ** 0.5))
        cellpar, vpa = cellpar_and_vpa(atoms)
        sg_symbol, sg_number = spacegroup_of(atoms)

        result = {
            "phase": phase,
            "natoms": len(atoms),
            "energy_eV": e_final,
            "fmax_final_eV_per_A": fmax_final,
            "converged": bool(converged),
            "n_steps": opt.nsteps,
            "cellpar": cellpar.tolist(),
            "volume_per_atom_A3": vpa,
            "spacegroup_symbol": sg_symbol,
            "spacegroup_number": sg_number,
        }
        out_path = f"{RESULTS_DIR}/{phase}_ase.json"
        with open(out_path, "w") as fh:
            json.dump(result, fh, indent=2)
        print(f"{phase}: converged={converged} nsteps={opt.nsteps} fmax={fmax_final:.3e} -> {out_path}")


if __name__ == "__main__":
    main()
