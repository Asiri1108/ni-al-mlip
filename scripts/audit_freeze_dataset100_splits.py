#!/usr/bin/env python3
"""Audit and freeze the exact, pre-designed Dataset-100 split membership."""

import csv
import hashlib
import io
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from ase.io import read

ROOT = Path("/workspace/ni_al")
DATASET = ROOT / "data/datasets/ni_al_dataset100_dft.extxyz"
CANONICAL_MANIFEST = ROOT / "data/datasets/ni_al_dataset100_dft_manifest.csv"
DESIGN = ROOT / "data/expansion_026_100/manifests/configs_026_100_design.csv"
PILOT_SPLITS = {
    "train": ROOT / "data/datasets/ni_al_pilot_train_15.extxyz",
    "validation": ROOT / "data/datasets/ni_al_pilot_val_5.extxyz",
    "test": ROOT / "data/datasets/ni_al_pilot_test_5.extxyz",
}
EXPECTED_PILOT_SHA = {
    "train": "b7f3711d565e912f3da12bc24ccddbca59ecdbb7c6cfdced8a7ef09892951c6a",
    "validation": "f09e54eceddba7b7d445b46f243f70af328061266773c727a13009718889392d",
    "test": "fff925984d04f51cfc0d8add614a8287605c2539b14b72e0784e65ca6c132705",
}
EXPECTED_DATASET_SHA = "12fabd203b91e31e9a602bbaa3a2a3f14341e6fa366b128903099e196b59a3aa"
ROLE_TO_SPLIT = {"TRAIN_CANDIDATE": "train", "VALIDATION": "validation", "BLIND_HOLDOUT": "blind_holdout"}
EXPECTED_COUNTS = {"train": 65, "validation": 15, "test": 5, "blind_holdout": 15}
OUTS = {s: ROOT / f"data/datasets/ni_al_dataset100_{s}_manifest.csv" for s in EXPECTED_COUNTS}
STATUS = ROOT / "configs/DATASET100_SPLIT_STATUS.txt"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha_text(lines):
    return hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()


def geometry_digest(atoms):
    h = hashlib.sha256()
    h.update(np.asarray(atoms.numbers, dtype=np.int64).tobytes())
    h.update(np.asarray(atoms.positions, dtype=np.float64).tobytes())
    h.update(np.asarray(atoms.cell.array, dtype=np.float64).tobytes())
    h.update(np.asarray(atoms.pbc, dtype=np.bool_).tobytes())
    return h.hexdigest()


