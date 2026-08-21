#!/usr/bin/env python3
"""Stage A: single-point LAMMPS (pair_style mliap unified, Kokkos/CUDA build)
vs plain ASE MACECalculator agreement check, on the SAME geometry, SAME
model weights, SAME dtype (float64).

Runs against tools/lammps/install/mliap_kokkos (not mliap_python): MACE's
ghost-atom feature exchange (forward_exchange/reverse_exchange, called
unconditionally by mace/modules/blocks.py::handle_lammps) only exists on
LAMMPS's Kokkos MLIAPDataPy variant -- the plain build fails with
AttributeError before any energy is computed. Uses activate_mliappy_kokkos /
load_unified_kokkos and '-sf kk' accordingly.

Two structures, both ordinary TRAIN-role data (no sealed/reserved configs
touched):
  - Al3Ni_relaxed: high-symmetry sanity check
  - cfg036_Al3Ni_rattle_large (16 atoms): general, low-symmetry geometry,
    exercises the neighbor list / triclinic cell path

PASS criterion: energy agreement to << the acceptance-threshold scale used
throughout this project (2.6183 meV/atom locked threshold) -- this is an
export/integration correctness check, not a model-quality check, so the
bar is numerical agreement (expect ~1e-4 eV/atom or tighter), not a
physics threshold.
"""
import os
os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

import numpy as np
import torch
from ase.io import read, write
from mace.calculators import MACECalculator

import lammps
import lammps.mliap

ROOT = "/workspace/ni_al"
RAW_MODEL = f"{ROOT}/models/al3ni_combined227_lora_v1/al3ni_combined227_lora_v1.model"
MLIAP_MODEL = f"{ROOT}/models/al3ni_combined227_lora_v1/al3ni_combined227_lora_v1.model-mliap_lammps.pt"
TRAIN = f"{ROOT}/data/datasets/ni_al_combined227_train_189.extxyz"
DFT = f"{ROOT}/data/datasets/ni_al_combined227_dft.extxyz"
DATA_TMP = "/tmp/stage_a_{cid}.data"

ELEMENT_ORDER = ["Al", "Ni"]  # from exported model.element_types, verified


def get_structure(cid):
    for path in (TRAIN, DFT):
        frames = read(path, index=":")
        by = {a.info.get("config_id"): a for a in frames}
        if cid in by:
            return by[cid].copy()
    raise KeyError(cid)


def mace_reference(atoms):
    calc = MACECalculator(model_paths=RAW_MODEL, device="cpu", default_dtype="float64")
    w = atoms.copy()
    w.calc = calc
    e = float(w.get_potential_energy())
    f = np.array(w.get_forces())
    del calc
    return e, f


def lammps_single_point(atoms, cid):
    data_file = DATA_TMP.format(cid=cid)
    write(data_file, atoms, format="lammps-data", specorder=ELEMENT_ORDER,
          masses=True, atom_style="atomic")

    # Kokkos build: MACE's ghost-atom feature exchange (forward_exchange /
    # reverse_exchange) only exists on the Kokkos MLIAPDataPy variant, so we
    # must run through the kk-suffixed pair style and the *_kokkos loader
    # functions -- matches examples/mliap/mliap_pytorch_Ta06A_kokkos.py.
    lmp = lammps.lammps(cmdargs=[
        "-k", "on", "g", "1", "-sf", "kk", "-pk", "kokkos", "neigh", "half", "newton", "on",
        "-log", "none", "-screen", "none",
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
run 0
""")

    e = lmp.get_thermo("pe")
    natoms = lmp.get_natoms()
    f_flat = np.array(lmp.numpy.extract_atom("f"), copy=True)
    ids = np.array(lmp.numpy.extract_atom("id"), copy=True)
    lmp.close()
    # Under the Kokkos array layout, extract_atom("f"/"id") returns
    # nlocal+nghost rows (periodic ghost copies appended after owned atoms --
    # e.g. 826 rows for a 16-atom cell at a 6 Angstrom cutoff), not just the
    # nlocal owned atoms. Owned atoms occupy the first `natoms` rows, in
    # read_data order (atom_modify sort is disabled, single process, so no
    # reordering occurs before ghost atoms are appended). Verify that
    # explicitly rather than assume it.
    owned = slice(0, natoms)
    expected_ids = np.arange(1, natoms + 1)
    if not np.array_equal(ids[owned], expected_ids):
        raise RuntimeError(
            f"owned-atom id layout not as expected: ids[:{natoms}]={ids[owned]}, "
            f"expected {expected_ids}. Ghost-atom slicing assumption is wrong."
        )
    f_flat = f_flat[owned]
    # NOTE: deliberately not calling lmp.finalize() -- Kokkos::Cuda::finalize()
    # segfaults in-process when torch + cupy + Kokkos all hold CUDA contexts
    # simultaneously (reproduced: crash happens strictly after run 0 succeeds
    # and results are already extracted, confirmed via PYTHONFAULTHANDLER
    # traceback pointing at lammps/core.py's finalize(), not at compute).
    # Harmless to skip for this one-shot-per-process script; OS reclaims
    # CUDA/Kokkos resources on exit.

    return float(e), f_flat, natoms


def main():
    cases = ["Al3Ni_relaxed", "cfg036_Al3Ni_rattle_large"]
    lines = ["LAMMPS STAGE A -- SINGLE-POINT AGREEMENT CHECK", ""]
    overall_ok = True

    for cid in cases:
        atoms = get_structure(cid)
        e_mace, f_mace = mace_reference(atoms)
        e_lammps, f_lammps, natoms = lammps_single_point(atoms, cid)

        assert natoms == len(atoms), f"{cid}: LAMMPS atom count {natoms} != {len(atoms)}"
        assert f_lammps.shape == f_mace.shape, f"{cid}: force array shape mismatch"

        e_diff = e_lammps - e_mace
        e_diff_per_atom_mev = abs(e_diff) / len(atoms) * 1000
        f_diff = f_lammps - f_mace
        f_max_abs_diff = float(np.abs(f_diff).max())

        ok = e_diff_per_atom_mev < 1.0 and f_max_abs_diff < 1e-2  # loose "did the export work" bar
        overall_ok = overall_ok and ok

        lines.append(f"=== {cid} (natoms={len(atoms)}) ===")
        lines.append(f"  MACE  (ASE calculator, cpu, float64): E = {e_mace:.8f} eV")
        lines.append(f"  LAMMPS (pair_style mliap unified):    E = {e_lammps:.8f} eV")
        lines.append(f"  Energy diff: {e_diff:.8e} eV  ({e_diff_per_atom_mev:.6f} meV/atom)")
        lines.append(f"  Max |force diff| (any atom, any component): {f_max_abs_diff:.8e} eV/Angstrom")
        lines.append(f"  {'PASS' if ok else 'FAIL'}")
        lines.append("")
        print("\n".join(lines[-7:]))

    lines.append(f"OVERALL: {'PASS' if overall_ok else 'FAIL'}")
    out = f"{ROOT}/configs/LAMMPS_STAGE_A_SINGLE_POINT_STATUS.txt"
    with open(out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nWrote {out}")
    print(f"OVERALL: {'PASS' if overall_ok else 'FAIL'}")


if __name__ == "__main__":
    main()
