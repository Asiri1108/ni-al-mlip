"""Phase 1: model + dataset integrity, split derivation, seal cross-check."""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from ase.io import read

out = {"note": "Models and DFT data taken from the local Windows archive "
               "(the local ni_al_2/*.tar.gz archive), not re-downloaded from "
               "RunPod. The HuggingFace copy was cross-checked by hash.",
       "models": {}, "datasets": {}, "splits": {}, "seal_cross_check": {},
       "chemical_potentials": {"mu_Al_eV_per_atom": C.MU_AL,
                               "mu_Ni_eV_per_atom": C.MU_NI,
                               "source": "configs/STEPB_ELEMENTAL_REFERENCES_STATUS.txt",
                               "method": "QE/PBE elemental references"}}

# --- models -------------------------------------------------------------
wanted = ["al3ni_combined227_lora_v1", "al3ni_combined227_seed20260812_lora_v1",
          "al3ni_combined227_seed20260813_lora_v1", "pilot25_matpes_pbe_lora_v1",
          "dataset100_matpes_pbe_lora_v1", "al3ni_combined113_lora_v1",
          "al3ni_combined127_lora_v1", "al3ni_combined129_lora_v1",
          "al3ni_combined211_lora_v1", "al3ni_combined218_lora_v1",
          "al3ni_combined220_lora_v1"]
for name in wanted:
    p = C.model_path(name)
    if not os.path.exists(p):
        out["models"][name] = {"status": "ABSENT"}
        continue
    rec = {"path": p, "bytes": os.path.getsize(p), "sha256": C.sha256(p)}
    try:
        c = C.calc(p)
        rec["load"] = "OK"
        rec["r_max"] = float(c.models[0].r_max)
        rec["n_params"] = int(sum(x.numel() for x in c.models[0].parameters()))
        del c
    except Exception as e:
        rec["load"] = f"FAILED: {type(e).__name__}: {e}"
    out["models"][name] = rec

p = C.BASE_MODEL
rec = {"path": p, "bytes": os.path.getsize(p), "sha256": C.sha256(p),
       "expected_sha256": "e618ad582b84239905b9c3b77ce6e9ce111b0ecd1533223a1a6aac7a696b8aa0",
       "expected_bytes": 79471284,
       "provenance": "configs/pilot25_matpes_pbe_lora_v1_PROVENANCE.txt"}
rec["hash_match"] = rec["sha256"] == rec["expected_sha256"]
try:
    c = C.calc(p); rec["load"] = "OK"; del c
except Exception as e:
    rec["load"] = f"FAILED: {type(e).__name__}: {e}"
out["models"]["MACE-MATPES-PBE-0 (base)"] = rec

# --- datasets -----------------------------------------------------------
recorded = {  # from configs/AL3NI_COMBINED227_MERGE_STATUS.txt
 "ni_al_combined227_dft.extxyz": "9051860ae83dea782d9e5e49e4bf68f992103eed703ad81ca1ded5ea98db29eb",
 "ni_al_combined227_train_189.extxyz": "41e4baf136bb430d39101acc3f3939c4390645fb355c509dd2b8e3ea310fe3f4",
 "ni_al_combined227_validation_18.extxyz": "079459f075a871d830249e713bdd11c0343774ff651689c94421a0b357c22aff"}
for f in sorted(glob.glob(os.path.join(C.DATA, "ni_al_combined*.extxyz"))):
    b = os.path.basename(f)
    r = {"n_configs": len(read(f, ":")), "sha256": C.sha256(f)}
    if b in recorded:
        r["recorded_sha256"] = recorded[b]
        r["hash_match"] = r["sha256"] == recorded[b]
    out["datasets"][b] = r

# --- splits -------------------------------------------------------------
atoms, split = C.load_dataset("combined227")
counts = {}
for v in split.values():
    counts[v] = counts.get(v, 0) + 1
out["splits"] = {"counts": counts,
                 "reserved_20": sorted(k for k, v in split.items() if v == "RESERVED"),
                 "sealed_pair_present_in_227": [k for k in split if "297" in k or "299" in k]}

# --- seal cross-check ---------------------------------------------------
out["seal_cross_check"] = {
 "status_file_searched_for": "configs/ROUND285_CONFIRMATION_STATUS.txt",
 "status_file_found": os.path.exists(os.path.join(C.ARCH, "configs",
                                                  "ROUND285_CONFIRMATION_STATUS.txt")),
 "actual_file_on_disk": "configs/AL3NI_ROUND285_FINAL_UNSEALING_RESULT.txt",
 "file_says": {"cfg297_Al3Ni_iso_expansion_meV_atom": 1.846570,
               "cfg299_Al3Ni_volume_rattle_expansion_meV_atom": 1.922083,
               "threshold_meV_atom": 2.6183, "verdict": "PASS (both)"},
 "prompt_alternative_claim": {"cfg297": 1.1927, "cfg299": 1.5780},
 "resolution": ("The on-disk unsealing record supports 1.847 / 1.922. The values "
                "1.1927 / 1.5780 appear nowhere in any status/report document in the "
                "archive (they occur only as coincidental training-loss substrings in "
                "MACE train logs). FILE WINS: 1.846570 / 1.922083."),
 "model_pin_in_unsealing_record":
     "e4fd54cc8a4a090fc9e32d6625269142824bfada8315433127b3aa3118c65cee",
 "model_pin_matches_local_file":
     out["models"]["al3ni_combined227_lora_v1"]["sha256"] ==
     "e4fd54cc8a4a090fc9e32d6625269142824bfada8315433127b3aa3118c65cee"}

json.dump(out, open(os.path.join(C.RESULTS, "model_dataset_integrity.json"), "w"), indent=2)
print(json.dumps({k: out[k] for k in ["splits", "seal_cross_check", "chemical_potentials"]}, indent=2))
print("\n--- model load summary ---")
for k, v in out["models"].items():
    print(f"  {k:42s} {v.get('load','?'):6s} sha={v.get('sha256','')[:12]} n_params={v.get('n_params','-')}")
print("\n--- dataset hash match ---")
for k, v in out["datasets"].items():
    if "hash_match" in v:
        print(f"  {k:42s} n={v['n_configs']:4d} match={v['hash_match']}")
