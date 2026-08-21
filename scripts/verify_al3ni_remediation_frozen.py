#!/usr/bin/env python3
"""Fail-closed verification of the frozen Al3Ni remediation design."""
from __future__ import annotations

import csv
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path("/workspace/ni_al")
BASE = ROOT / "data/al3ni_remediation_v1"
STATUS = ROOT / "configs/AL3NI_REMEDIATION_DESIGN_STATUS.txt"
EXPECTED = {
    "remediation_manifest.csv": "53ad131882494d526c5daa99404e05eaf515d44c593634507c6fc162d4ae973e",
    "split_membership_manifest.csv": "e51afe7df4e15e55bc76222ccd31fcc74a7bfb2310ee99de59f8c3e5424c6599",
    "rattle_seed_manifest.csv": "34ebcf4bbeb9040f62eed1359ecca879332b19739df7513aafd7ff16e93449bf",
    "artifact_sha256.csv": "a76cd1dd1d2f3cff6290a8b2369dfa9799dc4ccbfd1052bf8972f3a93c498d15",
    "generation_metadata.json": "d10761288469a1f8f1c89bbf1fc02ae249100c3d15875f7121f59b7cde8011b8",
    "PROVENANCE.txt": "019ce50d456461b9940eaa66f4493ed576e49ef312ff5119b0113a1001bcbe6e",
}
EXPECTED_IDS = [
    "cfg101_Al3Ni_iso_compression", "cfg102_Al3Ni_iso_compression",
    "cfg103_Al3Ni_iso_expansion", "cfg104_Al3Ni_volume_rattle_compression",
    "cfg105_Al3Ni_volume_rattle_expansion", "cfg106_Al3Ni_rattle_020",
    "cfg107_Al3Ni_volume_rattle_compression", "cfg108_Al3Ni_rattle_030",
    "cfg109_Al3Ni_iso_expansion", "cfg110_Al3Ni_volume_rattle_expansion",
]
CONFIRMATION = set(EXPECTED_IDS[-2:])


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fail(message: str) -> None:
    print(f"FROZEN DESIGN VERIFICATION FAILED: {message}", file=sys.stderr)
    raise SystemExit(2)


def main() -> None:
    for name, expected in EXPECTED.items():
        path = BASE / name
        if not path.is_file() or sha256(path) != expected:
            fail(f"governing artifact mismatch: {path}")

    status = STATUS.read_text()
    required = ["State: FROZEN BEFORE DFT", "TRAIN = 6", "VALIDATION = 2",
                "CONFIRMATION = 2", "TOTAL = 10", "DFT STARTED: NO"]
    if any(token not in status for token in required):
        fail("design status does not assert the frozen pre-DFT state")

    with (BASE / "remediation_manifest.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    with (BASE / "split_membership_manifest.csv").open(newline="") as stream:
        split_rows = list(csv.DictReader(stream))
    if [r["config_id"] for r in rows] != EXPECTED_IDS:
        fail("remediation manifest IDs/order differ from cfg101-cfg110")
    if [r["config_id"] for r in split_rows] != EXPECTED_IDS:
        fail("split manifest IDs/order differ from cfg101-cfg110")
    if Counter(r["split"] for r in split_rows) != Counter(
        {"TRAIN": 6, "VALIDATION": 2, "CONFIRMATION_HOLDOUT": 2}
    ):
        fail("split counts differ from frozen 6/2/2 allocation")
    got_confirmation = {r["config_id"] for r in split_rows
                        if r["split"] == "CONFIRMATION_HOLDOUT"}
    if got_confirmation != CONFIRMATION:
        fail("confirmation membership differs from cfg109/cfg110")
    for row in split_rows:
        if row["config_id"] in CONFIRMATION and not row["label_access_policy"].startswith("NEVER_"):
            fail(f"confirmation policy is not sealed: {row['config_id']}")

    manifest_by_id = {r["config_id"]: r for r in rows}
    for row in split_rows:
        source = manifest_by_id[row["config_id"]]
        for field in ("structure_sha256", "geometry_sha256", "qe_input_sha256"):
            if row[field] != source[field]:
                fail(f"cross-manifest {field} mismatch: {row['config_id']}")
        for field in ("structure_path", "qe_input_path"):
            path = Path(source[field])
            expected = source[field.replace("_path", "_sha256")]
            if not path.is_file() or sha256(path) != expected:
                fail(f"frozen {field} mismatch: {row['config_id']}")

    with (BASE / "artifact_sha256.csv").open(newline="") as stream:
        artifact_rows = list(csv.DictReader(stream))
    if len(artifact_rows) != 20:
        fail("artifact manifest does not contain exactly 20 structure/input records")
    for row in artifact_rows:
        path = Path(row["path"])
        if not path.is_file() or sha256(path) != row["sha256"] or path.stat().st_size != int(row["size_bytes"]):
            fail(f"artifact mismatch: {row['config_id']} {row['artifact_type']}")

    numbers = [int(re.match(r"cfg(\d{3})_", item).group(1)) for item in EXPECTED_IDS]
    if numbers != list(range(101, 111)):
        fail("internal expected ID range error")
    print("FROZEN DESIGN VERIFICATION PASS")
    print("CONFIGS: 10; TRAIN: 6; VALIDATION: 2; CONFIRMATION: 2")
    print("CFG109/CFG110 CONFIRMATION MEMBERSHIP AND LABEL SEAL: PASS")
    print("ALL STRUCTURE AND QE INPUT HASHES: PASS")


if __name__ == "__main__":
    main()
