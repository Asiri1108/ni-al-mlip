#!/usr/bin/env python3
"""Seed-variance noise floor measurement -- READ-ONLY.

Evaluates THREE combined-220 checkpoints, identical data/hyperparameters,
seed 20260811 (original al3ni_combined220_lora_v1) / 20260812 / 20260813,
on:
  - cfg109_Al3Ni_iso_expansion, cfg110_Al3Ni_volume_rattle_expansion
    (already unsealed once, per AL3NI_FINAL_UNSEALING_RESULT.txt -- their
    DFT labels are re-read here from the same QE XML outputs already read
    at unsealing time; this script does not unseal anything new)
  - cfg043_Al3Ni_volume_rattle_expansion (continuity probe, in the DFT set)
  - the reserved-20 (Dataset-100 TEST+BLIND_HOLDOUT), same set used to
    derive the locked 2.3865 meV/atom threshold

Same relative-energy formula throughout this project:
(E_pred(config) - E_pred(phase_relaxed)) / natoms, vs the DFT equivalent.

Does NOT retrain. Does NOT merge cfg109/cfg110 into TRAIN/VALIDATION.
Does NOT modify any dataset file.
"""

import csv
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import torch
from ase import Atoms
from ase.calculators.singlepoint import SinglePointCalculator
from ase.io import read
from ase.units import Bohr, Hartree
from mace.calculators import MACECalculator

ROOT = Path("/workspace/ni_al")
DATA = ROOT / "data/datasets/ni_al_combined220_dft.extxyz"
TEST = ROOT / "data/datasets/ni_al_dataset100_test_manifest.csv"
BLIND = ROOT / "data/datasets/ni_al_dataset100_blind_holdout_manifest.csv"
TRAIN_FILE = ROOT / "data/datasets/ni_al_combined220_train_182.extxyz"
VALID_FILE = ROOT / "data/datasets/ni_al_combined220_validation_18.extxyz"

MODELS = {
    20260811: ROOT / "models/al3ni_combined220_lora_v1/al3ni_combined220_lora_v1.model",
    20260812: ROOT / "models/al3ni_combined220_seed20260812_lora_v1/al3ni_combined220_seed20260812_lora_v1.model",
    20260813: ROOT / "models/al3ni_combined220_seed20260813_lora_v1/al3ni_combined220_seed20260813_lora_v1.model",
}

SEALED_CONFIGS = {
    "cfg109_Al3Ni_iso_expansion": {
        "structure": ROOT / "data/al3ni_remediation_v1/structures/cfg109_Al3Ni_iso_expansion.extxyz",
        "attempt": ROOT / "data/al3ni_remediation_v1/production_dft/cfg109_Al3Ni_iso_expansion/attempt_001",
    },
    "cfg110_Al3Ni_volume_rattle_expansion": {
        "structure": ROOT / "data/al3ni_remediation_v1/structures/cfg110_Al3Ni_volume_rattle_expansion.extxyz",
        "attempt": ROOT / "data/al3ni_remediation_v1/production_dft/cfg110_Al3Ni_volume_rattle_expansion/attempt_001",
    },
}
PROBE_ID = "cfg043_Al3Ni_volume_rattle_expansion"
THRESHOLD_MEV_ATOM = 2.3865


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def xml_labels(xml_path):
    root = ET.parse(xml_path).getroot()
    output = root.find("output")
    structure = output.find("atomic_structure")
    cell_node = structure.find("cell")
    pos_node = structure.find("atomic_positions")
    cell = np.array([[float(x.replace("D", "E")) for x in cell_node.find(k).text.split()]
                     for k in ("a1", "a2", "a3")], dtype=np.float64) * Bohr
    symbols, positions = [], []
    for atom in pos_node.findall("atom"):
        symbols.append(atom.attrib["name"])
        positions.append([float(x.replace("D", "E")) for x in atom.text.split()])
    positions = np.asarray(positions, dtype=np.float64) * Bohr
    energy = float(output.find("total_energy/etot").text.strip().replace("D", "E")) * Hartree
    forces = np.fromstring(output.find("forces").text.replace("D", "E"), sep=" ", dtype=np.float64).reshape((-1, 3)) * Hartree / Bohr
    stress = -np.fromstring(output.find("stress").text.replace("D", "E"), sep=" ", dtype=np.float64).reshape((3, 3)) * Hartree / (Bohr ** 3)
    if len(symbols) != int(structure.attrib["nat"]) or forces.shape != (len(symbols), 3):
        raise ValueError("QE XML atom/force dimensions inconsistent")
    return symbols, positions, cell, energy, forces, stress


