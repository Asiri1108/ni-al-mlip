"""One worker of the parallel NPT re-run.

The 10 NPT trajectories are independent, so they are split across several
processes instead of running one process that takes every core. MACE on CPU
scales sublinearly with thread count, so N processes at 12/N threads finish the
set sooner than one process at 12 threads.

Thread count is pinned BEFORE torch is imported - OMP_NUM_THREADS is read by
the OpenMP runtime at load time, so setting it later has no effect.

Each worker owns a fixed job list and writes one JSON row per finished run into
work/npt_rows/. Nothing is appended to md_summary.csv from here: concurrent
writers would interleave and corrupt it. phase11_npt_merge.py assembles the
rows once every worker has exited.

Usage:  NPT_THREADS=3 NPT_JOBS=AlNi:300,AlNi:900 python phase11_npt_worker.py
"""
import os, sys

THREADS = os.environ.get("NPT_THREADS", "3")
os.environ["OMP_NUM_THREADS"] = THREADS
os.environ["MKL_NUM_THREADS"] = THREADS
os.environ["OPENBLAS_NUM_THREADS"] = THREADS

import json, time
import torch
torch.set_num_threads(int(THREADS))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase11_md as M
import common as C

ROWS = os.path.join(C.ROOT, "work", "npt_rows")
os.makedirs(ROWS, exist_ok=True)

jobs = []
for tok in os.environ["NPT_JOBS"].split(","):
    ph, T = tok.split(":")
    jobs.append((ph.strip(), int(T)))

tag = os.environ.get("NPT_TAG", "w?")
print(f"[{tag}] threads={THREADS} jobs={jobs}", flush=True)

for ph, T in jobs:
    row_file = os.path.join(ROWS, f"{ph}_{T}K_NPT.json")
    if os.path.exists(row_file) and os.path.exists(M.npz_path(ph, T, "NPT")):
        print(f"[{tag}] skip {ph} {T}K NPT (already done)", flush=True)
        continue
    t0 = time.time()
    print(f"[{tag}] start {ph} {T}K NPT", flush=True)
    out = M.run(ph, T, "NPT")
    tmp = row_file + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(out, fh, indent=1)
    os.replace(tmp, row_file)
    print(f"[{tag}] done  {ph} {T}K NPT in {time.time()-t0:.0f}s", flush=True)

print(f"[{tag}] WORKER COMPLETE", flush=True)
