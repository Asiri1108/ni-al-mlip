"""Phase 11: MD stability, scoped to a CPU-only machine.

Scope agreed with the user: 5 phases x 4 temperatures (300/600/900/1200 K) NVT,
5 ps each; plus NPT at 300 K and 900 K for thermal expansion. Trajectories are
SHORT (5 ps, 2 fs timestep) - this bounds what may be concluded: it is a
stability and drift screen, not a converged transport or free-energy study.

Tracked: temperature stability, potential-energy drift, RDF, MSD, lattice
parameters (NPT), and displaced ("escaped") atoms.

BAROSTAT CORRECTION (2026-09-02)
--------------------------------
The first NPT pass used compressibility_au=5e-7. ASE wants that argument in
atomic units (A^3/eV); 5e-7 is a bar^-1-scale number, ~2e6 times too small, so
the Berendsen scaling factor was 1.0 to within 1e-10 and the cell never moved.
Those runs are archived under results/md/_archive_npt_broken/. The 20 NVT runs
were unaffected and were not repeated.

The compressibility is now taken per phase as 1/B0, with B0 the Phase 5 EOS
bulk modulus. It sets only the RATE at which the cell relaxes, never the
equilibrium volume it relaxes to:

    scl = 1 - (dt/taup)*(kappa/3)*(P_ext - P)   =>   tau_cell = taup/(kappa*B)

Choosing kappa = 1/B therefore makes tau_cell equal taup exactly for every
phase, which is what lets one equilibration window be correct for all of them.

EQUILIBRATION WINDOW
--------------------
With taup = 500 fs, tau_cell = 0.5 ps. Discarding 2.5 ps (= 5 tau) leaves a
residual transient of ~0.13% of alpha, against ~9% under the previous 1 ps
discard at taup = 1 ps. The trajectory length is unchanged at 5 ps, so removing
that bias costs nothing; it is purely a re-partition of the window. NVT keeps
its 1 ps discard: it has no cell to relax and taut = 100 fs, so 1 ps is already
10 thermostat time constants.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, common as C
from ase import units, Atoms
from ase.md.langevin import Langevin
from ase.md.nptberendsen import NPTBerendsen
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution, Stationary
from ase.optimize import FIRE
from ase.filters import FrechetCellFilter
from ase.geometry.analysis import Analysis

TEMPS = [300, 600, 900, 1200]
NPT_TEMPS = [300, 900]
DT = 2.0 * units.fs
NSTEPS = 2500          # 5 ps
EQUIL = {"NVT": 500, "NPT": 1250}   # steps discarded before averaging
TAUT = 100 * units.fs
TAUP = 500 * units.fs
RECORD_EVERY = 10
CHECKPOINT_EVERY = 100   # steps; bounds what a crash can cost
SUPER = {"Al3Ni": (2,2,2), "Al3Ni2": (3,3,2), "AlNi": (4,4,4),
         "Al3Ni5": (3,2,2), "AlNi3": (3,3,3)}

RES = os.path.join(C.RESULTS, "md")
CKPT = os.path.join(C.ROOT, "work", "md_ckpt")
SUMMARY = os.path.join(C.RESULTS, "md_summary.csv")
os.makedirs(RES, exist_ok=True)
os.makedirs(CKPT, exist_ok=True)

# The full schedule, in execution order. Used both for resuming and for deciding
# whether the run finished; nothing downstream may infer completion from the
# process merely having exited.
SCHEDULE = ([(ph, T, "NVT") for ph in C.PHASES for T in TEMPS] +
            [(ph, T, "NPT") for ph in C.PHASES for T in NPT_TEMPS])

_dataset = None
_calc = None
_kappa = {}


def dataset():
    global _dataset
    if _dataset is None:
        atoms, _split = C.load_dataset("combined227")
        _dataset = {a.info["phase"]: a for a in atoms
                    if a.info["config_type"] == "relaxed"}
    return _dataset


def calculator():
    global _calc
    if _calc is None:
        _calc = C.calc(C.model_path("al3ni_combined227_lora_v1"))
    return _calc


def compressibility_au(phase):
    """1/B0 in ASE atomic units (A^3/eV), B0 from the Phase 5 EOS fit.

    ASE documents compressibility_au as "the compressibility of the material,
    in atomic units (A^3/eV)"; its deprecated bar^-1 form is converted
    internally by dividing by (1e5 * units.Pascal). Passing a bar^-1 number
    straight into the _au slot is what broke the first pass.
    """
    if phase not in _kappa:
        eos = pd.read_csv(os.path.join(C.RESULTS, "eos_fit.csv"))
        row = eos[eos.phase == phase]
        if len(row) != 1:
            raise RuntimeError(f"no unique EOS row for {phase}; cannot set barostat")
        b0_gpa = float(row.B0_mace_GPa.iloc[0])
        _kappa[phase] = 1.0 / (b0_gpa * 1e9 * units.Pascal)
    return _kappa[phase]


def rdf_first_peak(a, rmax=6.0, nbins=120):
    d = a.get_all_distances(mic=True)
    d = d[np.triu_indices(len(a), 1)]
    h, edges = np.histogram(d, bins=nbins, range=(0.5, rmax))
    r = 0.5*(edges[1:]+edges[:-1])
    shell = 4*np.pi*r**2*(edges[1]-edges[0])
    g = h/shell
    return r, g/g.max() if g.max() > 0 else g


# --------------------------------------------------------------- relaxed base

def relaxed_base(ph):
    """FIRE-relaxed primitive cell for a phase, cached on disk.

    Every run of a phase re-relaxed the same cell to fmax=0.001 - six identical
    relaxations per phase across the schedule. The result depends only on the
    phase and the model, so it is computed once and reused.
    """
    cache = os.path.join(CKPT, f"relaxed_{ph}.npz")
    if os.path.exists(cache):
        with np.load(cache) as d:
            a = Atoms(numbers=d["numbers"], positions=d["positions"],
                      cell=d["cell"], pbc=True)
        a.calc = calculator()
        return a
    a = dataset()[ph].copy(); a.calc = calculator()
    FIRE(FrechetCellFilter(a), logfile=os.devnull).run(fmax=0.001, steps=2000)
    tmp = cache + ".tmp.npz"
    np.savez(tmp, numbers=a.get_atomic_numbers(), positions=a.get_positions(),
             cell=np.array(a.get_cell()))
    os.replace(tmp, cache)
    return a


# ---------------------------------------------------------------- checkpoints

REC_KEYS = ["t_ps", "T", "Epot", "Etot", "V", "msd", "cellpar"]


def ckpt_path(ph, T, ensemble):
    return os.path.join(CKPT, f"{ph}_{T}K_{ensemble}.ckpt.npz")


def save_ckpt(path, atoms, rec, step, a0, cell0):
    """Atomic checkpoint write: a crash mid-write cannot corrupt the resume."""
    tmp = path + ".tmp.npz"
    payload = {"step": step, "positions": atoms.get_positions(),
               "momenta": atoms.get_momenta(), "cell": np.array(atoms.get_cell()),
               "numbers": atoms.get_atomic_numbers(), "a0": a0, "cell0": cell0}
    for k in REC_KEYS:
        payload["rec_" + k] = np.array(rec[k])
    np.savez(tmp, **payload)
    os.replace(tmp, path)


def load_ckpt(path):
    # np.load holds the archive open; on Windows that would make the
    # os.remove(path) at the end of a finished run fail with WinError 32.
    with np.load(path) as d:
        atoms = Atoms(numbers=d["numbers"], positions=d["positions"],
                      cell=d["cell"], pbc=True)
        atoms.set_momenta(d["momenta"])
        rec = {}
        for k in REC_KEYS:
            arr = d["rec_" + k]
            rec[k] = [x.tolist() for x in arr] if arr.ndim > 1 else list(arr)
        return atoms, rec, int(d["step"]), d["a0"].copy(), d["cell0"].copy()


# ------------------------------------------------------------------- one run

def run(ph, T, ensemble, verbose=True):
    """One MD trajectory, resumable from its own checkpoint.

    On resume the thermostat's random stream restarts; that changes the
    particular noise realisation, not the distribution being sampled, so a
    resumed trajectory is statistically equivalent to an uninterrupted one.
    """
    path = ckpt_path(ph, T, ensemble)
    base = relaxed_base(ph)

    if os.path.exists(path):
        a, rec, start, a0, cell0 = load_ckpt(path)
        a.calc = calculator()
        if verbose:
            print(f"  resume {ph:7s} {T:5d}K {ensemble} from step {start}/{NSTEPS}",
                  flush=True)
    else:
        a = base.repeat(SUPER[ph]); a.calc = calculator()
        a0 = a.get_positions().copy(); cell0 = a.cell.cellpar().copy()
        MaxwellBoltzmannDistribution(a, temperature_K=T); Stationary(a)
        rec = {k: [] for k in REC_KEYS}
        start = 0

    if ensemble == "NVT":
        dyn = Langevin(a, DT, temperature_K=T, friction=0.01/units.fs)
    else:
        dyn = NPTBerendsen(a, DT, temperature_K=T, pressure_au=0.0,
                           taut=TAUT, taup=TAUP,
                           compressibility_au=compressibility_au(ph))

    t0 = time.time()
    for i in range(start, NSTEPS):
        dyn.run(1)
        if i % RECORD_EVERY == 0:
            rec["t_ps"].append(i*2.0/1000)
            rec["T"].append(a.get_temperature())
            rec["Epot"].append(a.get_potential_energy()/len(a))
            rec["Etot"].append((a.get_potential_energy()+a.get_kinetic_energy())/len(a))
            rec["V"].append(a.get_volume()/len(a))
            rec["msd"].append(float(((a.get_positions()-a0)**2).sum(axis=1).mean()))
            rec["cellpar"].append(a.cell.cellpar().tolist())
        if (i+1) % CHECKPOINT_EVERY == 0 and (i+1) < NSTEPS:
            save_ckpt(path, a, rec, i+1, a0, cell0)
    wall = time.time()-t0

    k = EQUIL[ensemble]//RECORD_EVERY
    Tarr = np.array(rec["T"][k:]); Ep = np.array(rec["Epot"][k:])
    tt = np.array(rec["t_ps"][k:])
    drift = np.polyfit(tt, Ep, 1)[0]*1000            # meV/atom/ps
    disp = np.sqrt(((a.get_positions()-a0)**2).sum(axis=1))
    r, g = rdf_first_peak(a)
    cp_all = np.array(rec["cellpar"])
    cp = cp_all[k:]
    out = {"phase": ph, "T_target_K": T, "ensemble": ensemble,
           "natoms": len(a), "ps": NSTEPS*2/1000,
           "T_mean_K": float(Tarr.mean()), "T_std_K": float(Tarr.std()),
           "Epot_drift_meV_atom_per_ps": float(drift),
           "Etot_final_meV_atom": float(rec["Etot"][-1]*1000),
           "msd_final_A2": float(rec["msd"][-1]),
           "max_disp_A": float(disp.max()),
           "n_escaped_gt_2A": int((disp > 2.0).sum()),
           "frac_escaped": float((disp > 2.0).mean()),
           "V_mean_A3_per_atom": float(np.mean(rec["V"][k:])),
           "V0_A3_per_atom": float(base.get_volume()/len(base)),
           "a_mean": float(cp[:,0].mean()), "b_mean": float(cp[:,1].mean()),
           "c_mean": float(cp[:,2].mean()),
           "da_total_A": float(cp_all[-1,0]-cp_all[0,0]),
           "equil_steps_discarded": EQUIL[ensemble],
           "taup_fs": (TAUP/units.fs) if ensemble == "NPT" else np.nan,
           "compressibility_au": compressibility_au(ph) if ensemble == "NPT" else np.nan,
           "wall_s": round(wall,1)}
    np.savez(os.path.join(RES, f"{ph}_{T}K_{ensemble}.npz"),
             **{k2: np.array(v) for k2, v in rec.items()}, rdf_r=r, rdf_g=g)
    if os.path.exists(path):
        os.remove(path)          # only after the trajectory is safely on disk
    if verbose:
        print(f"  {ph:7s} {T:5d}K {ensemble} T={out['T_mean_K']:7.1f}+-{out['T_std_K']:5.1f} "
              f"drift={drift:+8.3f} meV/at/ps MSD={out['msd_final_A2']:7.3f} A^2 "
              f"escaped={out['n_escaped_gt_2A']:3d}/{len(a)} "
              f"da={out['da_total_A']:+.4f} A ({wall:.0f}s)", flush=True)
    return out


def npz_path(ph, T, ensemble):
    return os.path.join(RES, f"{ph}_{T}K_{ensemble}.npz")


def thermal_expansion(df):
    tex = []
    for ph in C.PHASES:
        n = df[(df.phase == ph) & (df.ensemble == "NPT")].sort_values("T_target_K")
        if len(n) == 2:
            v1, v2 = n.V_mean_A3_per_atom.values; t1, t2 = n.T_target_K.values
            alpha_V = (v2-v1)/v1/(t2-t1)
            tex.append({"phase": ph, "T1_K": t1, "T2_K": t2, "V1": v1, "V2": v2,
                        "alpha_volumetric_per_K": alpha_V,
                        "alpha_linear_per_K": alpha_V/3.0})
    return pd.DataFrame(tex)


def load_done():
    """Rows already on disk, keyed by (phase, T, ensemble).

    A run counts as done only if BOTH its .npz trajectory and its summary row
    exist. A stray .npz without a summary row is treated as incomplete and is
    recomputed, since the summary carries fields the .npz does not store.
    """
    if not os.path.exists(SUMMARY):
        return {}
    try:
        prev = pd.read_csv(SUMMARY)
    except Exception:
        return {}
    out = {}
    for _, r in prev.iterrows():
        key = (r["phase"], int(r["T_target_K"]), r["ensemble"])
        if os.path.exists(npz_path(*key)):
            out[key] = r.to_dict()
    return out


def main():
    done = load_done()
    if done:
        print(f"RESUMING: {len(done)}/{len(SCHEDULE)} runs already on disk, skipping them",
              flush=True)
        for k in SCHEDULE:
            if k in done:
                print(f"  skip {k[0]:7s} {k[1]:5d}K {k[2]}", flush=True)

    rows = []
    for ph, T, ensemble in SCHEDULE:
        key = (ph, T, ensemble)
        if key in done:
            rows.append(done[key])
            continue
        rows.append(run(ph, T, ensemble))
        pd.DataFrame(rows).to_csv(SUMMARY, index=False)
    pd.DataFrame(rows).to_csv(SUMMARY, index=False)

    df = pd.DataFrame(rows)
    thermal_expansion(df).to_csv(
        os.path.join(C.RESULTS, "md_thermal_expansion.csv"), index=False)

    # Completion is decided by counting trajectories on disk, never by the
    # process having exited. A crash, a kill, or a shutdown all end the process
    # too, and a partial MD set must not be reported as a finished phase.
    present = [k for k in SCHEDULE if os.path.exists(npz_path(*k))]
    missing = [k for k in SCHEDULE if k not in present]
    if len(present) == len(SCHEDULE):
        print(f"\nPHASE 11 COMPLETE  ({len(present)}/{len(SCHEDULE)} trajectories)")
    else:
        print(f"\nPHASE 11 PARTIAL  ({len(present)}/{len(SCHEDULE)} trajectories present)")
        for k in missing:
            print(f"  MISSING {k[0]:7s} {k[1]:5d}K {k[2]}")
        print("Phase 15 is blocked until all trajectories exist. "
              "Re-run this script to resume; completed runs are skipped.")


if __name__ == "__main__":
    main()
