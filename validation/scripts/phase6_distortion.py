"""Phase 6: uniaxial / biaxial / shear distortion PES scans, +-4% strain.

Each mode is applied independently to the DFT-relaxed cell of each phase, atoms
scaled with the cell, single-point energy only (no relaxation). DFT points from
the 227 set are overlaid where a config matches the scan path exactly.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, common as C
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

EPS = np.linspace(-0.04, 0.04, 17)
atoms, split = C.load_dataset("combined227")
relaxed = {a.info["phase"]: a for a in atoms if a.info["config_type"] == "relaxed"}
calc = C.calc(C.model_path("al3ni_combined227_lora_v1"))

def deform(ref, mode, e):
    w = ref.copy()
    F = np.eye(3)
    if mode == "uniaxial_c":  F[2, 2] = 1 + e                  # c axis only
    elif mode == "biaxial_ab": F[0, 0] = F[1, 1] = 1 + e       # a and b together
    elif mode == "shear_xy":   F[1, 0] = e                     # engineering shear
    w.set_cell(ref.cell.array @ F.T, scale_atoms=True)
    return w

def matches(a, ref, mode, e):
    """True if config `a` lies exactly on the (mode, e) scan point."""
    t = deform(ref, mode, e)
    if not np.allclose(a.cell.array, t.cell.array, atol=1e-4): return False
    d = a.get_scaled_positions() - ref.get_scaled_positions(); d -= np.round(d)
    return np.abs(d).max() < 1e-6

rows, panels = [], []
for ph in C.PHASES:
    ref = relaxed[ph]; N = len(ref)
    w = ref.copy(); w.calc = calc; E0 = w.get_potential_energy()
    same = [a for a in atoms if a.info["phase"] == ph]
    for mode in ["uniaxial_c", "biaxial_ab", "shear_xy"]:
        Em = []
        for e in EPS:
            x = deform(ref, mode, e); x.calc = calc
            Em.append((x.get_potential_energy() - E0) / N * 1000)
        # DFT overlay: find configs that sit on this exact scan path
        dE, de = [], []
        for a in same:
            for e in np.linspace(-0.06, 0.06, 25):
                if matches(a, ref, mode, e):
                    dE.append((a.get_potential_energy() - ref.get_potential_energy()) / N * 1000)
                    de.append(e); break
        panels.append((ph, mode, np.array(Em), np.array(de), np.array(dE)))
        for e, v in zip(EPS, Em):
            rows.append({"phase": ph, "mode": mode, "strain": e, "dE_mace_meV_atom": v})
        print(f"  {ph:7s} {mode:11s} dE(+4%)={Em[-1]:8.2f}  dE(-4%)={Em[0]:8.2f}  n_dft_on_path={len(de)}", flush=True)

df = pd.DataFrame(rows)
df.to_csv(os.path.join(C.RESULTS, "distortion", "distortion_scans.csv"), index=False)

fig, axes = plt.subplots(3, 5, figsize=(19, 10.5), sharex=True)
titles = {"uniaxial_c": "uniaxial (c)", "biaxial_ab": "biaxial (a,b)", "shear_xy": "shear (xy)"}
for k, (ph, mode, Em, de, dE) in enumerate(panels):
    r = ["uniaxial_c", "biaxial_ab", "shear_xy"].index(mode)
    ax = axes[r][C.PHASES.index(ph)]
    ax.plot(EPS * 100, Em, color="#1baf7a", lw=2, marker="o", ms=4,
            markerfacecolor="#1baf7a", markeredgecolor="#fcfcfb", mew=0.8,
            zorder=3, label="MACE combined227")
    if len(de):
        ax.scatter(de * 100, dE, s=64, marker="x", color="#2a78d6", lw=1.8,
                   zorder=4, label="QE/PBE DFT")
    if ph == "Al3Ni" and mode != "shear_xy":
        ax.axvspan(3.5, 4.0, color="#eda100", alpha=0.16, zorder=0,
                   label="historical weak region")
    ax.axhline(0, color="#9a9a94", lw=0.8, zorder=1)
    ax.set_title(f"{ph} - {titles[mode]}", fontsize=10, loc="left")
    if r == 2: ax.set_xlabel("strain (%)")
    if C.PHASES.index(ph) == 0: ax.set_ylabel("$\Delta$E (meV/atom)")
    ax.legend(frameon=False, fontsize=7.5)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.grid(True, lw=0.4, color="#e4e4de"); ax.set_axisbelow(True)
fig.suptitle("Phase 6: distortion PES scans, $\pm$4% strain, MACE combined227 vs QE/PBE DFT",
             x=0.005, ha="left", fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.965])
fig.savefig(os.path.join(C.RESULTS, "distortion", "distortion_all.png"), dpi=140)
print("\nwrote results/distortion/distortion_all.png")
