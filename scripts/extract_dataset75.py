#!/usr/bin/env python3
"""Extract validated Dataset-75 QE labels into the canonical Pilot-compatible extxyz."""

import csv
import hashlib
import math
import os
import re
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
VALIDATION_REPORT = ROOT / "configs/DATASET100_DFT_VALIDATION_STATUS.txt"
VALIDATION_CSV = ROOT / "results/dataset100_dft_validation_v1/config_validation.csv"
DESIGN_CSV = ROOT / "data/expansion_026_100/manifests/configs_026_100_design.csv"
PILOT = ROOT / "data/processed/ni_al_pilot_dft_25.extxyz"
DATASET = ROOT / "data/processed/ni_al_expansion_dft_75.extxyz"
SHA_FILE = ROOT / "data/processed/ni_al_expansion_dft_75.extxyz.sha256"
MANIFEST = ROOT / "data/processed/ni_al_expansion_dft_75_manifest.csv"
PHASE_COUNTS = ROOT / "data/processed/ni_al_expansion_dft_75_phase_counts.txt"
SANITY = ROOT / "data/processed/ni_al_expansion_dft_75_label_sanity.txt"
EXPECTED_PHASES = {"AlNi": 13, "Al3Ni2": 14, "AlNi3": 12, "Al3Ni5": 17, "Al3Ni": 19}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require_gate():
    text = VALIDATION_REPORT.read_text(errors="strict")
    for statement in ("VALID CONFIGS: 75/75", "FAILED: 0", "MISSING: 0", "DUPLICATES: 0"):
        if statement not in text:
            raise RuntimeError(f"validation gate missing: {statement}")
    rows = list(csv.DictReader(VALIDATION_CSV.open(newline="")))
    if len(rows) != 75 or any(r["scientific_status"] != "VALID" for r in rows):
        raise RuntimeError("validation CSV is not exactly 75 VALID rows")
    return rows


def xml_labels(xml_path):
    root = ET.parse(xml_path).getroot()
    output = root.find("output")
    if output is None:
        raise ValueError("QE XML output section missing")
    structure = output.find("atomic_structure")
    cell_node = structure.find("cell") if structure is not None else None
    pos_node = structure.find("atomic_positions") if structure is not None else None
    if structure is None or cell_node is None or pos_node is None:
        raise ValueError("QE XML output geometry missing")
    cell = np.array([[float(x.replace("D", "E")) for x in cell_node.find(k).text.split()]
                     for k in ("a1", "a2", "a3")], dtype=np.float64) * Bohr
    symbols, positions = [], []
    for atom in pos_node.findall("atom"):
        symbols.append(atom.attrib["name"])
        positions.append([float(x.replace("D", "E")) for x in atom.text.split()])
    positions = np.asarray(positions, dtype=np.float64) * Bohr
    energy_node = output.find("total_energy/etot")
    force_node = output.find("forces")
    stress_node = output.find("stress")
    if energy_node is None or force_node is None or stress_node is None:
        raise ValueError("QE XML energy/forces/stress missing")
    energy = float(energy_node.text.strip().replace("D", "E")) * Hartree
    forces = np.fromstring(force_node.text.replace("D", "E"), sep=" ", dtype=np.float64).reshape((-1, 3)) * Hartree / Bohr
    # QE reports positive compression; ASE's stress convention is positive tension.
    stress = -np.fromstring(stress_node.text.replace("D", "E"), sep=" ", dtype=np.float64).reshape((3, 3)) * Hartree / (Bohr ** 3)
    if len(symbols) != int(structure.attrib["nat"]) or forces.shape != (len(symbols), 3):
        raise ValueError("QE XML atom/force dimensions inconsistent")
    return symbols, positions, cell, energy, forces, stress


