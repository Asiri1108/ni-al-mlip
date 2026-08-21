#!/usr/bin/env python3
"""Merge Round-300 (82, all TRAIN) into combined-129 -> combined-211.

Mirrors merge_round3_into_combined113.py / merge_round4_into_combined127.py
exactly. cfg109/cfg110 stay excluded and untouched (geometry-only
duplicate check permitted, labels never read). Dataset-100's TEST/
BLIND_HOLDOUT (20) unchanged.
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
COMBINED129_ALL = ROOT / "data/datasets/ni_al_combined129_dft.extxyz"
COMBINED129_TRAIN = ROOT / "data/datasets/ni_al_combined129_train_91.extxyz"
COMBINED129_VALID = ROOT / "data/datasets/ni_al_combined129_validation_18.extxyz"
ROUND300 = ROOT / "data/al3ni_remediation_v1/round300_dft.extxyz"
ROUND300_MANIFEST = ROOT / "data/al3ni_remediation_v1/round300_manifest.csv"
SEALED_DIR = ROOT / "data/al3ni_remediation_v1/structures"
SEALED_IDS = ["cfg109_Al3Ni_iso_expansion", "cfg110_Al3Ni_volume_rattle_expansion"]

OUT_ALL = ROOT / "data/datasets/ni_al_combined211_dft.extxyz"
OUT_TRAIN = ROOT / "data/datasets/ni_al_combined211_train_173.extxyz"
OUT_VALID = ROOT / "data/datasets/ni_al_combined211_validation_18.extxyz"
STATUS = ROOT / "configs/AL3NI_COMBINED211_MERGE_STATUS.txt"


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
    combined129 = read(COMBINED129_ALL, index=":")
    round300 = read(ROUND300, index=":")
    round300_rows = list(csv.DictReader(ROUND300_MANIFEST.open(newline="")))

    if len(combined129) != 129:
        raise RuntimeError("combined-129 source does not contain 129 frames")
    if len(round300) != 82:
        raise RuntimeError("round300 source does not contain 82 frames")
    if not all(r["target_role"] == "TRAIN" for r in round300_rows):
        raise RuntimeError("round300 manifest contains a non-TRAIN role; merge logic assumes all-TRAIN")

    ids129 = {a.info["config_id"] for a in combined129}
    ids300 = {a.info["config_id"] for a in round300}
    collide = ids129 & ids300
    if collide:
        raise RuntimeError(f"config_id collision with combined-129: {collide}")

    geoms129 = {geometry_fingerprint(a) for a in combined129}
    geoms300 = {a.info["config_id"]: geometry_fingerprint(a) for a in round300}
    dup_vs_129 = {cid for cid, g in geoms300.items() if g in geoms129}
    if dup_vs_129:
        raise RuntimeError(f"round300 geometry duplicates existing combined-129 members: {dup_vs_129}")

    sealed_geoms = {}
    for sid in SEALED_IDS:
        p = SEALED_DIR / f"{sid}.extxyz"
        sealed_geoms[sid] = geometry_fingerprint(read(p))
    dup_vs_sealed = {cid for cid, g in geoms300.items() if g in sealed_geoms.values()}
    if dup_vs_sealed:
        raise RuntimeError(f"round300 geometry duplicates sealed cfg109/cfg110: {dup_vs_sealed}")

    if len(set(geoms300.values())) != 82:
        raise RuntimeError("internal round300 geometry duplicate")

    combined_all = combined129 + round300
    combined_train = read(COMBINED129_TRAIN, index=":") + round300
    combined_valid = read(COMBINED129_VALID, index=":")

    if (len(combined_all), len(combined_train), len(combined_valid)) != (211, 173, 18):
        raise RuntimeError("post-merge counts do not match expectation (211/173/18)")

    write_atomic(OUT_ALL, combined_all)
    write_atomic(OUT_TRAIN, combined_train)
    write_atomic(OUT_VALID, combined_valid)

    check_all = read(OUT_ALL, index=":")
    check_train = read(OUT_TRAIN, index=":")
    check_valid = read(OUT_VALID, index=":")
    if len(check_all) != 211 or len(check_train) != 173 or len(check_valid) != 18:
        raise RuntimeError("round-trip count mismatch")
    all_ids = [a.info["config_id"] for a in check_all]
    if len(set(all_ids)) != 211:
        raise RuntimeError("round-trip duplicate config_id")

    phase_counts = Counter(a.info["phase"] for a in check_all)
    train_phase_counts = Counter(a.info["phase"] for a in check_train)

    lines = [
        "AL3NI COMBINED-211 MERGE STATUS (combined-129 + round300, 82 configs, 10 pods)",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        "",
        "SOURCES (all read-only, none modified)",
        f"  combined-129 all/train/val: {COMBINED129_ALL.name} (129) / {COMBINED129_TRAIN.name} (91) / {COMBINED129_VALID.name} (18)",
        f"  round300 (82, all TRAIN role, 10 pods): {ROUND300.name} (82)",
        "  cfg109/cfg110 (sealed): EXCLUDED, untouched -- geometry-only duplicate check performed, labels never read",
        "",
        "INTEGRITY CHECKS",
        "  config_id collision vs combined-129: NONE",
        "  geometry duplicate vs combined-129: NONE",
        "  geometry duplicate vs sealed cfg109/cfg110: NONE",
        "  internal round300 geometry duplicate: NONE",
        "",
        "OUTPUT",
        f"  All 211:       {OUT_ALL}  sha256={sha256(OUT_ALL)}",
        f"  TRAIN 173:     {OUT_TRAIN}  sha256={sha256(OUT_TRAIN)}",
        f"  VALIDATION 18: {OUT_VALID}  sha256={sha256(OUT_VALID)}",
        "",
        f"Round-trip: {len(check_all)}/211 all, {len(check_train)}/173 train, {len(check_valid)}/18 validation",
        f"Phase composition (all 211): {dict(phase_counts)}",
        f"Phase composition (TRAIN 173): {dict(train_phase_counts)}",
        "TEST/BLIND_HOLDOUT (Dataset-100's 20): UNCHANGED, not merged, referenced from original Dataset-100 files only.",
        "",
        "STATUS",
        "AL3NI COMBINED-211 MERGE COMPLETE",
    ]
    STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