def extract_sealed(cid, paths):
    attempt = paths["attempt"]
    meta_path = attempt / "config_complete.env"
    meta = dict(line.split("=", 1) for line in meta_path.read_text().splitlines() if "=" in line)
    if meta.get("EXIT_CODE") != "0" or meta.get("JOB_DONE") != "YES" or meta.get("SCF_CONVERGED") != "YES":
        raise RuntimeError(f"{cid}: DFT run did not complete cleanly ({meta})")
    qe_out = attempt / "qe.out"
    if sha256(qe_out) != meta.get("OUTPUT_SHA256"):
        raise RuntimeError(f"{cid}: qe.out sha256 changed since original DFT completion")
    xmls = list((attempt / "tmp").glob("*.save/data-file-schema.xml"))
    if len(xmls) != 1:
        raise RuntimeError(f"{cid}: expected one QE XML, found {len(xmls)}")
    symbols, positions, cell, energy, forces, stress = xml_labels(xmls[0])
    pre_dft = read(paths["structure"])
    if len(symbols) != len(pre_dft):
        raise RuntimeError(f"{cid}: XML natoms does not match pre-DFT structure")
    if not np.allclose(cell, pre_dft.cell.array, rtol=0, atol=1e-6):
        raise RuntimeError(f"{cid}: XML cell does not match pre-DFT structure")
    atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
    atoms.info.update({"config_id": cid, "phase": "Al3Ni"})
    atoms.calc = SinglePointCalculator(atoms, energy=energy, forces=forces, stress=stress)
    return atoms


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

    frames = read(DATA, index=":")
    by = {a.info["config_id"]: a for a in frames}
    relaxed = {p: by[f"{p}_relaxed"] for p in ("AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3")}

    memberships = {s: list(csv.DictReader(p.open())) for s, p in [("TEST", TEST), ("BLIND_HOLDOUT", BLIND)]}
    eval_ids = {r["config_id"] for rows in memberships.values() for r in rows}
    if len(eval_ids) != 20:
        raise RuntimeError("expected 20 unique reserved eval ids")

    train_ids = {a.info["config_id"] for a in read(TRAIN_FILE, index=":")}
    valid_ids = {a.info["config_id"] for a in read(VALID_FILE, index=":")}
    if eval_ids & train_ids or eval_ids & valid_ids:
        raise RuntimeError("LEAKAGE: reserved eval ids found in TRAIN/VALIDATION")
    if PROBE_ID in train_ids or PROBE_ID in valid_ids:
        raise RuntimeError("cfg043 unexpectedly in TRAIN/VALIDATION")
    for cid in SEALED_CONFIGS:
        if cid in train_ids or cid in valid_ids:
            raise RuntimeError(f"{cid} unexpectedly in TRAIN/VALIDATION -- ABORTING, sealed config must not be merged")

    sealed_atoms = {cid: extract_sealed(cid, paths) for cid, paths in SEALED_CONFIGS.items()}
    dft_relaxed_al3ni = float(relaxed["Al3Ni"].get_potential_energy())

    def dft_relative_sealed(atoms):
        return (float(atoms.get_potential_energy()) - dft_relaxed_al3ni) / len(atoms) * 1000

    dft_rel_sealed = {cid: dft_relative_sealed(a) for cid, a in sealed_atoms.items()}

    def dft_relative_indataset(cid):
        a = by[cid]
        phase = a.info["phase"]
        de = float(a.get_potential_energy())
        dre = float(relaxed[phase].get_potential_energy())
        return (de - dre) / len(a) * 1000

    dft_rel_probe = dft_relative_indataset(PROBE_ID)
    dft_rel_reserved = {cid: dft_relative_indataset(cid) for cid in eval_ids}

    # per-seed predictions
    per_seed = {}
    for seed, model_path in MODELS.items():
        print(f"Evaluating seed {seed} ({model_path.name})...", flush=True)
        structures = {"relaxed:Al3Ni": relaxed["Al3Ni"]}
        structures.update({f"sealed:{cid}": a for cid, a in sealed_atoms.items()})
        structures[f"probe:{PROBE_ID}"] = by[PROBE_ID]
        structures.update({f"reserved:{cid}": by[cid] for cid in eval_ids})
        for phase, a in relaxed.items():
            structures[f"relaxed:{phase}"] = a
        pred = predict(model_path, structures)

        seed_result = {}
        for cid in SEALED_CONFIGS:
            pre = (pred[f"sealed:{cid}"] - pred["relaxed:Al3Ni"]) / len(sealed_atoms[cid]) * 1000
            err = pre - dft_rel_sealed[cid]
            seed_result[cid] = {"dft": dft_rel_sealed[cid], "pred": pre, "error": err, "abs_error": abs(err)}

        pre_probe = (pred[f"probe:{PROBE_ID}"] - pred["relaxed:Al3Ni"]) / len(by[PROBE_ID]) * 1000
        err_probe = pre_probe - dft_rel_probe
        seed_result[PROBE_ID] = {"dft": dft_rel_probe, "pred": pre_probe, "error": err_probe, "abs_error": abs(err_probe)}

        reserved_result = {}
        for cid in eval_ids:
            phase = by[cid].info["phase"]
            pre = (pred[f"reserved:{cid}"] - pred[f"relaxed:{phase}"]) / len(by[cid]) * 1000
            err = pre - dft_rel_reserved[cid]
            reserved_result[cid] = {"dft": dft_rel_reserved[cid], "pred": pre, "error": err, "abs_error": abs(err), "phase": phase}
        seed_result["_reserved20"] = reserved_result

        per_seed[seed] = seed_result

    seeds = sorted(MODELS)

    def spread(vals):
        v = np.asarray(vals, float)
        return float(v.max() - v.min()), float(v.std(ddof=0)), float(v.std(ddof=1)) if len(v) > 1 else 0.0

    print("\n" + "=" * 100)
    print("PER-CONFIG SEED VARIANCE (abs relative-energy error, meV/atom)")
    print("=" * 100)
    focus_rows = {}
    for cid in list(SEALED_CONFIGS) + [PROBE_ID]:
        vals = [per_seed[s][cid]["abs_error"] for s in seeds]
        mx, sd_pop, sd_samp = spread(vals)
        focus_rows[cid] = (vals, mx, sd_pop, sd_samp)
        print(f"\n{cid}")
        for s, v in zip(seeds, vals):
            print(f"  seed {s}: {v:.4f}")
        print(f"  spread(max-min)={mx:.4f}  std(population)={sd_pop:.4f}  std(sample,n-1)={sd_samp:.4f}")

    print("\n" + "=" * 100)
    print("RESERVED-20: per-config abs relative-energy error across seeds")
    print("=" * 100)
    reserved_spreads = {}
    for cid in sorted(eval_ids):
        vals = [per_seed[s]["_reserved20"][cid]["abs_error"] for s in seeds]
        mx, sd_pop, sd_samp = spread(vals)
        reserved_spreads[cid] = (vals, mx, sd_pop, sd_samp)
        print(f"  {cid} ({per_seed[seeds[0]]['_reserved20'][cid]['phase']}): "
              f"seed811={vals[0]:.4f} seed812={vals[1]:.4f} seed813={vals[2]:.4f} "
              f"spread={mx:.4f} std={sd_pop:.4f}")

    print("\n" + "=" * 100)
    print("RESERVED-20 AGGREGATE PER SEED")
    print("=" * 100)
    agg = {}
    for s in seeds:
        errs = [per_seed[s]["_reserved20"][cid]["error"] for cid in eval_ids]
        abs_errs = [per_seed[s]["_reserved20"][cid]["abs_error"] for cid in eval_ids]
        rmse = float(np.sqrt(np.mean(np.square(errs))))
        mae = float(np.mean(np.abs(errs)))
        mx_cid = max(eval_ids, key=lambda c: per_seed[s]["_reserved20"][c]["abs_error"])
        agg[s] = {"rmse": rmse, "mae": mae, "max": max(abs_errs), "max_cid": mx_cid}
        print(f"  seed {s}: RMSE={rmse:.4f}  MAE={mae:.4f}  MAX={max(abs_errs):.4f} (at {mx_cid})")

    max_vals = [agg[s]["max"] for s in seeds]
    rmse_vals = [agg[s]["rmse"] for s in seeds]
    max_spread, max_sd_pop, _ = spread(max_vals)
    rmse_spread, rmse_sd_pop, _ = spread(rmse_vals)
    print(f"\n  RESERVED-20 MAX spread across seeds: {max_spread:.4f} meV/atom (std={max_sd_pop:.4f})")
    print(f"  RESERVED-20 RMSE spread across seeds: {rmse_spread:.4f} meV/atom (std={rmse_sd_pop:.4f})")
    same_cid = len({agg[s]["max_cid"] for s in seeds}) == 1
    print(f"  MAX held by same config across all 3 seeds: {same_cid} ({[agg[s]['max_cid'] for s in seeds]})")

    print("\n" + "=" * 100)
    print("FAILURE MARGIN VS THRESHOLD (2.3865 meV/atom), per seed")
    print("=" * 100)
    for cid in SEALED_CONFIGS:
        for s in seeds:
            ae = per_seed[s][cid]["abs_error"]
            margin = ae - THRESHOLD_MEV_ATOM
            verdict = "FAIL" if ae > THRESHOLD_MEV_ATOM else "PASS"
            print(f"  {cid} seed {s}: |error|={ae:.4f}  margin_over_threshold={margin:+.4f}  {verdict}")

    cfg109_spread = focus_rows["cfg109_Al3Ni_iso_expansion"][1]
    cfg110_spread = focus_rows["cfg110_Al3Ni_volume_rattle_expansion"][1]
    cfg043_spread = focus_rows[PROBE_ID][1]
    original_margin_109 = per_seed[20260811]["cfg109_Al3Ni_iso_expansion"]["abs_error"] - THRESHOLD_MEV_ATOM
    original_margin_110 = per_seed[20260811]["cfg110_Al3Ni_volume_rattle_expansion"]["abs_error"] - THRESHOLD_MEV_ATOM

    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"SEED SPREAD CFG109: {cfg109_spread:.4f} meV/atom")
    print(f"SEED SPREAD CFG110: {cfg110_spread:.4f} meV/atom")
    print(f"SEED SPREAD CFG043: {cfg043_spread:.4f} meV/atom")
    print(f"RESERVED-20 MAX PER SEED: " + ", ".join(f"seed{s}={agg[s]['max']:.4f}" for s in seeds))
    print(f"RESERVED-20 RMSE PER SEED: " + ", ".join(f"seed{s}={agg[s]['rmse']:.4f}" for s in seeds))
    print(f"Original (seed 20260811) failure margins: cfg109={original_margin_109:+.4f}  cfg110={original_margin_110:+.4f}")
    exceeds = (cfg109_spread < abs(original_margin_109)) and (cfg110_spread < abs(original_margin_110))
    print(f"FAILURE MARGIN VS NOISE FLOOR: {'margin exceeds noise' if exceeds else 'margin within noise'}")


if __name__ == "__main__":
    main()
