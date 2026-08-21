#!/usr/bin/env python3
"""Deterministically assemble immutable Pilot-25 and Expansion-75 DFT datasets."""

import csv
import hashlib
import os
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np
from ase.calculators.singlepoint import SinglePointCalculator
from ase.io import read, write

ROOT = Path("/workspace/ni_al")
PILOT = ROOT / "data/processed/ni_al_pilot_dft_25.extxyz"
EXPANSION = ROOT / "data/processed/ni_al_expansion_dft_75.extxyz"
PILOT_SHA = "35b2b65fe77d181b5da30dd23bbb7ff9fc4f41c0c0f603738172e2f833ab5b0b"
EXPANSION_SHA = "ff69c2bfed14bfcf48931949647d8f1b3c9353a89c20378c9113155940792137"
OUT = ROOT / "data/datasets/ni_al_dataset100_dft.extxyz"
MANIFEST = ROOT / "data/datasets/ni_al_dataset100_dft_manifest.csv"
CHECKSUM = ROOT / "data/datasets/ni_al_dataset100_dft.extxyz.sha256"
PHASES = ROOT / "data/datasets/ni_al_dataset100_dft_phase_summary.txt"
PERTURBATIONS = ROOT / "data/datasets/ni_al_dataset100_dft_perturbation_summary.csv"
PROVENANCE = ROOT / "data/datasets/ni_al_dataset100_dft_provenance_summary.txt"
STATUS = ROOT / "configs/DATASET100_ASSEMBLY_STATUS.txt"
EXPECTED_PHASES = {"AlNi": 18, "Al3Ni2": 19, "AlNi3": 17, "Al3Ni5": 22, "Al3Ni": 24}
SCHEMA = {
    "config_id", "phase", "config_type", "source", "dataset_origin",
    "source_record", "original_dataset", "original_dataset_sha256",
    "provenance", "qe_output_sha256", "canonical_input",
    "canonical_input_sha256",
}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def digest_array(value):
    a = np.asarray(value, dtype=np.float64)
    return hashlib.sha256(a.tobytes(order="C")).hexdigest()


def publish_bytes(path, content):
    """Create artifact, or accept an existing artifact only when byte-identical."""
    content = bytes(content)
    if path.exists():
        if path.read_bytes() != content:
            raise RuntimeError(f"refusing to overwrite divergent canonical artifact: {path}")
        return "IDENTICAL_EXISTING"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return "CREATED"


def normalized_frame(source, origin):
    result = source.calc.results
    atoms = source.copy()
    energy = np.float64(result["energy"])
    forces = np.array(result["forces"], dtype=np.float64, copy=True)
    stress = np.array(source.get_stress(), dtype=np.float64, copy=True)
    atoms.calc = SinglePointCalculator(atoms, energy=energy, forces=forces, stress=stress)
    cid = str(source.info["config_id"])
    if origin == "Pilot-25":
        additions = {
            "dataset_origin": origin,
            "source_record": f"Pilot-25:{cid}",
            "original_dataset": str(PILOT),
            "original_dataset_sha256": PILOT_SHA,
            "provenance": str(ROOT / "configs/PILOT25_PROVENANCE.txt"),
            "qe_output_sha256": "historical_not_recorded",
            "canonical_input": "historical_not_recorded",
            "canonical_input_sha256": "historical_not_recorded",
        }
    else:
        additions = {
            "dataset_origin": origin,
            "source_record": f"Expansion-75:{source.info['qe_output_sha256']}",
            "original_dataset": str(EXPANSION),
            "original_dataset_sha256": EXPANSION_SHA,
        }
    atoms.info.update(additions)
    if set(atoms.info) != SCHEMA:
        raise RuntimeError(f"{cid}: metadata schema mismatch: {sorted(atoms.info)}")
    return atoms


