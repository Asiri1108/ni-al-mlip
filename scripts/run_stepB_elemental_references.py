#!/usr/bin/env python3
"""STEP B -- QE/PBE elemental references (mu_Al, mu_Ni) for the unified
comparison matrix (NI_AL_UNIFIED_COMPARISON.md).

Two small cells (1 atom each), locked project production settings:
  ecutwfc=90 Ry, ecutrho=720 Ry, MV smearing, degauss=0.010 Ry,
  conv_thr=1.0d-10, mixing_beta=0.30, diagonalization='david'.

Elemental Ni is NOT covered by the five-phase locked settings -- it got its
own separate decision in the project's convergence campaign
(configs/NI_AL_DATA_SHOWCASE.md Section 6, lines 153/164-166):
  nspin=2, starting_magnetization(1)=0.60, k-mesh 22x22x22
  (adopted after 22x22x22 vs 24x24x24 gave dE=0.488716 meV/atom).
Using nspin=1 here would silently corrupt every formation energy derived
from mu_Ni, so it is hardcoded exactly as recorded, not re-derived.

Elemental Al has no prior convergence record in this project, so this
script runs its own small k-mesh check (20x20x20 vs 24x24x24, the same
final bracket used for Ni) at a fixed trial geometry before relaxing,
rather than assuming a mesh by analogy to Ni -- this project's own house
rule (project_knowledge.md) is that settings are decided per-element/phase,
never assumed by analogy.

Procedure per element: vc-relax, then an INDEPENDENT final SCF on the
relaxed cell (separate calculation, not just reading the last vc-relax
step -- same convention Phase 1 used per the task instructions). mu = E_total
(Ry, converted to eV) / natoms (=1 for these cells).
"""
import re
import subprocess
import time
from pathlib import Path

import numpy as np
from ase.build import bulk

R = Path("/workspace/ni_al")
QE = R / "tools/qe_gpu/builds/sm_89_autoconf/PW/src/pw.x"
PSEUDO_DIR = R / "tools/qe_pseudos"
NVROOT = R / "tools/qe_gpu/nvhpc/Linux_x86_64/26.5"

QE_SHA256 = "66b7ea9f173b006854fc9e27dc9982c332dad295384803d612da7dad3edc7f8e"
AL_PSEUDO_SHA256 = "fd7b78921e6d0939095b681c328732668eaefd1dee6882fdbc03be463550cc97"
NI_PSEUDO_SHA256 = "f76b86ce60cde3d83dfcc8df79ba05478db573d158289f1b226919442d977d25"

OUT = R / "results/unified_comparison_stepB_v1"
WORK = R / "runs/unified_comparison_stepB_v1"
RY_TO_EV = 13.605693122994

import hashlib


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_env():
    import os
    env = dict(os.environ)
    env["PATH"] = f"{NVROOT}/compilers/bin:" + env.get("PATH", "")
    env["NVHPC_CUDA_HOME"] = f"{NVROOT}/cuda/12.9"
    env["LD_LIBRARY_PATH"] = (
        f"{NVROOT}/compilers/lib:{NVROOT}/cuda/12.9/lib64:{NVROOT}/math_libs/12.9/lib64:"
        + env.get("LD_LIBRARY_PATH", "")
    )
    env["CUDA_VISIBLE_DEVICES"] = "0"
    env["OMP_NUM_THREADS"] = "8"
    env["OMP_PROC_BIND"] = "close"
    env["OMP_PLACES"] = "cores"
    return env


def cell_and_positions_block(atoms):
    cell = atoms.get_cell()
    lines = ["CELL_PARAMETERS angstrom"]
    for row in cell:
        lines.append(f"{row[0]:.10f} {row[1]:.10f} {row[2]:.10f}")
    lines.append("ATOMIC_POSITIONS crystal")
    scaled = atoms.get_scaled_positions()
    for sym, pos in zip(atoms.get_chemical_symbols(), scaled):
        lines.append(f"{sym} {pos[0]:.10f} {pos[1]:.10f} {pos[2]:.10f}")
    return "\n".join(lines)


