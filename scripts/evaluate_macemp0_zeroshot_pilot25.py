#!/usr/bin/env python3
"""Zero-shot MACE-MP-0 Small (the ORIGINAL Phase-1 foundation model, not
fine-tuned) on the project's own QE/PBE Pilot-25 dataset, using the
IDENTICAL relative-energy methodology already used for the recorded
MACE-MATPES-PBE-0 zero-shot baseline (configs/NI_AL_DATA_SHOWCASE.md
Section 7: "Relative-energy MAE 4.023 meV/atom ... Max 21.228 meV/atom
(AlNi_iso_m02)"). That baseline's dataset -- 5 phases x (1 relaxed + 4
perturbed families: iso_m02, iso_p02, rattle_003, shear015_rattle002) =
25 configs -- is exactly `data/processed/ni_al_pilot_dft_25.extxyz`
(confirmed by cross-referencing the family names and the AlNi_iso_m02
max-error example against that file's contents).

Formula (identical to scripts/evaluate_pilot25_test_v1.py, generalized
from that script's TEST-5-only subset to all 4 perturbed families):
  dft_rel(config)   = (E_dft[config]   - E_dft[phase_relaxed])   / natoms * 1000   (meV/atom)
  model_rel(config) = (E_model[config] - E_model[phase_relaxed]) / natoms * 1000
  relative_energy_error = model_rel - dft_rel
This cancels any difference in the two foundation models' atomic
reference-energy (E0) conventions, since both use the SAME phase's own
relaxed structure as the zero point -- exactly why this project uses this
metric for cross-model comparison instead of raw formation energy.

Only the foundation model changes (MACE-MP-0 Small vs MACE-MATPES-PBE-0);
reference (QE/PBE Pilot-25) and metric are held constant, matching the
one comparison this project's own record never made.

Read-only: loads a public pretrained checkpoint (downloaded once via
mace.calculators.mace_mp, cached to /root/.cache/mace/, not part of this
project's own datasets) and runs single-point inference only -- no
training, no MD, no modification of any project file.
"""
import json
import os

os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

import numpy as np
import torch
from ase.io import read
from mace.calculators import mace_mp, MACECalculator

ROOT = "/workspace/ni_al"
PILOT25 = f"{ROOT}/data/processed/ni_al_pilot_dft_25.extxyz"
OUT_DIR = f"{ROOT}/results/macemp0_zeroshot_pilot25_v1"
PHASES = ["AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3"]
FAMILIES = ["iso_m02", "iso_p02", "rattle_003", "shear015_rattle002"]

# Recorded MACE-MATPES-PBE-0 zero-shot baseline, held constant for
# comparison -- configs/NI_AL_DATA_SHOWCASE.md Section 7.
MATPES_PBE0_RECORDED = {
    "relative_energy_mae_mev_atom": 4.023,
    "relative_energy_rmse_mev_atom": 6.634,
    "relative_energy_max_abs_error_mev_atom": 21.228,
    "relative_energy_max_config": "AlNi_iso_m02",
    "force_mae_evA_by_phase": {
        "AlNi": 0.000441, "AlNi3": 0.000879, "Al3Ni5": 0.006676,
        "Al3Ni2": 0.015993, "Al3Ni": 0.054216,
    },
}


def refs(atoms):
    r = atoms.calc.results
    return (float(r["energy"]), np.asarray(r["forces"], dtype=float).copy())


