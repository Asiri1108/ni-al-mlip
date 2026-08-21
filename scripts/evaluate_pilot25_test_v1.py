#!/usr/bin/env python3
"""One-shot canonical TEST-5 evaluation; never trains or writes datasets."""

import csv
import json
from pathlib import Path

import numpy as np
import torch
from ase.io import read
from mace.calculators import MACECalculator


ROOT = Path("/workspace/ni_al")
TRAIN = ROOT / "data/datasets/ni_al_pilot_train_15.extxyz"
VALID = ROOT / "data/datasets/ni_al_pilot_val_5.extxyz"
TEST = ROOT / "data/datasets/ni_al_pilot_test_5.extxyz"
ZERO_MODEL = ROOT / "runs/pilot25_matpes_pbe_lora_v1/downloads/mace/MACEmatpespbeomatftmodel"
FT_MODEL = ROOT / "models/pilot25_matpes_pbe_lora_v1/pilot25_matpes_pbe_lora_v1.model"
OUT = ROOT / "results/pilot25_test_evaluation_v1"
GPA_PER_EV_A3 = 160.21766208
PHASES = ["AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3"]


def refs(atoms):
    result = atoms.calc.results
    return (
        float(result["energy"]),
        np.asarray(result["forces"], dtype=float).copy(),
        np.asarray(result["stress"], dtype=float).reshape(6).copy(),
    )


def validate():
    train = read(TRAIN, index=":")
    valid = read(VALID, index=":")
    test = read(TEST, index=":")
    assert len(train) == 15 and len(valid) == 5 and len(test) == 5
    assert {a.info["config_type"] for a in test} == {"shear015_rattle002"}
    assert {a.info["phase"] for a in test} == set(PHASES)
    ids = {k: {a.info["config_id"] for a in xs} for k, xs in [("train", train), ("valid", valid), ("test", test)]}
    assert len(ids["test"]) == 5
    assert not (ids["train"] & ids["valid"] or ids["train"] & ids["test"] or ids["valid"] & ids["test"])
    for atoms in train + valid + test:
        e, f, s = refs(atoms)
        assert np.isfinite(e) and np.isfinite(f).all() and np.isfinite(s).all()
        assert f.shape == (len(atoms), 3) and s.shape == (6,)
    relaxed = {a.info["phase"]: a for a in train if a.info["config_type"] == "relaxed"}
    assert set(relaxed) == set(PHASES)
    return test, relaxed


def predict(model_path, structures):
    calc = MACECalculator(model_paths=str(model_path), device="cuda", default_dtype="float64")
    output = {}
    for key, atoms in structures.items():
        work = atoms.copy()
        work.calc = calc
        output[key] = {
            "energy": float(work.get_potential_energy()),
            "forces": np.asarray(work.get_forces(), dtype=float),
            "stress": np.asarray(work.get_stress(voigt=True), dtype=float).reshape(6),
        }
    del calc
    torch.cuda.empty_cache()
    return output