def build_input(atoms, calc_type, prefix, outdir, kmesh, spin, forc_conv_thr=1.0e-4,
                 press_conv_thr=0.5, cell_factor=2.0):
    nat = len(atoms)
    control = [
        "&CONTROL",
        f"  calculation = '{calc_type}',",
        f"  prefix = '{prefix}',",
        f"  pseudo_dir = '{PSEUDO_DIR}',",
        f"  outdir = '{outdir}',",
        "  tprnfor = .true.,",
        "  tstress = .true.,",
        "  disk_io = 'low',",
        "  forc_conv_thr = %.3e," % forc_conv_thr if calc_type != "scf" else "",
        "  etot_conv_thr = 1.0d-6," if calc_type != "scf" else "",
        "/",
    ]
    control = [c for c in control if c]
    system = [
        "&SYSTEM", "  ibrav = 0,", f"  nat = {nat},", "  ntyp = 1,",
        "  ecutwfc = 90.0,", "  ecutrho = 720.0,",
        "  occupations = 'smearing',", "  smearing = 'mv',", "  degauss = 0.010,",
    ]
    if spin:
        system += ["  nspin = 2,", "  starting_magnetization(1) = 0.60,"]
    system.append("/")
    electrons = ["&ELECTRONS", "  conv_thr = 1.0d-10,", "  electron_maxstep = 200,",
                 "  mixing_beta = 0.30,", "  diagonalization = 'david',", "/"]
    blocks = control + system + electrons
    if calc_type == "vc-relax":
        blocks += ["&IONS", "  ion_dynamics = 'bfgs',", "/",
                   "&CELL", "  cell_dynamics = 'bfgs',", f"  press_conv_thr = {press_conv_thr},",
                   f"  cell_factor = {cell_factor},", "/"]
    symbol = atoms.get_chemical_symbols()[0]
    if symbol == "Al":
        species = "ATOMIC_SPECIES\nAl 26.9815385 Al.pbe-n-kjpaw_psl.1.0.0.UPF"
    else:
        species = "ATOMIC_SPECIES\nNi 58.6934 ni_pbe_v1.4.uspp.F.UPF"
    kpoints = f"K_POINTS automatic\n{kmesh[0]} {kmesh[1]} {kmesh[2]} 0 0 0"
    text = "\n".join(blocks) + "\n" + species + "\n" + cell_and_positions_block(atoms) + "\n" + kpoints + "\n"
    return text


def run_qe(input_text, workdir, tag):
    workdir.mkdir(parents=True, exist_ok=True)
    in_path = workdir / f"{tag}.in"
    out_path = workdir / f"{tag}.out"
    in_path.write_text(input_text)
    t0 = time.time()
    with open(out_path, "w") as f:
        result = subprocess.run([str(QE), "-in", str(in_path)], stdout=f, stderr=subprocess.STDOUT,
                                 env=run_env(), cwd=str(workdir))
    dt = time.time() - t0
    text = out_path.read_text()
    if "JOB DONE" not in text:
        raise RuntimeError(f"QE run {tag} did not finish cleanly (returncode {result.returncode}); see {out_path}")
    return text, dt


def parse_total_energy_ry(text):
    matches = re.findall(r"!\s+total energy\s+=\s+(-?\d+\.\d+)\s+Ry", text)
    if not matches:
        raise RuntimeError("no converged total energy line found")
    return float(matches[-1])


def parse_final_energy_vcrelax(text):
    # vc-relax prints "Final energy = ... Ry" at convergence; fall back to last SCF energy line.
    m = re.findall(r"Final energy\s+=\s+(-?\d+\.\d+)\s*Ry", text)
    if m:
        return float(m[-1])
    return parse_total_energy_ry(text)


def get_relaxed_cell(text, template_atoms):
    """Parse the authoritative final relaxed geometry from QE's
    'Begin final coordinates' / 'End final coordinates' block. Line counts
    are taken from template_atoms (3 cell rows, nat position rows) rather
    than relying on blank-line boundaries -- the ATOMIC_POSITIONS block in
    this section is NOT followed by a blank line before 'End final
    coordinates', which silently corrupts a blank-line-delimited regex."""
    m = re.search(r"Begin final coordinates\n(.*?)\nEnd final coordinates", text, re.S)
    if not m:
        raise RuntimeError("could not find 'Begin final coordinates' / 'End final coordinates' block")
    block = m.group(1)

    cell_m = re.search(r"CELL_PARAMETERS\s*\(angstrom\)\n(.*)", block, re.S)
    if not cell_m:
        raise RuntimeError("no CELL_PARAMETERS in final coordinates block")
    cell_lines = cell_m.group(1).strip("\n").splitlines()[:3]
    cell = np.array([[float(x) for x in line.split()] for line in cell_lines])

    pos_m = re.search(r"ATOMIC_POSITIONS\s*\(crystal\)\n(.*)", block, re.S)
    if not pos_m:
        raise RuntimeError("no ATOMIC_POSITIONS in final coordinates block")
    nat = len(template_atoms)
    pos_lines = pos_m.group(1).strip("\n").splitlines()[:nat]
    if len(pos_lines) != nat:
        raise RuntimeError(f"expected {nat} atomic position lines, got {len(pos_lines)}: {pos_lines}")

    atoms = template_atoms.copy()
    atoms.set_cell(cell)
    scaled = []
    for line in pos_lines:
        parts = line.split()
        scaled.append([float(parts[1]), float(parts[2]), float(parts[3])])
    atoms.set_scaled_positions(np.array(scaled))
    return atoms


