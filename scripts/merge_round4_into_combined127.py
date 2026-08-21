#!/usr/bin/env python3
"""Merge Round-4 (2, both TRAIN) into combined-127 -> combined-129.

Mirrors merge_round3_into_combined113.py exactly. cfg109/cfg110 stay
excluded and untouched (geometry-only duplicate check permitted, labels
never read). Dataset-100's TEST/BLIND_HOLDOUT (20) unchanged.
"""

import hashlib
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import csv
import numpy as np
from ase.io import read, write

ROOT = Path("/workspace/ni_al")
COMBINED127_ALL = ROOT / "data/datasets/ni_al_combined127_dft.extxyz"
COMBINED127_TRAIN = ROOT / "data/datasets/ni_al_combined127_train_89.extxyz"
COMBINED127_VALID = ROOT / "data/datasets/ni_al_combined127_validation_18.extxyz"
ROUND4 = ROOT / "data/al3ni_remediation_v1/round4_dft.extxyz"
ROUND4_MANIFEST = ROOT / "data/al3ni_remediation_v1/round4_biaxial_manifest.csv"
SEALED_DIR = ROOT / "data/al3ni_remediation_v1/structures"
SEALED_IDS = ["cfg109_Al3Ni_iso_expansion", "cfg110_Al3Ni_volume_rattle_expansion"]

OUT_ALL = ROOT / "data/datasets/ni_al_combined129_dft.extxyz"
OUT_TRAIN = ROOT / "data/datasets/ni_al_combined129_train_91.extxyz"
OUT_VALID = ROOT / "data/datasets/ni_al_combined129_validation_18.extxyz"
STATUS = ROOT / "configs/AL3NI_COMBINED129_MERGE_STATUS.txt"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def geometry_fingerprint(atoms):
    payload = bytearray(" ".join(atoms.get_chemical_symbols()), "ascii")
    payload.extend(np.round(np.asarray(atoms.cell), 10).tobytes())
    payload.extend(np.round(atoms.get_scaled_positions(wrap=True), 10).tobytes())
    return hashlib.sha256(payload).hexdigest()


def write_atomic(path, frames):
    tmp = path.with_suffix(path.suffix + ".tmp")
    write(tmp, frames, format="extxyz")
    os.replace(tmp, path)


def main():
    combined127 = read(COMBINED127_ALL, index=":")
    round4 = read(ROUND4, index=":")
    round4_rows = list(csv.DictReader(ROUND4_MANIFEST.open(newline="")))

    if len(combined127) != 127:
        raise RuntimeError("combined-127 source does not contain 127 frames")
    if len(round4) != 2:
        raise RuntimeError("round4 source does not contain 2 frames")
    if not all(r["target_role"] == "TRAIN" for r in round4_rows):
        raise RuntimeError("round4 manifest contains a non-TRAIN role; merge logic assumes all-TRAIN")

    ids127 = {a.info["config_id"] for a in combined127}
    ids4 = {a.info["config_id"] for a in round4}
    collide = ids127 & ids4
    if collide:
        raise RuntimeError(f"config_id collision with combined-127: {collide}")

    geoms127 = {geometry_fingerprint(a) for a in combined127}
    geoms4 = {a.info["config_id"]: geometry_fingerprint(a) for a in round4}
    dup_vs_127 = {cid for cid, g in geoms4.items() if g in geoms127}
    if dup_vs_127:
        raise RuntimeError(f"round4 geometry duplicates existing combined-127 members: {dup_vs_127}")

    sealed_geoms = {}
    for sid in SEALED_IDS:
        p = SEALED_DIR / f"{sid}.extxyz"
        sealed_geoms[sid] = geometry_fingerprint(read(p))
    dup_vs_sealed = {cid for cid, g in geoms4.items() if g in sealed_geoms.values()}
    if dup_vs_sealed:
        raise RuntimeError(f"round4 geometry duplicates sealed cfg109/cfg110: {dup_vs_sealed}")

    if len(set(geoms4.values())) != 2:
        raise RuntimeError("internal round4 geometry duplicate")

    combined_all = combined127 + round4
    combined_train = read(COMBINED127_TRAIN, index=":") + round4
    combined_valid = read(COMBINED127_VALID, index=":")

    if (len(combined_all), len(combined_train), len(combined_valid)) != (129, 91, 18):
        raise RuntimeError("post-merge counts do not match expectation (129/91/18)")

    write_atomic(OUT_ALL, combined_all)
    write_atomic(OUT_TRAIN, combined_train)
    write_atomic(OUT_VALID, combined_valid)

    check_all = read(OUT_ALL, index=":")
    check_train = read(OUT_TRAIN, index=":")
    check_valid = read(OUT_VALID, index=":")
    if len(check_all) != 129 or len(check_train) != 91 or len(check_valid) != 18:
        raise RuntimeError("round-trip count mismatch")
    all_ids = [a.info["config_id"] for a in check_all]
    if len(set(all_ids)) != 129:
        raise RuntimeError("round-trip duplicate config_id")

    phase_counts = Counter(a.info["phase"] for a in check_all)

    lines = [
        "AL3NI COMBINED-129 MERGE STATUS (combined-127 + round4 cfg143,cfg145)",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        "",
        "SOURCES (all read-only, none modified)",
        f"  combined-127 all/train/val: {COMBINED127_ALL.name} (127) / {COMBINED127_TRAIN.name} (89) / {COMBINED127_VALID.name} (18)",
        f"  round4 (cfg143 Al3Ni5, cfg145 AlNi3, both TRAIN role): {ROUND4.name} (2)",
        "  cfg109/cfg110 (sealed): EXCLUDED, untouched -- geometry-only duplicate check performed, labels never read",
        "",
        "INTEGRITY CHECKS",
        "  config_id collision vs combined-127: NONE",
        "  geometry duplicate vs combined-127: NONE",
        "  geometry duplicate vs sealed cfg109/cfg110: NONE",
        "  internal round4 geometry duplicate: NONE",
        "",
        "OUTPUT",
        f"  All 129:      {OUT_ALL}  sha256={sha256(OUT_ALL)}",
        f"  TRAIN 91:     {OUT_TRAIN}  sha256={sha256(OUT_TRAIN)}",
        f"  VALIDATION 18: {OUT_VALID}  sha256={sha256(OUT_VALID)}",
        "",
        f"Round-trip: {len(check_all)}/129 all, {len(check_train)}/91 train, {len(check_valid)}/18 validation",
        f"Phase composition (all 129): {dict(phase_counts)}",
        "TEST/BLIND_HOLDOUT (Dataset-100's 20): UNCHANGED, not merged, referenced from original Dataset-100 files only.",
        "",
        "COVERAGE IMPACT",
        "Al3Ni5/biaxial and AlNi3/biaxial (the last two Tier-1 zero-TRAIN-support buckets",
        "after round3) now each have exactly 1 TRAIN member -- INFO_LOW_TRAIN_COUNT territory,",
        "not fully resolved, but no longer EXTRAPOLATION_NO_TRAIN_SUPPORT.",
        "",
        "STATUS",
        "AL3NI COMBINED-129 MERGE COMPLETE",
    ]
    STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
