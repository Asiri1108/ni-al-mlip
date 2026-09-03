"""Phase 5: energy-volume curves + Birch-Murnaghan fit, with DFT overlay."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, common as C
from scipy.optimize import curve_fit
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

def birch_murnaghan(V, E0, V0, B0, Bp):
    """3rd-order Birch-Murnaghan. B0 in eV/A^3."""
    t = (V0 / V) ** (2.0 / 3.0) - 1.0
    return E0 + 9.0 * V0 * B0 / 16.0 * (t**3 * Bp + t**2 * (6.0 - 4.0 * (V0 / V) ** (2.0/3.0)))

GPA = 160.21766208
atoms, split = C.load_dataset("combined227")
relaxed = {a.info["phase"]: a for a in atoms if a.info["config_type"] == "relaxed"}
calc = C.calc(C.model_path("al3ni_combined227_lora_v1"))

# DFT points available for overlay: isotropic-scaling configs only (pure volume change)
def iso_scale(a, ref):
    """Return V/V0 if `a` is a pure isotropic scaling of `ref`, else None.

    Both conditions are required: the cell must be s*I times the reference cell
    AND the fractional coordinates must be unchanged. Testing the cell alone
    wrongly admits the volume_rattle family (isotropically scaled cell but
    rattled positions), which puts several distinct energies at one volume and
    corrupts the Birch-Murnaghan fit.
    """
    r = np.linalg.solve(ref.cell.array, a.cell.array)
    s = np.cbrt(np.linalg.det(r))
    if not np.allclose(r, np.eye(3)*s, atol=1e-6):
        return None
    df = a.get_scaled_positions() - ref.get_scaled_positions()
    df -= np.round(df)
    if np.abs(df).max() > 1e-6:
        return None
    return s**3

fits, curves = [], []
for ph in C.PHASES:
    ref = relaxed[ph]; N = len(ref); V0 = ref.get_volume()
    Vs, Es = [], []
    for f in np.linspace(0.90, 1.10, 11):
        w = ref.copy()
        w.set_cell(ref.cell.array * f ** (1/3.), scale_atoms=True)
        w.calc = calc
        Vs.append(w.get_volume()); Es.append(w.get_potential_energy())
    Vs, Es = np.array(Vs), np.array(Es)
    p0 = [Es.min(), V0, 1.0, 4.0]
    popt, _ = curve_fit(birch_murnaghan, Vs, Es, p0=p0, maxfev=200000)
    E0f, V0f, B0f, Bpf = popt
    resid = Es - birch_murnaghan(Vs, *popt)

    # DFT overlay
    dV, dE = [], []
    for a in atoms:
        if a.info["phase"] != ph: continue
        s = iso_scale(a, ref)
        if s is not None and 0.90 - 1e-9 <= s <= 1.10 + 1e-9:
            dV.append(a.get_volume()); dE.append(a.get_potential_energy())
    dV, dE = np.array(dV), np.array(dE)

    dft_fit = None
    if len(dV) >= 4:
        try:
            po, _ = curve_fit(birch_murnaghan, dV, dE,
                              p0=[dE.min(), V0, 1.0, 4.0], maxfev=200000)
            dft_fit = po
        except Exception: pass

    fits.append({"phase": ph, "natoms": N, "V0_dft_ref_A3": V0,
                 "V0_mace_fit_A3": V0f, "dV0_pct": (V0f-V0)/V0*100,
                 "B0_mace_GPa": B0f*GPA, "Bp_mace": Bpf,
                 "E0_mace_eV_per_atom": E0f/N,
                 "fit_max_resid_meV_atom": float(np.abs(resid).max()/N*1000),
                 "n_dft_iso_points": len(dV),
                 "dft_window": "0.90-1.10 V0, same window as the MACE scan",
                 "V0_dft_fit_A3": dft_fit[1] if dft_fit is not None else np.nan,
                 "B0_dft_GPa": dft_fit[2]*GPA if dft_fit is not None else np.nan,
                 "Bp_dft": dft_fit[3] if dft_fit is not None else np.nan,
                 "dB0_GPa": (B0f-dft_fit[2])*GPA if dft_fit is not None else np.nan})
    curves.append((ph, Vs, Es, N, popt, dV, dE, dft_fit, V0))
    print(f"  {ph:7s} V0_fit={V0f:8.3f} A^3 ({(V0f-V0)/V0*100:+.3f}%)  B0={B0f*GPA:7.2f} GPa"
          f"  n_dft={len(dV):2d}" + (f"  B0_dft={dft_fit[2]*GPA:7.2f} GPa" if dft_fit is not None else ""), flush=True)

df = pd.DataFrame(fits)
df.to_csv(os.path.join(C.RESULTS, "eos_fit.csv"), index=False)

# small multiples: one panel per phase, single series per panel -> no legend needed
fig, axes = plt.subplots(1, 5, figsize=(19, 3.9))
for ax, (ph, Vs, Es, N, popt, dV, dE, dft_fit, V0) in zip(axes, curves):
    Vg = np.linspace(Vs.min(), Vs.max(), 300)
    ax.plot(Vg/N, (birch_murnaghan(Vg, *popt)-popt[0])/N*1000, color="#1baf7a", lw=2, zorder=2)
    ax.scatter(Vs/N, (Es-popt[0])/N*1000, s=34, facecolor="#1baf7a",
               edgecolor="#fcfcfb", lw=1.2, zorder=3, label="MACE")
    if len(dV):
        ax.scatter(dV/N, (dE-(dft_fit[0] if dft_fit is not None else dE.min()))/N*1000,
                   s=52, marker="x", color="#2a78d6", lw=1.6, zorder=4, label="DFT (iso)")
    ax.axvline(V0/N, color="#9a9a94", lw=0.9, ls=":", zorder=1)
    ax.set_title(f"{ph}   $B_0$ = {popt[2]*GPA:.1f} GPa", fontsize=10, loc="left")
    ax.set_xlabel("V per atom ($\AA^3$)")
    if ax is axes[0]: ax.set_ylabel("E $-$ E$_0$ (meV/atom)")
    ax.legend(frameon=False, fontsize=8)
    for s in ("top","right"): ax.spines[s].set_visible(False)
    ax.grid(True, lw=0.4, color="#e4e4de"); ax.set_axisbelow(True)
fig.suptitle("Phase 5: energy-volume equation of state, 0.90-1.10 $V_0$, MACE combined227 vs QE/PBE DFT",
             x=0.005, ha="left", fontsize=12)
fig.tight_layout(rect=[0,0,1,0.94])
fig.savefig(os.path.join(C.RESULTS, "eos", "eos_all_phases.png"), dpi=150)
print("\nwrote results/eos/eos_all_phases.png")
pd.set_option("display.width", 250)
print(df.to_string(index=False, float_format=lambda v: f"{v:10.4f}"))
