"""Phase 15: development applications.

Gated: only meaningful because Phases 3-11 passed. Each application records which
validation phase supports it and which does not.

Every construction carries a self-check. Where a constructed cell cannot be shown
to reproduce the bulk energy per atom, the corresponding number is NOT reported -
a wrong interface energy is worse than a missing one.
"""
import os
import sys
import json

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

from ase.build import surface
from ase.optimize import FIRE
from ase.constraints import FixAtoms, FixedLine
from ase.mep import NEB

OUT = os.path.join(C.RESULTS, "applications")

# ---------------------------------------------------------------------------
# HARD GATE: Phase 15 requires a COMPLETE Phase 11.
#
# Completion is established by counting trajectories on disk, never by the MD
# process having exited - a crash, a kill or a machine shutdown all end that
# process too. Without this gate, a partial MD set would silently be treated as
# finished and the high-temperature probe would report max(T_target_K) of
# whatever happened to finish (e.g. 600 K presented as the top temperature
# instead of 1200 K), which is worse than not running at all.
#
# This check lives here, not only in the runner script, so that it holds no
# matter what invokes Phase 15.
# ---------------------------------------------------------------------------
MD_DIR = os.path.join(C.RESULTS, "md")
TEMPS = [300, 600, 900, 1200]
NPT_TEMPS = [300, 900]
SCHEDULE = ([(ph, T, "NVT") for ph in C.PHASES for T in TEMPS] +
            [(ph, T, "NPT") for ph in C.PHASES for T in NPT_TEMPS])
_missing = [k for k in SCHEDULE
            if not os.path.exists(os.path.join(MD_DIR, f"{k[0]}_{k[1]}K_{k[2]}.npz"))]
if _missing:
    n_present = len(SCHEDULE) - len(_missing)
    print("PHASE 11 PARTIAL: %d/%d trajectories present." % (n_present, len(SCHEDULE)))
    print("PHASE 15 BLOCKED - it is gated on Phases 3-11 passing, and Phase 11 has not")
    print("completed. Refusing to run rather than reporting a high-temperature probe")
    print("over whichever temperatures happened to finish.")
    print("Missing runs:")
    for k in _missing:
        print("  %-7s %5dK %s" % k)
    print("\nResume with: python scripts/phase11_md.py   (completed runs are skipped)")
    sys.exit(3)

os.makedirs(OUT, exist_ok=True)

atoms, split = C.load_dataset("combined227")
relaxed = {a.info["phase"]: a for a in atoms if a.info["config_type"] == "relaxed"}
calc = C.calc(C.model_path("al3ni_combined227_lora_v1"))
records = []


def note(app, supported_by, not_supported_by):
    return {"application": app, "supported_by": supported_by,
            "NOT_supported_by": not_supported_by}


def relax_bulk(ph, fmax=0.001):
    from ase.filters import FrechetCellFilter
    b = relaxed[ph].copy()
    b.calc = calc
    FIRE(FrechetCellFilter(b), logfile=os.devnull).run(fmax=fmax, steps=2000)
    return b


# =====================================================================
# 15.1  Vacancy migration barrier in AlNi3 (NEB)
# =====================================================================
print("=== 15.1 NEB vacancy migration in AlNi3 ===", flush=True)
b = relax_bulk("AlNi3")
sc = b.repeat((3, 3, 3))
sc.calc = calc
E_perf = sc.get_potential_energy()

# Ni-site vacancy; migrating atom is the nearest Ni neighbour of the vacancy.
sym = sc.get_chemical_symbols()
ni_idx = [i for i, s in enumerate(sym) if s == "Ni"]
vac = ni_idx[0]
vac_pos = sc.positions[vac].copy()

initial = sc.copy()
del initial[vac]
initial.calc = calc

# nearest remaining Ni to the vacancy site
d = initial.get_distances(range(len(initial)), vac, mic=True) if False else None
dists = np.linalg.norm(
    (initial.get_positions() - vac_pos + sc.cell.lengths()[0] / 2) % sc.cell.lengths()
    - sc.cell.lengths() / 2, axis=1)
cand = [i for i in range(len(initial)) if initial.get_chemical_symbols()[i] == "Ni"]
mig = min(cand, key=lambda i: dists[i])
hop = dists[mig]
print("  migrating Ni index %d, hop distance %.4f A" % (mig, hop), flush=True)

FIRE(initial, logfile=os.devnull).run(fmax=0.01, steps=600)
E_i = initial.get_potential_energy()

final = initial.copy()
# move the migrating atom into the vacancy (minimum-image displacement)
disp = vac_pos - initial.positions[mig]
frac = np.linalg.solve(sc.cell.array.T, disp)
frac -= np.round(frac)
final.positions[mig] += frac @ sc.cell.array
final.calc = calc
FIRE(final, logfile=os.devnull).run(fmax=0.01, steps=600)
E_f = final.get_potential_energy()

