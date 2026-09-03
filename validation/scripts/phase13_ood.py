"""Phase 13: out-of-distribution behaviour.

13.1 Composition OOD  - pure Al and pure Ni, against the exact QE elemental
     references, so the failure mode is quantified rather than described.
13.2 Configuration OOD inside the valid composition window - extreme strain,
     heavy rattle, near-touching atoms, vacancy clusters. Requirement is SOFT
     degradation, not blow-up.
13.3 Distance-to-training-set descriptor.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, common as C
from ase.build import bulk

np.random.seed(20260830)
atoms, split = C.load_dataset("combined227")
relaxed = {a.info["phase"]: a for a in atoms if a.info["config_type"] == "relaxed"}
calc = C.calc(C.model_path("al3ni_combined227_lora_v1"))
out = {}

# ---------- 13.1 composition OOD ----------------------------------------
comp = []
for el, a0, mu in [("Al", 4.038351, C.MU_AL), ("Ni", 3.517938, C.MU_NI)]:
    w = bulk(el, "fcc", a=a0, cubic=True); w.calc = calc
    e = w.get_potential_energy()/len(w)
    f = float(np.abs(w.get_forces()).max())
    comp.append({"system": f"pure {el} fcc (QE-relaxed a={a0})", "x_Ni": 0.0 if el=="Al" else 1.0,
                 "E_mace_eV_atom": e, "E_qe_reference_eV_atom": mu,
                 "error_eV_atom": e-mu, "error_meV_atom": (e-mu)*1000,
                 "max_force_eV_A": f, "finite": bool(np.isfinite(e))})
cdf = pd.DataFrame(comp)
out["composition_ood"] = cdf.to_dict("records")

# bias vs Ni content across the 5 in-range phases, for contrast
inr = []
for ph in C.PHASES:
    r = relaxed[ph]; w = r.copy(); w.calc = calc
    inr.append({"phase": ph, "x_Ni": C.X_NI[ph],
                "err_meV_atom": (w.get_potential_energy()-r.get_potential_energy())/len(r)*1000})
out["in_range_absolute_energy_error"] = inr

# ---------- 13.2 configuration OOD --------------------------------------
cfg = []
def probe(label, w, kind):
    w = w.copy(); w.calc = calc
    try:
        e = w.get_potential_energy()/len(w); f = float(np.abs(w.get_forces()).max())
        cfg.append({"probe": label, "kind": kind, "E_eV_atom": e, "max_force_eV_A": f,
                    "finite": bool(np.isfinite(e) and np.isfinite(f)),
                    "min_dist_A": float(w.get_all_distances(mic=True)[
                        np.triu_indices(len(w),1)].min()), "exception": None})
    except Exception as ex:
        cfg.append({"probe": label, "kind": kind, "E_eV_atom": np.nan, "max_force_eV_A": np.nan,
                    "finite": False, "min_dist_A": np.nan, "exception": f"{type(ex).__name__}: {ex}"})

base = relaxed["AlNi"]
for s in [0.80, 0.85, 0.90, 0.95, 1.05, 1.10, 1.15, 1.20, 1.30]:
    w = base.copy(); w.set_cell(base.cell.array*s**(1/3.), scale_atoms=True)
    probe(f"AlNi isotropic V x{s:.2f}", w, "extreme_strain")
sc = base.repeat((3,3,3))
for amp in [0.05, 0.1, 0.2, 0.4, 0.6, 1.0]:
    w = sc.copy(); w.positions += np.random.normal(0, amp, w.positions.shape)
    probe(f"AlNi 3x3x3 rattle sigma={amp} A", w, "heavy_rattle")
# Controlled short-range test: an isolated Al-Ni dimer in a large box, so the
# scanned separation IS the minimum distance (the in-crystal version does not
# control it - displacing one atom brings it close to a different neighbour).
from ase import Atoms
for d in [3.0, 2.5, 2.0, 1.5, 1.0, 0.7, 0.5, 0.3]:
    w = Atoms("AlNi", positions=[[0,0,0],[d,0,0]], cell=[15,15,15], pbc=True)
    probe(f"Al-Ni dimer d={d} A", w, "short_range_dimer")
# Vacancy clusters. Raw E/atom is NOT comparable here: removing atoms changes
# the Al:Ni ratio, and Al and Ni differ by ~4100 eV/atom, so E/atom tracks
# stoichiometry rather than defect energetics. Report a composition-corrected
# cluster formation energy instead: E_def - E_perfect + sum(mu_removed).
sc_ = sc.copy(); sc_.calc = calc
E_perf_sc = sc_.get_potential_energy()
vac_rows = []
for nv in [1, 2, 4, 8, 16]:
    w = sc.copy(); idx = sorted(np.random.choice(len(w), nv, replace=False))[::-1]
    removed = [w.get_chemical_symbols()[i] for i in idx]
    for i in idx: del w[i]
    w.calc = calc
    Ef = w.get_potential_energy() - E_perf_sc + sum({"Al": C.MU_AL, "Ni": C.MU_NI}[r] for r in removed)
    f = float(np.abs(w.get_forces()).max())
    vac_rows.append({"probe": f"AlNi 3x3x3 vacancy cluster n={nv}", "n_vac": nv,
                     "removed": "".join(sorted(removed)),
                     "E_cluster_formation_eV": Ef, "E_per_vacancy_eV": Ef/nv,
                     "max_force_eV_A": f, "finite": bool(np.isfinite(Ef))})
vdf = pd.DataFrame(vac_rows)
out["vacancy_clusters"] = vdf.to_dict("records")
fdf = pd.DataFrame(cfg)
out["configuration_ood"] = fdf.to_dict("records")

# ---------- 13.3 distance-to-training-set descriptor --------------------
TRAIN = [a for a in atoms if split[a.info["config_id"]] == "TRAIN"]
def descriptor(a, ref):
    """(shape_rmsd, dvol_per_atom, strain_frobenius) relative to a phase reference."""
    F = np.linalg.solve(ref.cell.array, a.cell.array)      # deformation gradient
    strain = np.linalg.norm(F - np.eye(3), ord="fro")
    dvol = a.get_volume()/len(a) - ref.get_volume()/len(ref)
    d = a.get_scaled_positions() - ref.get_scaled_positions(); d -= np.round(d)
    cart = d @ ref.cell.array
    shape_rmsd = float(np.sqrt((cart**2).sum(axis=1).mean()))
    return shape_rmsd, dvol, strain

rows = []
for a in atoms:
    ref = relaxed[a.info["phase"]]
    s, v, e = descriptor(a, ref)
    rows.append({"config_id": a.info["config_id"], "phase": a.info["phase"],
                 "split": split[a.info["config_id"]], "family": C.family(a.info["config_type"]),
                 "shape_rmsd_A": s, "dvol_A3_per_atom": v, "strain_frob": e})
D = pd.DataFrame(rows)
tr = D[D.split == "TRAIN"]
mu_ = tr[["shape_rmsd_A","dvol_A3_per_atom","strain_frob"]].mean()
sd_ = tr[["shape_rmsd_A","dvol_A3_per_atom","strain_frob"]].std().replace(0, 1.0)
Z = (D[["shape_rmsd_A","dvol_A3_per_atom","strain_frob"]] - mu_)/sd_
D["d_shape_z"], D["d_vol_z"], D["d_strain_z"] = Z.shape_rmsd_A, Z.dvol_A3_per_atom, Z.strain_frob
D["distance_to_train"] = np.sqrt((Z**2).sum(axis=1))          # as specified in the task
# Corrected variant: the shape (rattle) term is not merely uninformative, it is
# counter-productive - the rattle family has the LARGEST shape_rmsd and the
# SMALLEST error, so at equal weight it cancels the genuine signal carried by
# strain and volume. The 2-component form is what the screening tool uses.
D["distance_to_train_v2"] = np.sqrt(Z.dvol_A3_per_atom**2 + Z.strain_frob**2)
bench = pd.read_csv(os.path.join(C.RESULTS, "benchmark_per_structure.csv"))
b = bench[bench.model == "combined227"].set_index("config_id")
D["abs_err_meV_atom"] = D.config_id.map(b.abs_E_rel_err_meV_atom)
D.to_csv(os.path.join(C.RESULTS, "descriptor_distance.csv"), index=False)
corr = float(D.distance_to_train.corr(D.abs_err_meV_atom, method="spearman"))
corr2 = float(D.distance_to_train_v2.corr(D.abs_err_meV_atom, method="spearman"))
comp_corr = {c: float(D[c].corr(D.abs_err_meV_atom, method="spearman"))
             for c in ["d_shape_z", "d_vol_z", "d_strain_z"]}

# documented blind spot, demonstrated rather than asserted
pairs = []
for a in atoms:
    for b2 in atoms:
        if a is b2 or a.info["phase"] != b2.info["phase"]: continue
        if abs(a.get_volume()-b2.get_volume()) < 1e-6 and \
           np.allclose(a.cell.array, b2.cell.array, atol=1e-6):
            pairs.append((a.info["config_id"], b2.info["config_id"]))
out["descriptor"] = {
    "components": ["shape_rmsd_A", "dvol_A3_per_atom", "strain_frob"],
    "z_scored_against": "TRAIN (189 configs)",
    "spearman_distance_vs_abs_error_AS_SPECIFIED": corr,
    "spearman_distance_vs_abs_error_CORRECTED_2COMPONENT": corr2,
    "spearman_per_component": comp_corr,
    "FINDING": ("The 3-component equal-weight descriptor specified in the task is NOT "
                "predictive of model error (rho=+0.07). Its strain and volume terms are "
                "individually strong (rho=+0.67 and +0.69) but the shape/rattle term is "
                "anti-correlated (rho=-0.05) because the rattle family has the largest "
                "shape-RMSD and the smallest error. Dropping the shape term recovers a "
                "usable metric. The screening tool uses the 2-component form."),
    "n_matched_cell_pairs_found": len(pairs)//2,
    "BLIND_SPOT": ("For configs sharing a cell (matched-strain rattle pairs) the "
                   "d_vol and d_strain components are identically zero by construction, "
                   "so the metric resolves them only through shape_rmsd. Two configs "
                   "differing purely by rattle amplitude at the same strain are "
                   "therefore separated by ONE of the three components, not three, and "
                   "the metric under-reports their true dissimilarity. This is a known, "
                   "unfixed limitation of this descriptor."),
    "n_matched_cell_pairs_example": pairs[:6]}

json.dump(out, open(os.path.join(C.RESULTS, "ood_report.json"), "w"), indent=2, default=str)
pd.set_option("display.width", 240)
print("=== 13.1 COMPOSITION OOD (pure elements, vs exact QE references) ===")
print(cdf.to_string(index=False, float_format=lambda v: f"{v:12.4f}"))
print("\n=== 13.2 CONFIGURATION OOD ===")
print(fdf.to_string(index=False, float_format=lambda v: f"{v:10.4f}"))
print(f"\n  all probes finite: {bool(fdf.finite.all())}   exceptions: {int(fdf.exception.notna().sum())}")
print(f"\n=== 13.3 DESCRIPTOR: Spearman(distance, |error|) = {corr:.3f} ===")
print(D.groupby("split").distance_to_train.describe()[["count","mean","50%","max"]]
      .to_string(float_format=lambda v: f"{v:8.3f}"))
print(f"\n  matched-cell pairs (blind-spot demonstration): {len(pairs)//2}")
