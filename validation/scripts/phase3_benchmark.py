"""Phase 3: DFT vs MACE single-point benchmark on exact DFT geometries.

Metric definitions, fixed before any number was computed:
  * Relative energy error. For each config, E_rel = (E(config) - E(phase_relaxed))/N,
    in meV/atom; the error is |E_rel_model - E_rel_DFT|. This is the project's
    canonical metric (identical formula to the sealed acceptance criterion) and is
    the only energy metric comparable across models, because MACE absolute energies
    carry a model-dependent constant offset per element.
  * Force error: component-wise over all 3N Cartesian components, eV/A.
  * Stress error: component-wise over the 6 Voigt components, GPa.
No relaxation is performed anywhere in this phase.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, common as C

GPA = 160.21766208  # eV/A^3 -> GPa

MODELS = {
    "base_MATPES_PBE_0": C.BASE_MODEL,
    "pilot25":           C.model_path("pilot25_matpes_pbe_lora_v1"),
    "combined227":       C.model_path("al3ni_combined227_lora_v1"),
    "combined227_seed812": C.model_path("al3ni_combined227_seed20260812_lora_v1"),
    "combined227_seed813": C.model_path("al3ni_combined227_seed20260813_lora_v1"),
}

atoms, split = C.load_dataset("combined227")
ref_id = {a.info["phase"]: a.info["config_id"]
          for a in atoms if a.info["config_type"] == "relaxed"}

# DFT reference quantities
dft = {}
for a in atoms:
    dft[a.info["config_id"]] = {
        "E": a.get_potential_energy(), "F": a.get_forces(),
        "S": a.get_stress(voigt=True), "N": len(a),
        "phase": a.info["phase"], "config_type": a.info["config_type"],
        "family": C.family(a.info["config_type"]),
        "split": split[a.info["config_id"]]}

rows = []
for mname, mpath in MODELS.items():
    t0 = time.time()
    calc = C.calc(mpath)
    pred = {}
    for a in atoms:
        w = a.copy(); w.calc = calc
        pred[a.info["config_id"]] = {"E": w.get_potential_energy(),
                                     "F": w.get_forces(),
                                     "S": w.get_stress(voigt=True)}
    # relative energies, referenced to each phase's own relaxed structure
    for cid, d in dft.items():
        r = ref_id[d["phase"]]
        N = d["N"]
        e_dft = (d["E"] - dft[r]["E"]) / N * 1000.0
        e_prd = (pred[cid]["E"] - pred[r]["E"]) / N * 1000.0
        dF = pred[cid]["F"] - d["F"]
        dS = (pred[cid]["S"] - d["S"]) * GPA
        rows.append({
            "model": mname, "config_id": cid, "phase": d["phase"],
            "config_type": d["config_type"], "family": d["family"],
            "split": d["split"], "natoms": N,
            "E_rel_dft_meV_atom": e_dft, "E_rel_pred_meV_atom": e_prd,
            "E_rel_err_meV_atom": e_prd - e_dft,
            "abs_E_rel_err_meV_atom": abs(e_prd - e_dft),
            "F_mae_eV_A": float(np.abs(dF).mean()),
            "F_rmse_eV_A": float(np.sqrt((dF ** 2).mean())),
            "F_max_abs_eV_A": float(np.abs(dF).max()),
            "S_mae_GPa": float(np.abs(dS).mean()),
            "S_rmse_GPa": float(np.sqrt((dS ** 2).mean())),
            "E_abs_pred_eV": pred[cid]["E"], "E_abs_dft_eV": d["E"],
        })
    print(f"  {mname:22s} 227 configs in {time.time()-t0:6.1f}s", flush=True)

df = pd.DataFrame(rows)
df.to_csv(os.path.join(C.RESULTS, "benchmark_per_structure.csv"), index=False)

def agg(g):
    return pd.Series({
        "n": len(g),
        "E_rel_MAE_meV_atom": g["abs_E_rel_err_meV_atom"].mean(),
        "E_rel_RMSE_meV_atom": np.sqrt((g["E_rel_err_meV_atom"] ** 2).mean()),
        "E_rel_MAX_meV_atom": g["abs_E_rel_err_meV_atom"].max(),
        "F_MAE_eV_A": g["F_mae_eV_A"].mean(),
        "F_RMSE_eV_A": np.sqrt((g["F_rmse_eV_A"] ** 2).mean()),
        "S_MAE_GPa": g["S_mae_GPa"].mean(),
    })

overall = df.groupby("model").apply(agg, include_groups=False).reindex(MODELS.keys())
overall.to_csv(os.path.join(C.RESULTS, "model_comparison.csv"))
per_phase = df.groupby(["model", "phase"]).apply(agg, include_groups=False)
per_phase.to_csv(os.path.join(C.RESULTS, "per_phase_metrics.csv"))
per_fam = df.groupby(["model", "family"]).apply(agg, include_groups=False)
per_fam.to_csv(os.path.join(C.RESULTS, "per_deformation_metrics.csv"))
per_split = df.groupby(["model", "split"]).apply(agg, include_groups=False)
per_split.to_csv(os.path.join(C.RESULTS, "per_split_metrics.csv"))

pd.set_option("display.width", 200, "display.float_format", lambda v: f"{v:9.4f}")
print("\n================ OVERALL (all 227) ================")
print(overall.to_string())
print("\n================ combined227 BY PHASE ================")
print(per_phase.loc["combined227"].to_string())
print("\n================ combined227 BY DEFORMATION FAMILY ================")
print(per_fam.loc["combined227"].reindex(C.FAMILY_ORDER).to_string())
print("\n================ combined227 BY SPLIT ROLE ================")
print(per_split.loc["combined227"].to_string())
