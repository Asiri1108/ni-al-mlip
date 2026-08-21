#!/usr/bin/env python3
"""STEP A -- EAM (LAMMPS) relative-energy + per-phase force evaluation on
combined-227, for the unified comparison matrix (NI_AL_UNIFIED_COMPARISON.md).

Runs 3 verified NIST EAM/alloy potentials (Pun-Mishin 2009, Mishin 2004
ipr2, Mishin 2002) single-point on all 227 combined-227 structures via the
newly-built manybody_eam LAMMPS install (tools/lammps/install/manybody_eam
-- PKG_MANYBODY, the only build with eam/alloy). Each structure is run in
its own subprocess invocation of the lmp binary (no LAMMPS python module
needed for a static single point), atom id order fixed to match the
original ASE frame order so LAMMPS forces align 1:1 with DFT forces.

Relative energy (identical convention to scripts/evaluate_dataset100_final.py
and scripts/evaluate_macemp0_zeroshot_pilot25.py):
  dft_rel(config)   = (E_dft[config]   - E_dft[phase_relaxed])   / natoms * 1000   (meV/atom)
  eam_rel(config)   = (E_eam[config]   - E_eam[phase_relaxed])   / natoms * 1000
  relative_energy_error = eam_rel - dft_rel
This cancels each EAM potential's own arbitrary energy zero against DFT's,
using that potential's OWN prediction on the phase's own relaxed structure
as its zero point -- no elemental references needed.
"""
import csv
import json
import subprocess
import time
from pathlib import Path

import numpy as np
from ase.io import read

R = Path("/workspace/ni_al")
DATA = R / "data/datasets/ni_al_combined227_dft.extxyz"
TEST_MANIFEST = R / "data/datasets/ni_al_dataset100_test_manifest.csv"
BLIND_MANIFEST = R / "data/datasets/ni_al_dataset100_blind_holdout_manifest.csv"
LMP = R / "tools/lammps/install/manybody_eam/bin/lmp"
LMP_LIB = R / "tools/lammps/install/manybody_eam/lib"
POT_DIR = R / "tools/eam_potentials"
OUT_DIR = R / "results/unified_comparison_stepA_v1"
LOG_DIR = R / "logs/unified_comparison_stepA_v1"

POTENTIALS = {
    "pun_mishin_2009": POT_DIR / "Mishin-Ni-Al-2009.eam.alloy",
    "mishin_2004_ipr2": POT_DIR / "NiAl_Mishin_2004.eam.alloy",
    "mishin_2002": POT_DIR / "NiAl02.eam.alloy",
}
MASS_NI = 58.71
MASS_AL = 26.982

TMP_DIR = Path("/tmp/eam_eval_combined227")


def write_lammps_data(atoms, path):
    """Write a LAMMPS data file with atom id == original ASE index + 1,
    type 1 = Ni, type 2 = Al, full (triclinic-safe) cell."""
    symbols = atoms.get_chemical_symbols()
    for s in symbols:
        if s not in ("Ni", "Al"):
            raise ValueError(f"unexpected element {s}")
    positions = atoms.get_positions()
    cell = atoms.get_cell()

    # LAMMPS triclinic box representation (ASE cell rows are lattice vectors a,b,c).
    a, b, c = cell[0], cell[1], cell[2]
    ax = np.linalg.norm(a)
    bx = np.dot(b, a) / ax
    by = np.sqrt(np.dot(b, b) - bx**2)
    cx = np.dot(c, a) / ax
    cy = (np.dot(b, c) - bx * cx) / by
    cz = np.sqrt(np.dot(c, c) - cx**2 - cy**2)
    xlo, ylo, zlo = 0.0, 0.0, 0.0
    xhi, yhi, zhi = ax, by, cz
    xy, xz, yz = bx, cx, cy

    # Rotate atom positions into the same LAMMPS-aligned frame as the cell.
    R1 = a / ax
    R2 = np.cross(np.array([0, 0, 1.0]), R1)
    # Build proper rotation matrix mapping ASE cartesian -> LAMMPS cell-aligned frame.
    Ahat = a / np.linalg.norm(a)
    Bhat_component = b - np.dot(b, Ahat) * Ahat
    Bhat = Bhat_component / np.linalg.norm(Bhat_component)
    Chat = np.cross(Ahat, Bhat)
    Mrot = np.array([Ahat, Bhat, Chat])
    lammps_positions = positions @ Mrot.T

    n = len(atoms)
    lines = [
        "LAMMPS data file, generated for unified comparison EAM eval", "",
        f"{n} atoms", "", "2 atom types", "",
        f"{xlo:.10f} {xhi:.10f} xlo xhi",
        f"{ylo:.10f} {yhi:.10f} ylo yhi",
        f"{zlo:.10f} {zhi:.10f} zlo zhi",
        f"{xy:.10f} {xz:.10f} {yz:.10f} xy xz yz", "",
        "Masses", "", f"1 {MASS_NI}", f"2 {MASS_AL}", "",
        "Atoms  # atomic", "",
    ]
    for i, (sym, pos) in enumerate(zip(symbols, lammps_positions)):
        typ = 1 if sym == "Ni" else 2
        lines.append(f"{i+1} {typ} {pos[0]:.10f} {pos[1]:.10f} {pos[2]:.10f}")
    Path(path).write_text("\n".join(lines) + "\n")
    return Mrot


