"""Phase 3.3: parity plots for energy, forces and stress (three-way model comparison)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, common as C
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GPA = 160.21766208
# categorical slots 1-3 of the validated reference palette (all-pairs safe)
COL = {"base_MATPES_PBE_0": "#2a78d6", "pilot25": "#eb6834", "combined227": "#1baf7a"}
MRK = {"base_MATPES_PBE_0": "o", "pilot25": "s", "combined227": "^"}
LBL = {"base_MATPES_PBE_0": "MACE-MATPES-PBE-0 (base)", "pilot25": "pilot25 LoRA",
       "combined227": "combined227 LoRA (final)"}
PATHS = {"base_MATPES_PBE_0": C.BASE_MODEL, "pilot25": C.model_path("pilot25_matpes_pbe_lora_v1"),
         "combined227": C.model_path("al3ni_combined227_lora_v1")}

atoms, split = C.load_dataset("combined227")
ref_id = {a.info["phase"]: a.info["config_id"] for a in atoms if a.info["config_type"] == "relaxed"}
byid = {a.info["config_id"]: a for a in atoms}

F_dft = np.concatenate([a.get_forces().ravel() for a in atoms])
S_dft = np.concatenate([a.get_stress(voigt=True) * GPA for a in atoms])

data = {}
for m, p in PATHS.items():
    calc = C.calc(p)
    E, F, S = {}, [], []
    for a in atoms:
        w = a.copy(); w.calc = calc
        E[a.info["config_id"]] = w.get_potential_energy()
        F.append(w.get_forces().ravel()); S.append(w.get_stress(voigt=True) * GPA)
    er_d, er_p = [], []
    for a in atoms:
        cid = a.info["config_id"]; r = ref_id[a.info["phase"]]; N = len(a)
        er_d.append((a.get_potential_energy() - byid[r].get_potential_energy()) / N * 1000)
        er_p.append((E[cid] - E[r]) / N * 1000)
    data[m] = {"E_d": np.array(er_d), "E_p": np.array(er_p),
               "F": np.concatenate(F), "S": np.concatenate(S)}
    print(f"  {m} done", flush=True)

def parity(key_d, key_p, xlabel, fname, title, unit):
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    lo = min(key_d.min(), min(data[m][key_p].min() for m in PATHS))
    hi = max(key_d.max(), max(data[m][key_p].max() for m in PATHS))
    pad = 0.04 * (hi - lo)
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color="#9a9a94", lw=1.0,
            zorder=1, label="_nolegend_")
    for m in PATHS:
        y = data[m][key_p]
        rmse = np.sqrt(((y - key_d) ** 2).mean())
        ax.scatter(key_d, y, s=16, c=COL[m], marker=MRK[m], alpha=0.72,
                   linewidths=0.5, edgecolors="none", zorder=3,
                   label=f"{LBL[m]}  (RMSE {rmse:.4g} {unit})")
    ax.set_xlim(lo - pad, hi + pad); ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlabel(f"DFT {xlabel}"); ax.set_ylabel(f"MACE {xlabel}")
    ax.set_title(title, loc="left", fontsize=11)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.grid(True, lw=0.4, color="#e4e4de", zorder=0)
    ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(os.path.join(C.RESULTS, fname), dpi=150)
    plt.close(fig); print("  wrote", fname)

parity(data["combined227"]["E_d"], "E_p", "relative energy (meV/atom)",
       "parity_energy.png", "Relative energy parity, 227 DFT geometries", "meV/atom")
parity(F_dft, "F", "force component (eV/A)", "parity_forces.png",
       "Force-component parity, 5436 components", "eV/A")
parity(S_dft, "S", "stress component (GPa)", "parity_stress.png",
       "Stress-component parity, 1362 Voigt components", "GPa")