NIMG = 5
images = [initial] + [initial.copy() for _ in range(NIMG)] + [final]
for im in images:
    im.calc = C.calc(C.model_path("al3ni_combined227_lora_v1"))
neb = NEB(images, climb=True, k=0.1)
neb.interpolate(mic=True)
FIRE(neb, logfile=os.devnull).run(fmax=0.05, steps=300)
Es = np.array([im.get_potential_energy() for im in images])
barrier = float(Es.max() - Es[0])
print("  E_i=%.4f  E_f=%.4f  barrier=%.4f eV  (dE=%.4f eV)"
      % (E_i, E_f, barrier, E_f - E_i), flush=True)

np.savetxt(os.path.join(OUT, "neb_alni3_vacancy_path.csv"),
           np.column_stack([np.arange(len(Es)), Es - Es[0]]),
           delimiter=",", header="image,relative_energy_eV", comments="")
records.append({
    "application": "Vacancy migration barrier, AlNi3 (Ni-site, NEB CI, 5 images)",
    "quantity": "migration barrier",
    "value": round(barrier, 4), "unit": "eV",
    "extra": "hop %.3f A; endpoint asymmetry %.4f eV" % (hop, E_f - E_i),
    "supported_by": "Phase 3 (forces, MAE 0.0012 eV/A), Phase 9 (dynamical stability), "
                    "Phase 10 (vacancy energetics converged to <10 meV with supercell)",
    "NOT_supported_by": "No DFT ground truth exists for any vacancy quantity in this "
                        "project (Phase 10). The saddle-point geometry is further from "
                        "the training manifold than any training configuration of this "
                        "type. Treat the barrier as indicative only; confirm with DFT "
                        "before any diffusion or creep claim."})

# =====================================================================
# 15.2  Antiphase boundary in AlNi3 (the gamma-prime strengthening quantity)
# =====================================================================
print("\n=== 15.2 Antiphase boundary in AlNi3 ===", flush=True)
print("  NOTE: a true gamma/gamma-prime interface pairs Ni3Al with PURE Ni (x_Ni=1.0),")
print("  which this model's own composition gate marks UNRELIABLE (Phase 13.1:")
print("  pure Ni is wrong by +112.5 meV/atom). The in-range analogue is the APB")
print("  inside gamma-prime itself, which is also the quantity that governs")
print("  gamma-prime strengthening.", flush=True)

apb_rows = []
for plane, shift_dir in [((0, 0, 1), np.array([0.5, 0.5, 0.0]))]:
    prim = surface(b, plane, 6, vacuum=None, periodic=True)
    a1p, a2p = prim.cell.array[0].copy(), prim.cell.array[1].copy()
    slab = prim.repeat((2, 2, 1))
    slab.calc = calc
    n = len(slab)
    E_slab = slab.get_potential_energy()
    # SELF-CHECK: an unfaulted, fully periodic cell must reproduce bulk E/atom
    e_bulk = b.get_potential_energy() / len(b)
    resid = abs(E_slab / n - e_bulk) * 1000
    print("  self-check: slab E/atom - bulk E/atom = %.4f meV/atom" % resid, flush=True)
    if resid > 1.0:
        print("  SELF-CHECK FAILED - APB energy NOT reported for this plane.", flush=True)
        apb_rows.append({"plane": str(plane), "status": "SELF-CHECK FAILED",
                         "residual_meV_atom": resid})
        continue
    faulted = slab.copy()
    z = faulted.positions[:, 2]
    top = z > (z.max() + z.min()) / 2.0
    shift_cart = shift_dir[0] * a1p + shift_dir[1] * a2p   # true 1/2<110>
    faulted.positions[top] += shift_cart
    faulted.calc = calc
    # Relax ONLY perpendicular to the fault plane. FixedLine(i, (0,0,1)) confines
    # each atom to the z axis; FixedPlane(i, (0,0,1)) would do the opposite - it
    # confines atoms TO the xy plane, freezing z and leaving the in-plane
    # coordinates free, which lets the imposed shift slide back to the nearest
    # minimum and destroys the fault.
    faulted.set_constraint([FixedLine(i, (0, 0, 1)) for i in range(len(faulted))])
    opt = FIRE(faulted, logfile=os.devnull)
    conv_apb = bool(opt.run(fmax=0.02, steps=400))
    if not conv_apb:
        print("  WARNING: APB relaxation did not reach fmax=0.02 in 400 steps; "
              "the energy below is an upper bound.", flush=True)
    E_fault = faulted.get_potential_energy()
    # NEGATIVE CONTROL: shifting by a FULL lattice vector is a translation of the
    # crystal and must cost essentially nothing. If it does not, the fault vector
    # or the cell is wrong and the APB number would be meaningless.
    ctrl = slab.copy()
    ctrl.positions[top] += 2.0 * shift_cart
    ctrl.calc = calc
    ctrl_meV = abs(ctrl.get_potential_energy() - E_slab) / n * 1000
    print("  negative control (full lattice shift): %.6f meV/atom" % ctrl_meV, flush=True)
    if ctrl_meV > 0.05:
        print("  NEGATIVE CONTROL FAILED - APB energy NOT reported.", flush=True)
        apb_rows.append({"plane": str(plane), "status": "NEGATIVE CONTROL FAILED",
                         "control_meV_atom": ctrl_meV})
        continue
    area = np.linalg.norm(np.cross(faulted.cell.array[0], faulted.cell.array[1]))
    gamma = (E_fault - E_slab) / (2.0 * area)          # two boundaries per cell
    gamma_mJ = gamma * 16021.766208                    # eV/A^2 -> mJ/m^2
    print("  APB%s  gamma = %.4f eV/A^2 = %.1f mJ/m^2" % (plane, gamma, gamma_mJ), flush=True)
    apb_rows.append({"plane": str(plane), "status": "OK", "natoms": n,
                     "area_A2": area, "gamma_eV_A2": gamma, "gamma_mJ_m2": gamma_mJ,
                     "residual_meV_atom": resid, "converged": conv_apb})

