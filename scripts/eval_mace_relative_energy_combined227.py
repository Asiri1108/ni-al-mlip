#!/usr/bin/env python3
"""STEP A -- MACE relative-energy + per-phase force evaluation on
combined-227, for the unified comparison matrix (NI_AL_UNIFIED_COMPARISON.md).

Three methods, all single-point inference only (no training):
  - MACE-MP-0 Small (zero-shot public foundation checkpoint)
  - MACE-MATPES-PBE-0 (zero-shot public foundation checkpoint)
  - al3ni_combined227_lora_v1 (this project's fine-tuned checkpoint)

Same relative-energy convention as scripts/evaluate_dataset100_final.py and
scripts/eval_eam_relative_energy_combined227.py:
  dft_rel(config)    = (E_dft[config]    - E_dft[phase_relaxed])    / natoms * 1000
  method_rel(config) = (E_method[config] - E_method[phase_relaxed]) / natoms * 1000
  relative_energy_error = method_rel - dft_rel
"""
import csv
import json
import time
from pathlib import Path

import numpy as np
import torch
from ase.io import read
from mace.calculators import mace_mp, MACECalculator

R = Path("/workspace/ni_al")
DATA = R / "data/datasets/ni_al_combined227_dft.extxyz"
TEST_MANIFEST = R / "data/datasets/ni_al_dataset100_test_manifest.csv"
BLIND_MANIFEST = R / "data/datasets/ni_al_dataset100_blind_holdout_manifest.csv"
FINETUNED_MODEL = R / "models/al3ni_combined227_lora_v1/al3ni_combined227_lora_v1.model"
OUT_DIR = R / "results/unified_comparison_stepA_v1"


def stats(x):
    x = np.asarray(x, float)
    return float(np.mean(np.abs(x))), float(np.sqrt(np.mean(x * x))), float(np.max(np.abs(x)))


def predict_all(calc, frames):
    out = {}
    for a in frames:
        w = a.copy()
        w.calc = calc
        e = float(w.get_potential_energy())
        f = np.asarray(w.get_forces(), float)
        out[a.info["config_id"]] = (e, f)
    return out


def main():
    start = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    frames = read(DATA, ":")
    print(f"Loaded {len(frames)} combined-227 structures", flush=True)

    reserved_ids = set()
    for manifest in (TEST_MANIFEST, BLIND_MANIFEST):
        for row in csv.DictReader(manifest.open()):
            reserved_ids.add(row["config_id"])
    assert len(reserved_ids) == 20, f"expected 20 reserved ids, got {len(reserved_ids)}"

    relaxed = {a.info["phase"]: a for a in frames if a.info.get("config_type") == "relaxed"}
    assert set(relaxed) == {"AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3"}

    methods = {}

    print("\nLoading MACE-MP-0 Small (zero-shot)...", flush=True)
    calc = mace_mp(model="small", device="cuda", default_dtype="float64")
    t0 = time.time()
    methods["macemp0_small"] = predict_all(calc, frames)
    print(f"  done in {time.time()-t0:.1f}s", flush=True)
    del calc
    torch.cuda.empty_cache()

    print("\nLoading MACE-MATPES-PBE-0 (zero-shot)...", flush=True)
    calc = mace_mp(model="mace-matpes-pbe-0", device="cuda", default_dtype="float64")
    t0 = time.time()
    methods["mace_matpes_pbe_0"] = predict_all(calc, frames)
    print(f"  done in {time.time()-t0:.1f}s", flush=True)
    del calc
    torch.cuda.empty_cache()

    print(f"\nLoading al3ni_combined227_lora_v1 (fine-tuned) from {FINETUNED_MODEL}...", flush=True)
    calc = MACECalculator(model_paths=str(FINETUNED_MODEL), device="cuda", default_dtype="float64")
    t0 = time.time()
    methods["al3ni_combined227_lora_v1"] = predict_all(calc, frames)
    print(f"  done in {time.time()-t0:.1f}s", flush=True)
    del calc
    torch.cuda.empty_cache()

    all_rows = []
    for method_name, pred in methods.items():
        relaxed_e = {phase: pred[relaxed[phase].info["config_id"]][0] for phase in relaxed}
        for a in frames:
            cid = a.info["config_id"]
            phase = a.info["phase"]
            natoms = len(a)
            dft_e = float(a.get_potential_energy())
            dft_f = np.asarray(a.get_forces(), float)
            dft_e_relaxed = float(relaxed[phase].get_potential_energy())
            dft_rel = (dft_e - dft_e_relaxed) / natoms * 1000.0

            m_e, m_f = pred[cid]
            m_rel = (m_e - relaxed_e[phase]) / natoms * 1000.0
            rel_error = m_rel - dft_rel
            force_error = m_f - dft_f
            f_mae, f_rmse, f_max = stats(force_error)

            all_rows.append({
                "method": method_name, "config_id": cid, "phase": phase,
                "config_type": a.info.get("config_type"), "natoms": natoms,
                "reserved_20": cid in reserved_ids,
                "dft_relative_energy_mev_atom": dft_rel,
                "method_relative_energy_mev_atom": m_rel,
                "relative_energy_error_mev_atom": rel_error,
                "force_mae_evA": f_mae, "force_rmse_evA": f_rmse, "force_max_evA": f_max,
                "_force_error": force_error.reshape(-1).tolist(),
            })

    public = [{k: v for k, v in r.items() if not k.startswith("_")} for r in all_rows]
    with (OUT_DIR / "mace_per_config.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(public[0]))
        w.writeheader()
        w.writerows(public)

    summary = []
    for method_name in methods:
        for subset_name, pred_fn in [("ALL_227", lambda r: True),
                                       ("RESERVED_20", lambda r: r["reserved_20"]),
                                       ("NON_RESERVED_207", lambda r: not r["reserved_20"])]:
            rows = [r for r in all_rows if r["method"] == method_name and pred_fn(r)]
            if not rows:
                continue
            re_mae, re_rmse, re_max = stats([r["relative_energy_error_mev_atom"] for r in rows])
            force_all = np.concatenate([r["_force_error"] for r in rows])
            f_mae, f_rmse, f_max = stats(force_all)
            summary.append({
                "method": method_name, "subset": subset_name, "count": len(rows),
                "relative_energy_mae_mev_atom": re_mae,
                "relative_energy_rmse_mev_atom": re_rmse,
                "relative_energy_max_abs_mev_atom": re_max,
                "force_mae_evA": f_mae, "force_rmse_evA": f_rmse, "force_max_evA": f_max,
            })
            for phase in sorted({r["phase"] for r in rows}):
                prows = [r for r in rows if r["phase"] == phase]
                pforce = np.concatenate([r["_force_error"] for r in prows])
                pf_mae, pf_rmse, pf_max = stats(pforce)
                pre_mae, pre_rmse, pre_max = stats([r["relative_energy_error_mev_atom"] for r in prows])
                summary.append({
                    "method": method_name, "subset": f"{subset_name}:{phase}", "count": len(prows),
                    "relative_energy_mae_mev_atom": pre_mae,
                    "relative_energy_rmse_mev_atom": pre_rmse,
                    "relative_energy_max_abs_mev_atom": pre_max,
                    "force_mae_evA": pf_mae, "force_rmse_evA": pf_rmse, "force_max_evA": pf_max,
                })

    with (OUT_DIR / "mace_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)
    (OUT_DIR / "mace_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nDone in {time.time()-start:.1f}s. Wrote {OUT_DIR}/mace_per_config.csv and mace_summary.csv")


if __name__ == "__main__":
    main()
