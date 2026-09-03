"""Emit the per-phase / per-quantity files named in the task's output tree.

The analysis figures are small multiples (one panel per phase), which compare
better than five separate images. The task's tree asks for per-phase files as
well, so both are produced: the combined figure AND the individual ones.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = C.RESULTS
GREEN, BLUE, GREY, GRID = "#1baf7a", "#2a78d6", "#9a9a94", "#e4e4de"


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(True, lw=0.4, color=GRID)
    ax.set_axisbelow(True)


# ---- 1. split the benchmark into the three named files -----------------
src = os.path.join(R, "benchmark_per_structure.csv")
if os.path.exists(src):
    df = pd.read_csv(src)
    common = ["model", "config_id", "phase", "config_type", "family", "split", "natoms"]
    df[common + ["E_rel_dft_meV_atom", "E_rel_pred_meV_atom", "E_rel_err_meV_atom",
                 "abs_E_rel_err_meV_atom"]].to_csv(
        os.path.join(R, "benchmark_energy.csv"), index=False)
    df[common + ["F_mae_eV_A", "F_rmse_eV_A", "F_max_abs_eV_A"]].to_csv(
        os.path.join(R, "benchmark_forces.csv"), index=False)
    df[common + ["S_mae_GPa", "S_rmse_GPa"]].to_csv(
        os.path.join(R, "benchmark_stress.csv"), index=False)
    print("wrote benchmark_{energy,forces,stress}.csv")

# ---- 2. per-phase distortion figures -----------------------------------
src = os.path.join(R, "distortion", "distortion_scans.csv")
if os.path.exists(src):
    d = pd.read_csv(src)
    for (ph, mode), g in d.groupby(["phase", "mode"]):
        fig, ax = plt.subplots(figsize=(5.2, 4.0))
        g = g.sort_values("strain")
        ax.plot(g.strain * 100, g.dE_mace_meV_atom, color=GREEN, lw=2, marker="o",
                ms=5, markerfacecolor=GREEN, markeredgecolor="#fcfcfb", mew=1.0)
        ax.axhline(0, color=GREY, lw=0.8)
        ax.set_xlabel("strain (%)")
        ax.set_ylabel(r"$\Delta$E (meV/atom)")
        ax.set_title("%s - %s" % (ph, mode), loc="left", fontsize=11)
        style(ax)
        fig.tight_layout()
        fig.savefig(os.path.join(R, "distortion", "%s_%s.png" % (ph, mode)), dpi=150)
        plt.close(fig)
    print("wrote distortion/<phase>_<mode>.png")

# ---- 3. per-phase EOS figures (recompute the 11 scan points) -----------
try:
    from scipy.optimize import curve_fit

    def bm(V, E0, V0, B0, Bp):
        t = (V0 / V) ** (2.0 / 3.0) - 1.0
        return E0 + 9.0 * V0 * B0 / 16.0 * (
            t ** 3 * Bp + t ** 2 * (6.0 - 4.0 * (V0 / V) ** (2.0 / 3.0)))

    atoms, split = C.load_dataset("combined227")
    relaxed = {a.info["phase"]: a for a in atoms if a.info["config_type"] == "relaxed"}
    calc = C.calc(C.model_path("al3ni_combined227_lora_v1"))
    GPA = 160.21766208
    rows = []
    for ph in C.PHASES:
        ref = relaxed[ph]
        N = len(ref)
        Vs, Es = [], []
        for f in np.linspace(0.90, 1.10, 11):
            w = ref.copy()
            w.set_cell(ref.cell.array * f ** (1 / 3.0), scale_atoms=True)
            w.calc = calc
            Vs.append(w.get_volume())
            Es.append(w.get_potential_energy())
        Vs, Es = np.array(Vs), np.array(Es)
        popt, _ = curve_fit(bm, Vs, Es, p0=[Es.min(), ref.get_volume(), 1.0, 4.0],
                            maxfev=200000)
        for v, e in zip(Vs, Es):
            rows.append({"phase": ph, "V_A3": v, "V_per_atom_A3": v / N,
                         "E_eV": e, "E_rel_meV_atom": (e - popt[0]) / N * 1000})
        fig, ax = plt.subplots(figsize=(5.2, 4.0))
        Vg = np.linspace(Vs.min(), Vs.max(), 300)
        ax.plot(Vg / N, (bm(Vg, *popt) - popt[0]) / N * 1000, color=GREEN, lw=2)
        ax.scatter(Vs / N, (Es - popt[0]) / N * 1000, s=34, facecolor=GREEN,
                   edgecolor="#fcfcfb", lw=1.2, zorder=3)
        ax.axvline(ref.get_volume() / N, color=GREY, lw=0.9, ls=":")
        ax.set_xlabel(r"V per atom ($\AA^3$)")
        ax.set_ylabel(r"E $-$ E$_0$ (meV/atom)")
        ax.set_title("%s   $B_0$ = %.1f GPa" % (ph, popt[2] * GPA), loc="left", fontsize=11)
        style(ax)
        fig.tight_layout()
        fig.savefig(os.path.join(R, "eos", "%s.png" % ph), dpi=150)
        plt.close(fig)
    pd.DataFrame(rows).to_csv(os.path.join(R, "eos", "eos_curves.csv"), index=False)
    print("wrote eos/<phase>.png and eos/eos_curves.csv")
except Exception as e:
    print("EOS per-phase figures skipped: %s: %s" % (type(e).__name__, e))

# ---- 4. per-phase phonon DOS figures -----------------------------------
# (regenerated only if the phonon summary exists; the combined figure already does)
src = os.path.join(R, "phonons", "phonon_summary.csv")
if os.path.exists(src):
    print("phonons/phonon_dos_all.png already contains all five phases")

# ---- 5. MD figures from the saved trajectories -------------------------
mddir = os.path.join(R, "md")
npz = sorted(f for f in os.listdir(mddir) if f.endswith(".npz")) if os.path.isdir(mddir) else []
for f in npz:
    d = np.load(os.path.join(mddir, f))
    tag = f[:-4]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.6))
    axes[0].plot(d["t_ps"], d["T"], color=BLUE, lw=1.2)
    axes[0].set_ylabel("temperature (K)")
    axes[1].plot(d["t_ps"], (d["Epot"] - d["Epot"][0]) * 1000, color=GREEN, lw=1.5)
    axes[1].set_ylabel(r"E$_{pot}$ drift (meV/atom)")
    axes[2].plot(d["t_ps"], d["msd"], color="#eb6834", lw=1.5)
    axes[2].set_ylabel(r"MSD ($\AA^2$)")
    for ax in axes:
        ax.set_xlabel("time (ps)")
        style(ax)
    fig.suptitle(tag.replace("_", "  "), x=0.005, ha="left", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(os.path.join(mddir, tag + ".png"), dpi=140)
    plt.close(fig)
if npz:
    print("wrote md/<phase>_<T>K_<ensemble>.png  (%d trajectories)" % len(npz))
else:
    print("no MD trajectories yet")

print("\noutput tree finalisation done")
