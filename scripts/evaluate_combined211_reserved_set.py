#!/usr/bin/env python3
"""First reserved-set (TEST+BLIND_HOLDOUT, 20 structures, never trained on)
evaluation since Dataset-100. Every checkpoint since (combined-113/127/129/
211) has only ever been measured via the 2-point non-sealed interim gate --
this is the real generalization check, reusing evaluate_dataset100_final.py's
exact method (relative-energy formula, error stats, GPa conversion) rather
than reinventing it.

OLD = dataset100_matpes_pbe_lora_v1 (the last model this exact evaluation
was ever run against). NEW = al3ni_combined211_lora_v1. Neither TEST nor
BLIND_HOLDOUT has ever been passed to any training run in this project's
history (verified below by leakage check, not assumed).

cfg109/cfg110 are not part of TEST/BLIND_HOLDOUT and are not touched here.
"""

import csv
import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from ase.io import read
from mace.calculators import MACECalculator

R = Path("/workspace/ni_al")
OUT = R / "results/combined211_reserved_evaluation_v1"
DATA = R / "data/datasets/ni_al_combined211_dft.extxyz"
TRAIN_FILE = R / "data/datasets/ni_al_combined211_train_173.extxyz"
TEST = R / "data/datasets/ni_al_dataset100_test_manifest.csv"
BLIND = R / "data/datasets/ni_al_dataset100_blind_holdout_manifest.csv"
NEW = R / "models/al3ni_combined211_lora_v1/al3ni_combined211_lora_v1.model"
OLD = R / "models/dataset100_matpes_pbe_lora_v1/dataset100_matpes_pbe_lora_v1.model"
STATUS = R / "configs/COMBINED211_RESERVED_EVALUATION_STATUS.txt"
GPA = 160.21766208


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def refs(a):
    return float(a.get_potential_energy()), np.asarray(a.get_forces(), float), np.asarray(a.get_stress(), float)


def stats(x):
    x = np.asarray(x, float)
    return float(np.mean(np.abs(x))), float(np.sqrt(np.mean(x * x))), float(np.max(np.abs(x)))


def predict(path, structures):
    calc = MACECalculator(model_paths=str(path), device="cuda", default_dtype="float64")
    out = {}
    for key, a in structures.items():
        w = a.copy()
        w.calc = calc
        out[key] = (float(w.get_potential_energy()), np.asarray(w.get_forces(), float), np.asarray(w.get_stress(), float))
    del calc
    torch.cuda.empty_cache()
    return out


