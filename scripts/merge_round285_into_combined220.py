#!/usr/bin/env python3
"""Merge Round-285 (7, all TRAIN) into combined-220 -> combined-227.

Densifies the Al3Ni high-expansion regime (+3.0%..+5.0%, iso_expansion +
volume_rattle_expansion) after cfg109/cfg110's 2026-08-17 unsealing FAIL
was traced to a data-density gap (seed variance and LoRA-rank capacity
both ruled out -- see configs/project_knowledge.md Section 5).

cfg297/cfg299 (round285's new sealed confirmation pair,
data/al3ni_remediation_v1/round285_sealed_manifest.csv) are explicitly
NOT read anywhere in this script -- only round285_dft.extxyz (the 7-frame
TRAIN-only extraction output) is opened. Their absence from every written
output is verified below by direct config_id search, not by relying on
this script simply "not including" them.
"""

import hashlib
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from ase.io import read, write

ROOT = Path("/workspace/ni_al")
COMBINED220_ALL = ROOT / "data/datasets/ni_al_combined220_dft.extxyz"
COMBINED220_TRAIN = ROOT / "data/datasets/ni_al_combined220_train_182.extxyz"
COMBINED220_VALID = ROOT / "data/datasets/ni_al_combined220_validation_18.extxyz"
ROUND285 = ROOT / "data/al3ni_remediation_v1/round285_dft.extxyz"

OUT_ALL = ROOT / "data/datasets/ni_al_combined227_dft.extxyz"
OUT_TRAIN = ROOT / "data/datasets/ni_al_combined227_train_189.extxyz"
OUT_VALID = ROOT / "data/datasets/ni_al_combined227_validation_18.extxyz"
STATUS = ROOT / "configs/AL3NI_COMBINED227_MERGE_STATUS.txt"

SEALED_IDS_MUST_BE_ABSENT = {"cfg297_Al3Ni_iso_expansion", "cfg299_Al3Ni_volume_rattle_expansion"}


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


def assert_sealed_absent_from_file(path):
    """grep-equivalent: search the raw text of a written file for either sealed
    config_id, not just check the in-memory frame list."""
    text = path.read_text()
    hits = [sid for sid in SEALED_IDS_MUST_BE_ABSENT if sid in text]
    if hits:
        raise RuntimeError(f"SEALED CONFIG ID FOUND IN {path}: {hits} -- ABORTING, file left in place for inspection")
    return 0


