#!/usr/bin/env python3
"""Extract validated Round-214 QE labels into extxyz (7 configs, pods A/B/C)."""

import csv
import hashlib
import math
import os
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from ase import Atoms
from ase.calculators.singlepoint import SinglePointCalculator
from ase.io import read, write
from ase.units import Bohr, Hartree

ROOT = Path("/workspace/ni_al")
BASE = ROOT / "data/al3ni_remediation_v1"
ASSIGNMENT = ROOT / "configs/ROUND214_POD_ASSIGNMENT.csv"
MANIFESTS = [BASE / "round212_manifest.csv", BASE / "round213_manifest.csv"]
PROD_BASE = BASE / "round214_production_dft"
DATASET = BASE / "round214_dft.extxyz"
SHA_FILE = BASE / "round214_dft.extxyz.sha256"
OUT_MANIFEST = BASE / "round214_dft_manifest.csv"
SANITY = BASE / "round214_dft_label_sanity.txt"
EXPECTED_TOTAL = 7


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


def main():
    pod_by_id = {r["config_id"]: r["pod"] for r in csv.DictReader(ASSIGNMENT.open(newline=""))}
    manifest = {}
    for path in MANIFESTS:
        for r in csv.DictReader(path.open(newline="")):
            if r["config_id"] in pod_by_id:
                manifest[r["config_id"]] = r

    if len(manifest) != EXPECTED_TOTAL:
        raise RuntimeError(f"expected {EXPECTED_TOTAL} configs, found {len(manifest)}")

    frames, manifest_rows = [], []
    for cid, r in manifest.items():
        pod = pod_by_id[cid]
        attempt = PROD_BASE / f"pod{pod}" / cid / "attempt_001"
        meta_path = attempt / "execution_metadata.env"
        meta = dict(line.split("=", 1) for line in meta_path.read_text().splitlines() if "=" in line)
        if meta.get("EXIT_CODE") != "0" or meta.get("JOB_DONE") != "YES" or meta.get("SCF_CONVERGED") != "YES":
            raise RuntimeError(f"{cid}: run did not complete cleanly ({meta})")
        if meta.get("GPU_ACCELERATION_ACTIVE") != "YES":
            raise RuntimeError(f"{cid}: GPU acceleration was not active for this run")

        canonical_input = Path(r["qe_input_path"])
        if sha256(canonical_input) != meta.get("CANONICAL_INPUT_SHA256"):
            raise RuntimeError(f"{cid}: canonical QE input changed since execution")
        qe_out = attempt / "qe.out"
        if sha256(qe_out) != meta.get("OUTPUT_SHA256"):
            raise RuntimeError(f"{cid}: qe.out changed since execution")

        xmls = list((attempt / "tmp").glob("*.save/data-file-schema.xml"))
        if len(xmls) != 1:
            raise RuntimeError(f"{cid}: expected one QE XML, found {len(xmls)}")
        symbols, positions, cell, energy, forces, stress = xml_labels(xmls[0])

        pre_dft = read(Path(r["structure_path"]))
        if len(symbols) != len(pre_dft):
            raise RuntimeError(f"{cid}: XML natoms does not match pre-DFT structure")
        if Counter(symbols) != Counter(pre_dft.get_chemical_symbols()):
            raise RuntimeError(f"{cid}: XML composition does not match pre-DFT structure")
        if not np.allclose(cell, pre_dft.cell.array, rtol=0, atol=1e-6):
            raise RuntimeError(f"{cid}: XML cell does not match pre-DFT structure")

        atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
        atoms.info.update({
            "config_id": cid, "phase": r["phase"], "config_type": r["config_family"],
            "target_role": r["target_role"], "source": "QE_7.6_PBE", "provenance": str(qe_out),
            "qe_output_sha256": meta["OUTPUT_SHA256"], "canonical_input": str(canonical_input),
            "canonical_input_sha256": meta["CANONICAL_INPUT_SHA256"],
        })
        atoms.calc = SinglePointCalculator(atoms, energy=energy, forces=forces, stress=stress)
        frames.append(atoms)
        manifest_rows.append({
            "config_id": cid, "phase": r["phase"], "config_type": r["config_family"],
            "target_role": r["target_role"], "natoms": len(atoms),
            "energy_eV": format(energy, ".17g"), "force_components": forces.size,
            "stress_components": stress.size,
            "canonical_input": str(canonical_input), "canonical_input_sha256": meta["CANONICAL_INPUT_SHA256"],
            "qe_output": str(qe_out), "qe_output_sha256": meta["OUTPUT_SHA256"],
            "qe_xml": str(xmls[0]), "source": "QE_7.6_PBE",
        })

    ids = [a.info["config_id"] for a in frames]
    if len(frames) != EXPECTED_TOTAL or len(set(ids)) != EXPECTED_TOTAL:
        raise RuntimeError("coverage failure")
    phase_counts = Counter(a.info["phase"] for a in frames)

    for a in frames:
        vals = np.concatenate((a.positions.ravel(), a.cell.array.ravel(),
                                np.atleast_1d(a.calc.results["energy"]),
                                a.calc.results["forces"].ravel(),
                                np.asarray(a.calc.results["stress"]).ravel()))
        if not np.isfinite(vals).all():
            raise RuntimeError(f"{a.info['config_id']}: non-finite extracted label or geometry")

    tmp = DATASET.with_suffix(DATASET.suffix + ".tmp")
    write(tmp, frames, format="extxyz")
    os.replace(tmp, DATASET)
    dataset_hash = sha256(DATASET)
    SHA_FILE.write_text(f"{dataset_hash}  {DATASET.name}\n")

    fields = ["config_id", "phase", "config_type", "target_role", "natoms", "energy_eV",
              "force_components", "stress_components", "canonical_input", "canonical_input_sha256",
              "qe_output", "qe_output_sha256", "qe_xml", "source"]
    with OUT_MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(manifest_rows)

    check = read(DATASET, index=":")
    energy_count = sum(a.calc is not None and "energy" in a.calc.results and math.isfinite(float(a.calc.results["energy"])) for a in check)
    force_count = sum(a.calc is not None and np.asarray(a.calc.results.get("forces", [])).shape == (len(a), 3) and np.isfinite(a.calc.results["forces"]).all() for a in check)
    stress_count = sum(a.calc is not None and np.asarray(a.calc.results.get("stress", [])).shape == (6,) and np.isfinite(a.calc.results["stress"]).all() for a in check)
    if (len(check), energy_count, force_count, stress_count) != (EXPECTED_TOTAL,) * 4:
        raise RuntimeError(f"round-trip failure: {(len(check), energy_count, force_count, stress_count)}")
    for before, after in zip(frames, check):
        if not np.allclose(before.cell.array, after.cell.array, rtol=0, atol=5e-8) or not np.allclose(before.positions, after.positions, rtol=0, atol=5e-8):
            raise RuntimeError(f"{before.info['config_id']}: geometry round-trip mismatch")
        if abs(before.calc.results["energy"] - after.calc.results["energy"]) > 1e-10:
            raise RuntimeError(f"{before.info['config_id']}: energy precision loss")
        if not np.allclose(before.calc.results["forces"], after.calc.results["forces"], rtol=0, atol=5e-9):
            raise RuntimeError(f"{before.info['config_id']}: force precision loss")
        if not np.allclose(before.get_stress(), after.get_stress(), rtol=0, atol=1e-14):
            raise RuntimeError(f"{before.info['config_id']}: stress precision loss")

    energies = np.array([a.calc.results["energy"] for a in check])
    fmax = np.array([np.linalg.norm(a.calc.results["forces"], axis=1).max() for a in check])
    snorm = np.array([np.linalg.norm(a.calc.results["stress"]) for a in check])
    SANITY.write_text("\n".join([
        "ROUND-214 DFT LABEL SANITY SUMMARY",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"Dataset: {DATASET}", f"Dataset SHA256: {dataset_hash}",
        "", "ROUND-TRIP COUNTS",
        f"Structures: {len(check)}/{EXPECTED_TOTAL}", f"Energies: {energy_count}/{EXPECTED_TOTAL}",
        f"Force arrays: {force_count}/{EXPECTED_TOTAL}", f"Stress tensors: {stress_count}/{EXPECTED_TOTAL}",
        "", "PER-PHASE COUNTS", *(f"{p} = {phase_counts[p]}" for p in sorted(phase_counts)),
        "", "LABEL RANGES",
        f"Total energy eV: min={energies.min():.17g} max={energies.max():.17g}",
        f"Maximum per-frame |force| eV/Angstrom: min={fmax.min():.17g} max={fmax.max():.17g}",
        f"ASE Voigt stress norm eV/Angstrom^3: min={snorm.min():.17g} max={snorm.max():.17g}",
        "", "STATUS", "ROUND-214 DFT EXTRACTION COMPLETE", f"CONFIGS: {EXPECTED_TOTAL}/{EXPECTED_TOTAL}",
        "cfg109/cfg110 sealed confirmation data: NOT ACCESSED", "",
    ]))
    print(f"dataset={DATASET}")
    print(f"sha256={dataset_hash}")
    print(f"ROUND-214 DFT EXTRACTION COMPLETE\nCONFIGS: {EXPECTED_TOTAL}/{EXPECTED_TOTAL}")


if __name__ == "__main__":
    main()
