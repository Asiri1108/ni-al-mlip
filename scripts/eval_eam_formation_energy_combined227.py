#!/usr/bin/env python3
"""Formation energy + volume error for the 3 EAM potentials via LAMMPS,
matching Phase 1's convention (see eval_mace_formation_energy_combined227.py
docstring) and the same "own equilibrium, both sides" rule.

Elemental mu: lattice-constant scan + quadratic fit (1 DOF for a 1-atom fcc
primitive cell), identical methodology to the MACE script for a clean
side-by-side comparison.

Compound relaxation: LAMMPS `minimize` + `fix box/relax` (isotropic +
shape-flexible via aniso, matching FrechetCellFilter's full cell freedom)
starting from the DFT-relaxed geometry, using the same EAM potential.
"""
import json
import subprocess
import time
from pathlib import Path

import numpy as np
from ase.io import read
from ase.build import bulk

import sys
sys.path.insert(0, str(Path(__file__).parent))
from eval_eam_relative_energy_combined227 import (
    POTENTIALS, LMP, LMP_LIB, MASS_NI, MASS_AL, write_lammps_data,
)

R = Path("/workspace/ni_al")
DATA = R / "data/datasets/ni_al_combined227_dft.extxyz"
OUT = R / "results/unified_comparison_formation_energy_v1"
OUT.mkdir(parents=True, exist_ok=True)
TMP_DIR = Path("/tmp/eam_formation_energy")


def single_point_energy(atoms, potential_path, tag):
    """Cheap PE-only single point (no force dump needed for the lattice scan)."""
    work = TMP_DIR / tag
    work.mkdir(parents=True, exist_ok=True)
    data_path = work / "structure.data"
    write_lammps_data(atoms, data_path)
    in_path = work / "in.eval"
    in_path.write_text(f"""units metal
atom_style atomic
boundary p p p
read_data {data_path}
mass 1 {MASS_NI}
mass 2 {MASS_AL}
pair_style eam/alloy
pair_coeff * * {potential_path} Ni Al
run 0
print "EVAL_PE_EV $(pe)"
""")
    result = subprocess.run([str(LMP), "-in", str(in_path)], capture_output=True, text=True,
                             env={"LD_LIBRARY_PATH": str(LMP_LIB), "PATH": "/usr/bin:/bin"}, cwd=str(work))
    if result.returncode != 0:
        raise RuntimeError(f"lmp failed for {tag}:\n{result.stdout[-2000:]}")
    for line in result.stdout.splitlines():
        if line.startswith("EVAL_PE_EV"):
            return float(line.split()[1])
    raise RuntimeError(f"no PE found for {tag}")


def elemental_mu(potential_path, element, a_center, arange=0.05, npts=9, tag_prefix=""):
    a_values = np.linspace(a_center * (1 - arange), a_center * (1 + arange), npts)
    energies = []
    for i, a in enumerate(a_values):
        atoms = bulk(element, "fcc", a=a, cubic=False)
        e = single_point_energy(atoms, potential_path, f"{tag_prefix}/mu_{element}/{i}")
        energies.append(e)
    coeffs = np.polyfit(a_values, energies, 2)
    a_min = -coeffs[1] / (2 * coeffs[0])
    atoms = bulk(element, "fcc", a=a_min, cubic=False)
    e_min = single_point_energy(atoms, potential_path, f"{tag_prefix}/mu_{element}/fit")
    return float(e_min), float(a_min)


def relax_compound(atoms_in, potential_path, tag):
    work = TMP_DIR / tag
    work.mkdir(parents=True, exist_ok=True)
    data_path = work / "structure.data"
    write_lammps_data(atoms_in, data_path)
    in_path = work / "in.relax"
    log_path = work / "log.lammps"
    in_path.write_text(f"""units metal
atom_style atomic
boundary p p p
read_data {data_path}
mass 1 {MASS_NI}
mass 2 {MASS_AL}
pair_style eam/alloy
pair_coeff * * {potential_path} Ni Al
neighbor 2.0 bin
neigh_modify delay 0 every 1 check yes
fix 1 all box/relax aniso 0.0 vmax 0.001
min_style cg
minimize 1.0e-14 1.0e-8 10000 100000
unfix 1
min_style cg
minimize 1.0e-14 1.0e-8 10000 100000
print "RESULT_PE $(pe) RESULT_VOL $(vol) RESULT_NATOMS $(atoms)"
""")
    result = subprocess.run([str(LMP), "-in", str(in_path), "-log", str(log_path)],
                             capture_output=True, text=True,
                             env={"LD_LIBRARY_PATH": str(LMP_LIB), "PATH": "/usr/bin:/bin"}, cwd=str(work))
    if result.returncode != 0:
        raise RuntimeError(f"lmp relax failed for {tag}:\n{result.stdout[-3000:]}")
    pe = vol = natoms = None
    for line in result.stdout.splitlines():
        if line.startswith("RESULT_PE"):
            parts = line.split()
            pe, vol, natoms = float(parts[1]), float(parts[3]), int(parts[5])
    if pe is None:
        raise RuntimeError(f"no result line for {tag}:\n{result.stdout[-2000:]}")
    return pe, vol, natoms


def run_method(method_name, potential_path, relaxed_frames):
    print(f"\n=== {method_name} ===", flush=True)
    t0 = time.time()
    mu_al, a_al = elemental_mu(potential_path, "Al", 4.05, tag_prefix=method_name)
    mu_ni, a_ni = elemental_mu(potential_path, "Ni", 3.52, tag_prefix=method_name)
    print(f"  mu_Al = {mu_al:.6f} eV/atom (a={a_al:.4f} A), "
          f"mu_Ni = {mu_ni:.6f} eV/atom (a={a_ni:.4f} A)  [{time.time()-t0:.1f}s]", flush=True)

    phases = {}
    for phase, atoms in relaxed_frames.items():
        pe, vol, natoms = relax_compound(atoms, potential_path, f"{method_name}/relax_{phase}")
        n_al = atoms.get_chemical_symbols().count("Al")
        n_ni = atoms.get_chemical_symbols().count("Ni")
        e_f = (pe - n_al * mu_al - n_ni * mu_ni) / natoms
        phases[phase] = {
            "natoms": natoms, "n_Al": n_al, "n_Ni": n_ni,
            "relaxed_energy_eV": pe, "relaxed_volume_A3": vol,
            "relaxed_volume_per_atom_A3": vol / natoms,
            "formation_energy_eV_atom": e_f,
        }
        print(f"  {phase}: E_f = {e_f:.6f} eV/atom, V/atom = {vol/natoms:.4f} A^3", flush=True)

    return {
        "method": method_name, "mu_Al_eV_atom": mu_al, "mu_Al_relaxed_a_A": a_al,
        "mu_Ni_eV_atom": mu_ni, "mu_Ni_relaxed_a_A": a_ni, "phases": phases,
    }


def main():
    frames = read(DATA, ":")
    relaxed_frames = {a.info["phase"]: a for a in frames if a.info.get("config_type") == "relaxed"}
    assert set(relaxed_frames) == {"AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3"}

    all_results = {}
    for pot_name, pot_path in POTENTIALS.items():
        all_results[pot_name] = run_method(pot_name, pot_path, relaxed_frames)

    (OUT / "eam_formation_energy.json").write_text(json.dumps(all_results, indent=2))
    print(f"\nDone. Wrote {OUT}/eam_formation_energy.json")


if __name__ == "__main__":
    main()
