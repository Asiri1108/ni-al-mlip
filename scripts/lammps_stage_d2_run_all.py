#!/usr/bin/env python3
"""Stage D-2 driver: NPT-only supercell MD for the 3 small-cell phases
(AlNi, AlNi3, Al3Ni2), one subprocess per phase, sequential (process
isolation for the dropped lmp.finalize() -- see
lammps_stage_d2_run_phase.py's docstring).

Runs the SMALLEST supercell (AlNi3, 108 atoms) first, to get the earliest
possible cost signal at the lowest cost. Times each phase; after the first
phase completes, prints a linear-in-atom-count projected runtime for the
other two. If the first phase's wall-clock exceeds NINETY_MIN_S, stops
(does not launch the remaining phases) and reports why -- explicit
instruction, since ~100-200 atoms through the ML-IAP Python callback is
far heavier than Stage D's 2-8 atom primitive cells and the true cost was
unknown going in.
"""
import json
import os
import subprocess
import sys
import time

ROOT = "/workspace/ni_al"
VENV_PY = f"{ROOT}/envs/mace-py312-cu128/bin/python"
WORKER = f"{ROOT}/scripts/lammps_stage_d2_run_phase.py"
KOKKOS_PREFIX = f"{ROOT}/tools/lammps/install/mliap_kokkos"

PHASES = ["AlNi3", "AlNi", "Al3Ni2"]  # smallest atom count first
ATOM_COUNTS = {"AlNi3": 108, "AlNi": 128, "Al3Ni2": 135}

NINETY_MIN_S = 90 * 60

env = dict(os.environ)
env["LD_LIBRARY_PATH"] = f"{KOKKOS_PREFIX}/lib:" + env.get("LD_LIBRARY_PATH", "")
env["PYTHONPATH"] = f"{KOKKOS_PREFIX}/pyinstall:" + env.get("PYTHONPATH", "")

os.makedirs(f"{ROOT}/logs/lammps_stage_d2", exist_ok=True)
os.makedirs(f"{ROOT}/results/lammps_stage_d2", exist_ok=True)

results = {}
for i, phase in enumerate(PHASES):
    print(f"=== {phase} ({ATOM_COUNTS[phase]} atoms): launching subprocess ===", flush=True)
    proc_log = f"{ROOT}/logs/lammps_stage_d2/{phase}_subprocess.log"
    t0 = time.time()
    with open(proc_log, "w") as logfh:
        proc = subprocess.run(
            [VENV_PY, WORKER, phase],
            cwd=ROOT, env=env, stdout=logfh, stderr=subprocess.STDOUT,
        )
    elapsed_s = time.time() - t0
    json_path = f"{ROOT}/results/lammps_stage_d2/{phase}_summary.json"
    ok = proc.returncode == 0 and os.path.exists(json_path)
    results[phase] = {
        "returncode": proc.returncode, "json_exists": os.path.exists(json_path),
        "ok": ok, "elapsed_s": elapsed_s, "atoms": ATOM_COUNTS[phase],
    }
    status = "OK" if ok else f"FAILED (returncode={proc.returncode}, see {proc_log})"
    print(f"=== {phase}: {status}  elapsed={elapsed_s/60:.1f} min ===", flush=True)

    if i == 0:
        per_atom_s = elapsed_s / ATOM_COUNTS[phase]
        print(f"=== PROJECTED RUNTIME (linear-in-atom-count scaling from {phase}: "
              f"{elapsed_s/60:.1f} min @ {ATOM_COUNTS[phase]} atoms -- a rough projection, "
              f"not re-measured, since GPU kernel-launch overhead may not scale purely "
              f"linearly at this atom-count range) ===", flush=True)
        for other in PHASES[1:]:
            proj_s = per_atom_s * ATOM_COUNTS[other]
            print(f"    {other} ({ATOM_COUNTS[other]} atoms): ~{proj_s/60:.1f} min", flush=True)

        if elapsed_s > NINETY_MIN_S:
            print(f"=== STOPPING: {phase} took {elapsed_s/60:.1f} min (> 90 min threshold) -- "
                  f"NOT launching the remaining {len(PHASES)-1} phases. ===", flush=True)
            break

with open(f"{ROOT}/results/lammps_stage_d2/run_all_timing.json", "w") as fh:
    json.dump(results, fh, indent=2)

print("\nSUMMARY")
for phase, r in results.items():
    print(f"  {phase}: {'OK' if r['ok'] else 'FAILED'}  ({r['elapsed_s']/60:.1f} min, {r['atoms']} atoms)")
not_launched = [p for p in PHASES if p not in results]
if not_launched:
    print(f"  NOT LAUNCHED (90-min stop-rule): {not_launched}")

n_ok = sum(1 for r in results.values() if r["ok"])
print(f"\n{n_ok}/{len(results)} launched phases completed successfully")
sys.exit(0 if (n_ok == len(results) and not not_launched) else 1)
