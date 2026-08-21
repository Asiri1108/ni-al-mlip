from pathlib import Path
from collections import defaultdict
import numpy as np
from ase.io import read, write

SRC = Path("/workspace/ni_al/data/processed/pilot01_all.extxyz")
TRAIN = Path("/workspace/ni_al/data/datasets/pilot01_train.extxyz")
VALID = Path("/workspace/ni_al/data/datasets/pilot01_valid.extxyz")

data = read(str(SRC), index=":")

print("======================================")
print("NI-AL PILOT01 DATASET VALIDATION")
print("======================================")
print("Configurations:", len(data))

assert len(data) == 18

by_phase = defaultdict(list)

for i, atoms in enumerate(data):
    assert "REF_energy" in atoms.info
    assert "REF_forces" in atoms.arrays

    energy = float(atoms.info["REF_energy"])
    forces = np.asarray(atoms.arrays["REF_forces"])

    assert np.isfinite(energy)
    assert forces.shape == (len(atoms), 3)
    assert np.all(np.isfinite(forces))
    assert atoms.cell.volume > 0

    phase = atoms.info["phase"]
    config = atoms.info["configuration"]

    force_norm = np.linalg.norm(forces, axis=1)
    fmax = float(force_norm.max())

    by_phase[phase].append(
        {
            "atoms": atoms,
            "config": config,
            "epa": energy / len(atoms),
            "fmax": fmax,
        }
    )

print()
print("=== PER-PHASE SANITY CHECK ===")

for phase in sorted(by_phase):
    rows = by_phase[phase]
    emin = min(r["epa"] for r in rows)

    print()
    print(phase, "| configurations:", len(rows))

    for r in sorted(rows, key=lambda x: x["config"]):
        de = (r["epa"] - emin) * 1000.0

        print(
            f"  {r['config']:24s}"
            f" dE={de:10.3f} meV/atom"
            f" Fmax={r['fmax']:8.4f} eV/A"
        )

print()
print("=== SPLIT ===")

train = []
valid = []

for atoms in data:
    config = atoms.info["configuration"]

    # Deterministic validation:
    # one iso_p02 configuration from every phase.
    if config == "iso_p02":
        valid.append(atoms)
    else:
        train.append(atoms)

print("Train:", len(train))
print("Valid:", len(valid))

assert len(train) == 13
assert len(valid) == 5

train_phases = sorted(set(a.info["phase"] for a in train))
valid_phases = sorted(set(a.info["phase"] for a in valid))

print("Train phases:", train_phases)
print("Valid phases:", valid_phases)

write(str(TRAIN), train, format="extxyz")
write(str(VALID), valid, format="extxyz")

print()
print("TRAIN :", TRAIN)
print("VALID :", VALID)
print()
print("DATASET VALIDATION: PASS")