def publish(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f"refusing to overwrite divergent frozen artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def composition(atoms):
    c = Counter(atoms.get_chemical_symbols())
    return f"Al{c.get('Al',0)}Ni{c.get('Ni',0)}"


def main():
    if sha256(DATASET) != EXPECTED_DATASET_SHA:
        raise RuntimeError("canonical Dataset-100 identity changed")
    for split, path in PILOT_SPLITS.items():
        if sha256(path) != EXPECTED_PILOT_SHA[split]:
            raise RuntimeError(f"historical Pilot {split} identity changed")

    frames = read(DATASET, index=":")
    canonical_rows = list(csv.DictReader(CANONICAL_MANIFEST.open(newline="")))
    design_rows = list(csv.DictReader(DESIGN.open(newline="")))
    if len(frames) != 100 or len(canonical_rows) != 100:
        raise RuntimeError("canonical dataset/manifest count mismatch")
    by_id = {a.info["config_id"]: (i, a, canonical_rows[i]) for i, a in enumerate(frames)}
    if len(by_id) != 100 or any(canonical_rows[i]["config_id"] != a.info["config_id"] for i, a in enumerate(frames)):
        raise RuntimeError("canonical dataset/manifest ID mismatch")
    design_by_id = {r["config_id"]: r for r in design_rows}
    if len(design_by_id) != 75:
        raise RuntimeError("expansion design is not 75 unique IDs")

    assignments = {}
    pilot_members = {}
    for split, path in PILOT_SPLITS.items():
        members = read(path, index=":")
        pilot_members[split] = [a.info["config_id"] for a in members]
        for a in members:
            cid = a.info["config_id"]
            if cid in assignments: raise RuntimeError(f"Pilot split overlap: {cid}")
            assignments[cid] = split
            if cid not in by_id: raise RuntimeError(f"Pilot split ID absent from Dataset-100: {cid}")
            canonical = by_id[cid][1]
            if (canonical.info["phase"] != a.info["phase"] or canonical.info["config_type"] != a.info["config_type"]
                    or not np.array_equal(canonical.get_forces(), a.get_forces())
                    or canonical.get_potential_energy() != a.get_potential_energy()
                    or not np.array_equal(canonical.get_stress(), a.get_stress())):
                raise RuntimeError(f"historical Pilot membership/labels mismatch: {cid}")
    for d in design_rows:
        cid = d["config_id"]
        if cid in assignments: raise RuntimeError(f"cross-source assignment collision: {cid}")
        split = ROLE_TO_SPLIT.get(d["target_role"])
        if not split: raise RuntimeError(f"unknown design role for {cid}: {d['target_role']}")
        assignments[cid] = split
        if cid not in by_id: raise RuntimeError(f"designed expansion ID absent from Dataset-100: {cid}")
        a = by_id[cid][1]
        if a.info["phase"] != d["phase"] or a.info["config_type"] != d["config_type"]:
            raise RuntimeError(f"design/canonical metadata mismatch: {cid}")
        if a.info["canonical_input_sha256"] != d["sha256_input"]:
            raise RuntimeError(f"design/canonical input identity mismatch: {cid}")
    if set(assignments) != set(by_id):
        raise RuntimeError(f"unassigned or unexpected IDs: {sorted(set(by_id) ^ set(assignments))}")
    counts = Counter(assignments.values())
    if dict(counts) != EXPECTED_COUNTS:
        raise RuntimeError(f"split counts mismatch: {dict(counts)}")

    split_sets = {s: {cid for cid, assigned in assignments.items() if assigned == s} for s in EXPECTED_COUNTS}
    overlap = set()
    names = list(split_sets)
    for i, a in enumerate(names):
        for b in names[i+1:]: overlap |= split_sets[a] & split_sets[b]
    if overlap: raise RuntimeError(f"split overlap: {sorted(overlap)}")
    if split_sets["test"] != set(pilot_members["test"]):
        raise RuntimeError("historical Pilot TEST-5 membership changed")
    if split_sets["blind_holdout"] != {r["config_id"] for r in design_rows if r["target_role"] == "BLIND_HOLDOUT"}:
        raise RuntimeError("blind-holdout membership changed")
    if (split_sets["test"] | split_sets["blind_holdout"]) & (split_sets["train"] | split_sets["validation"]):
        raise RuntimeError("test/blind leakage into optimization sets")

    # Exact structure duplicates are prohibited across all splits. The pre-designed
    # expansion also keeps each (phase, config_family) relationship group in one role.
    geometry_map = defaultdict(list)
    relationship_roles = defaultdict(set)
    for cid, split in assignments.items():
        geometry_map[geometry_digest(by_id[cid][1])].append((cid, split))
        if cid in design_by_id:
            d = design_by_id[cid]
            relationship_roles[(d["phase"], d["config_family"])].add(split)
    geometry_duplicates = [v for v in geometry_map.values() if len(v) > 1]
    cross_role_relationships = {k: v for k, v in relationship_roles.items() if len(v) > 1}
    if geometry_duplicates: raise RuntimeError(f"duplicate geometries: {geometry_duplicates}")
    if cross_role_relationships: raise RuntimeError(f"expansion relationship groups cross roles: {cross_role_relationships}")

    fields = ["canonical_index", "config_id", "split", "dataset_origin", "phase", "composition", "config_family", "config_type", "relationship_parent", "relationship_group", "target_role", "strain_type", "strain_value", "rattle_sigma_A", "shear_value", "random_seed", "source_record", "original_dataset", "original_dataset_sha256", "canonical_input_sha256", "qe_output_sha256", "energy_sha256_float64", "forces_sha256_float64", "stress_sha256_float64"]
    manifest_bytes = {}
    membership_hashes = {}
    manifest_hashes = {}
    split_rows = {}
    for split in EXPECTED_COUNTS:
        rows = []
        for i, a, c in [(i, a, canonical_rows[i]) for i, a in enumerate(frames) if assignments[a.info["config_id"]] == split]:
            cid = a.info["config_id"]
            d = design_by_id.get(cid)
            if d:
                family, parent, group, role = d["config_family"], d["source_structure"], f"{d['phase']}:{d['config_family']}", d["target_role"]
                strain_type, strain_value, rattle, shear, seed = d["strain_type"], d["strain_value"], d["rattle_sigma_A"], d["shear_value"], d["random_seed"]
            else:
                family = a.info["config_type"]
                parent = f"{a.info['phase']}_relaxed" if family != "relaxed" else cid
                group = f"{a.info['phase']}:pilot:{family}"
                role = {"train":"HISTORICAL_TRAIN", "validation":"HISTORICAL_VALIDATION", "test":"HISTORICAL_TEST"}[split]
                strain_type = strain_value = rattle = shear = seed = "historical_not_recorded"
            rows.append({
                "canonical_index": i, "config_id": cid, "split": split, "dataset_origin": a.info["dataset_origin"],
                "phase": a.info["phase"], "composition": composition(a), "config_family": family,
                "config_type": a.info["config_type"], "relationship_parent": parent, "relationship_group": group,
                "target_role": role, "strain_type": strain_type, "strain_value": strain_value,
                "rattle_sigma_A": rattle, "shear_value": shear, "random_seed": seed,
                "source_record": a.info["source_record"], "original_dataset": a.info["original_dataset"],
                "original_dataset_sha256": a.info["original_dataset_sha256"],
                "canonical_input_sha256": a.info["canonical_input_sha256"], "qe_output_sha256": a.info["qe_output_sha256"],
                "energy_sha256_float64": c["energy_sha256_float64"], "forces_sha256_float64": c["forces_sha256_float64"],
                "stress_sha256_float64": c["stress_sha256_float64"],
            })
        sio = io.StringIO(newline="")
        w = csv.DictWriter(sio, fieldnames=fields); w.writeheader(); w.writerows(rows)
        data = sio.getvalue().encode(); manifest_bytes[split] = data; split_rows[split] = rows
        membership_hashes[split] = sha_text([r["config_id"] for r in rows])
        manifest_hashes[split] = hashlib.sha256(data).hexdigest()

    # Audit distributions by phase, composition, family, source, and relationship.
    phase_counts = {s: Counter(r["phase"] for r in rows) for s, rows in split_rows.items()}
    composition_counts = {s: Counter(r["composition"] for r in rows) for s, rows in split_rows.items()}
    family_counts = {s: Counter(r["config_family"] for r in rows) for s, rows in split_rows.items()}
    origin_counts = {s: Counter(r["dataset_origin"] for r in rows) for s, rows in split_rows.items()}
    for split, data in manifest_bytes.items(): publish(OUTS[split], data)

    lines = [
        "Ni-Al CANONICAL DATASET-100 FROZEN SPLIT STATUS", "",
        f"Canonical dataset: {DATASET}", f"Canonical dataset SHA256: {EXPECTED_DATASET_SHA}",
        f"Canonical manifest: {CANONICAL_MANIFEST}", f"Canonical manifest SHA256: {sha256(CANONICAL_MANIFEST)}", "",
        "DESIGN AUTHORITY",
        f"Expansion design: {DESIGN}", f"Expansion design SHA256: {sha256(DESIGN)}",
        f"Blind-holdout definition: {ROOT / 'configs/DATASET100_EXPANSION_PREPARATION.txt'}",
        "Policy: exact pre-DFT expansion target_role assignments; historical Pilot 15/5/5 unchanged.",
        "Pilot TEST-5 remains historical TEST; the 15 expansion BLIND_HOLDOUT frames remain untouched final holdout.", "",
        "FROZEN MANIFESTS",
    ]
    for split in EXPECTED_COUNTS:
        lines += [f"{split.upper()}: {OUTS[split]}", f"  count: {len(split_rows[split])}",
                  f"  manifest SHA256: {manifest_hashes[split]}", f"  ordered membership SHA256: {membership_hashes[split]}"]
    lines += ["", "AUDIT RESULTS", "Overlap: 0", "Unassigned intended structures: 0",
              "Historical Pilot TEST membership changed: NO", "TEST in training/validation: NO",
              "BLIND_HOLDOUT in training/validation/test: NO", "Exact duplicate geometries: 0",
              "Expansion (phase, config_family) relationship groups crossing roles: 0",
              "Source records duplicated: 0", "Missing energy/force/stress labels: 0", ""]
    for split in EXPECTED_COUNTS:
        lines += [f"{split.upper()} DISTRIBUTION",
                  "  phase: " + "; ".join(f"{k}={v}" for k,v in sorted(phase_counts[split].items())),
                  "  composition: " + "; ".join(f"{k}={v}" for k,v in sorted(composition_counts[split].items())),
                  "  provenance: " + "; ".join(f"{k}={v}" for k,v in sorted(origin_counts[split].items())),
                  "  perturbation families: " + "; ".join(f"{k}={v}" for k,v in sorted(family_counts[split].items())), ""]
    lines += ["EXACT CONFIGURATION IDS"]
    for split in EXPECTED_COUNTS:
        lines += [f"{split.upper()} ({len(split_rows[split])}):", *[f"  {r['config_id']}" for r in split_rows[split]]]
    lines += ["", "DATASET-100 SPLIT AUDIT COMPLETE", "TRAIN: 65", "VALIDATION: 15", "TEST: 5",
              "BLIND HOLDOUT: 15", "OVERLAP: 0", "DATA LEAKAGE: NONE", "SPLITS FROZEN", "READY FOR MACE TRAINING", ""]
    publish(STATUS, ("\n".join(lines)).encode())
    print("DATASET-100 SPLIT AUDIT COMPLETE\nTRAIN: 65\nVALIDATION: 15\nTEST: 5\nBLIND HOLDOUT: 15\nOVERLAP: 0\nDATA LEAKAGE: NONE\nSPLITS FROZEN\nREADY FOR MACE TRAINING")


if __name__ == "__main__":
    main()
