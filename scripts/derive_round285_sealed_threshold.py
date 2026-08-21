#!/usr/bin/env python3
"""Derive the round285 sealed-pair (cfg297/cfg299) acceptance threshold --
READ-ONLY, does NOT read cfg297/cfg299 in any way.

Lessons applied from the combined-220/cfg109-cfg110 threshold history:
  1. cfg043 excluded from the derivation basis (design-contaminated --
     AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt, CFG043 EXCLUSION RATIONALE).
  2. cfg109/cfg110 excluded (consumed, and were round285's explicit
     optimization target -- including them would bias the threshold toward
     the exact points the data was added to fix).
  3. NOT derived from a single seed. Evaluates combined-227's reserved-19
     (Dataset-100 TEST+BLIND_HOLDOUT minus cfg043) under all 3 seeds already
     used elsewhere in this project (20260811/812/813) and locks the
     threshold as the MAX of the three seeds' own per-seed maxima -- i.e.
     robust to whichever seed a future final checkpoint happens to use, not
     just the single seed that happened to train first.
"""

import csv
from pathlib import Path

import numpy as np
import torch
from ase.io import read
from mace.calculators import MACECalculator

ROOT = Path("/workspace/ni_al")
DFT = ROOT / "data/datasets/ni_al_combined227_dft.extxyz"
TRAIN = ROOT / "data/datasets/ni_al_combined227_train_189.extxyz"
VALID = ROOT / "data/datasets/ni_al_combined227_validation_18.extxyz"
TEST = ROOT / "data/datasets/ni_al_dataset100_test_manifest.csv"
BLIND = ROOT / "data/datasets/ni_al_dataset100_blind_holdout_manifest.csv"

MODELS = {
    20260811: ROOT / "models/al3ni_combined227_lora_v1/al3ni_combined227_lora_v1.model",
    20260812: ROOT / "models/al3ni_combined227_seed20260812_lora_v1/al3ni_combined227_seed20260812_lora_v1.model",
    20260813: ROOT / "models/al3ni_combined227_seed20260813_lora_v1/al3ni_combined227_seed20260813_lora_v1.model",
}
PROBE_ID = "cfg043_Al3Ni_volume_rattle_expansion"
SEALED_IDS_DO_NOT_READ = {"cfg297_Al3Ni_iso_expansion", "cfg299_Al3Ni_volume_rattle_expansion"}


def predict(model_path, structures):
    calc = MACECalculator(model_paths=str(model_path), device="cuda", default_dtype="float64")
    out = {}
    for key, a in structures.items():
        w = a.copy()
        w.calc = calc
        out[key] = float(w.get_potential_energy())
    del calc
    torch.cuda.empty_cache()
    return out


def main():
    for seed, p in MODELS.items():
        if not p.exists():
            raise RuntimeError(f"missing model for seed {seed}: {p}")

    dft = read(DFT, index=":")
    by = {a.info["config_id"]: a for a in dft}
    if not SEALED_IDS_DO_NOT_READ.isdisjoint(by.keys() & SEALED_IDS_DO_NOT_READ):
        pass  # membership check only, never constructs/reads a sealed structure below

    memberships = {s: list(csv.DictReader(p.open())) for s, p in [("TEST", TEST), ("BLIND_HOLDOUT", BLIND)]}
    eval_ids = {r["config_id"] for rows in memberships.values() for r in rows}
    if len(eval_ids) != 20:
        raise RuntimeError("expected 20 unique reserved eval ids")
    reserved19 = eval_ids - {PROBE_ID}
    if len(reserved19) != 19:
        raise RuntimeError("expected 19 after excluding cfg043")

    train_ids = {a.info["config_id"] for a in read(TRAIN, index=":")}
    valid_ids = {a.info["config_id"] for a in read(VALID, index=":")}
    if not eval_ids.isdisjoint(train_ids) or not eval_ids.isdisjoint(valid_ids):
        raise RuntimeError("LEAKAGE: reserved eval ids found in TRAIN/VALIDATION")
    if not SEALED_IDS_DO_NOT_READ.isdisjoint(train_ids) or not SEALED_IDS_DO_NOT_READ.isdisjoint(valid_ids):
        raise RuntimeError("SEALED config id found in TRAIN/VALIDATION -- ABORTING")

    relaxed = {p: by[f"{p}_relaxed"] for p in ("AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3")}

    def dft_relative(cid):
        a = by[cid]
        phase = a.info["phase"]
        de = float(a.get_potential_energy())
        dre = float(relaxed[phase].get_potential_energy())
        return (de - dre) / len(a) * 1000

    dft_rel = {cid: dft_relative(cid) for cid in reserved19}

    per_seed = {}
    for seed, model_path in MODELS.items():
        print(f"Evaluating seed {seed}...", flush=True)
        structures = {f"reserved:{cid}": by[cid] for cid in reserved19}
        for phase, a in relaxed.items():
            structures[f"relaxed:{phase}"] = a
        pred = predict(model_path, structures)

        seed_result = {}
        for cid in reserved19:
            phase = by[cid].info["phase"]
            pre = (pred[f"reserved:{cid}"] - pred[f"relaxed:{phase}"]) / len(by[cid]) * 1000
            err = pre - dft_rel[cid]
            seed_result[cid] = abs(err)
        per_seed[seed] = seed_result

    seeds = sorted(MODELS)
    print("\n" + "=" * 100)
    print("PER-SEED RESERVED-19 (excl. cfg043) DISTRIBUTION")
    print("=" * 100)
    seed_maxes = {}
    for s in seeds:
        vals = per_seed[s]
        arr = np.array(list(vals.values()))
        mx_cid = max(vals, key=vals.get)
        seed_maxes[s] = (vals[mx_cid], mx_cid)
        print(f"\nseed {s}: min={arr.min():.4f} median={np.median(arr):.4f} p75={np.percentile(arr,75):.4f} "
              f"p90={np.percentile(arr,90):.4f} max={arr.max():.4f} (at {mx_cid})")

    locked = max(v[0] for v in seed_maxes.values())
    locked_seed = max(seed_maxes, key=lambda s: seed_maxes[s][0])
    locked_cid = seed_maxes[locked_seed][1]

    print("\n" + "=" * 100)
    print("SENSITIVITY TABLE (max of reserved-19, per seed)")
    print("=" * 100)
    for s in seeds:
        print(f"  seed {s}: max={seed_maxes[s][0]:.4f} (at {seed_maxes[s][1]})")
    spread = max(v[0] for v in seed_maxes.values()) - min(v[0] for v in seed_maxes.values())
    print(f"\n  spread across 3 seeds: {spread:.4f} meV/atom")
    print(f"  LOCKED THRESHOLD (max across seeds): {locked:.4f} meV/atom, from seed {locked_seed}, config {locked_cid}")


if __name__ == "__main__":
    main()