def main():
    print("=== STEP B: QE/PBE elemental references (mu_Al, mu_Ni) ===", flush=True)
    print(f"Verifying pinned hashes...", flush=True)
    assert sha256(QE) == QE_SHA256, "QE binary hash mismatch"
    al_pseudo = PSEUDO_DIR / "Al.pbe-n-kjpaw_psl.1.0.0.UPF"
    ni_pseudo = PSEUDO_DIR / "ni_pbe_v1.4.uspp.F.UPF"
    assert sha256(al_pseudo) == AL_PSEUDO_SHA256, "Al pseudopotential hash mismatch"
    assert sha256(ni_pseudo) == NI_PSEUDO_SHA256, "Ni pseudopotential hash mismatch"
    print("  QE binary, Al pseudo, Ni pseudo: all match pinned hashes", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    results = {}

    # ---- Al k-mesh convergence check (no prior record; own decision, not assumed) ----
    print("\n--- Al k-mesh convergence check (20x20x20 vs 24x24x24, trial a=4.05 A) ---", flush=True)
    al_trial = bulk("Al", "fcc", a=4.05, cubic=False)
    kmesh_results = {}
    for kmesh in [(20, 20, 20), (24, 24, 24)]:
        tag = f"Al_kmesh_{kmesh[0]}"
        text, dt = run_qe(
            build_input(al_trial, "scf", tag, str(WORK / tag / "tmp"), kmesh, spin=False),
            WORK / tag, tag)
        e_ry = parse_total_energy_ry(text)
        kmesh_results[kmesh] = e_ry
        print(f"  {kmesh}: E = {e_ry:.10f} Ry ({dt:.1f}s)", flush=True)
    dE_mev_atom = abs(kmesh_results[(20, 20, 20)] - kmesh_results[(24, 24, 24)]) * RY_TO_EV * 1000.0
    print(f"  dE(20 vs 24) = {dE_mev_atom:.6f} meV/atom", flush=True)
    # Same convergence bar the project's own Ni campaign implicitly used: adopt the
    # coarser mesh if the two brackets agree below ~0.5 meV/atom (Ni's own dE was
    # 0.488716 meV/atom and 22x22x22, the coarser of its two final brackets, was
    # adopted); otherwise fall back to the denser mesh.
    if dE_mev_atom < 0.5:
        al_kmesh = (20, 20, 20)
        al_justification = (
            f"20x20x20 adopted: dE(20 vs 24)={dE_mev_atom:.6f} meV/atom, below the "
            f"0.5 meV/atom bar implied by Ni's own adopted precedent (dE=0.488716 "
            f"meV/atom at 22-vs-24, coarser mesh adopted)."
        )
    else:
        al_kmesh = (24, 24, 24)
        al_justification = (
            f"24x24x24 adopted: dE(20 vs 24)={dE_mev_atom:.6f} meV/atom, at/above the "
            f"0.5 meV/atom bar -- denser mesh required."
        )
    print(f"  ADOPTED: {al_kmesh} -- {al_justification}", flush=True)
    results["al_kmesh_convergence"] = {
        "E_20x20x20_Ry": kmesh_results[(20, 20, 20)], "E_24x24x24_Ry": kmesh_results[(24, 24, 24)],
        "dE_mev_atom": dE_mev_atom, "adopted": al_kmesh, "justification": al_justification,
    }

    # ---- Al vc-relax + independent final SCF ----
    print("\n--- Al vc-relax ---", flush=True)
    text, dt = run_qe(
        build_input(al_trial, "vc-relax", "Al_vcrelax", str(WORK / "Al_vcrelax" / "tmp"), al_kmesh, spin=False),
        WORK / "Al_vcrelax", "Al_vcrelax")
    print(f"  vc-relax done in {dt:.1f}s", flush=True)
    al_relaxed = get_relaxed_cell(text, al_trial)
    a_relaxed = np.linalg.norm(al_relaxed.get_cell()[0]) * np.sqrt(2)  # primitive -> conventional fcc a
    print(f"  relaxed conventional a = {a_relaxed:.6f} A", flush=True)

    print("--- Al final SCF (independent, on relaxed cell) ---", flush=True)
    text, dt = run_qe(
        build_input(al_relaxed, "scf", "Al_finalscf", str(WORK / "Al_finalscf" / "tmp"), al_kmesh, spin=False),
        WORK / "Al_finalscf", "Al_finalscf")
    e_al_ry = parse_total_energy_ry(text)
    mu_al_ev = e_al_ry * RY_TO_EV / len(al_relaxed)
    print(f"  E_Al = {e_al_ry:.10f} Ry -> mu_Al = {mu_al_ev:.8f} eV/atom ({dt:.1f}s)", flush=True)
    results["Al"] = {"kmesh": al_kmesh, "relaxed_a_angstrom": a_relaxed,
                      "E_total_Ry": e_al_ry, "mu_eV_atom": mu_al_ev, "nspin": 1}

    # ---- Ni: locked settings from configs/NI_AL_DATA_SHOWCASE.md (not re-derived) ----
    ni_kmesh = (22, 22, 22)
    print(f"\n--- Ni vc-relax (LOCKED: nspin=2, mag=0.60, kmesh={ni_kmesh}) ---", flush=True)
    ni_trial = bulk("Ni", "fcc", a=3.52, cubic=False)
    text, dt = run_qe(
        build_input(ni_trial, "vc-relax", "Ni_vcrelax", str(WORK / "Ni_vcrelax" / "tmp"), ni_kmesh, spin=True),
        WORK / "Ni_vcrelax", "Ni_vcrelax")
    print(f"  vc-relax done in {dt:.1f}s", flush=True)
    ni_relaxed = get_relaxed_cell(text, ni_trial)
    a_relaxed_ni = np.linalg.norm(ni_relaxed.get_cell()[0]) * np.sqrt(2)
    print(f"  relaxed conventional a = {a_relaxed_ni:.6f} A", flush=True)

    print("--- Ni final SCF (independent, on relaxed cell) ---", flush=True)
    text, dt = run_qe(
        build_input(ni_relaxed, "scf", "Ni_finalscf", str(WORK / "Ni_finalscf" / "tmp"), ni_kmesh, spin=True),
        WORK / "Ni_finalscf", "Ni_finalscf")
    e_ni_ry = parse_total_energy_ry(text)
    mu_ni_ev = e_ni_ry * RY_TO_EV / len(ni_relaxed)
    mag_match = re.findall(r"total magnetization\s+=\s+(-?\d+\.\d+)\s*Bohr mag/cell", text)
    print(f"  E_Ni = {e_ni_ry:.10f} Ry -> mu_Ni = {mu_ni_ev:.8f} eV/atom ({dt:.1f}s), "
          f"final magnetization = {mag_match[-1] if mag_match else 'N/A'} muB/cell", flush=True)
    results["Ni"] = {"kmesh": ni_kmesh, "relaxed_a_angstrom": a_relaxed_ni,
                      "E_total_Ry": e_ni_ry, "mu_eV_atom": mu_ni_ev, "nspin": 2,
                      "starting_magnetization": 0.60,
                      "final_magnetization_muB_cell": float(mag_match[-1]) if mag_match else None}

    import json
    (OUT / "stepB_elemental_references.json").write_text(json.dumps(results, indent=2))
    status_lines = [
        "STEP B -- QE/PBE ELEMENTAL REFERENCES (mu_Al, mu_Ni)", "",
        f"QE binary SHA256: {QE_SHA256}", f"Al pseudopotential SHA256: {AL_PSEUDO_SHA256}",
        f"Ni pseudopotential SHA256: {NI_PSEUDO_SHA256}", "",
        "Al k-mesh convergence check:",
        f"  E(20x20x20) = {kmesh_results[(20,20,20)]:.10f} Ry",
        f"  E(24x24x24) = {kmesh_results[(24,24,24)]:.10f} Ry",
        f"  dE = {dE_mev_atom:.6f} meV/atom",
        f"  ADOPTED: {al_kmesh}", f"  Justification: {al_justification}", "",
        f"mu_Al = {mu_al_ev:.8f} eV/atom (nspin=1, kmesh={al_kmesh}, relaxed a={a_relaxed:.6f} A)",
        f"mu_Ni = {mu_ni_ev:.8f} eV/atom (nspin=2, start_mag=0.60, kmesh={ni_kmesh}, relaxed a={a_relaxed_ni:.6f} A)",
        "", "STEP B STATUS: COMPLETE",
    ]
    (R / "configs/STEPB_ELEMENTAL_REFERENCES_STATUS.txt").write_text("\n".join(status_lines) + "\n")
    print("\n=== STEP B COMPLETE ===", flush=True)
    print(f"mu_Al = {mu_al_ev:.8f} eV/atom", flush=True)
    print(f"mu_Ni = {mu_ni_ev:.8f} eV/atom", flush=True)


if __name__ == "__main__":
    main()