def run_single_point(atoms, potential_path, tag):
    work = TMP_DIR / tag
    work.mkdir(parents=True, exist_ok=True)
    data_path = work / "structure.data"
    Mrot = write_lammps_data(atoms, data_path)
    dump_path = work / "forces.dump"
    in_path = work / "in.eval"
    in_path.write_text(f"""units metal
atom_style atomic
boundary p p p
read_data {data_path}
mass 1 {MASS_NI}
mass 2 {MASS_AL}
pair_style eam/alloy
pair_coeff * * {potential_path} Ni Al
neighbor 2.0 bin
neigh_modify delay 0 every 1 check yes
dump 1 all custom 1 {dump_path} id type fx fy fz
dump_modify 1 sort id format float %.12e
run 0
print "EVAL_PE_EV $(pe) EVAL_NATOMS $(atoms)"
""")
    result = subprocess.run(
        [str(LMP), "-in", str(in_path)],
        capture_output=True, text=True,
        env={"LD_LIBRARY_PATH": str(LMP_LIB), "PATH": "/usr/bin:/bin"},
        cwd=str(work),
    )
    if result.returncode != 0:
        raise RuntimeError(f"lmp failed for {tag}:\n{result.stdout[-3000:]}\n{result.stderr[-3000:]}")
    pe = None
    for line in result.stdout.splitlines():
        if line.startswith("EVAL_PE_EV"):
            parts = line.split()
            pe = float(parts[1])
            natoms = int(parts[3])
    if pe is None:
        raise RuntimeError(f"no PE found for {tag}\n{result.stdout[-2000:]}")

    # Parse the force dump (LAMMPS-frame forces), map back to original ASE order,
    # then rotate back into ASE's original cartesian frame with Mrot.T (inverse of
    # the rotation Mrot applied to positions -- forces transform the same way).
    dump_lines = dump_path.read_text().splitlines()
    idx = dump_lines.index("ITEM: ATOMS id type fx fy fz") + 1
    forces_by_id = {}
    for line in dump_lines[idx: idx + natoms]:
        parts = line.split()
        aid = int(parts[0])
        fx, fy, fz = float(parts[2]), float(parts[3]), float(parts[4])
        forces_by_id[aid] = np.array([fx, fy, fz])
    forces_lammps_frame = np.array([forces_by_id[i + 1] for i in range(natoms)])
    forces_ase_frame = forces_lammps_frame @ Mrot  # inverse rotation (Mrot is orthonormal)
    return pe, forces_ase_frame


def stats(x):
    x = np.asarray(x, float)
    return float(np.mean(np.abs(x))), float(np.sqrt(np.mean(x * x))), float(np.max(np.abs(x)))


