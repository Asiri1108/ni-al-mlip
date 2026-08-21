#!/usr/bin/env python3
"""Round285 success-criteria evaluation -- READ-ONLY.

Evaluates combined-220 (baseline) and combined-227 (post-round285) on
cfg109, cfg110, cfg043, and the reserved-20 (Dataset-100 TEST+BLIND_HOLDOUT),
same relative-energy formula used throughout this project. cfg109/cfg110
DFT labels re-read from the same QE outputs already unsealed once
(AL3NI_FINAL_UNSEALING_RESULT.txt) -- not re-unsealed here.

cfg297/cfg299 (round285's sealed confirmation pair) are NOT read anywhere
in this script -- not their geometry, not their labels.

Does NOT retrain. Does NOT merge. Does NOT modify any dataset file.
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
TEST = ROOT / "data/datasets/ni_al_dataset100_test_manifest.csv"
BLIND = ROOT / "data/datasets/ni_al_dataset100_blind_holdout_manifest.csv"

MODELS = {
    "combined220": {
        "model": ROOT / "models/al3ni_combined220_lora_v1/al3ni_combined220_lora_v1.model",
        "dft": ROOT / "data/datasets/ni_al_combined220_dft.extxyz",
        "train": ROOT / "data/datasets/ni_al_combined220_train_182.extxyz",
        "valid": ROOT / "data/datasets/ni_al_combined220_validation_18.extxyz",
    },
    "combined227": {
        "model": ROOT / "models/al3ni_combined227_lora_v1/al3ni_combined227_lora_v1.model",
        "dft": ROOT / "data/datasets/ni_al_combined227_dft.extxyz",
        "train": ROOT / "data/datasets/ni_al_combined227_train_189.extxyz",
        "valid": ROOT / "data/datasets/ni_al_combined227_validation_18.extxyz",
    },
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
# EXPLICIT EXCLUSION -- never read, never referenced anywhere below
SEALED_ROUND285_IDS_DO_NOT_READ = {"cfg297_Al3Ni_iso_expansion", "cfg299_Al3Ni_volume_rattle_expansion"}


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
    sealed_atoms = {cid: extract_sealed(cid, paths) for cid, paths in SEALED_CONFIGS.items()}

    memberships = {s: list(csv.DictReader(p.open())) for s, p in [("TEST", TEST), ("BLIND_HOLDOUT", BLIND)]}
    eval_ids = {r["config_id"] for rows in memberships.values() for r in rows}
    if len(eval_ids) != 20:
        raise RuntimeError("expected 20 unique reserved eval ids")

    results = {}
    for tag, paths in MODELS.items():
        print(f"Evaluating {tag}...", flush=True)
        dft = read(paths["dft"], index=":")
        by = {a.info["config_id"]: a for a in dft if a.info.get("phase") == "Al3Ni" or a.info["config_id"] in eval_ids or a.info["config_id"] == PROBE_ID}
        by_full = {a.info["config_id"]: a for a in dft}
        relaxed = {p: by_full[f"{p}_relaxed"] for p in ("AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3")}

        train_ids = {a.info["config_id"] for a in read(paths["train"], index=":")}
        valid_ids = {a.info["config_id"] for a in read(paths["valid"], index=":")}
        if not eval_ids.isdisjoint(train_ids) or not eval_ids.isdisjoint(valid_ids):
            raise RuntimeError(f"{tag}: LEAKAGE -- reserved eval ids found in TRAIN/VALIDATION")
        if PROBE_ID in train_ids or PROBE_ID in valid_ids:
            raise RuntimeError(f"{tag}: cfg043 unexpectedly in TRAIN/VALIDATION")
        for cid in SEALED_CONFIGS:
            if cid in train_ids or cid in valid_ids:
                raise RuntimeError(f"{tag}: {cid} unexpectedly in TRAIN/VALIDATION")
        if not train_ids.isdisjoint(SEALED_ROUND285_IDS_DO_NOT_READ) or not valid_ids.isdisjoint(SEALED_ROUND285_IDS_DO_NOT_READ):
            raise RuntimeError(f"{tag}: round285 SEALED config id found in TRAIN/VALIDATION -- ABORTING")

        dft_relaxed_al3ni = float(relaxed["Al3Ni"].get_potential_energy())

        def dft_relative_sealed(atoms):
            return (float(atoms.get_potential_energy()) - dft_relaxed_al3ni) / len(atoms) * 1000
        dft_rel_sealed = {cid: dft_relative_sealed(a) for cid, a in sealed_atoms.items()}

        def dft_relative_indataset(cid):
            a = by_full[cid]
            phase = a.info["phase"]
            de = float(a.get_potential_energy())
            dre = float(relaxed[phase].get_potential_energy())
            return (de - dre) / len(a) * 1000

        dft_rel_probe = dft_relative_indataset(PROBE_ID)
        dft_rel_reserved = {cid: dft_relative_indataset(cid) for cid in eval_ids}

        structures = {"relaxed:Al3Ni": relaxed["Al3Ni"]}
        structures.update({f"sealed:{cid}": a for cid, a in sealed_atoms.items()})
        structures[f"probe:{PROBE_ID}"] = by_full[PROBE_ID]
        structures.update({f"reserved:{cid}": by_full[cid] for cid in eval_ids})
        for phase, a in relaxed.items():
            structures[f"relaxed:{phase}"] = a
        pred = predict(paths["model"], structures)

        r = {}
        for cid in SEALED_CONFIGS:
            pre = (pred[f"sealed:{cid}"] - pred["relaxed:Al3Ni"]) / len(sealed_atoms[cid]) * 1000
            err = pre - dft_rel_sealed[cid]
            r[cid] = {"abs_error": abs(err)}

        pre_probe = (pred[f"probe:{PROBE_ID}"] - pred["relaxed:Al3Ni"]) / len(by_full[PROBE_ID]) * 1000
        r[PROBE_ID] = {"abs_error": abs(pre_probe - dft_rel_probe)}

        reserved = {}
        for cid in eval_ids:
            phase = by_full[cid].info["phase"]
            pre = (pred[f"reserved:{cid}"] - pred[f"relaxed:{phase}"]) / len(by_full[cid]) * 1000
            err = pre - dft_rel_reserved[cid]
            reserved[cid] = abs(err)
        errs = [(pred[f"reserved:{cid}"] - pred[f"relaxed:{by_full[cid].info['phase']}"]) / len(by_full[cid]) * 1000 - dft_rel_reserved[cid] for cid in eval_ids]
        rmse = float(np.sqrt(np.mean(np.square(errs))))
        mae = float(np.mean(np.abs(errs)))
        r["_reserved20_rmse"] = rmse
        r["_reserved20_mae"] = mae
        r["_reserved20_max"] = max(reserved.values())
        r["_reserved20_max_cid"] = max(reserved, key=reserved.get)

        results[tag] = r

    print("\n" + "=" * 100)
    print("RESULTS")
    print("=" * 100)
    for tag, r in results.items():
        print(f"\n{tag}:")
        print(f"  cfg109 |error| = {r['cfg109_Al3Ni_iso_expansion']['abs_error']:.4f} meV/atom")
        print(f"  cfg110 |error| = {r['cfg110_Al3Ni_volume_rattle_expansion']['abs_error']:.4f} meV/atom")
        print(f"  cfg043 |error| = {r[PROBE_ID]['abs_error']:.4f} meV/atom")
        print(f"  reserved-20 RMSE = {r['_reserved20_rmse']:.4f}  MAE = {r['_reserved20_mae']:.4f}  "
              f"MAX = {r['_reserved20_max']:.4f} (at {r['_reserved20_max_cid']})")

    c220 = results["combined220"]
    c227 = results["combined227"]
    d109 = c220['cfg109_Al3Ni_iso_expansion']['abs_error'] - c227['cfg109_Al3Ni_iso_expansion']['abs_error']
    d110 = c220['cfg110_Al3Ni_volume_rattle_expansion']['abs_error'] - c227['cfg110_Al3Ni_volume_rattle_expansion']['abs_error']

    print("\n" + "=" * 100)
    print("DELTA (combined220_error - combined227_error; positive = improvement)")
    print("=" * 100)
    print(f"cfg109: {c220['cfg109_Al3Ni_iso_expansion']['abs_error']:.4f} -> {c227['cfg109_Al3Ni_iso_expansion']['abs_error']:.4f}  delta={d109:+.4f}")
    print(f"cfg110: {c220['cfg110_Al3Ni_volume_rattle_expansion']['abs_error']:.4f} -> {c227['cfg110_Al3Ni_volume_rattle_expansion']['abs_error']:.4f}  delta={d110:+.4f}")

    NOISE_FLOOR = 0.43
    THRESHOLD = 2.4
    e109 = c227['cfg109_Al3Ni_iso_expansion']['abs_error']
    e110 = c227['cfg110_Al3Ni_volume_rattle_expansion']['abs_error']

    both_below_threshold = e109 < THRESHOLD and e110 < THRESHOLD
    both_beyond_noise = d109 > NOISE_FLOOR and d110 > NOISE_FLOOR
    at_least_one_beyond_noise = d109 > NOISE_FLOOR or d110 > NOISE_FLOOR
    both_within_noise = d109 <= NOISE_FLOOR and d110 <= NOISE_FLOOR

    if both_below_threshold and both_beyond_noise:
        verdict = "SUCCESS"
    elif at_least_one_beyond_noise and not both_below_threshold:
        verdict = "PARTIAL"
    elif both_within_noise:
        verdict = "FAILURE"
    else:
        verdict = "PARTIAL"  # at least one beyond noise, not both below threshold -- covered above but kept for completeness

    print("\n" + "=" * 100)
    print("VERDICT (per configs/ROUND285_SUCCESS_CRITERIA.txt, applied verbatim)")
    print("=" * 100)
    print(f"cfg109 < 2.4: {e109 < THRESHOLD}   cfg110 < 2.4: {e110 < THRESHOLD}")
    print(f"cfg109 delta > 0.43: {d109 > NOISE_FLOOR}   cfg110 delta > 0.43: {d110 > NOISE_FLOOR}")
    print(f"VERDICT: {verdict}")


if __name__ == "__main__":
    main()
