#!/usr/bin/env python3
"""Stage B driver: run each phase's LAMMPS relaxation in its own subprocess
(process isolation for the dropped lmp.finalize() -- see
lammps_stage_b_relax_phase.py's docstring). Continues to the next phase
regardless of a crash in the current one.
"""
import os
import subprocess
import sys

ROOT = "/workspace/ni_al"
VENV_PY = f"{ROOT}/envs/mace-py312-cu128/bin/python"
WORKER = f"{ROOT}/scripts/lammps_stage_b_relax_phase.py"
KOKKOS_PREFIX = f"{ROOT}/tools/lammps/install/mliap_kokkos"
PHASES = ["AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3"]

env = dict(os.environ)
env["LD_LIBRARY_PATH"] = f"{KOKKOS_PREFIX}/lib:" + env.get("LD_LIBRARY_PATH", "")
env["PYTHONPATH"] = f"{KOKKOS_PREFIX}/pyinstall:" + env.get("PYTHONPATH", "")

os.makedirs(f"{ROOT}/logs/lammps_stage_b", exist_ok=True)

results = {}
for phase in PHASES:
    print(f"=== {phase}: launching subprocess ===", flush=True)
    proc_log = f"{ROOT}/logs/lammps_stage_b/{phase}_subprocess.log"
    with open(proc_log, "w") as logfh:
        proc = subprocess.run(
            [VENV_PY, WORKER, phase],
            cwd=ROOT, env=env, stdout=logfh, stderr=subprocess.STDOUT,
        )
    json_path = f"{ROOT}/results/lammps_stage_b/{phase}_lammps.json"
    ok = proc.returncode == 0 and os.path.exists(json_path)
    results[phase] = {"returncode": proc.returncode, "json_exists": os.path.exists(json_path), "ok": ok}
    status = "OK" if ok else f"FAILED (returncode={proc.returncode}, see {proc_log})"
    print(f"=== {phase}: {status} ===", flush=True)

print("\nSUMMARY")
for phase, r in results.items():
    print(f"  {phase}: {'OK' if r['ok'] else 'FAILED'}")

n_ok = sum(1 for r in results.values() if r["ok"])
print(f"\n{n_ok}/{len(PHASES)} phases completed successfully")
sys.exit(0 if n_ok == len(PHASES) else 1)