def main():
    start = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    frames = read(DATA, ":")
    print(f"Loaded {len(frames)} combined-227 structures", flush=True)
    by_cid = {a.info["config_id"]: a for a in frames}

    reserved_ids = set()
    for manifest in (TEST_MANIFEST, BLIND_MANIFEST):
        for row in csv.DictReader(manifest.open()):
            reserved_ids.add(row["config_id"])
    assert len(reserved_ids) == 20, f"expected 20 reserved ids, got {len(reserved_ids)}"

    relaxed = {a.info["phase"]: a for a in frames if a.info.get("config_type") == "relaxed"}
    assert set(relaxed) == {"AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3"}

    all_rows = []
    for pot_name, pot_path in POTENTIALS.items():
        print(f"\n=== {pot_name} ===", flush=True)
        pred = {}
        t0 = time.time()
        for i, a in enumerate(frames):
            cid = a.info["config_id"]
            pe, forces = run_single_point(a, pot_path, f"{pot_name}/{cid}")
            pred[cid] = (pe, forces)
            if (i + 1) % 40 == 0:
                print(f"  {i+1}/{len(frames)} done ({time.time()-t0:.1f}s)", flush=True)
        print(f"  {pot_name}: {len(frames)} structures in {time.time()-t0:.1f}s", flush=True)

        relaxed_e = {phase: pred[relaxed[phase].info["config_id"]][0] for phase in relaxed}
        for a in frames:
            cid = a.info["config_id"]
            phase = a.info["phase"]
            natoms = len(a)
            dft_e = float(a.get_potential_energy())
            dft_f = np.asarray(a.get_forces(), float)
            dft_e_relaxed = float(relaxed[phase].get_potential_energy())
            dft_rel = (dft_e - dft_e_relaxed) / natoms * 1000.0

            eam_e, eam_f = pred[cid]
            eam_rel = (eam_e - relaxed_e[phase]) / natoms * 1000.0
            rel_error = eam_rel - dft_rel
            force_error = eam_f - dft_f
            f_mae, f_rmse, f_max = stats(force_error)

            all_rows.append({
                "method": pot_name, "config_id": cid, "phase": phase,
                "config_type": a.info.get("config_type"), "natoms": natoms,
                "reserved_20": cid in reserved_ids,
                "dft_relative_energy_mev_atom": dft_rel,
                "method_relative_energy_mev_atom": eam_rel,
                "relative_energy_error_mev_atom": rel_error,
                "force_mae_evA": f_mae, "force_rmse_evA": f_rmse, "force_max_evA": f_max,
                "_force_error": force_error.reshape(-1).tolist(),
            })

    public = [{k: v for k, v in r.items() if not k.startswith("_")} for r in all_rows]
    with (OUT_DIR / "eam_per_config.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(public[0]))
        w.writeheader()
        w.writerows(public)

    summary = []
    for pot_name in POTENTIALS:
        for subset_name, pred_fn in [("ALL_227", lambda r: True),
                                       ("RESERVED_20", lambda r: r["reserved_20"]),
                                       ("NON_RESERVED_207", lambda r: not r["reserved_20"])]:
            rows = [r for r in all_rows if r["method"] == pot_name and pred_fn(r)]
            if not rows:
                continue
            re_mae, re_rmse, re_max = stats([r["relative_energy_error_mev_atom"] for r in rows])
            force_all = np.concatenate([r["_force_error"] for r in rows])
            f_mae, f_rmse, f_max = stats(force_all)
            summary.append({
                "method": pot_name, "subset": subset_name, "count": len(rows),
                "relative_energy_mae_mev_atom": re_mae,
                "relative_energy_rmse_mev_atom": re_rmse,
                "relative_energy_max_abs_mev_atom": re_max,
                "force_mae_evA": f_mae, "force_rmse_evA": f_rmse, "force_max_evA": f_max,
            })
            for phase in sorted({r["phase"] for r in rows}):
                prows = [r for r in rows if r["phase"] == phase]
                pforce = np.concatenate([r["_force_error"] for r in prows])
                pf_mae, pf_rmse, pf_max = stats(pforce)
                pre_mae, pre_rmse, pre_max = stats([r["relative_energy_error_mev_atom"] for r in prows])
                summary.append({
                    "method": pot_name, "subset": f"{subset_name}:{phase}", "count": len(prows),
                    "relative_energy_mae_mev_atom": pre_mae,
                    "relative_energy_rmse_mev_atom": pre_rmse,
                    "relative_energy_max_abs_mev_atom": pre_max,
                    "force_mae_evA": pf_mae, "force_rmse_evA": pf_rmse, "force_max_evA": pf_max,
                })

    with (OUT_DIR / "eam_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)

    (OUT_DIR / "eam_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nDone in {time.time()-start:.1f}s. Wrote {OUT_DIR}/eam_per_config.csv and eam_summary.csv")


if __name__ == "__main__":
    main()