def main():
    if sha256(PILOT) != PILOT_SHA:
        raise RuntimeError("Pilot-25 SHA256 does not match canonical historical identity")
    if sha256(EXPANSION) != EXPANSION_SHA:
        raise RuntimeError("Expansion-75 SHA256 does not match verified identity")
    pilot = read(PILOT, index=":")
    expansion = read(EXPANSION, index=":")
    if len(pilot) != 25 or len(expansion) != 75:
        raise RuntimeError(f"input composition mismatch: Pilot={len(pilot)}, Expansion={len(expansion)}")
    frames = [normalized_frame(a, "Pilot-25") for a in pilot]
    frames += [normalized_frame(a, "Expansion-75") for a in expansion]

    ids = [a.info["config_id"] for a in frames]
    records = [a.info["source_record"] for a in frames]
    origins = Counter(a.info["dataset_origin"] for a in frames)
    phases = Counter(a.info["phase"] for a in frames)
    types = Counter((a.info["dataset_origin"], a.info["config_type"]) for a in frames)
    expected_expansion = {f"cfg{i:03d}_" for i in range(26, 101)}
    found_expansion = {next((p for p in expected_expansion if cid.startswith(p)), "") for cid in ids if cid.startswith("cfg")}
    missing_expansion = sorted(expected_expansion - found_expansion)
    if len(frames) != 100 or origins != {"Pilot-25": 25, "Expansion-75": 75}:
        raise RuntimeError(f"dataset composition failure: frames={len(frames)}, origins={dict(origins)}")
    if len(set(ids)) != 100:
        raise RuntimeError("duplicate config IDs")
    if len(set(records)) != 100:
        raise RuntimeError("duplicate source records")
    if missing_expansion:
        raise RuntimeError(f"missing expansion IDs: {missing_expansion}")
    if dict(phases) != EXPECTED_PHASES:
        raise RuntimeError(f"canonical phase counts mismatch: {dict(phases)}")
    if any(a.info["phase"] not in EXPECTED_PHASES for a in frames):
        raise RuntimeError("non-canonical phase label")
    for a in frames:
        results = a.calc.results if a.calc else {}
        if not np.isfinite(results.get("energy", np.nan)):
            raise RuntimeError(f"{a.info['config_id']}: missing/non-finite energy")
        if np.asarray(results.get("forces", [])).shape != (len(a), 3) or not np.isfinite(results["forces"]).all():
            raise RuntimeError(f"{a.info['config_id']}: incomplete/non-finite forces")
        if np.asarray(a.get_stress()).shape != (6,) or not np.isfinite(a.get_stress()).all():
            raise RuntimeError(f"{a.info['config_id']}: incomplete/non-finite stress")
        if not a.pbc.all() or not np.isfinite(a.positions).all() or not np.isfinite(a.cell.array).all():
            raise RuntimeError(f"{a.info['config_id']}: invalid periodic geometry")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fd, candidate_name = tempfile.mkstemp(prefix=f".{OUT.name}.candidate.", dir=OUT.parent)
    os.close(fd)
    candidate = Path(candidate_name)
    try:
        write(candidate, frames, format="extxyz")
        candidate_bytes = candidate.read_bytes()
    finally:
        if candidate.exists():
            candidate.unlink()
    publish_bytes(OUT, candidate_bytes)
    dataset_sha = sha256(OUT)

    combined = read(OUT, index=":")
    if len(combined) != 100:
        raise RuntimeError("assembled read-back frame count mismatch")
    missing_labels = 0
    manifest_rows = []
    for source, assembled in zip(pilot + expansion, combined):
        sr, ar = source.calc.results, assembled.calc.results
        if (np.float64(sr["energy"]) != np.float64(ar["energy"])
                or not np.array_equal(np.asarray(sr["forces"]), np.asarray(ar["forces"]))
                or not np.array_equal(source.get_stress(), assembled.get_stress())):
            raise RuntimeError(f"{assembled.info['config_id']}: DFT label changed during assembly")
        if set(assembled.info) != SCHEMA:
            raise RuntimeError(f"{assembled.info['config_id']}: read-back schema mismatch")
        if not {"energy", "forces", "stress"}.issubset(ar):
            missing_labels += 1
        manifest_rows.append({
            "index": len(manifest_rows), "config_id": assembled.info["config_id"],
            "phase": assembled.info["phase"], "config_type": assembled.info["config_type"],
            "dataset_origin": assembled.info["dataset_origin"], "source_record": assembled.info["source_record"],
            "natoms": len(assembled), "energy_eV": format(float(ar["energy"]), ".17g"),
            "energy_sha256_float64": digest_array([ar["energy"]]),
            "forces_shape": f"{len(assembled)}x3", "forces_sha256_float64": digest_array(ar["forces"]),
            "stress_shape": "6", "stress_sha256_float64": digest_array(assembled.get_stress()),
            "original_dataset": assembled.info["original_dataset"],
            "original_dataset_sha256": assembled.info["original_dataset_sha256"],
            "provenance": assembled.info["provenance"],
            "canonical_input": assembled.info["canonical_input"],
            "canonical_input_sha256": assembled.info["canonical_input_sha256"],
            "qe_output_sha256": assembled.info["qe_output_sha256"],
        })
    if missing_labels:
        raise RuntimeError(f"missing labels after read-back: {missing_labels}")

    fields = list(manifest_rows[0])
    import io
    sio = io.StringIO(newline="")
    writer = csv.DictWriter(sio, fieldnames=fields); writer.writeheader(); writer.writerows(manifest_rows)
    publish_bytes(MANIFEST, sio.getvalue().encode())
    publish_bytes(CHECKSUM, f"{dataset_sha}  {OUT.name}\n".encode())
    phase_text = "\n".join(["CANONICAL DATASET-100 PHASE SUMMARY", *(f"{p} = {phases[p]}" for p in ["AlNi", "Al3Ni2", "AlNi3", "Al3Ni5", "Al3Ni"]), "TOTAL = 100", ""])
    publish_bytes(PHASES, phase_text.encode())
    psio = io.StringIO(newline="")
    pw = csv.writer(psio); pw.writerow(["dataset_origin", "config_type", "count"])
    for (origin, kind), count in sorted(types.items()): pw.writerow([origin, kind, count])
    publish_bytes(PERTURBATIONS, psio.getvalue().encode())
    provenance_text = "\n".join([
        "CANONICAL DATASET-100 PROVENANCE SUMMARY", "",
        f"Canonical dataset: {OUT}", f"Canonical dataset SHA256: {dataset_sha}", "",
        "INPUT A — PILOT-25", f"Path: {PILOT}", f"SHA256: {PILOT_SHA}", "Frames: 25",
        f"Permanent provenance: {ROOT / 'configs/PILOT25_PROVENANCE.txt'}", "",
        "INPUT B — EXPANSION-75", f"Path: {EXPANSION}", f"SHA256: {EXPANSION_SHA}", "Frames: 75",
        f"Per-frame QE provenance: {ROOT / 'data/processed/ni_al_expansion_dft_75_manifest.csv'}", "",
        "ASSEMBLY GUARANTEES",
        "Inputs were read only. No DFT was recalculated. Energies were not shifted or normalized.",
        "Every read-back energy, force array, and ASE stress vector is exactly equal to its source value.",
        "Units match Pilot-25: eV, Angstrom, eV/Angstrom, eV/Angstrom^3.",
        "All frames use one metadata schema and identify their immutable source dataset and source record.", ""
    ])
    publish_bytes(PROVENANCE, provenance_text.encode())
    status_text = "\n".join([
        "CANONICAL Ni-Al DATASET-100 ASSEMBLY STATUS", "",
        f"Dataset: {OUT}", f"SHA256: {dataset_sha}", f"Manifest: {MANIFEST}", "",
        "VALIDATION", "Structures: 100/100", "Pilot frames: 25/25", "Expansion frames: 75/75",
        "Unique config IDs: 100/100", "Unique source records: 100/100", "Missing expansion IDs 026-100: 0",
        "Energy labels: 100/100", "Force arrays: 100/100", "Stress tensors: 100/100",
        "Consistent metadata schema: YES", "Consistent Pilot-compatible units: YES", "Canonical phase labels: YES",
        "Source DFT labels exactly preserved on read-back: YES", "", "PHASE COUNTS",
        *(f"{p} = {phases[p]}" for p in ["AlNi", "Al3Ni2", "AlNi3", "Al3Ni5", "Al3Ni"]), "TOTAL = 100", "",
        "CANONICAL DATASET-100 ASSEMBLY COMPLETE", "PILOT: 25", "EXPANSION: 75", "TOTAL: 100",
        "DUPLICATES: 0", "MISSING LABELS: 0", "READY FOR SPLIT AUDIT", ""
    ])
    publish_bytes(STATUS, status_text.encode())
    print(f"dataset={OUT}\nsha256={dataset_sha}")
    print("CANONICAL DATASET-100 ASSEMBLY COMPLETE\nPILOT: 25\nEXPANSION: 75\nTOTAL: 100\nDUPLICATES: 0\nMISSING LABELS: 0\nREADY FOR SPLIT AUDIT")


if __name__ == "__main__":
    main()
