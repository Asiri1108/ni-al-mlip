#!/usr/bin/env python3
"""Formation energy + volume error for the 3 MACE methods, matching Phase 1's
convention (inbox/ni_al_step8_final_report.txt Section 7/22): mu_Al/mu_Ni are
each method's OWN energy at its OWN relaxed elemental equilibrium (never
DFT's elemental geometry), and the compound energy/volume is each method's
OWN full-cell relaxation of the phase (never DFT's geometry either) -- "the
matching relaxation state" rule, applied consistently on both sides.

Elemental mu: since a 1-atom fcc primitive cell has exactly one degree of
freedom (the lattice constant), mu is obtained by a lattice-constant scan
plus a quadratic fit to locate the minimum, then one evaluation at that
fitted point -- equivalent to a converged vc-relax for an isotropic cell,
without depending on any particular optimizer's convergence settings.

Compound relaxation: full cell+position relax (ASE FrechetCellFilter + BFGS)
starting from the DFT-relaxed geometry, using each MACE model itself.
"""
import json
import time
from pathlib import Path

import numpy as np
import torch
from ase.io import read
from ase.build import bulk
from ase.optimize import BFGS
from ase.filters import FrechetCellFilter
from mace.calculators import mace_mp, MACECalculator

R = Path("/workspace/ni_al")
DATA = R / "data/datasets/ni_al_combined227_dft.extxyz"
FINETUNED_MODEL = R / "models/al3ni_combined227_lora_v1/al3ni_combined227_lora_v1.model"
OUT = R / "results/unified_comparison_formation_energy_v1"
OUT.mkdir(parents=True, exist_ok=True)


def elemental_mu(calc, element, a_center, arange=0.05, npts=9):
    a_values = np.linspace(a_center * (1 - arange), a_center * (1 + arange), npts)
    energies = []
    for a in a_values:
        atoms = bulk(element, "fcc", a=a, cubic=False)
        atoms.calc = calc
        energies.append(atoms.get_potential_energy())
    coeffs = np.polyfit(a_values, energies, 2)
    a_min = -coeffs[1] / (2 * coeffs[0])
    atoms = bulk(element, "fcc", a=a_min, cubic=False)
    atoms.calc = calc
    e_min = atoms.get_potential_energy()
    return float(e_min), float(a_min), {"a_scan": a_values.tolist(), "e_scan": energies}


def relax_compound(calc, atoms_in, fmax=1e-3, steps=300):
    atoms = atoms_in.copy()
    atoms.calc = calc
    ecf = FrechetCellFilter(atoms)
    opt = BFGS(ecf, logfile=None)
    opt.run(fmax=fmax, steps=steps)
    e = float(atoms.get_potential_energy())
    vol = float(atoms.get_volume())
    converged = opt.converged()
    return e, vol, converged, len(atoms)


def run_method(method_name, calc, relaxed_frames):
    print(f"\n=== {method_name} ===", flush=True)
    t0 = time.time()
    mu_al, a_al, al_scan = elemental_mu(calc, "Al", 4.05)
    mu_ni, a_ni, ni_scan = elemental_mu(calc, "Ni", 3.52)
    print(f"  mu_Al = {mu_al:.6f} eV/atom (a={a_al:.4f} A), "
          f"mu_Ni = {mu_ni:.6f} eV/atom (a={a_ni:.4f} A)  [{time.time()-t0:.1f}s]", flush=True)

    phases = {}
    for phase, atoms in relaxed_frames.items():
        e, vol, converged, natoms = relax_compound(calc, atoms)
        formula = atoms.get_chemical_formula(empirical=True)
        n_al = atoms.get_chemical_symbols().count("Al")
        n_ni = atoms.get_chemical_symbols().count("Ni")
        e_f = (e - n_al * mu_al - n_ni * mu_ni) / natoms
        phases[phase] = {
            "natoms": natoms, "n_Al": n_al, "n_Ni": n_ni,
            "relaxed_energy_eV": e, "relaxed_volume_A3": vol,
            "relaxed_volume_per_atom_A3": vol / natoms,
            "formation_energy_eV_atom": e_f, "converged": bool(converged),
        }
        print(f"  {phase}: E_f = {e_f:.6f} eV/atom, V/atom = {vol/natoms:.4f} A^3, "
              f"converged={converged}", flush=True)

    return {
        "method": method_name, "mu_Al_eV_atom": mu_al, "mu_Al_relaxed_a_A": a_al,
        "mu_Ni_eV_atom": mu_ni, "mu_Ni_relaxed_a_A": a_ni, "phases": phases,
    }


def main():
    frames = read(DATA, ":")
    relaxed_frames = {a.info["phase"]: a for a in frames if a.info.get("config_type") == "relaxed"}
    assert set(relaxed_frames) == {"AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3"}

    all_results = {}

    print("Loading MACE-MP-0 Small (zero-shot)...", flush=True)
    calc = mace_mp(model="small", device="cuda", default_dtype="float64")
    all_results["macemp0_small"] = run_method("macemp0_small", calc, relaxed_frames)
    del calc
    torch.cuda.empty_cache()

    print("\nLoading MACE-MATPES-PBE-0 (zero-shot)...", flush=True)
    calc = mace_mp(model="mace-matpes-pbe-0", device="cuda", default_dtype="float64")
    all_results["mace_matpes_pbe_0"] = run_method("mace_matpes_pbe_0", calc, relaxed_frames)
    del calc
    torch.cuda.empty_cache()

    print(f"\nLoading al3ni_combined227_lora_v1 (fine-tuned)...", flush=True)
    calc = MACECalculator(model_paths=str(FINETUNED_MODEL), device="cuda", default_dtype="float64")
    all_results["al3ni_combined227_lora_v1"] = run_method("al3ni_combined227_lora_v1", calc, relaxed_frames)
    del calc
    torch.cuda.empty_cache()

    (OUT / "mace_formation_energy.json").write_text(json.dumps(all_results, indent=2))
    print(f"\nDone. Wrote {OUT}/mace_formation_energy.json")


if __name__ == "__main__":
    main()
