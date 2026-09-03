"""Are the Phase 11 NVT temperature fluctuations canonical?

Read-only: operates on the .npz trajectories already on disk. Does NOT touch the
running Phase 11 process and does not need a model.

Canonical NVT with N_dof degrees of freedom gives sigma_T/<T> = sqrt(2/N_dof).
ASE's Atoms.get_temperature() reports with N_dof = 3N (no constraint objects are
attached), so that is the comparison basis; Langevin's fixcm=True actually samples
3N-3, a -0.4% effect on sigma_T/T, far below the sampling error established below.

The point of this script: a 5 ps run leaves ~4 ps after equilibration, which is
too few independent samples to measure sigma_T to better than ~8-10%. Any apparent
"suppression" must be tested against that, not read off directly.
"""
import sys, os, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, common as C

KB = 8.617333262e-5
EQUIL_PS = 1.0
NATOMS = {"Al3Ni": 128, "Al3Ni2": 90, "AlNi": 128, "Al3Ni5": 96, "AlNi3": 108}


def tau_int(x, dt):
    x = x - x.mean(); n = len(x)
    c = np.correlate(x, x, "full")[n-1:]; c = c/c[0]
    k = int(np.argmax(c <= 0)) if (c <= 0).any() else len(c)
    return max((0.5 + c[1:k].sum())*dt, dt/2)


rows = []
for f in sorted(glob.glob(os.path.join(C.RESULTS, "md", "*_NVT.npz"))):
    tag = os.path.basename(f)[:-4]
    ph = tag.split("_")[0]
    d = np.load(f)
    t, T, Ep, Et = d["t_ps"], d["T"], d["Epot"], d["Etot"]
    N = NATOMS[ph]
    dof_reported = float(np.median(2*(Et-Ep)*N/(T*KB)))   # what ASE divided by
    m = t >= EQUIL_PS
    tt, TT = t[m], T[m]
    dt = float(tt[1]-tt[0])
    obs = TT.std(ddof=1)/TT.mean()
    exp = np.sqrt(2/(3*N))
    tau = tau_int(TT, dt)
    neff = (tt[-1]-tt[0])/(2*tau)
    se = obs/np.sqrt(2*max(neff, 1))
    blocks = np.array_split(TT, 4)
    bsd = np.array([b.std(ddof=1)/b.mean() for b in blocks])
    rows.append({
        "run": tag, "natoms": N, "dof_used_by_ase": dof_reported,
        "T_mean": float(TT.mean()), "sigma_over_T": float(obs),
        "canonical_sqrt_2_over_3N": float(exp),
        "implied_N": float(2/(3*obs**2)),
        "tau_int_fs": float(tau*1000), "n_eff": float(neff),
        "z_vs_canonical": float((obs-exp)/se),
        "block_sigma_over_T": [float(x) for x in bsd],
        "block_se": float(bsd.std(ddof=1)/2),
        "t_vs_canonical_blocks": float((obs-exp)/(bsd.std(ddof=1)/2)),
        "consistent_with_canonical_at_2sigma": bool(abs((obs-exp)/se) < 2),
    })
    r = rows[-1]
    print(f"{tag:22s} N={N:4d} dof_ase={dof_reported:5.1f}  sigma/T={obs:.5f} "
          f"(canonical {exp:.5f}, implied N={r['implied_N']:.1f})  "
          f"n_eff={neff:.0f}  z={r['z_vs_canonical']:+.2f}  "
          f"t_block={r['t_vs_canonical_blocks']:+.2f}")

json.dump(rows, open(os.path.join(C.RESULTS, "phase11_fluctuation_check.json"), "w"), indent=2)
print("\nNVT thermostat: Langevin (ase.md.langevin), friction 0.01/fs  -> canonical")
print("NPT thermostat: NPTBerendsen (ase.md.nptberendsen)             -> NOT canonical")
print(f"\n{len(rows)} NVT run(s) analysed; "
      f"{sum(r['consistent_with_canonical_at_2sigma'] for r in rows)} consistent with canonical at 2 sigma.")