def mae_rmse(x):
    x = np.asarray(x, dtype=float)
    return float(np.mean(np.abs(x))), float(np.sqrt(np.mean(x**2)))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    frames = read(PILOT25, index=":")
    assert len(frames) == 25, f"expected 25 Pilot-25 configs, got {len(frames)}"
    by_key = {(a.info["phase"], a.info["config_type"]): a for a in frames}
    relaxed = {p: by_key[(p, "relaxed")] for p in PHASES}
    perturbed = {(p, f): by_key[(p, f)] for p in PHASES for f in FAMILIES}
    assert len(relaxed) == 5 and len(perturbed) == 20

    print("Loading MACE-MP-0 Small (public foundation checkpoint, cached "
          "if already downloaded)...", flush=True)
    calc = mace_mp(model="small", device="cuda", default_dtype="float64")

    print("Evaluating all 25 Pilot-25 configs zero-shot with MACE-MP-0 Small...", flush=True)
    predictions = {}
    for key, atoms in {**{("relaxed", p): relaxed[p] for p in PHASES},
                        **{(f"{p}", f): perturbed[(p, f)] for p in PHASES for f in FAMILIES}}.items():
        work = atoms.copy()
        work.calc = calc
        e = float(work.get_potential_energy())
        f = np.asarray(work.get_forces(), dtype=float)
        predictions[key] = (e, f)
    del calc
    torch.cuda.empty_cache()

    rows = []
    rel_errors_all = []
    force_errors_by_phase = {p: [] for p in PHASES}
    for p in PHASES:
        dft_e_relaxed, _ = refs(relaxed[p])
        model_e_relaxed, _ = predictions[("relaxed", p)]
        for fam in FAMILIES:
            atoms = perturbed[(p, fam)]
            natoms = len(atoms)
            dft_e, dft_f = refs(atoms)
            model_e, model_f = predictions[(p, fam)]

            dft_rel = (dft_e - dft_e_relaxed) / natoms * 1000.0
            model_rel = (model_e - model_e_relaxed) / natoms * 1000.0
            rel_error = model_rel - dft_rel
            force_error = model_f - dft_f
            f_mae, f_rmse = mae_rmse(force_error)

            rows.append({
                "config_id": atoms.info["config_id"], "phase": p, "config_type": fam,
                "n_atoms": natoms,
                "dft_relative_energy_mev_atom": dft_rel,
                "macemp0_relative_energy_mev_atom": model_rel,
                "macemp0_relative_energy_error_mev_atom": rel_error,
                "macemp0_force_mae_evA": f_mae,
                "macemp0_force_rmse_evA": f_rmse,
            })
            rel_errors_all.append(rel_error)
            force_errors_by_phase[p].append(force_error.reshape(-1))

    re_mae, re_rmse = mae_rmse(rel_errors_all)
    re_max_idx = int(np.argmax(np.abs(rel_errors_all)))
    re_max_config = rows[re_max_idx]["config_id"]
    re_max = float(np.abs(rel_errors_all[re_max_idx]))

    force_mae_by_phase = {}
    for p in PHASES:
        allf = np.concatenate(force_errors_by_phase[p])
        f_mae, f_rmse = mae_rmse(allf)
        force_mae_by_phase[p] = f_mae

    overall_force_mae, overall_force_rmse = mae_rmse(
        np.concatenate([np.concatenate(force_errors_by_phase[p]) for p in PHASES]))

    macemp0 = {
        "relative_energy_mae_mev_atom": re_mae,
        "relative_energy_rmse_mev_atom": re_rmse,
        "relative_energy_max_abs_error_mev_atom": re_max,
        "relative_energy_max_config": re_max_config,
        "force_mae_evA_overall": overall_force_mae,
        "force_rmse_evA_overall": overall_force_rmse,
        "force_mae_evA_by_phase": force_mae_by_phase,
    }

    result = {
        "macemp0_zeroshot": macemp0,
        "matpes_pbe0_zeroshot_recorded": MATPES_PBE0_RECORDED,
        "per_config": rows,
        "dataset": PILOT25,
        "n_configs_evaluated": len(rows),
        "model_checkpoint": "MACE-MP-0 Small, 2023-12-10-mace-128-L0_energy_epoch-249.model (public, via mace_mp(model='small'))",
    }
    out_path = f"{OUT_DIR}/macemp0_vs_matpespbe0_zeroshot.json"
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2)

    print(json.dumps({"macemp0_zeroshot": macemp0,
                       "matpes_pbe0_zeroshot_recorded": MATPES_PBE0_RECORDED}, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