def main():
    combined220 = read(COMBINED220_ALL, index=":")
    round285 = read(ROUND285, index=":")

    if len(combined220) != 220:
        raise RuntimeError(f"combined-220 source does not contain 220 frames (found {len(combined220)})")
    if len(round285) != 7:
        raise RuntimeError("round285 source does not contain 7 frames")

    round285_ids = {a.info["config_id"] for a in round285}
    if not round285_ids.isdisjoint(SEALED_IDS_MUST_BE_ABSENT):
        raise RuntimeError(f"SEALED config id present in round285 extraction source itself: "
                            f"{round285_ids & SEALED_IDS_MUST_BE_ABSENT} -- ABORTING before any write")
    if not all(a.info["target_role"] == "TRAIN" for a in round285):
        raise RuntimeError("round285 source contains a non-TRAIN role")

    ids220 = {a.info["config_id"] for a in combined220}
    collide = ids220 & round285_ids
    if collide:
        raise RuntimeError(f"config_id collision with combined-220: {collide}")

    geoms220 = {geometry_fingerprint(a) for a in combined220}
    geoms285 = {a.info["config_id"]: geometry_fingerprint(a) for a in round285}
    dup_vs_220 = {cid for cid, g in geoms285.items() if g in geoms220}
    if dup_vs_220:
        raise RuntimeError(f"round285 geometry duplicates existing combined-220 members: {dup_vs_220}")
    if len(set(geoms285.values())) != 7:
        raise RuntimeError("internal round285 geometry duplicate")

    train220_ids = {a.info["config_id"] for a in read(COMBINED220_TRAIN, index=":")}
    geoms_train220 = {geometry_fingerprint(a) for a in combined220 if a.info["config_id"] in train220_ids}
    dup_vs_train = {cid for cid, g in geoms285.items() if g in geoms_train220}
    if dup_vs_train:
        raise RuntimeError(f"round285 geometry duplicates existing TRAIN members: {dup_vs_train}")

    combined_all = combined220 + round285
    combined_train = read(COMBINED220_TRAIN, index=":") + round285
    combined_valid = read(COMBINED220_VALID, index=":")

    if (len(combined_all), len(combined_train), len(combined_valid)) != (227, 189, 18):
        raise RuntimeError("post-merge counts do not match expectation (227/189/18)")

    all_ids_premerge = [a.info["config_id"] for a in combined_all]
    if not SEALED_IDS_MUST_BE_ABSENT.isdisjoint(all_ids_premerge):
        raise RuntimeError("SEALED config id found in pre-write in-memory frame list -- ABORTING")

    write_atomic(OUT_ALL, combined_all)
    write_atomic(OUT_TRAIN, combined_train)
    write_atomic(OUT_VALID, combined_valid)

    # Physical absence check: raw text search of every written file, not just the
    # in-memory object that was serialized. Catches e.g. a stray comment, a leftover
    # info key, or any other unexpected textual trace.
    for path in (OUT_ALL, OUT_TRAIN, OUT_VALID):
        assert_sealed_absent_from_file(path)

    check_all = read(OUT_ALL, index=":")
    check_train = read(OUT_TRAIN, index=":")
    check_valid = read(OUT_VALID, index=":")
    if len(check_all) != 227 or len(check_train) != 189 or len(check_valid) != 18:
        raise RuntimeError("round-trip count mismatch")
    all_ids = [a.info["config_id"] for a in check_all]
    if len(set(all_ids)) != 227:
        raise RuntimeError("round-trip duplicate config_id")
    if not SEALED_IDS_MUST_BE_ABSENT.isdisjoint(set(all_ids)):
        raise RuntimeError("SEALED config id found in round-trip-read frame list -- ABORTING")

    phase_counts = Counter(a.info["phase"] for a in check_all)
    train_phase_counts = Counter(a.info["phase"] for a in check_train)
    before_phase_counts = Counter(a.info["phase"] for a in combined220)
    before_train_phase_counts = Counter(a.info["phase"] for a in read(COMBINED220_TRAIN, index=":"))

    lines = [
        "AL3NI COMBINED-227 MERGE STATUS (combined-220 + round285, 7 configs, all TRAIN)",
        "", f"Generated UTC: {datetime.now(timezone.utc).isoformat()}", "",
        "SOURCES (all read-only, none modified)",
        f"  combined-220 all/train/val: {COMBINED220_ALL.name} (220) / {COMBINED220_TRAIN.name} (182) / {COMBINED220_VALID.name} (18)",
        f"  round285 (7, all TRAIN role): {ROUND285.name} (7) -- cfg287,288,289,290,292,293,294",
        "  cfg297/cfg299 (sealed): NOT READ, NOT REFERENCED, verified physically absent from all 3 output files (grep-equivalent text search, not just object exclusion)",
        "  cfg109/cfg110 (consumed, unsealed 2026-08-17): NOT READ, NOT REFERENCED",
        "",
        "INTEGRITY CHECKS",
        "  config_id collision vs combined-220: NONE",
        "  geometry duplicate vs combined-220 (all roles): NONE",
        "  geometry duplicate vs combined-220 TRAIN only: NONE",
        "  internal round285 geometry duplicate: NONE",
        "  cfg297/cfg299 physical absence (raw text search, all 3 output files): CONFIRMED ABSENT",
        "",
        "OUTPUT",
        f"  All 227:       {OUT_ALL}  sha256={sha256(OUT_ALL)}",
        f"  TRAIN 189:     {OUT_TRAIN}  sha256={sha256(OUT_TRAIN)}",
        f"  VALIDATION 18: {OUT_VALID}  sha256={sha256(OUT_VALID)}",
        "",
        f"Round-trip: {len(check_all)}/227 all, {len(check_train)}/189 train, {len(check_valid)}/18 validation",
        "",
        "BEFORE (combined-220) / AFTER (combined-227)",
        "  TOTAL:      220 -> 227",
        "  TRAIN:      182 -> 189",
        "  VALIDATION: 18 -> 18 (unchanged)",
        f"  Phase composition, all (before):  {dict(sorted(before_phase_counts.items()))}",
        f"  Phase composition, all (after):   {dict(sorted(phase_counts.items()))}",
        f"  Phase composition, TRAIN (before): {dict(sorted(before_train_phase_counts.items()))}",
        f"  Phase composition, TRAIN (after):  {dict(sorted(train_phase_counts.items()))}",
        "TEST/BLIND_HOLDOUT (Dataset-100's 20): UNCHANGED.",
        "",
        "COVERAGE IMPACT",
        "Densifies Al3Ni iso_expansion/volume_rattle_expansion TRAIN rungs across +3.0%..+5.0%:",
        "s=4.0%, 4.5%, 5.0% now have both families (previously only s=2.0%/4.6%/5.6% did, with",
        "s=3.0% iso-only). s=3.0% volume_rattle_expansion added (cfg290), completing that rung's pair.",
        "Largest remaining TRAIN gap in +3.0%..+5.0%: 1.0 point (3.0%->4.0%), by design -- the only",
        "interval that could not be densified to 0.5 points without leaking against cfg043 (the",
        "design-contaminated feedback probe). See configs/ROUND285_HIGH_EXPANSION_DENSIFY_DESIGN_STATUS.md.",
        "",
        "STATUS", "AL3NI COMBINED-227 MERGE COMPLETE",
    ]
    STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
