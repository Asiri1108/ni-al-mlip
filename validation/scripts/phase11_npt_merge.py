"""Assemble md_summary.csv and md_thermal_expansion.csv after the NPT re-run.

Run this only once every worker has printed WORKER COMPLETE. It rebuilds the
summary from two sources that never overlap:

  * the 20 NVT rows already in md_summary.csv - untouched by the barostat fix,
    and deliberately NOT recomputed
  * the 10 NPT rows written as JSON by the workers

Completion is decided by counting trajectories on disk, not by any process
having exited, matching the rule the main script follows.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, numpy as np, common as C
import phase11_md as M   # constants + thermal_expansion only; no MD is run here

ROWS = os.path.join(C.ROOT, "work", "npt_rows")

prev = pd.read_csv(M.SUMMARY)
nvt = prev[prev.ensemble == "NVT"].copy()
if len(nvt) != 20:
    sys.exit(f"expected 20 NVT rows in md_summary.csv, found {len(nvt)}")

npt_rows = []
missing = []
for ph in C.PHASES:
    for T in M.NPT_TEMPS:
        f = os.path.join(ROWS, f"{ph}_{T}K_NPT.json")
        if not os.path.exists(f):
            missing.append((ph, T)); continue
        with open(f) as fh:
            npt_rows.append(json.load(fh))

if missing:
    print("MERGE ABORTED - NPT rows still missing:")
    for ph, T in missing:
        print(f"  MISSING {ph:7s} {T:5d}K NPT")
    sys.exit(1)

df = pd.concat([nvt, pd.DataFrame(npt_rows)], ignore_index=True)

# order the rows the way SCHEDULE runs them, so the file reads predictably
order = {k: i for i, k in enumerate(M.SCHEDULE)}
df["_o"] = [order[(r.phase, int(r.T_target_K), r.ensemble)] for r in df.itertuples()]
df = df.sort_values("_o").drop(columns="_o").reset_index(drop=True)
df.to_csv(M.SUMMARY, index=False)

tex = M.thermal_expansion(df)
tex.to_csv(os.path.join(C.RESULTS, "md_thermal_expansion.csv"), index=False)

present = [k for k in M.SCHEDULE if os.path.exists(M.npz_path(*k))]
print(f"md_summary.csv: {len(df)} rows "
      f"({(df.ensemble=='NVT').sum()} NVT + {(df.ensemble=='NPT').sum()} NPT)")
print(f"duplicate keys: {df.duplicated(['phase','T_target_K','ensemble']).sum()}")
print()
print("thermal expansion:")
print(tex.to_string(index=False))
print()
# a linear expansion coefficient for a metallic aluminide sits near 1e-5 /K;
# anything below 1e-7 means the cell did not move and the barostat is inert
bad = tex[tex.alpha_linear_per_K.abs() < 1e-7]
if len(bad):
    print("WARNING - alpha_linear below 1e-7 /K for: " + ", ".join(bad.phase))
    print("The cell did not move. Do not use these numbers.")
else:
    print(f"alpha_linear range: {tex.alpha_linear_per_K.min():.3e} .. "
          f"{tex.alpha_linear_per_K.max():.3e} /K  (physical scale ~1e-5)")
print()
if len(present) == len(M.SCHEDULE):
    print(f"PHASE 11 COMPLETE  ({len(present)}/{len(M.SCHEDULE)} trajectories)")
else:
    print(f"PHASE 11 PARTIAL  ({len(present)}/{len(M.SCHEDULE)} trajectories present)")