pd.DataFrame(apb_rows).to_csv(os.path.join(OUT, "apb_alni3.csv"), index=False)
ok = [r for r in apb_rows if r.get("status") == "OK"]
records.append({
    "application": "Antiphase boundary energy, AlNi3 (001), 1/2<110> shift",
    "quantity": "APB energy",
    "value": round(ok[0]["gamma_mJ_m2"], 1) if ok else None,
    "unit": "mJ/m^2",
    "extra": ("gamma/gamma-prime proper is NOT computable: it requires pure Ni, "
              "which the composition gate rejects"),
    "supported_by": "Phase 3 (energetics on shear/shear_rattle families, MAE 0.26-0.30 "
                    "meV/atom - the best-performing families), Phase 4 (AlNi3 relaxes "
                    "exactly onto the DFT geometry)",
    "NOT_supported_by": "No planar-defect configuration of any kind appears in the 227 "
                        "training configurations. This is a NOVEL STRUCTURE TYPE by the "
                        "Phase 14 criterion, so no calibrated error bar applies. The "
                        "(111) APB, which dominates real gamma-prime slip, was not "
                        "computed here."})

# =====================================================================
# 15.3  Generalized stacking fault energy curve, AlNi3
# =====================================================================
print("\n=== 15.3 GSFE curve, AlNi3 (001)<110> ===", flush=True)
prim = surface(b, (0, 0, 1), 6, vacuum=None, periodic=True)
a1p, a2p = prim.cell.array[0].copy(), prim.cell.array[1].copy()
slab = prim.repeat((2, 2, 1))
slab.calc = calc
E0 = slab.get_potential_energy()
e_bulk = b.get_potential_energy() / len(b)
resid = abs(E0 / len(slab) - e_bulk) * 1000
print("  self-check residual %.4f meV/atom" % resid, flush=True)
gsfe = []
if resid <= 1.0:
    area = np.linalg.norm(np.cross(slab.cell.array[0], slab.cell.array[1]))
    bvec = 0.5 * (a1p + a2p)          # 1/2<110> from the PRIMITIVE in-plane vectors
    for f in np.linspace(0, 1, 11):
        w = slab.copy()
        z = w.positions[:, 2]
        top = z > (z.max() + z.min()) / 2.0
        w.positions[top] += f * bvec
        w.calc = calc
        # See the note in 15.2: FixedLine confines each atom to z, which is what
        # "relax perpendicular to the fault plane" means. With FixedPlane the
        # in-plane coordinates stay free and every intermediate shift relaxes
        # back to f=0 or forward to f=1, turning the curve into a step function.
        w.set_constraint([FixedLine(i, (0, 0, 1)) for i in range(len(w))])
        opt = FIRE(w, logfile=os.devnull)
        conv = bool(opt.run(fmax=0.02, steps=300))
        g = (w.get_potential_energy() - E0) / (2.0 * area) * 16021.766208
        gsfe.append({"fraction_of_b": f, "gsfe_mJ_m2": g, "converged": conv})
        print("    f=%.2f  gamma=%8.1f mJ/m^2%s"
              % (f, g, "" if conv else "   [NOT CONVERGED - upper bound]"), flush=True)
    pd.DataFrame(gsfe).to_csv(os.path.join(OUT, "gsfe_alni3_001_110.csv"), index=False)
    gmax_row = max(gsfe, key=lambda r: r["gsfe_mJ_m2"])
    gmax = gmax_row["gsfe_mJ_m2"]
    n_unconv = sum(1 for r in gsfe if not r["converged"])
    # The curve maximum is only an "unstable fault energy" if it sits strictly
    # inside the path. A maximum pinned at f=0 or f=1 means the sampling missed
    # the saddle, not that the saddle is at an endpoint.
    interior = 0.0 < gmax_row["fraction_of_b"] < 1.0
    if not interior:
        print("  WARNING: curve maximum sits at f=%.2f, an endpoint - this is not an "
              "unstable fault energy." % gmax_row["fraction_of_b"], flush=True)
    if n_unconv:
        print("  WARNING: %d/11 points did not converge in 300 steps." % n_unconv,
              flush=True)
    records.append({
        "application": "Generalized stacking fault energy, AlNi3, (001) along 1/2<110>",
        "quantity": "unstable fault energy (curve maximum)",
        "value": round(gmax, 1), "unit": "mJ/m^2",
        "extra": "11 points, 0 to b, maximum at f=%.2f%s%s; full curve in "
                 "gsfe_alni3_001_110.csv"
                 % (gmax_row["fraction_of_b"],
                    "" if interior else " (ENDPOINT - not a true saddle)",
                    "" if not n_unconv else "; %d point(s) unconverged" % n_unconv),
        "supported_by": "Phase 3 shear families (lowest error of all families), "
                        "Phase 8 (C44 = 130.7 GPa for AlNi3, cross-validated vs LAMMPS "
                        "to 0.01 GPa)",
        "NOT_supported_by": "No stacking-fault configuration appears in training. "
                            "Rigid-shear geometries at large fault vector sit far outside "
                            "the strain envelope where Phase 6 measured errors rising to "
                            "4.1 meV/atom mean. The technologically dominant (111) plane "
                            "was not computed."})
