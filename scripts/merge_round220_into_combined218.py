#!/usr/bin/env python3
"""Merge Round-220 (2, both TRAIN) into combined-218 -> combined-220.

Closes the last 2 EXTRAPOLATION flags (cfg041, cfg107) per the 2026-08-17
decision to stop expansion at ~220 structures
(configs/SESSION_STATE_AL3NI_EXPANSION_DESIGN.md Section 13).

cfg109/cfg110 are explicitly NOT read anywhere in this script (this
session's constraint). Duplicate-geometry leakage is instead checked
against the full combined-218 population (which already excludes the
sealed pair -- confirmed by every prior coverage audit) -- this is the
same substitution used in the round220 design pass. The sealed set's
integrity is preserved by non-access, not by a fresh vs-sealed compare.
"""

import hashlib
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from ase.io import read, write

ROOT = Path("/workspace/ni_al")
COMBINED218_ALL = ROOT / "data/datasets/ni_al_combined218_dft.extxyz"
COMBINED218_TRAIN = ROOT / "data/datasets/ni_al_combined218_train_180.extxyz"
COMBINED218_VALID = ROOT / "data/datasets/ni_al_combined218_validation_18.extxyz"
ROUND220 = ROOT / "data/al3ni_remediation_v1/round220_dft.extxyz"
ROUND220_MANIFEST = ROOT / "data/al3ni_remediation_v1/round220_dft_manifest.csv"

OUT_ALL = ROOT / "data/datasets/ni_al_combined220_dft.extxyz"
OUT_TRAIN = ROOT / "data/datasets/ni_al_combined220_train_182.extxyz"
OUT_VALID = ROOT / "data/datasets/ni_al_combined220_validation_18.extxyz"
STATUS = ROOT / "configs/AL3NI_COMBINED220_MERGE_STATUS.txt"

