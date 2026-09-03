"""Phase 10: vacancy formation energies, Al-site and Ni-site, with a supercell
size-convergence check.

Definition used:
    E_vac(X) = E_defect(N-1, relaxed) - E_perfect(N) + mu_X
with mu_X the QE/PBE elemental chemical potential (same references as Phase 7).
The reservoir choice shifts the absolute value; it is stated explicitly rather
than left implicit. Cell vectors are held fixed (constant-volume vacancy).

There is NO DFT ground truth for these in the archive: MODEL PREDICTION ONLY.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, common as C
from ase.optimize import FIRE
from ase.filters import FrechetCellFilter

atoms, split = C.load_dataset("combined227")
relaxed = {a.info["phase"]: a for a in atoms if a.info["config_type"] == "relaxed"}
calc = C.calc(C.model_path("al3ni_combined227_lora_v1"))
MU = {"Al": C.MU_AL, "Ni": C.MU_NI}
SIZES = {"Al3Ni":  [(2,2,2), (3,2,2)],
         "Al3Ni2": [(3,3,2), (4,4,3)],
         "AlNi":   [(4,4,4), (5,5,5)],
         "Al3Ni5": [(3,2,2), (4,3,3)],
         "AlNi3":  [(3,3,3), (4,4,4)]}

rows = []
for ph in C.PHASES:
    base = relaxed[ph].copy(); base.calc = calc
    FIRE(FrechetCellFilter(base), logfile=os.devnull).run(fmax=0.001, steps=2000)
    for S in SIZES[ph]:
        sc = base.repeat(S); sc.calc = calc
        Eperf = sc.get_potential_energy(); N = len(sc)
        for el in ["Al", "Ni"]:
            idx = [i for i, s in enumerate(sc.get_chemical_symbols()) if s == el]
            if not idx: continue
            d = sc.copy(); del d[idx[0]]; d.calc = calc
            t0 = time.time()
            opt = FIRE(d, logfile=os.devnull); opt.run(fmax=0.01, steps=600)
            Ev = d.get_potential_energy() - Eperf + MU[el]
            rows.append({"phase": ph, "site": el, "supercell": "x".join(map(str, S)),
                         "N_perfect": N, "E_vac_eV": Ev,
                         "relax_steps": opt.get_number_of_steps(),
                         "converged": bool(opt.converged()),
                         "wall_s": round(time.time()-t0, 1)})
            print(f"  {ph:7s} {el}-site {str(S):10s} N={N:4d}  E_vac={Ev:8.4f} eV  "
                  f"steps={opt.get_number_of_steps():3d} conv={opt.converged()} "
                  f"({time.time()-t0:.0f}s)", flush=True)
            pd.DataFrame(rows).to_csv(os.path.join(C.RESULTS, "defect_energies.csv"), index=False)

df = pd.DataFrame(rows)
piv = df.pivot_table(index=["phase","site"], columns="supercell", values="E_vac_eV")
conv = df.sort_values("N_perfect").groupby(["phase","site"]).E_vac_eV.agg(list)
out = []
for (ph, el), v in conv.items():
    out.append({"phase": ph, "site": el, "E_vac_small_eV": v[0], "E_vac_large_eV": v[-1],
                "size_convergence_eV": v[-1]-v[0],
                "converged_within_50meV": bool(abs(v[-1]-v[0]) < 0.05)})
cdf = pd.DataFrame(out)
cdf.to_csv(os.path.join(C.RESULTS, "defect_size_convergence.csv"), index=False)
pd.set_option("display.width", 220)
print("\n=== VACANCY FORMATION ENERGIES (MODEL PREDICTION - NO DFT GROUND TRUTH) ===")
print(piv.to_string(float_format=lambda v: f"{v:9.4f}"))
print("\n=== SUPERCELL SIZE CONVERGENCE ===")
print(cdf.to_string(index=False, float_format=lambda v: f"{v:9.4f}"))
