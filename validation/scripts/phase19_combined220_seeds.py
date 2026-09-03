"""Can the 2.3865 combined-220 threshold be re-derived as a max over three seeds,
the same way 2.6183 was for combined-227?

Protocol is copied verbatim from scripts/phase16_data_efficiency.py: the fixed
reserved-19 set (RESERVED-20 minus cfg043, excluded as design-contaminated), and
E_MAX = max |E_rel_pred - E_rel_dft| in meV/atom, with
E_rel = (E(config) - E(phase_relaxed))/N.

Seed 20260811 is al3ni_combined220_lora_v1 and is recomputed here rather than
read from data_efficiency.csv, so the reproduction is end-to-end.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, common as C

SEEDS = [(20260811, "al3ni_combined220_lora_v1"),
         (20260812, "al3ni_combined220_seed20260812_lora_v1"),
         (20260813, "al3ni_combined220_seed20260813_lora_v1")]
EXCL = {"cfg043_Al3Ni_volume_rattle_expansion"}
RECORDED = 2.3865

atoms, split = C.load_dataset("combined227")
ref_id = {a.info["phase"]: a.info["config_id"] for a in atoms if a.info["config_type"] == "relaxed"}
byid = {a.info["config_id"]: a for a in atoms}
RES = [a for a in atoms if split[a.info["config_id"]] == "RESERVED"]
RES19 = [a for a in RES if a.info["config_id"] not in EXCL]
assert len(RES) == 20 and len(RES19) == 19, (len(RES), len(RES19))

need = {a.info["config_id"]: a for a in RES}
for ph, r in ref_id.items():
    need[r] = byid[r]

rows, percfg = [], []
for seed, name in SEEDS:
    calc = C.calc(C.model_path(name))
    P = {}
    for cid, a in need.items():
        w = a.copy(); w.calc = calc
        P[cid] = w.get_potential_energy()
    errs = {}
    for a in RES19:
        cid = a.info["config_id"]; r = ref_id[a.info["phase"]]; n = len(a)
        ed = (a.get_potential_energy() - byid[r].get_potential_energy())/n*1000
        ep = (P[cid] - P[r])/n*1000
        errs[cid] = abs(ep - ed)
        percfg.append({"seed": seed, "config_id": cid, "abs_err_meV_atom": errs[cid]})
    anchor = max(errs, key=errs.get)
    rows.append({"seed": seed, "model": name,
                 "res19_E_MAX": max(errs.values()),
                 "res19_E_MAE": float(np.mean(list(errs.values()))),
                 "anchor_config": anchor})
    print(f"  seed {seed}  E_MAX={max(errs.values()):.4f}  E_MAE={np.mean(list(errs.values())):.4f}"
          f"  anchor={anchor}", flush=True)

df = pd.DataFrame(rows)
df.to_csv(os.path.join(C.RESULTS, "combined220_seed_thresholds.csv"), index=False)
pd.DataFrame(percfg).to_csv(os.path.join(C.RESULTS, "combined220_seed_res19_per_config.csv"), index=False)

three = float(df.res19_E_MAX.max())
single = float(df[df.seed == 20260811].res19_E_MAX.iloc[0])
out = {
    "recorded_combined220_threshold": RECORDED,
    "per_seed_res19_max": {int(r.seed): r.res19_E_MAX for _, r in df.iterrows()},
    "per_seed_anchor": {int(r.seed): r.anchor_config for _, r in df.iterrows()},
    "max_over_three_seeds": three,
    "seed20260811_alone": single,
    "single_seed_reproduces_2_3865": abs(single - RECORDED) < 5e-4,
    "three_seed_max_reproduces_2_3865": abs(three - RECORDED) < 5e-4,
    "anchor_identical_across_seeds": len(set(df.anchor_config)) == 1,
}
json.dump(out, open(os.path.join(C.RESULTS, "combined220_seed_thresholds.json"), "w"), indent=2)
print("\n" + json.dumps(out, indent=2))

# ---------------------------------------------------------------------------
# Robustness of the cfg109/cfg110 FAIL verdict to how the threshold is derived.
#
# Values are read from the public, byte-identical unsealing record
# configs/AL3NI_FINAL_UNSEALING_RESULT.txt (they cannot be recomputed here:
# the cfg109/cfg110 geometries and labels are not present in ANY extxyz in the
# archive or in either public repository - only this record holds the numbers).
# ---------------------------------------------------------------------------
UNSEALED = {"cfg109_Al3Ni_iso_expansion": 3.767116,
            "cfg110_Al3Ni_volume_rattle_expansion": 3.732003}
CANDIDATES = {
    "locked single-seed max of reserved-19 (2.3865, the bar actually used)": RECORDED,
    "max INCLUDING cfg043, locked then corrected away same day": 3.0402,
    "max over three seeds, the round-285 method applied retrospectively": three,
    "documented fallback: p90 of reserved-19": 1.5907,
}
rob = []
for label, thr in CANDIDATES.items():
    verdicts = {c: ("PASS" if e <= thr else "FAIL") for c, e in UNSEALED.items()}
    rob.append({"basis": label, "threshold_meV_atom": round(thr, 4),
                **verdicts,
                "overall": "PASS" if all(v == "PASS" for v in verdicts.values()) else "FAIL"})
out["cfg109_cfg110_unsealed_errors"] = UNSEALED
out["fail_verdict_robustness"] = rob
out["fail_verdict_robust_to_all_candidate_thresholds"] = all(r["overall"] == "FAIL" for r in rob)
out["seed_spread_meV_atom"] = float(df.res19_E_MAX.max() - df.res19_E_MAX.min())
out["anchor_sequence_811_812_813"] = [df[df.seed == s].anchor_config.iloc[0].split("_")[0]
                                      for s in (20260811, 20260812, 20260813)]
out["recorded_seed_spread_in_ROUND285_criterion"] = 0.808
out["recorded_anchor_sequence_in_ROUND285_criterion"] = ["cfg060", "cfg075", "cfg060"]
out["reproduces_recorded_seed_variance_finding"] = (
    abs(out["seed_spread_meV_atom"] - 0.808) < 5e-4
    and out["anchor_sequence_811_812_813"] == ["cfg060", "cfg075", "cfg060"])
json.dump(out, open(os.path.join(C.RESULTS, "combined220_seed_thresholds.json"), "w"), indent=2)

print("\n=== cfg109/cfg110 FAIL robustness ===")
print(pd.DataFrame(rob).to_string(index=False))
print(f"\nseed spread          = {out['seed_spread_meV_atom']:.4f} meV/atom "
      f"(ROUND285 criterion records 0.808)")
print(f"anchor sequence      = {' -> '.join(out['anchor_sequence_811_812_813'])} "
      f"(ROUND285 criterion records cfg060 -> cfg075 -> cfg060)")
print(f"reproduces recorded seed-variance finding: "
      f"{out['reproduces_recorded_seed_variance_finding']}")
