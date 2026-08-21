#!/usr/bin/env python3
"""FINAL UNSEALING. Runs exactly once, ever, in this project's history.

Reads cfg109_Al3Ni_iso_expansion / cfg110_Al3Ni_volume_rattle_expansion
DFT labels (energy, forces, stress) for the first time -- both completed
successfully back on 2026-08-13 (JOB_DONE=YES, SCF_CONVERGED=YES,
config_complete.env) but were never read: every prior script that touched
these config_ids read geometry only, or explicitly skipped them (verified
by grep across configs/*_STATUS.txt, results/, and scripts/*.py before
this script was ever written).

Preconditions (re-verified in-script, defense in depth against the
preconditions already checked by hand before this file was written):
  - configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt sha256 matches the
    locked value referenced in this script.
  - models/al3ni_combined220_lora_v1/al3ni_combined220_lora_v1.model
    sha256 matches the frozen checkpoint already used for the reserved-20
    evaluation on record.

Evaluates the FROZEN al3ni_combined220_lora_v1 checkpoint on both configs
using the exact relative-energy formula used throughout this project:
(E_pred(config) - E_pred(phase_relaxed)) / natoms, vs. the DFT-derived
equivalent. Applies the locked threshold (2.3865 meV/atom, max of the 19
genuinely independent held-out configs, cfg060) verbatim, per-config, both
must pass.

This script does NOT merge cfg109/cfg110 into any TRAIN/VALIDATION split,
does NOT retrain anything. It is the acceptance-test read only.
"""

import hashlib
from datetime import datetime, timezone
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
ACCEPTANCE_FILE = ROOT / "configs/AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt"
ACCEPTANCE_SHA256_EXPECTED = "8e38968a1ce2b2e1213a2ce3d5ad60cdb127b17f1e5c99e44f64a36defbefd6a"
MODEL = ROOT / "models/al3ni_combined220_lora_v1/al3ni_combined220_lora_v1.model"
MODEL_SHA256_EXPECTED = "1c39751f9b0cc5cb3ecd0687e1d2fb5c6ee9f174256654a90b3e66d79f2dc6ee"
DATA = ROOT / "data/datasets/ni_al_combined220_dft.extxyz"
THRESHOLD_MEV_ATOM = 2.3865

CONFIGS = {
    "cfg109_Al3Ni_iso_expansion": {
        "structure": ROOT / "data/al3ni_remediation_v1/structures/cfg109_Al3Ni_iso_expansion.extxyz",
        "attempt": ROOT / "data/al3ni_remediation_v1/production_dft/cfg109_Al3Ni_iso_expansion/attempt_001",
    },
    "cfg110_Al3Ni_volume_rattle_expansion": {
        "structure": ROOT / "data/al3ni_remediation_v1/structures/cfg110_Al3Ni_volume_rattle_expansion.extxyz",
        "attempt": ROOT / "data/al3ni_remediation_v1/production_dft/cfg110_Al3Ni_volume_rattle_expansion/attempt_001",
    },
}

OUT_STATUS = ROOT / "configs/AL3NI_FINAL_UNSEALING_RESULT.txt"


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


def predict(path, structures):
    calc = MACECalculator(model_paths=str(path), device="cuda", default_dtype="float64")
    out = {}
    for key, a in structures.items():
        w = a.copy()
        w.calc = calc
        out[key] = float(w.get_potential_energy())
    del calc
    torch.cuda.empty_cache()
    return out