def main():
    valid_rows = require_gate()
    pilot = read(PILOT, index=":")
    if len(pilot) != 25:
        raise RuntimeError("Pilot reference does not contain 25 frames")
    pilot_keys = {"config_id", "phase", "config_type", "source"}
    if any(not pilot_keys.issubset(a.info) or not {"energy", "forces", "stress"}.issubset(a.calc.results) for a in pilot):
        raise RuntimeError("Pilot reference conventions are not as expected")

    design = {r["config_id"]: r for r in csv.DictReader(DESIGN_CSV.open(newline=""))}
    if len(design) != 75:
        raise RuntimeError("design manifest does not contain 75 unique configurations")
    frames, manifest_rows = [], []
    for v in valid_rows:
        cid = v["config_id"]
        if cid not in design:
            raise RuntimeError(f"{cid}: absent from design manifest")
        d = design[cid]
        output = Path(v["output_path"])
        attempt = output.parent
        xmls = list((attempt / "tmp").glob("*.save/data-file-schema.xml"))
        if len(xmls) != 1:
            raise RuntimeError(f"{cid}: expected one QE XML, found {len(xmls)}")
        symbols, positions, cell, energy, forces, stress = xml_labels(xmls[0])
        if len(symbols) != int(v["natoms"]):
            raise RuntimeError(f"{cid}: XML natoms mismatch")
        canonical_input = ROOT / "data/expansion_026_100/qe_inputs" / f"{cid}.in"
        if sha256(canonical_input) != v["input_sha256"]:
            raise RuntimeError(f"{cid}: canonical input changed after validation")
        if sha256(output) != v["output_sha256"]:
            raise RuntimeError(f"{cid}: raw output changed after validation")
        atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
        atoms.info.update({
            "config_id": cid,
            "phase": v["phase"],
            "config_type": d["config_type"],
            "source": "QE_7.6_PBE",
            "provenance": str(output),
            "qe_output_sha256": v["output_sha256"],
            "canonical_input": str(canonical_input),
            "canonical_input_sha256": v["input_sha256"],
        })
        atoms.calc = SinglePointCalculator(atoms, energy=energy, forces=forces, stress=stress)
        frames.append(atoms)
        manifest_rows.append({
            "config_id": cid, "phase": v["phase"], "config_type": d["config_type"],
            "natoms": len(atoms), "energy_eV": format(energy, ".17g"),
            "force_components": forces.size, "stress_components": stress.size,
            "canonical_input": str(canonical_input), "canonical_input_sha256": v["input_sha256"],
            "qe_output": str(output), "qe_output_sha256": v["output_sha256"],
            "qe_xml": str(xmls[0]), "source": "QE_7.6_PBE",
        })

    ids = [a.info["config_id"] for a in frames]
    phases = Counter(a.info["phase"] for a in frames)
    if len(frames) != 75 or len(set(ids)) != 75 or dict(phases) != EXPECTED_PHASES:
        raise RuntimeError(f"coverage failure: frames={len(frames)}, unique={len(set(ids))}, phases={dict(phases)}")
    if any(not np.isfinite(np.concatenate((a.positions.ravel(), a.cell.array.ravel(),
                                            np.atleast_1d(a.calc.results["energy"]),
                                            a.calc.results["forces"].ravel(),
                                            np.asarray(a.calc.results["stress"]).ravel()))).all() for a in frames):
        raise RuntimeError("non-finite extracted label or geometry")

    # ASE's extxyz writer is the exact serialization convention used by Pilot-25.
    tmp = DATASET.with_suffix(DATASET.suffix + ".tmp")
    write(tmp, frames, format="extxyz")
    os.replace(tmp, DATASET)
    dataset_hash = sha256(DATASET)
    SHA_FILE.write_text(f"{dataset_hash}  {DATASET.name}\n")
    fields = ["config_id", "phase", "config_type", "natoms", "energy_eV", "force_components", "stress_components", "canonical_input", "canonical_input_sha256", "qe_output", "qe_output_sha256", "qe_xml", "source"]
    with MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(manifest_rows)

    # Independent round-trip verification through the same consumer used for Pilot-25.
    check = read(DATASET, index=":")
    energy_count = sum(a.calc is not None and "energy" in a.calc.results and math.isfinite(float(a.calc.results["energy"])) for a in check)
    force_count = sum(a.calc is not None and np.asarray(a.calc.results.get("forces", [])).shape == (len(a), 3) and np.isfinite(a.calc.results["forces"]).all() for a in check)
    stress_count = sum(a.calc is not None and np.asarray(a.calc.results.get("stress", [])).shape == (6,) and np.isfinite(a.calc.results["stress"]).all() for a in check)
    if (len(check), energy_count, force_count, stress_count) != (75, 75, 75, 75):
        raise RuntimeError(f"round-trip labels failure: {(len(check), energy_count, force_count, stress_count)}")
    for before, after in zip(frames, check):
        if before.info != after.info or before.get_chemical_symbols() != after.get_chemical_symbols() or not after.pbc.all():
            raise RuntimeError(f"{before.info['config_id']}: metadata/species/PBC round-trip mismatch")
        if not np.allclose(before.cell.array, after.cell.array, rtol=0, atol=5e-8) or not np.allclose(before.positions, after.positions, rtol=0, atol=5e-8):
            raise RuntimeError(f"{before.info['config_id']}: geometry round-trip mismatch")
        if abs(before.calc.results["energy"] - after.calc.results["energy"]) > 1e-10:
            raise RuntimeError(f"{before.info['config_id']}: energy precision loss")
        if not np.allclose(before.calc.results["forces"], after.calc.results["forces"], rtol=0, atol=5e-9):
            raise RuntimeError(f"{before.info['config_id']}: force precision loss exceeds Pilot convention")
        if not np.allclose(before.get_stress(), after.get_stress(), rtol=0, atol=1e-14):
            raise RuntimeError(f"{before.info['config_id']}: stress precision loss")

    PHASE_COUNTS.write_text("\n".join(["DATASET-75 PER-PHASE COUNTS", *(f"{p} = {phases[p]}" for p in ["AlNi", "Al3Ni2", "AlNi3", "Al3Ni5", "Al3Ni"]), "TOTAL = 75", ""]) )
    energies = np.array([a.calc.results["energy"] for a in check])
    fmax = np.array([np.linalg.norm(a.calc.results["forces"], axis=1).max() for a in check])
    snorm = np.array([np.linalg.norm(a.calc.results["stress"]) for a in check])
    SANITY.write_text("\n".join([
        "DATASET-75 LABEL SANITY SUMMARY", f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"Dataset: {DATASET}", f"Dataset SHA256: {dataset_hash}",
        "Reference convention: data/processed/ni_al_pilot_dft_25.extxyz (ASE extxyz; eV, Angstrom, eV/Angstrom, eV/Angstrom^3)",
        "Label source: high-precision QE 7.6 data-file-schema.xml; stress sign converted from QE positive-compression to ASE positive-tension convention.",
        "", "ROUND-TRIP COUNTS", f"Structures: {len(check)}/75", f"Energies: {energy_count}/75",
        f"Force arrays: {force_count}/75", f"Stress tensors: {stress_count}/75", f"Unique config IDs: {len(set(ids))}/75",
        "All species, Cartesian positions, cells, PBC, labels, and provenance metadata are finite and present.",
        "", "LABEL RANGES", f"Total energy eV: min={energies.min():.17g} max={energies.max():.17g}",
        f"Maximum per-frame |force| eV/Angstrom: min={fmax.min():.17g} max={fmax.max():.17g}",
        f"ASE Voigt stress norm eV/Angstrom^3: min={snorm.min():.17g} max={snorm.max():.17g}",
        "", "STATUS", "DATASET-75 EXTRACTION COMPLETE", "CONFIGS: 75/75", "READY FOR PILOT-25 + EXPANSION-75 ASSEMBLY", ""
    ]))
    print(f"dataset={DATASET}")
    print(f"sha256={dataset_hash}")
    print("DATASET-75 EXTRACTION COMPLETE\nCONFIGS: 75/75\nREADY FOR PILOT-25 + EXPANSION-75 ASSEMBLY")


if __name__ == "__main__":
    main()
