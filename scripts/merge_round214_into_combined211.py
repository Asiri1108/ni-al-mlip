#!/usr/bin/env python3
"""Merge Round-214 (7, all TRAIN) into combined-211 -> combined-218."""

import hashlib
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import csv
import numpy as np
from ase.io import read, write

ROOT = Path("/workspace/ni_al")
COMBINED211_ALL = ROOT / "data/datasets/ni_al_combined211_dft.extxyz"
COMBINED211_TRAIN = ROOT / "data/datasets/ni_al_combined211_train_173.extxyz"
COMBINED211_VALID = ROOT / "data/datasets/ni_al_combined211_validation_18.extxyz"
ROUND214 = ROOT / "data/al3ni_remediation_v1/round214_dft.extxyz"
ROUND214_MANIFEST = ROOT / "data/al3ni_remediation_v1/round214_dft_manifest.csv"
SEALED_DIR = ROOT / "data/al3ni_remediation_v1/structures"
SEALED_IDS = ["cfg109_Al3Ni_iso_expansion", "cfg110_Al3Ni_volume_rattle_expansion"]

OUT_ALL = ROOT / "data/datasets/ni_al_combined218_dft.extxyz"
OUT_TRAIN = ROOT / "data/datasets/ni_al_combined218_train_180.extxyz"
OUT_VALID = ROOT / "data/datasets/ni_al_combined218_validation_18.extxyz"
STATUS = ROOT / "configs/AL3NI_COMBINED218_MERGE_STATUS.txt"


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
    combined211 = read(COMBINED211_ALL, index=":")
    round214 = read(ROUND214, index=":")
    round214_rows = list(csv.DictReader(ROUND214_MANIFEST.open(newline="")))

    if len(combined211) != 211:
        raise RuntimeError("combined-211 source does not contain 211 frames")
    if len(round214) != 7:
        raise RuntimeError("round214 source does not contain 7 frames")
    if not all(r["target_role"] == "TRAIN" for r in round214_rows):
        raise RuntimeError("round214 manifest contains a non-TRAIN role")

    ids211 = {a.info["config_id"] for a in combined211}
    ids214 = {a.info["config_id"] for a in round214}
    collide = ids211 & ids214
    if collide:
        raise RuntimeError(f"config_id collision with combined-211: {collide}")

    geoms211 = {geometry_fingerprint(a) for a in combined211}
    geoms214 = {a.info["config_id"]: geometry_fingerprint(a) for a in round214}
    dup_vs_211 = {cid for cid, g in geoms214.items() if g in geoms211}
    if dup_vs_211:
        raise RuntimeError(f"round214 geometry duplicates existing combined-211 members: {dup_vs_211}")

    sealed_geoms = {}
    for sid in SEALED_IDS:
        p = SEALED_DIR / f"{sid}.extxyz"
        sealed_geoms[sid] = geometry_fingerprint(read(p))
    dup_vs_sealed = {cid for cid, g in geoms214.items() if g in sealed_geoms.values()}
    if dup_vs_sealed:
        raise RuntimeError(f"round214 geometry duplicates sealed cfg109/cfg110: {dup_vs_sealed}")

    if len(set(geoms214.values())) != 7:
        raise RuntimeError("internal round214 geometry duplicate")

    combined_all = combined211 + round214
    combined_train = read(COMBINED211_TRAIN, index=":") + round214
    combined_valid = read(COMBINED211_VALID, index=":")

    if (len(combined_all), len(combined_train), len(combined_valid)) != (218, 180, 18):
        raise RuntimeError("post-merge counts do not match expectation (218/180/18)")

    write_atomic(OUT_ALL, combined_all)
    write_atomic(OUT_TRAIN, combined_train)
    write_atomic(OUT_VALID, combined_valid)

    check_all = read(OUT_ALL, index=":")
    check_train = read(OUT_TRAIN, index=":")
    check_valid = read(OUT_VALID, index=":")
    if len(check_all) != 218 or len(check_train) != 180 or len(check_valid) != 18:
        raise RuntimeError("round-trip count mismatch")
    all_ids = [a.info["config_id"] for a in check_all]
    if len(set(all_ids)) != 218:
        raise RuntimeError("round-trip duplicate config_id")

    phase_counts = Counter(a.info["phase"] for a in check_all)
    train_phase_counts = Counter(a.info["phase"] for a in check_train)

    lines = [
        "AL3NI COMBINED-218 MERGE STATUS (combined-211 + round214, 7 configs, pods A/B/C)",
        "", f"Generated UTC: {datetime.now(timezone.utc).isoformat()}", "",
        "SOURCES (all read-only, none modified)",
        f"  combined-211 all/train/val: {COMBINED211_ALL.name} (211) / {COMBINED211_TRAIN.name} (173) / {COMBINED211_VALID.name} (18)",
        f"  round214 (7, all TRAIN role, pods A/B/C): {ROUND214.name} (7)",
        "  cfg109/cfg110 (sealed): EXCLUDED, untouched",
        "",
        "INTEGRITY CHECKS",
        "  config_id collision vs combined-211: NONE",
        "  geometry duplicate vs combined-211: NONE",
        "  geometry duplicate vs sealed cfg109/cfg110: NONE",
        "  internal round214 geometry duplicate: NONE",
        "",
        "OUTPUT",
        f"  All 218:      {OUT_ALL}  sha256={sha256(OUT_ALL)}",
        f"  TRAIN 180:    {OUT_TRAIN}  sha256={sha256(OUT_TRAIN)}",
        f"  VALIDATION 18: {OUT_VALID}  sha256={sha256(OUT_VALID)}",
        "",
        f"Round-trip: {len(check_all)}/218 all, {len(check_train)}/180 train, {len(check_valid)}/18 validation",
        f"Phase composition (all 218): {dict(phase_counts)}",
        f"Phase composition (TRAIN 180): {dict(train_phase_counts)}",
        "TEST/BLIND_HOLDOUT (Dataset-100's 20): UNCHANGED.",
        "",
        "COVERAGE IMPACT",
        "Closes the last 4 EXTRAPOLATION flags after round300 (cfg042 Al3Ni, cfg074 Al3Ni2,",
        "cfg059/cfg061 Al3Ni5) plus AlNi's 2 remaining thin buckets (shear n=1->3,",
        "volume_rattle n=2->3). Projected: zero open EXTRAPOLATION flags project-wide.",
        "",
        "STATUS", "AL3NI COMBINED-218 MERGE COMPLETE",
    ]
    STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