def aggregate(rows, model):
    energy = [r[f"{model}_energy_error_mev_atom"] for r in rows]
    rel = [r[f"{model}_relative_energy_error_mev_atom"] for r in rows]
    force = np.concatenate([np.asarray(r[f"_{model}_force_error"]) for r in rows])
    stress = np.concatenate([np.asarray(r[f"_{model}_stress_error_gpa"]) for r in rows])
    e = stats(energy); re = stats(rel); f = stats(force); s = stats(stress)
    return {
        "energy_mae_mev_atom": e[0], "energy_rmse_mev_atom": e[1], "energy_max_abs_mev_atom": e[2],
        "relative_energy_mae_mev_atom": re[0], "relative_energy_rmse_mev_atom": re[1], "relative_energy_max_abs_mev_atom": re[2],
        "force_mae_evA": f[0], "force_rmse_evA": f[1], "force_max_component_error_evA": f[2],
        "stress_mae_gpa": s[0], "stress_rmse_gpa": s[1], "stress_max_component_error_gpa": s[2],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    for p in (DATA, TRAIN_FILE, TEST, BLIND, NEW, OLD):
        if not p.exists():
            raise RuntimeError(f"missing required file: {p}")

    frames = read(DATA, index=":")
    by = {a.info["config_id"]: a for a in frames}
    memberships = {s: list(csv.DictReader(p.open())) for s, p in [("TEST", TEST), ("BLIND_HOLDOUT", BLIND)]}
    if len(memberships["TEST"]) != 5 or len(memberships["BLIND_HOLDOUT"]) != 15:
        raise RuntimeError("evaluation membership count wrong (expected 5 TEST, 15 BLIND_HOLDOUT)")
    eval_ids = {r["config_id"] for rows in memberships.values() for r in rows}
    if len(eval_ids) != 20:
        raise RuntimeError("expected 20 unique reserved eval ids")

    train_frames = read(TRAIN_FILE, index=":")
    train_ids = {a.info["config_id"] for a in train_frames}
    leakage = eval_ids & train_ids
    if leakage:
        raise RuntimeError(f"LEAKAGE: reserved eval ids found in combined-211 TRAIN: {leakage}")

    relaxed = {}
    for phase in ("AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3"):
        cid = f"{phase}_relaxed"
        if cid not in by:
            raise RuntimeError(f"missing relaxed reference: {cid}")
        relaxed[phase] = by[cid]

    structures = {f"eval:{cid}": by[cid] for cid in eval_ids}
    structures.update({f"relaxed:{p}": a for p, a in relaxed.items()})

    print("Evaluating OLD model (dataset100_matpes_pbe_lora_v1)...", flush=True)
    old = predict(OLD, structures)
    print("Evaluating NEW model (al3ni_combined211_lora_v1)...", flush=True)
    new = predict(NEW, structures)

    rows = []
    for split, members in memberships.items():
        for m in members:
            cid = m["config_id"]
            a = by[cid]
            de, df, ds = refs(a)
            phase = a.info["phase"]
            dre = (de - refs(relaxed[phase])[0]) / len(a) * 1000
            row = {"split": split, "config_id": cid, "phase": phase,
                   "natoms": len(a), "dft_energy_eV": de, "dft_energy_per_atom_eV": de / len(a),
                   "dft_relative_energy_mev_atom": dre}
            for label, pred in [("dataset100", old), ("combined211", new)]:
                pe, pf, ps = pred[f"eval:{cid}"]
                pre = (pe - pred[f"relaxed:{phase}"][0]) / len(a) * 1000
                ee = (pe - de) / len(a) * 1000
                fe = pf - df
                se = (ps - ds) * GPA
                fs = stats(fe); ss = stats(se)
                row.update({
                    f"{label}_energy_eV": pe, f"{label}_energy_error_mev_atom": ee,
                    f"{label}_relative_energy_mev_atom": pre, f"{label}_relative_energy_error_mev_atom": pre - dre,
                    f"{label}_force_mae_evA": fs[0], f"{label}_force_rmse_evA": fs[1], f"{label}_force_max_component_error_evA": fs[2],
                    f"{label}_stress_mae_gpa": ss[0], f"{label}_stress_rmse_gpa": ss[1], f"{label}_stress_max_component_error_gpa": ss[2],
                    f"_{label}_force_error": fe.reshape(-1), f"_{label}_stress_error_gpa": se.reshape(-1),
                })
            rows.append(row)

    public = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    with (OUT / "combined211_reserved_per_config.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(public[0]))
        w.writeheader()
        w.writerows(public)

    per_split = {}
    for split in ("TEST", "BLIND_HOLDOUT"):
        split_rows = [r for r in rows if r["split"] == split]
        per_split[split] = {"dataset100": aggregate(split_rows, "dataset100"), "combined211": aggregate(split_rows, "combined211")}
    per_split["ALL_20"] = {"dataset100": aggregate(rows, "dataset100"), "combined211": aggregate(rows, "combined211")}

    lines = [
        "COMBINED-211 RESERVED-SET (TEST+BLIND_HOLDOUT) EVALUATION",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        "First reserved-set evaluation run against any checkpoint since Dataset-100.",
        "",
        f"DATA: {DATA} sha256={sha(DATA)}",
        f"TRAIN (leakage check source): {TRAIN_FILE} sha256={sha(TRAIN_FILE)}",
        f"TEST membership: {TEST} (5)  BLIND_HOLDOUT membership: {BLIND} (15)",
        f"OLD model: {OLD} sha256={sha(OLD)}",
        f"NEW model: {NEW} sha256={sha(NEW)}",
        "",
        "LEAKAGE CHECK: PASS -- 0/20 reserved eval config_ids found in combined-211 TRAIN (173).",
        "",
    ]
    for split in ("TEST", "BLIND_HOLDOUT", "ALL_20"):
        n = 5 if split == "TEST" else (15 if split == "BLIND_HOLDOUT" else 20)
        lines.append(f"=== {split} (n={n}) ===")
        for label in ("dataset100", "combined211"):
            s = per_split[split][label]
            lines.append(
                f"  {label}: energy MAE/RMSE={s['energy_mae_mev_atom']:.3f}/{s['energy_rmse_mev_atom']:.3f} meV/atom | "
                f"rel-energy MAE/RMSE={s['relative_energy_mae_mev_atom']:.3f}/{s['relative_energy_rmse_mev_atom']:.3f} meV/atom | "
                f"force MAE/RMSE={s['force_mae_evA']*1000:.2f}/{s['force_rmse_evA']*1000:.2f} meV/A | "
                f"stress MAE/RMSE={s['stress_mae_gpa']:.4f}/{s['stress_rmse_gpa']:.4f} GPa"
            )
        d100 = per_split[split]["dataset100"]; c211 = per_split[split]["combined211"]
        lines.append(
            f"  CHANGE (combined211 - dataset100), negative=improvement: "
            f"rel-energy RMSE {c211['relative_energy_rmse_mev_atom']-d100['relative_energy_rmse_mev_atom']:+.3f} meV/atom, "
            f"force RMSE {(c211['force_rmse_evA']-d100['force_rmse_evA'])*1000:+.2f} meV/A, "
            f"stress RMSE {c211['stress_rmse_gpa']-d100['stress_rmse_gpa']:+.4f} GPa"
        )
        lines.append("")

    lines += ["STATUS", "COMBINED-211 RESERVED-SET EVALUATION COMPLETE",
              "cfg109/cfg110 NOT part of TEST/BLIND_HOLDOUT, not evaluated, not touched."]
    STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nPer-config CSV: {OUT / 'combined211_reserved_per_config.csv'}")


if __name__ == "__main__":
    main()
