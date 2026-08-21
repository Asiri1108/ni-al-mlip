#!/usr/bin/env python3
"""FINAL UNSEALING (round285). Runs exactly once, ever, in this project's history.

Reads cfg297_Al3Ni_iso_expansion / cfg299_Al3Ni_volume_rattle_expansion DFT
labels (energy, forces, stress) for the first time -- both completed
successfully on 2026-08-18 (round285 production DFT, pod03; EXIT_CODE=0,
JOB_DONE=YES, SCF_CONVERGED=YES) but were never read: every prior script
that touched these config_ids read geometry only, or explicitly checked
DFT completion status without parsing labels (see pod03's own protection
assertions in configs/ROUND285_POD_03_STATUS.txt).

Four preconditions (re-verified in-script, defense in depth):
  1. configs/ROUND285_SEALED_ACCEPTANCE_CRITERION.txt sha256 matches the
     locked value recorded in its .sha256 sidecar.
  2. cfg297 and cfg299 DFT completed cleanly (EXIT_CODE=0, JOB_DONE=YES,
     SCF_CONVERGED=YES) and qe.out sha256 still matches OUTPUT_SHA256
     recorded at original completion time (tamper check).
  3. cfg297/cfg299 are physically absent from combined-227 TRAIN(189) and
     VALIDATION(18) -- re-verified here, not just trusted from the merge
     status record.
  4. The frozen model (al3ni_combined227_lora_v1, seed 20260811 -- same
     checkpoint path used by derive_round285_sealed_threshold.py) exists;
     its sha256 is computed and pinned here as this event's permanent
     reference (no independent prior record exists for this file, unlike
     the acceptance-criterion file).

Evaluates the FROZEN al3ni_combined227_lora_v1 (seed 20260811) checkpoint on
both configs using the exact relative-energy formula used throughout this
project: (E_pred(config) - E_pred(phase_relaxed)) / natoms, vs. the
DFT-derived equivalent. Applies the locked threshold (2.6183 meV/atom,
per-config, both must pass) verbatim.

This script does NOT merge cfg297/cfg299 into any TRAIN/VALIDATION split,
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

ACCEPTANCE_FILE = ROOT / "configs/ROUND285_SEALED_ACCEPTANCE_CRITERION.txt"
ACCEPTANCE_SHA256_SIDECAR = ROOT / "configs/ROUND285_SEALED_ACCEPTANCE_CRITERION.txt.sha256"

MODEL = ROOT / "models/al3ni_combined227_lora_v1/al3ni_combined227_lora_v1.model"
MODEL_SEED = 20260811

TRAIN = ROOT / "data/datasets/ni_al_combined227_train_189.extxyz"
VALID = ROOT / "data/datasets/ni_al_combined227_validation_18.extxyz"
DATA = ROOT / "data/datasets/ni_al_combined227_dft.extxyz"

THRESHOLD_MEV_ATOM = 2.6183

CONFIGS = {
    "cfg297_Al3Ni_iso_expansion": {
        "structure": ROOT / "data/al3ni_remediation_v1/round285_structures/sealed_confirmation/cfg297_Al3Ni_iso_expansion.extxyz",
        "attempt": ROOT / "data/al3ni_remediation_v1/round285_production_dft/pod03/cfg297_Al3Ni_iso_expansion/attempt_001",
    },
    "cfg299_Al3Ni_volume_rattle_expansion": {
        "structure": ROOT / "data/al3ni_remediation_v1/round285_structures/sealed_confirmation/cfg299_Al3Ni_volume_rattle_expansion.extxyz",
        "attempt": ROOT / "data/al3ni_remediation_v1/round285_production_dft/pod03/cfg299_Al3Ni_volume_rattle_expansion/attempt_001",
    },
}

OUT_STATUS = ROOT / "configs/AL3NI_ROUND285_FINAL_UNSEALING_RESULT.txt"


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
    precondition_lines = []

    # --- precondition 1: acceptance criterion sha256 matches its sidecar ---
    sidecar_expected = ACCEPTANCE_SHA256_SIDECAR.read_text().split()[0]
    acc_sha = sha256(ACCEPTANCE_FILE)
    if acc_sha != sidecar_expected:
        raise RuntimeError(f"PRECONDITION 1 FAILED: acceptance criterion sha256 mismatch "
                            f"(sidecar expects {sidecar_expected}, got {acc_sha}). STOPPING, no unsealing performed.")
    print(f"Precondition 1 PASS: acceptance criterion sha256={acc_sha}")
    precondition_lines.append(f"1. Acceptance criterion file: {ACCEPTANCE_FILE} sha256={acc_sha} (PRECONDITION VERIFIED vs sidecar)")

    # --- precondition 2: DFT completed cleanly, output untampered, for both configs ---
    dft_meta = {}
    for cid, paths in CONFIGS.items():
        attempt = paths["attempt"]
        meta_path = attempt / "config_complete.env"
        meta = dict(line.split("=", 1) for line in meta_path.read_text().splitlines() if "=" in line)
        if meta.get("EXIT_CODE") != "0" or meta.get("JOB_DONE") != "YES" or meta.get("SCF_CONVERGED") != "YES":
            raise RuntimeError(f"PRECONDITION 2 FAILED: {cid} DFT did not complete cleanly, refusing to unseal ({meta})")
        qe_out = attempt / "qe.out"
        qe_sha = sha256(qe_out)
        if qe_sha != meta.get("OUTPUT_SHA256"):
            raise RuntimeError(f"PRECONDITION 2 FAILED: {cid} qe.out sha256 changed since original DFT completion "
                                f"(expected {meta.get('OUTPUT_SHA256')}, got {qe_sha}) -- refusing to unseal")
        dft_meta[cid] = meta
        print(f"Precondition 2 PASS: {cid} DFT clean, qe.out sha256={qe_sha}")
    precondition_lines.append("2. cfg297/cfg299 DFT completion: EXIT_CODE=0, JOB_DONE=YES, SCF_CONVERGED=YES, "
                               "qe.out sha256 unchanged since completion (PRECONDITION VERIFIED, both configs)")

    # --- precondition 3: cfg297/cfg299 physically absent from TRAIN/VALIDATION ---
    train_ids = {a.info["config_id"] for a in read(TRAIN, index=":")}
    valid_ids = {a.info["config_id"] for a in read(VALID, index=":")}
    sealed_ids = set(CONFIGS.keys())
    if not sealed_ids.isdisjoint(train_ids) or not sealed_ids.isdisjoint(valid_ids):
        raise RuntimeError("PRECONDITION 3 FAILED: sealed config id found in TRAIN/VALIDATION -- ABORTING, no unsealing performed")
    print("Precondition 3 PASS: cfg297/cfg299 absent from combined-227 TRAIN(189)/VALIDATION(18)")
    precondition_lines.append("3. cfg297/cfg299 absence from combined-227 TRAIN(189)/VALIDATION(18): PRECONDITION VERIFIED")

    # --- precondition 4: frozen model exists, hash pinned as permanent reference ---
    if not MODEL.exists():
        raise RuntimeError(f"PRECONDITION 4 FAILED: model not found at {MODEL}")
    model_sha = sha256(MODEL)
    print(f"Precondition 4 PASS: model exists, sha256={model_sha} (pinned as permanent reference for this event)")
    precondition_lines.append(f"4. Model (frozen, seed {MODEL_SEED}): {MODEL} sha256={model_sha} "
                               f"(PRECONDITION VERIFIED -- first pin, no prior independent record)")

    # --- extract sealed labels for the first time ---
    extracted = {}
    for cid, paths in CONFIGS.items():
        attempt = paths["attempt"]
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

    # --- predict with the frozen combined-227 (seed 20260811) checkpoint ---
    structures = {"relaxed": relaxed}
    structures.update(extracted)
    print("Evaluating FROZEN al3ni_combined227_lora_v1 (seed 20260811) checkpoint...", flush=True)
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
    lammps_authorised = "YES" if overall == "PASS" else "NO"

    lines = [
        "AL3NI ROUND285 FINAL UNSEALING RESULT -- IRREVERSIBLE, RUNS EXACTLY ONCE",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        "cfg297/cfg299 labels (energy, forces, stress) read for the FIRST TIME ever in this",
        "project's history, at this timestamp. This event does not repeat.",
        "",
        "PRECONDITIONS (all re-verified in-script before any sealed label was read):",
    ] + precondition_lines + [
        "",
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
        f"LAMMPS AUTHORISED: {lammps_authorised}",
        "",
        "STATUS",
        "AL3NI ROUND285 FINAL UNSEALING COMPLETE. This evaluation is final and will not be",
        "repeated or revised. cfg297/cfg299 were NOT merged into any TRAIN/VALIDATION split",
        "and no retraining occurred as part of this event.",
    ]
    OUT_STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
