#!/usr/bin/env python3
"""Stage D-3 driver: NPT trajectory (dump) runs for OVITO animation, one
subprocess per phase, sequential (process isolation for the dropped
lmp.finalize()). Continues to the next phase regardless of a crash in the
current one, and reports dump file size per phase (the caller's stated
concern: reduce dump frequency rather than ship something impractical to
download if any single file exceeds ~200 MB).

Usage: lammps_stage_d3_trajectory_run_all.py [PHASE ...]
Defaults to AlNi + Al3Ni5 (the original 2) if no phases are given on the
command line; pass phases explicitly to run a subset (e.g. just Al3Ni).
"""
import os
import subprocess
import sys
import time

ROOT = "/workspace/ni_al"
VENV_PY = f"{ROOT}/envs/mace-py312-cu128/bin/python"
WORKER = f"{ROOT}/scripts/lammps_stage_d3_trajectory_run_phase.py"
KOKKOS_PREFIX = f"{ROOT}/tools/lammps/install/mliap_kokkos"

PHASES = sys.argv[1:] if len(sys.argv) > 1 else ["AlNi", "Al3Ni5"]
SIZE_WARN_BYTES = 200 * 1024 * 1024

env = dict(os.environ)
env["LD_LIBRARY_PATH"] = f"{KOKKOS_PREFIX}/lib:" + env.get("LD_LIBRARY_PATH", "")
env["PYTHONPATH"] = f"{KOKKOS_PREFIX}/pyinstall:" + env.get("PYTHONPATH", "")

os.makedirs(f"{ROOT}/logs/lammps_stage_d3", exist_ok=True)
os.makedirs(f"{ROOT}/results/lammps_stage_d3", exist_ok=True)

results = {}
for phase in PHASES:
    print(f"=== {phase}: launching subprocess ===", flush=True)
    proc_log = f"{ROOT}/logs/lammps_stage_d3/{phase}_subprocess.log"
    t0 = time.time()
    with open(proc_log, "w") as logfh:
        proc = subprocess.run(
            [VENV_PY, WORKER, phase],
            cwd=ROOT, env=env, stdout=logfh, stderr=subprocess.STDOUT,
        )
    elapsed_s = time.time() - t0
    json_path = f"{ROOT}/results/lammps_stage_d3/{phase}_summary.json"
    ok = proc.returncode == 0 and os.path.exists(json_path)
    dump_path = f"{ROOT}/results/lammps_stage_d3/{phase}_trajectory.dump"
    dump_size = os.path.getsize(dump_path) if os.path.exists(dump_path) else None
    results[phase] = {"returncode": proc.returncode, "ok": ok, "elapsed_s": elapsed_s,
                       "dump_size_bytes": dump_size}
    status = "OK" if ok else f"FAILED (returncode={proc.returncode}, see {proc_log})"
    dump_mb = f"{dump_size/1e6:.1f} MB" if dump_size else "N/A"
    warn = ""
    if dump_size and dump_size > SIZE_WARN_BYTES:
        warn = f"  *** WARNING: exceeds 200 MB threshold ***"
    print(f"=== {phase}: {status}  elapsed={elapsed_s/60:.1f} min  dump={dump_mb}{warn} ===", flush=True)

print("\nSUMMARY")
for phase, r in results.items():
    dump_mb = f"{r['dump_size_bytes']/1e6:.1f} MB" if r['dump_size_bytes'] else "N/A"
    print(f"  {phase}: {'OK' if r['ok'] else 'FAILED'}  ({r['elapsed_s']/60:.1f} min, dump={dump_mb})")

n_ok = sum(1 for r in results.values() if r["ok"])
print(f"\n{n_ok}/{len(PHASES)} phases completed successfully")
sys.exit(0 if n_ok == len(PHASES) else 1)
