#!/usr/bin/env python3
"""Validate canonical Pilot 25 and create the fixed type-based splits.

The canonical EXTXYZ is read-only. Outputs are written only after every
integrity and scientific validation assertion has passed.
"""

from __future__ import annotations

import hashlib
import math
import platform
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import ase
import mace
import numpy as np
import torch
from ase.io import read, write


ROOT = Path("/workspace/ni_al")
CANONICAL = ROOT / "data/processed/ni_al_pilot_dft_25.extxyz"
REPORT = ROOT / "data/processed/pilot25_validation_report.txt"
TRAIN = ROOT / "data/datasets/ni_al_pilot_train_15.extxyz"
VALID = ROOT / "data/datasets/ni_al_pilot_val_5.extxyz"
TEST = ROOT / "data/datasets/ni_al_pilot_test_5.extxyz"
EXPECTED_SHA256 = "35b2b65fe77d181b5da30dd23bbb7ff9fc4f41c0c0f603738172e2f833ab5b0b"
EXPECTED_SIZE = 28755
PHASES = ("AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3")
CONFIG_TYPES = (
    "relaxed",
    "iso_m02",
    "iso_p02",
    "rattle_003",
    "shear015_rattle002",
)
TRAIN_TYPES = {"relaxed", "iso_m02", "iso_p02"}
VALID_TYPES = {"rattle_003"}
TEST_TYPES = {"shear015_rattle002"}
EXPECTED_RATIOS = {
    "AlNi": (1, 1),
    "Al3Ni": (3, 1),
    "Al3Ni2": (3, 2),
    "Al3Ni5": (3, 5),
    "AlNi3": (1, 3),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reduced_al_ni_ratio(atoms) -> tuple[int, int]:
    counts = Counter(atoms.get_chemical_symbols())
    assert set(counts) == {"Al", "Ni"}, f"unexpected elements: {dict(counts)}"
    divisor = math.gcd(counts["Al"], counts["Ni"])
    return counts["Al"] // divisor, counts["Ni"] // divisor


def geometry_fingerprint(atoms) -> str:
    """Hash species, cell, and wrapped fractional positions at tight tolerance."""
    payload = bytearray(" ".join(atoms.get_chemical_symbols()), "ascii")
    payload.extend(np.round(np.asarray(atoms.cell), 10).tobytes())
    payload.extend(np.round(atoms.get_scaled_positions(wrap=True), 10).tobytes())
    return hashlib.sha256(payload).hexdigest()


def robust_high_outliers(values: dict[str, float]) -> list[str]:
    """Return extreme high-side flags using median + 8 scaled MAD.

    This is a review aid, not an automatic exclusion rule. A zero MAD produces
    no flags because it provides no useful robust scale estimate.
    """
    array = np.asarray(list(values.values()), dtype=float)
    median = float(np.median(array))
    mad = float(np.median(np.abs(array - median)))
    if mad == 0.0:
        return []
    threshold = median + 8.0 * 1.4826 * mad
    return sorted(key for key, value in values.items() if value > threshold)


def main() -> None:
    assert CANONICAL.is_file(), f"missing canonical dataset: {CANONICAL}"
    assert CANONICAL.stat().st_size == EXPECTED_SIZE
    canonical_hash = sha256(CANONICAL)
    assert canonical_hash == EXPECTED_SHA256

    frames = read(CANONICAL, index=":")
    assert len(frames) == 25
    phase_counts = Counter(a.info.get("phase") for a in frames)
    type_counts = Counter(a.info.get("config_type") for a in frames)
    assert set(phase_counts) == set(PHASES)
    assert all(phase_counts[p] == 5 for p in PHASES)
    assert set(type_counts) == set(CONFIG_TYPES)
    assert all(type_counts[t] == 5 for t in CONFIG_TYPES)

    ids = [a.info.get("config_id") for a in frames]
    assert all(isinstance(item, str) and item for item in ids)
    assert len(ids) == len(set(ids)) == 25

    metrics: list[dict[str, object]] = []
    fingerprints: dict[str, str] = {}
    for index, atoms in enumerate(frames):
        config_id = atoms.info["config_id"]
        phase = atoms.info["phase"]
        config_type = atoms.info["config_type"]
        assert config_id == f"{phase}_{config_type}"
        assert reduced_al_ni_ratio(atoms) == EXPECTED_RATIOS[phase]
        assert len(atoms) > 0
        assert np.all(np.isfinite(atoms.positions))
        assert np.all(np.isfinite(np.asarray(atoms.cell)))
        assert np.all(atoms.pbc), f"non-periodic cell: {config_id}"
        volume = float(atoms.get_volume())
        assert np.isfinite(volume) and volume > 1.0e-10

        assert atoms.calc is not None, f"missing calculator data: {config_id}"
        assert {"energy", "forces", "stress"}.issubset(atoms.calc.results)
        energy = float(atoms.get_potential_energy())
        forces = np.asarray(atoms.get_forces(), dtype=float)
        stress = np.asarray(atoms.get_stress(voigt=True), dtype=float)
        assert np.isfinite(energy)
        assert forces.shape == (len(atoms), 3)
        assert np.all(np.isfinite(forces))
        assert stress.shape == (6,)
        assert np.all(np.isfinite(stress))

        fingerprint = geometry_fingerprint(atoms)
        assert fingerprint not in fingerprints, (
            f"duplicate geometry: {config_id} and {fingerprints.get(fingerprint)}"
        )
        fingerprints[fingerprint] = config_id
        force_norms = np.linalg.norm(forces, axis=1)
        metrics.append(
            {
                "index": index,
                "config_id": config_id,
                "phase": phase,
                "config_type": config_type,
                "n_atoms": len(atoms),
                "energy_pa": energy / len(atoms),
                "fmax": float(force_norms.max()),
                "frms": float(np.sqrt(np.mean(forces**2))),
                "stress_mag": float(np.linalg.norm(stress)),
                "volume": volume,
            }
        )

    train = [a for a in frames if a.info["config_type"] in TRAIN_TYPES]
    valid = [a for a in frames if a.info["config_type"] in VALID_TYPES]
    test = [a for a in frames if a.info["config_type"] in TEST_TYPES]
    assert (len(train), len(valid), len(test)) == (15, 5, 5)
    for split in (train, valid, test):
        assert {a.info["phase"] for a in split} == set(PHASES)
    split_ids = [a.info["config_id"] for split in (train, valid, test) for a in split]
    assert len(split_ids) == len(set(split_ids)) == 25
    assert set(split_ids) == set(ids)

    fmax_values = {str(row["config_id"]): float(row["fmax"]) for row in metrics}
    frms_values = {str(row["config_id"]): float(row["frms"]) for row in metrics}
    stress_values = {
        str(row["config_id"]): float(row["stress_mag"]) for row in metrics
    }
    outlier_flags = {
        "maximum force": robust_high_outliers(fmax_values),
        "RMS force": robust_high_outliers(frms_values),
        "stress magnitude": robust_high_outliers(stress_values),
    }

    lines = [
        "NI-AL FINAL PILOT 25 VALIDATION REPORT",
        "=" * 44,
        f"Validation time (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"Canonical path: {CANONICAL}",
        f"Canonical size: {CANONICAL.stat().st_size} bytes",
        f"Canonical SHA256: {canonical_hash}",
        "Validation result: PASS",
        "",
        "SUMMARY",
        "-------",
        f"Frames: {len(frames)}",
        f"Unique config_id values: {len(set(ids))}",
        f"Unique geometry fingerprints: {len(fingerprints)}",
        "Phase counts: " + ", ".join(f"{p}={phase_counts[p]}" for p in PHASES),
        "Config-type counts: "
        + ", ".join(f"{t}={type_counts[t]}" for t in CONFIG_TYPES),
        "Reference keys observed through ASE: energy, forces, stress",
        "All energies, forces, stresses, cells, and coordinates are finite.",
        "Every force array has shape (number_of_atoms, 3).",
        "Every ASE Voigt stress has shape (6,).",
        "All cells are periodic and have positive finite volume.",
        "All reduced Al:Ni compositions agree with phase labels.",
        "No duplicate config_id or duplicate geometry fingerprint was found.",
        "",
        "PER-CONFIGURATION METRICS",
        "-------------------------",
        "config_id                       phase    type                     N  energy_eV/atom     Fmax_eV/A     Frms_eV/A  |stress|_eV/A^3",
    ]
    for row in metrics:
        lines.append(
            f"{row['config_id']:<31s} {row['phase']:<8s} "
            f"{row['config_type']:<24s} {row['n_atoms']:>2d} "
            f"{row['energy_pa']:>15.8f} {row['fmax']:>13.8f} "
            f"{row['frms']:>13.8f} {row['stress_mag']:>17.8f}"
        )
    lines.extend(["", "OUTLIER REVIEW", "--------------"])
    for metric, flags in outlier_flags.items():
        lines.append(
            f"Robust extreme-high {metric} flags: " + (", ".join(flags) if flags else "none")
        )
    lines.extend(
        [
            "The flagging rule is median + 8 * 1.4826 * MAD and is advisory only.",
            "No configuration was removed or altered.",
            "",
            "FIXED SPLIT",
            "-----------",
            f"TRAIN: {len(train)} (relaxed, iso_m02, iso_p02), all five phases",
            f"VALIDATION: {len(valid)} (rattle_003), all five phases",
            f"TEST: {len(test)} (shear015_rattle002), all five phases",
            "Combined split config_id values: 25 unique; exact canonical coverage.",
            "TEST is reserved and must not be used for model selection or tuning.",
            "",
            "SOFTWARE",
            "--------",
            f"Python: {platform.python_version()}",
            f"ASE: {ase.__version__}",
            f"MACE: {mace.__version__}",
            f"PyTorch: {torch.__version__}",
            f"CUDA available during validation: {torch.cuda.is_available()}",
        ]
    )

    # Only write generated artifacts after every assertion above has passed.
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write(TRAIN, train, format="extxyz")
    write(VALID, valid, format="extxyz")
    write(TEST, test, format="extxyz")
    print("PILOT25 VALIDATION: PASS")
    print(f"Canonical SHA256: {canonical_hash}")
    print(f"Split counts: train={len(train)} validation={len(valid)} test={len(test)}")
    for metric, flags in outlier_flags.items():
        print(f"Outlier flags ({metric}): {', '.join(flags) if flags else 'none'}")


if __name__ == "__main__":
    main()
