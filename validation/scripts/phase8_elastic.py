"""Phase 8: elastic constants from finite strain + MACE stress.

Central differences on the full 6x6 stiffness tensor, then symmetry-appropriate
reduction. Polycrystalline moduli via Voigt-Reuss-Hill.
No pre-registered threshold exists for these -> REPORTED, NOT GATED.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, common as C
from ase.optimize import FIRE
from ase.filters import FrechetCellFilter

GPA = 160.21766208
DELTA = 0.005
atoms, split = C.load_dataset("combined227")
relaxed = {a.info["phase"]: a for a in atoms if a.info["config_type"] == "relaxed"}
calc = C.calc(C.model_path("al3ni_combined227_lora_v1"))

def voigt_strain(i, d):
    e = np.zeros(6); e[i] = d
    return np.array([[1+e[0], e[5]/2, e[4]/2],
                     [e[5]/2, 1+e[1], e[3]/2],
                     [e[4]/2, e[3]/2, 1+e[2]]])

rows = []
for ph in C.PHASES:
    base = relaxed[ph].copy(); base.calc = calc
    # relax to the model's own minimum first: elastic constants are only defined
    # at a stress-free reference state
    FIRE(FrechetCellFilter(base), logfile=os.devnull).run(fmax=0.001, steps=2000)
    cell0 = base.cell.array.copy()
    Cij = np.zeros((6, 6))
    for i in range(6):
        sp, sm = [], []
        for sgn, store in ((+1, sp), (-1, sm)):
            w = base.copy()
            w.set_cell(cell0 @ voigt_strain(i, sgn*DELTA).T, scale_atoms=True)
            w.calc = calc
            # Relax internal coordinates at fixed cell (relaxed-ion constants).
            # fmax must be tight: at fmax=0.01 the low-symmetry phases come out
            # ~10 GPa too stiff because residual internal forces are not relieved.
            # Converged at 0.001 (verified against the archive LAMMPS Stage C run).
            FIRE(w, logfile=os.devnull).run(fmax=0.001, steps=2000)
            store.append(w.get_stress(voigt=True))
        Cij[i] = (sp[0] - sm[0]) / (2*DELTA) * GPA
    Cij = 0.5 * (Cij + Cij.T)

    # Voigt-Reuss-Hill
    Kv = (Cij[:3, :3].sum()) / 9.0
    Gv = ((Cij[0,0]+Cij[1,1]+Cij[2,2]) - (Cij[0,1]+Cij[0,2]+Cij[1,2])
          + 3*(Cij[3,3]+Cij[4,4]+Cij[5,5])) / 15.0
    try:
        S = np.linalg.inv(Cij)
        Kr = 1.0/(S[:3,:3].sum())
        Gr = 15.0/(4*(S[0,0]+S[1,1]+S[2,2]) - 4*(S[0,1]+S[0,2]+S[1,2])
                   + 3*(S[3,3]+S[4,4]+S[5,5]))
    except np.linalg.LinAlgError:
        Kr = Gr = np.nan
    K = (Kv+Kr)/2; G = (Gv+Gr)/2
    E = 9*K*G/(3*K+G); nu = (3*K-2*G)/(2*(3*K+G))
    ev = np.linalg.eigvalsh(Cij)

    rows.append({"phase": ph, "C11": Cij[0,0], "C22": Cij[1,1], "C33": Cij[2,2],
                 "C12": Cij[0,1], "C13": Cij[0,2], "C23": Cij[1,2],
                 "C44": Cij[3,3], "C55": Cij[4,4], "C66": Cij[5,5],
                 "K_VRH_GPa": K, "G_VRH_GPa": G, "E_VRH_GPa": E, "nu": nu,
                 "min_eigenvalue_GPa": ev.min(),
                 "born_stable": bool(ev.min() > 0)})
    np.savetxt(os.path.join(C.RESULTS, f"elastic_Cij_{ph}.csv"), Cij,
               delimiter=",", fmt="%.4f")
    print(f"  {ph:7s} C11={Cij[0,0]:7.1f} C12={Cij[0,1]:7.1f} C44={Cij[3,3]:7.1f} "
          f"K={K:6.1f} G={G:6.1f} E={E:6.1f} nu={nu:5.3f} "
          f"min_eig={ev.min():7.2f} {'STABLE' if ev.min()>0 else 'UNSTABLE'}", flush=True)

df = pd.DataFrame(rows)
df.to_csv(os.path.join(C.RESULTS, "elastic_constants.csv"), index=False)
eos = pd.read_csv(os.path.join(C.RESULTS, "eos_fit.csv"))
df = df.merge(eos[["phase","B0_mace_GPa","B0_dft_GPa"]], on="phase")
df["K_vs_B0_EOS_diff_GPa"] = df.K_VRH_GPa - df.B0_mace_GPa
pd.set_option("display.width", 240)
print("\n=== ELASTIC SUMMARY (REPORTED, NOT GATED - no pre-registered bar) ===")
print(df[["phase","C11","C12","C44","K_VRH_GPa","G_VRH_GPa","E_VRH_GPa","nu",
          "born_stable","B0_mace_GPa","K_vs_B0_EOS_diff_GPa"]]
      .to_string(index=False, float_format=lambda v: f"{v:9.3f}"))
print("\nInternal consistency check: K(VRH, elastic tensor) vs B0(EOS fit) - "
      "these are independent routes to the same bulk modulus.")
