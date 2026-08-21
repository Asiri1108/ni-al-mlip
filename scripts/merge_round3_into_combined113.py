#!/usr/bin/env python3
"""Merge Round-3 (14, all TRAIN) into combined-113 -> combined-127.

Mirrors the combined-113 merge exactly (same file-naming convention, same
exclusions): cfg109/cfg110 stay excluded and untouched (sealed, per
AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt -- geometry-only duplicate check
is permitted, labels are never read). Dataset-100's TEST/BLIND_HOLDOUT (20)
is unchanged, not merged, referenced from the original files only.
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
COMBINED113_ALL = ROOT / "data/datasets/ni_al_combined113_dft.extxyz"
COMBINED113_TRAIN = ROOT / "data/datasets/ni_al_combined113_train_75.extxyz"
COMBINED113_VALID = ROOT / "data/datasets/ni_al_combined113_validation_18.extxyz"
ROUND3 = ROOT / "data/al3ni_remediation_v1/round3_dft.extxyz"
ROUND3_MANIFEST = ROOT / "data/al3ni_remediation_v1/round3_manifest.csv"
SEALED_DIR = ROOT / "data/al3ni_remediation_v1/structures"
SEALED_IDS = ["cfg109_Al3Ni_iso_expansion", "cfg110_Al3Ni_volume_rattle_expansion"]

OUT_ALL = ROOT / "data/datasets/ni_al_combined127_dft.extxyz"
OUT_TRAIN = ROOT / "data/datasets/ni_al_combined127_train_89.extxyz"
OUT_VALID = ROOT / "data/datasets/ni_al_combined127_validation_18.extxyz"
STATUS = ROOT / "configs/AL3NI_COMBINED127_MERGE_STATUS.txt"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def geometry_fingerprint(atoms):
    """Verbatim from validate_and_split_pilot25.py."""
    payload = bytearray(" ".join(atoms.get_chemical_symbols()), "ascii")
    payload.extend(np.round(np.asarray(atoms.cell), 10).tobytes())
    payload.extend(np.round(atoms.get_scaled_positions(wrap=True), 10).tobytes())
    return hashlib.sha256(payload).hexdigest()


def write_atomic(path, frames):
    tmp = path.with_suffix(path.suffix + ".tmp")
    write(tmp, frames, format="extxyz")
    os.replace(tmp, path)


def main():
    combined113 = read(COMBINED113_ALL, index=":")
    round3 = read(ROUND3, index=":")
    round3_rows = list(csv.DictReader(ROUND3_MANIFEST.open(newline="")))

    if len(combined113) != 113:
        raise RuntimeError("combined-113 source does not contain 113 frames")
    if len(round3) != 14:
        raise RuntimeError("round3 source does not contain 14 frames")
    if not all(r["target_role"] == "TRAIN" for r in round3_rows):
        raise RuntimeError("round3 manifest contains a non-TRAIN role; merge logic assumes all-TRAIN")

    # 1. No config_id collision.
    ids113 = {a.info["config_id"] for a in combined113}
    ids3 = {a.info["config_id"] for a in round3}
    collide = ids113 & ids3
    if collide:
        raise RuntimeError(f"config_id collision with combined-113: {collide}")

    # 2. No duplicate geometry vs combined-113.
    geoms113 = {geometry_fingerprint(a) for a in combined113}
    geoms3 = {a.info["config_id"]: geometry_fingerprint(a) for a in round3}
    dup_vs_113 = {cid for cid, g in geoms3.items() if g in geoms113}
    if dup_vs_113:
        raise RuntimeError(f"round3 geometry duplicates existing combined-113 members: {dup_vs_113}")

    # 3. No duplicate geometry vs sealed cfg109/cfg110 (geometry-only read; labels never touched).
    sealed_geoms = {}
    for sid in SEALED_IDS:
        p = SEALED_DIR / f"{sid}.extxyz"
        sealed_geoms[sid] = geometry_fingerprint(read(p))
    dup_vs_sealed = {cid for cid, g in geoms3.items() if g in sealed_geoms.values()}
    if dup_vs_sealed:
        raise RuntimeError(f"round3 geometry duplicates sealed cfg109/cfg110: {dup_vs_sealed}")

    # 4. Internal round3 uniqueness (already checked at extraction time, re-verify here).
    if len(set(geoms3.values())) != 14:
        raise RuntimeError("internal round3 geometry duplicate")

    combined_all = combined113 + round3
    combined_train = read(COMBINED113_TRAIN, index=":") + round3
    combined_valid = read(COMBINED113_VALID, index=":")

    if (len(combined_all), len(combined_train), len(combined_valid)) != (127, 89, 18):
        raise RuntimeError("post-merge counts do not match expectation (127/89/18)")

    write_atomic(OUT_ALL, combined_all)
    write_atomic(OUT_TRAIN, combined_train)
    write_atomic(OUT_VALID, combined_valid)

    # Round-trip verify.
    check_all = read(OUT_ALL, index=":")
    check_train = read(OUT_TRAIN, index=":")
    check_valid = read(OUT_VALID, index=":")
    if len(check_all) != 127 or len(check_train) != 89 or len(check_valid) != 18:
        raise RuntimeError("round-trip count mismatch")
    all_ids = [a.info["config_id"] for a in check_all]
    if len(set(all_ids)) != 127:
        raise RuntimeError("round-trip duplicate config_id")

    phase_counts = Counter(a.info["phase"] for a in check_all)

    lines = [
        "AL3NI COMBINED-127 MERGE STATUS (combined-113 + round3 cfg117-cfg141)",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        "",
        "SOURCES (all read-only, none modified)",
        f"  combined-113 all/train/val: {COMBINED113_ALL.name} (113) / {COMBINED113_TRAIN.name} (75) / {COMBINED113_VALID.name} (18)",
        f"  round3 (cfg117-cfg141, 14, all TRAIN role): {ROUND3.name} (14)",
        "  cfg109/cfg110 (sealed): EXCLUDED, untouched -- geometry-only duplicate check performed, labels never read",
        "",
        "INTEGRITY CHECKS",
        "  config_id collision vs combined-113: NONE",
        "  geometry duplicate vs combined-113: NONE",
        "  geometry duplicate vs sealed cfg109/cfg110: NONE",
        "  internal round3 geometry duplicate: NONE",
        "",
        "OUTPUT",
        f"  All 127:      {OUT_ALL}  sha256={sha256(OUT_ALL)}",
        f"  TRAIN 89:     {OUT_TRAIN}  sha256={sha256(OUT_TRAIN)}",
        f"  VALIDATION 18: {OUT_VALID}  sha256={sha256(OUT_VALID)}",
        "",
        f"Round-trip: {len(check_all)}/127 all, {len(check_train)}/89 train, {len(check_valid)}/18 validation",
        f"Phase composition (all 127): {dict(phase_counts)}",
        "TEST/BLIND_HOLDOUT (Dataset-100's 20): UNCHANGED, not merged, referenced from original Dataset-100 files only.",
        "",
        "STATUS",
        "AL3NI COMBINED-127 MERGE COMPLETE",
    ]
    STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