def mae_rmse(error):
    error = np.asarray(error, dtype=float)
    return float(np.mean(np.abs(error))), float(np.sqrt(np.mean(error**2)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    test, relaxed = validate()
    test_by_phase = {a.info["phase"]: a for a in test}
    structures = {f"test:{p}": test_by_phase[p] for p in PHASES}
    structures.update({f"relaxed:{p}": relaxed[p] for p in PHASES})

    print("Loading/evaluating exact zero-shot MACE-MATPES-PBE-0", flush=True)
    zero = predict(ZERO_MODEL, structures)
    print("Loading/evaluating canonical fine-tuned model", flush=True)
    ft = predict(FT_MODEL, structures)

    rows = []
    all_force = {"zero": [], "ft": []}
    all_stress = {"zero": [], "ft": []}
    rel_errors = {"zero": [], "ft": []}
    for phase in PHASES:
        atoms = test_by_phase[phase]
        dft_e, dft_f, dft_s = refs(atoms)
        dft_rel = (dft_e - refs(relaxed[phase])[0]) / len(atoms) * 1000.0
        row = {
            "config_id": atoms.info["config_id"],
            "phase": phase,
            "config_type": atoms.info["config_type"],
            "n_atoms": len(atoms),
            "dft_relative_energy_mev_atom": dft_rel,
        }
        for label, pred in [("zero", zero), ("ft", ft)]:
            test_pred = pred[f"test:{phase}"]
            relaxed_pred = pred[f"relaxed:{phase}"]
            model_rel = (test_pred["energy"] - relaxed_pred["energy"]) / len(atoms) * 1000.0
            rel_error = model_rel - dft_rel
            force_error = test_pred["forces"] - dft_f
            stress_error = test_pred["stress"] - dft_s
            f_mae, f_rmse = mae_rmse(force_error)
            s_mae_ev, s_rmse_ev = mae_rmse(stress_error)
            row.update({
                f"{label}_relative_energy_mev_atom": model_rel,
                f"{label}_relative_energy_error_mev_atom": rel_error,
                f"{label}_force_mae_evA": f_mae,
                f"{label}_force_rmse_evA": f_rmse,
                f"{label}_fmax_reference_evA": float(np.linalg.norm(dft_f, axis=1).max()),
                f"{label}_fmax_prediction_evA": float(np.linalg.norm(test_pred["forces"], axis=1).max()),
                f"{label}_stress_mae_evA3": s_mae_ev,
                f"{label}_stress_rmse_evA3": s_rmse_ev,
                f"{label}_stress_mae_gpa": s_mae_ev * GPA_PER_EV_A3,
                f"{label}_stress_rmse_gpa": s_rmse_ev * GPA_PER_EV_A3,
            })
            all_force[label].append(force_error.reshape(-1))
            all_stress[label].append(stress_error.reshape(-1))
            rel_errors[label].append(rel_error)
        rows.append(row)

    metrics = []
    values = {}
    for label in ("zero", "ft"):
        re_mae, re_rmse = mae_rmse(rel_errors[label])
        f_mae, f_rmse = mae_rmse(np.concatenate(all_force[label]))
        s_mae_ev, s_rmse_ev = mae_rmse(np.concatenate(all_stress[label]))
        values[label] = {
            "relative_energy_mae_mev_atom": re_mae,
            "relative_energy_rmse_mev_atom": re_rmse,
            "relative_energy_max_abs_error_mev_atom": float(np.max(np.abs(rel_errors[label]))),
            "force_mae_evA": f_mae,
            "force_rmse_evA": f_rmse,
            "stress_mae_evA3": s_mae_ev,
            "stress_rmse_evA3": s_rmse_ev,
            "stress_mae_gpa": s_mae_ev * GPA_PER_EV_A3,
            "stress_rmse_gpa": s_rmse_ev * GPA_PER_EV_A3,
        }
    summary_specs = [
        ("Relative Energy MAE", "meV/atom", "relative_energy_mae_mev_atom"),
        ("Relative Energy RMSE", "meV/atom", "relative_energy_rmse_mev_atom"),
        ("Force MAE", "eV/A", "force_mae_evA"),
        ("Force RMSE", "eV/A", "force_rmse_evA"),
        ("Stress MAE", "GPa", "stress_mae_gpa"),
        ("Stress RMSE", "GPa", "stress_rmse_gpa"),
    ]
    for metric, unit, key in summary_specs:
        z, f = values["zero"][key], values["ft"][key]
        metrics.append({"metric": metric, "unit": unit, "zero_shot": z, "fine_tuned": f,
                        "improvement_percent": 100.0 * (z - f) / z})

    per_config = OUT / "pilot25_test_per_config.csv"
    with per_config.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    with (OUT / "pilot25_test_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metrics[0]))
        writer.writeheader(); writer.writerows(metrics)
    (OUT / "pilot25_test_metrics.json").write_text(json.dumps({"aggregate": values, "summary": metrics, "per_config": rows}, indent=2))

    try:
        import matplotlib.pyplot as plt
        x = np.arange(len(PHASES)); width = 0.36
        plot_specs = [
            ("pilot25_test_force_before_after.png", "Force MAE (eV/A)", "zero_force_mae_evA", "ft_force_mae_evA"),
            ("pilot25_test_stress_before_after.png", "Stress MAE (GPa)", "zero_stress_mae_gpa", "ft_stress_mae_gpa"),
            ("pilot25_test_relative_energy_before_after.png", "Absolute relative-energy error (meV/atom)", "zero_relative_energy_error_mev_atom", "ft_relative_energy_error_mev_atom"),
        ]
        for filename, ylabel, zk, fk in plot_specs:
            z = [abs(r[zk]) for r in rows]; f = [abs(r[fk]) for r in rows]
            fig, ax = plt.subplots(figsize=(8, 4.8)); ax.bar(x-width/2, z, width, label="Zero-shot"); ax.bar(x+width/2, f, width, label="Fine-tuned")
            ax.set_xticks(x, PHASES); ax.set_ylabel(ylabel); ax.legend(); ax.grid(axis="y", alpha=.25); fig.tight_layout(); fig.savefig(OUT/filename, dpi=180); plt.close(fig)
        fig, ax = plt.subplots(figsize=(8, 4.8)); names=[m["metric"] for m in metrics]; changes=[m["improvement_percent"] for m in metrics]
        ax.bar(np.arange(len(names)), changes, color=["#2a9d8f" if v >= 0 else "#e76f51" for v in changes]); ax.axhline(0,color="black",lw=.8)
        ax.set_xticks(np.arange(len(names)), names, rotation=30, ha="right"); ax.set_ylabel("Improvement (%)"); ax.grid(axis="y",alpha=.25); fig.tight_layout(); fig.savefig(OUT/"pilot25_test_metric_improvement.png",dpi=180); plt.close(fig)
        print("PLOTS_CREATED 4", flush=True)
    except ImportError:
        print("PLOTS_SKIPPED matplotlib unavailable", flush=True)

    print(json.dumps({"aggregate": values, "summary": metrics}, indent=2), flush=True)


if __name__ == "__main__":
    main()
