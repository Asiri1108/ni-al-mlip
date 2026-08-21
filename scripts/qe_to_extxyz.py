from pathlib import Path
import csv
import numpy as np

from ase.io import read, write

ROOT = Path("/workspace/ni_al/data/raw_dft/diverse_pilot_01")
OUT = Path("/workspace/ni_al/data/processed/pilot01_all.extxyz")
MANIFEST = Path("/workspace/ni_al/data/processed/pilot01_manifest.csv")

OUT.parent.mkdir(parents=True, exist_ok=True)

files = sorted(
    p for p in ROOT.rglob("*.out")
    if "interrupted" not in p.name.lower()
)

configs = []
rows = []

print("Found canonical .out files:", len(files))

for path in files:
    rel = path.relative_to(ROOT)

    try:
        text = path.read_text(errors="ignore")

        if "JOB DONE" not in text:
            rows.append({
                "file": str(rel),
                "status": "SKIP_NO_JOB_DONE",
                "formula": "",
                "natoms": "",
                "energy_eV": "",
                "energy_eV_per_atom": "",
                "max_force_eV_A": "",
                "rms_force_eV_A": "",
            })
            print("SKIP no JOB DONE:", rel)
            continue

        atoms = read(
            str(path),
            index=-1,
            format="espresso-out",
        )

        energy = float(atoms.get_potential_energy())
        forces = np.asarray(atoms.get_forces(), dtype=float)

        if forces.shape != (len(atoms), 3):
            raise RuntimeError(
                f"Bad force shape {forces.shape}; expected {(len(atoms), 3)}"
            )

        if not np.isfinite(energy):
            raise RuntimeError("Non-finite energy")

        if not np.all(np.isfinite(forces)):
            raise RuntimeError("Non-finite forces")

        clean = atoms.copy()
        clean.calc = None

        clean.info["REF_energy"] = energy
        clean.info["source_file"] = str(rel)
        clean.info["phase"] = rel.parts[0]
        clean.info["configuration"] = rel.parts[1]

        clean.arrays["REF_forces"] = forces

        configs.append(clean)

        force_norms = np.linalg.norm(forces, axis=1)

        rows.append({
            "file": str(rel),
            "status": "OK",
            "formula": atoms.get_chemical_formula(),
            "natoms": len(atoms),
            "energy_eV": energy,
            "energy_eV_per_atom": energy / len(atoms),
            "max_force_eV_A": float(force_norms.max()),
            "rms_force_eV_A": float(np.sqrt(np.mean(forces**2))),
        })

        print(
            f"OK  {rel} | "
            f"{atoms.get_chemical_formula()} | "
            f"N={len(atoms)} | "
            f"E={energy:.8f} eV | "
            f"E/N={energy/len(atoms):.8f} eV/atom | "
            f"Fmax={force_norms.max():.6f} eV/A"
        )

    except Exception as exc:
        rows.append({
            "file": str(rel),
            "status": f"ERROR: {exc}",
            "formula": "",
            "natoms": "",
            "energy_eV": "",
            "energy_eV_per_atom": "",
            "max_force_eV_A": "",
            "rms_force_eV_A": "",
        })
        print("ERROR:", rel)
        print("      ", repr(exc))

if configs:
    write(str(OUT), configs, format="extxyz")

fieldnames = [
    "file",
    "status",
    "formula",
    "natoms",
    "energy_eV",
    "energy_eV_per_atom",
    "max_force_eV_A",
    "rms_force_eV_A",
]

with MANIFEST.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print()
print("===================================")
print("Valid configurations :", len(configs))
print("Rejected/skipped     :", len(files) - len(configs))
print("Dataset              :", OUT)
print("Manifest             :", MANIFEST)

if configs:
    energies_pa = np.array(
        [a.info["REF_energy"] / len(a) for a in configs]
    )
    max_forces = np.array(
        [
            np.linalg.norm(a.arrays["REF_forces"], axis=1).max()
            for a in configs
        ]
    )

    print(
        "Energy/atom range   :",
        f"{energies_pa.min():.6f}",
        "to",
        f"{energies_pa.max():.6f}",
        "eV/atom",
    )
    print(
        "Maximum force range :",
        f"{max_forces.min():.6f}",
        "to",
        f"{max_forces.max():.6f}",
        "eV/A",
    )
print("===================================")