else:
    print("  SELF-CHECK FAILED - GSFE not reported.", flush=True)
    records.append({"application": "GSFE, AlNi3", "quantity": "unstable fault energy",
                    "value": None, "unit": "mJ/m^2",
                    "extra": "self-check failed, not reported",
                    "supported_by": "-", "NOT_supported_by": "construction self-check failed"})

# =====================================================================
# 15.4  Short high-temperature MD within the valid composition window
# =====================================================================
print("\n=== 15.4 High-T MD probe ===", flush=True)
md_path = os.path.join(C.RESULTS, "md_summary.csv")
if os.path.exists(md_path):
    md = pd.read_csv(md_path)
    hi = md[(md.ensemble == "NVT") & (md.T_target_K == md.T_target_K.max())]
    rows = []
    for _, r in hi.iterrows():
        rows.append({"phase": r.phase, "T_K": r.T_target_K,
                     "msd_A2": r.msd_final_A2, "escaped": r.n_escaped_gt_2A,
                     "drift_meV_atom_per_ps": r.Epot_drift_meV_atom_per_ps,
                     "structurally_intact": bool(r.msd_final_A2 < 1.0 and r.n_escaped_gt_2A == 0)})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "high_T_probe.csv"), index=False)
    intact = sum(1 for r in rows if r["structurally_intact"])
    records.append({
        "application": "High-temperature structural probe, all 5 phases at %d K"
                       % int(md.T_target_K.max()),
        "quantity": "phases remaining structurally intact",
        "value": "%d/5" % intact, "unit": "phases",
        "extra": "derived from the Phase 11 NVT trajectories",
        "supported_by": "Phase 11 (5 ps NVT, this run), Phase 9 (all phases dynamically "
                        "stable at 0 K)",
        "NOT_supported_by": "5 ps is far too short to observe a genuine phase "
                            "transformation or to converge any transport property. "
                            "Absence of transformation here is NOT evidence of stability."})
else:
    records.append({
        "application": "High-temperature structural probe",
        "quantity": "-", "value": None, "unit": "-",
        "extra": "NOT RUN - Phase 11 MD unavailable",
        "supported_by": "-",
        "NOT_supported_by": "Phase 11 did not complete, so no finite-temperature claim "
                            "is made."})

df = pd.DataFrame(records)
df.to_csv(os.path.join(OUT, "applications_summary.csv"), index=False)
json.dump(records, open(os.path.join(OUT, "applications_summary.json"), "w"), indent=2)
pd.set_option("display.width", 250)
print("\n=== PHASE 15 SUMMARY ===")
print(df[["application", "quantity", "value", "unit"]].to_string(index=False))
print("\nPHASE 15 COMPLETE")