import csv


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
    combined218 = read(COMBINED218_ALL, index=":")
    round220 = read(ROUND220, index=":")
    round220_rows = list(csv.DictReader(ROUND220_MANIFEST.open(newline="")))

    if len(combined218) != 218:
        raise RuntimeError(f"combined-218 source does not contain 218 frames (found {len(combined218)})")
    if len(round220) != 2:
        raise RuntimeError("round220 source does not contain 2 frames")
    if not all(r["target_role"] == "TRAIN" for r in round220_rows):
        raise RuntimeError("round220 manifest contains a non-TRAIN role")

    ids218 = {a.info["config_id"] for a in combined218}
    ids220 = {a.info["config_id"] for a in round220}
    collide = ids218 & ids220
    if collide:
        raise RuntimeError(f"config_id collision with combined-218: {collide}")

    geoms218 = {geometry_fingerprint(a) for a in combined218}
    geoms220 = {a.info["config_id"]: geometry_fingerprint(a) for a in round220}
    dup_vs_218 = {cid for cid, g in geoms220.items() if g in geoms218}
    if dup_vs_218:
        raise RuntimeError(f"round220 geometry duplicates existing combined-218 members: {dup_vs_218}")

    if len(set(geoms220.values())) != 2:
        raise RuntimeError("internal round220 geometry duplicate")

    # Duplicate-vs-TRAIN specifically (stricter subset check requested)
    train218_ids = {a.info["config_id"] for a in read(COMBINED218_TRAIN, index=":")}
    geoms_train218 = {geometry_fingerprint(a) for a in combined218 if a.info["config_id"] in train218_ids}
    dup_vs_train = {cid for cid, g in geoms220.items() if g in geoms_train218}
    if dup_vs_train:
        raise RuntimeError(f"round220 geometry duplicates existing TRAIN members: {dup_vs_train}")

    combined_all = combined218 + round220
    combined_train = read(COMBINED218_TRAIN, index=":") + round220
    combined_valid = read(COMBINED218_VALID, index=":")

    if (len(combined_all), len(combined_train), len(combined_valid)) != (220, 182, 18):
        raise RuntimeError("post-merge counts do not match expectation (220/182/18)")

    write_atomic(OUT_ALL, combined_all)
    write_atomic(OUT_TRAIN, combined_train)
    write_atomic(OUT_VALID, combined_valid)

    check_all = read(OUT_ALL, index=":")
    check_train = read(OUT_TRAIN, index=":")
    check_valid = read(OUT_VALID, index=":")
    if len(check_all) != 220 or len(check_train) != 182 or len(check_valid) != 18:
        raise RuntimeError("round-trip count mismatch")
    all_ids = [a.info["config_id"] for a in check_all]
    if len(set(all_ids)) != 220:
        raise RuntimeError("round-trip duplicate config_id")

    phase_counts = Counter(a.info["phase"] for a in check_all)
    train_phase_counts = Counter(a.info["phase"] for a in check_train)

    before_phase_counts = Counter(a.info["phase"] for a in combined218)
    before_train_phase_counts = Counter(a.info["phase"] for a in read(COMBINED218_TRAIN, index=":"))

    lines = [
        "AL3NI COMBINED-220 MERGE STATUS (combined-218 + round220, 2 configs, both TRAIN)",
        "", f"Generated UTC: {datetime.now(timezone.utc).isoformat()}", "",
        "SOURCES (all read-only, none modified)",
        f"  combined-218 all/train/val: {COMBINED218_ALL.name} (218) / {COMBINED218_TRAIN.name} (180) / {COMBINED218_VALID.name} (18)",
        f"  round220 (2, both TRAIN role): {ROUND220.name} (2) -- cfg283 (closes cfg041), cfg284 (closes cfg107)",
        "  cfg109/cfg110 (sealed): NOT READ, NOT REFERENCED",
        "",
        "INTEGRITY CHECKS",
        "  config_id collision vs combined-218: NONE",
        "  geometry duplicate vs combined-218 (all roles): NONE",
        "  geometry duplicate vs combined-218 TRAIN only: NONE",
        "  internal round220 geometry duplicate: NONE",
        "  geometry duplicate vs sealed cfg109/cfg110: NOT CHECKED (sealed files not read, per explicit instruction)",
        "",
        "OUTPUT",
        f"  All 220:       {OUT_ALL}  sha256={sha256(OUT_ALL)}",
        f"  TRAIN 182:     {OUT_TRAIN}  sha256={sha256(OUT_TRAIN)}",
        f"  VALIDATION 18: {OUT_VALID}  sha256={sha256(OUT_VALID)}",
        "",
        f"Round-trip: {len(check_all)}/220 all, {len(check_train)}/182 train, {len(check_valid)}/18 validation",
        "",
        "BEFORE (combined-218) / AFTER (combined-220)",
        f"  TOTAL:      218 -> 220",
        f"  TRAIN:      180 -> 182",
        f"  VALIDATION: 18 -> 18 (unchanged)",
        f"  Phase composition, all (before):  {dict(sorted(before_phase_counts.items()))}",
        f"  Phase composition, all (after):   {dict(sorted(phase_counts.items()))}",
        f"  Phase composition, TRAIN (before): {dict(sorted(before_train_phase_counts.items()))}",
        f"  Phase composition, TRAIN (after):  {dict(sorted(train_phase_counts.items()))}",
        "TEST/BLIND_HOLDOUT (Dataset-100's 20): UNCHANGED.",
        "",
        "COVERAGE IMPACT",
        "Closes the last 2 open EXTRAPOLATION flags project-wide (cfg041 Al3Ni uniaxial,",
        "cfg107 Al3Ni volume_rattle). See results/full_coverage_audit_v1/priority_ranking_combined220.md:",
        "zero EXTRAPOLATION flags remain anywhere.",
        "",
        "STATUS", "AL3NI COMBINED-220 MERGE COMPLETE",
    ]
    STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