def main():
    # --- preconditions, re-verified in-script ---
    acc_sha = sha256(ACCEPTANCE_FILE)
    if acc_sha != ACCEPTANCE_SHA256_EXPECTED:
        raise RuntimeError(f"PRECONDITION FAILED: acceptance criterion sha256 mismatch "
                            f"(expected {ACCEPTANCE_SHA256_EXPECTED}, got {acc_sha}). STOPPING, no unsealing performed.")
    model_sha = sha256(MODEL)
    if model_sha != MODEL_SHA256_EXPECTED:
        raise RuntimeError(f"PRECONDITION FAILED: model sha256 mismatch "
                            f"(expected {MODEL_SHA256_EXPECTED}, got {model_sha}). STOPPING, no unsealing performed.")
    print(f"Precondition PASS: acceptance criterion sha256={acc_sha}")
    print(f"Precondition PASS: model sha256={model_sha}")

    # --- extract sealed labels for the first time ---
    extracted = {}
    for cid, paths in CONFIGS.items():
        attempt = paths["attempt"]
        meta_path = attempt / "config_complete.env"
        meta = dict(line.split("=", 1) for line in meta_path.read_text().splitlines() if "=" in line)
        if meta.get("EXIT_CODE") != "0" or meta.get("JOB_DONE") != "YES" or meta.get("SCF_CONVERGED") != "YES":
            raise RuntimeError(f"{cid}: DFT run did not complete cleanly, refusing to unseal ({meta})")

        qe_out = attempt / "qe.out"
        if sha256(qe_out) != meta.get("OUTPUT_SHA256"):
            raise RuntimeError(f"{cid}: qe.out sha256 changed since original DFT completion -- refusing to unseal")

        xmls = list((attempt / "tmp").glob("*.save/data-file-schema.xml"))
        if len(xmls) != 1:
            raise RuntimeError(f"{cid}: expected one QE XML, found {len(xmls)}")
        symbols, positions, cell, energy, forces, stress = xml_labels(xmls[0])

        pre_dft = read(paths["structure"])
        if len(symbols) != len(pre_dft):
            raise RuntimeError(f"{cid}: XML natoms does not match pre-DFT structure")
        if not np.allclose(cell, pre_dft.cell.array, rtol=0, atol=1e-6):
            raise RuntimeError(f"{cid}: XML cell does not match pre-DFT structure")
        vals = np.concatenate((positions.ravel(), cell.ravel(), np.atleast_1d(energy), forces.ravel(), stress.ravel()))
        if not np.isfinite(vals).all():
            raise RuntimeError(f"{cid}: non-finite extracted label or geometry")

        atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
        atoms.info.update({"config_id": cid, "phase": "Al3Ni"})
        atoms.calc = SinglePointCalculator(atoms, energy=energy, forces=forces, stress=stress)
        extracted[cid] = atoms
        print(f"Extracted (first read, ever) {cid}: E={energy:.6f} eV, natoms={len(atoms)}, "
              f"max|F|={np.linalg.norm(forces, axis=1).max():.6f} eV/A")

    # --- reference: Al3Ni_relaxed, same DFT source used throughout the project ---
    dft_frames = read(DATA, index=":")
    by = {a.info["config_id"]: a for a in dft_frames}
    relaxed = by["Al3Ni_relaxed"]
    dft_relaxed_e = float(relaxed.get_potential_energy())

    def dft_relative(cid, atoms):
        return (float(atoms.get_potential_energy()) - dft_relaxed_e) / len(atoms) * 1000

    dft_rel = {cid: dft_relative(cid, a) for cid, a in extracted.items()}

    # --- predict with the frozen combined-220 checkpoint ---
    structures = {"relaxed": relaxed}
    structures.update(extracted)
    print("Evaluating FROZEN al3ni_combined220_lora_v1 checkpoint...", flush=True)
    pred = predict(MODEL, structures)

    def pred_relative(cid, atoms):
        return (pred[cid] - pred["relaxed"]) / len(atoms) * 1000

    results = {}
    for cid, atoms in extracted.items():
        pre = pred_relative(cid, atoms)
        dre = dft_rel[cid]
        err = pre - dre
        abs_err = abs(err)
        verdict = "PASS" if abs_err <= THRESHOLD_MEV_ATOM else "FAIL"
        results[cid] = {"dft_relative": dre, "pred_relative": pre, "error": err, "abs_error": abs_err, "verdict": verdict}

    overall = "PASS" if all(r["verdict"] == "PASS" for r in results.values()) else "FAIL"

    lines = [
        "AL3NI FINAL UNSEALING RESULT -- IRREVERSIBLE, RUNS EXACTLY ONCE",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        "cfg109/cfg110 labels (energy, forces, stress) read for the FIRST TIME ever in this",
        "project's history, at this timestamp. This event does not repeat.",
        "",
        f"Acceptance criterion file: {ACCEPTANCE_FILE} sha256={acc_sha} (PRECONDITION VERIFIED)",
        f"Model (frozen): {MODEL} sha256={model_sha} (PRECONDITION VERIFIED)",
        f"THRESHOLD (locked, verbatim from acceptance criterion): {THRESHOLD_MEV_ATOM} meV/atom, per-config, both must pass",
        "",
        f"DFT relaxed reference (Al3Ni_relaxed): {dft_relaxed_e:.6f} eV",
        "",
    ]
    for cid, r in results.items():
        lines.append(f"=== {cid} ===")
        lines.append(f"  DFT relative energy:  {r['dft_relative']:.6f} meV/atom")
        lines.append(f"  Pred relative energy: {r['pred_relative']:.6f} meV/atom")
        lines.append(f"  Relative-energy error: {r['error']:.6f} meV/atom  |error|={r['abs_error']:.6f} meV/atom")
        lines.append(f"  Threshold: {THRESHOLD_MEV_ATOM} meV/atom -> {r['verdict']}")
        lines.append("")

    lines += [
        f"OVERALL RESULT: {overall}",
        "",
        "STATUS",
        "AL3NI FINAL UNSEALING COMPLETE. This evaluation is final and will not be repeated",
        "or revised. cfg109/cfg110 were NOT merged into any TRAIN/VALIDATION split and no",
        "retraining occurred as part of this event.",
    ]
    OUT_STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
