"""Provenance diff: public sources vs the artifacts the validation actually consumed.

PUBLIC-SOURCE MODE. Public copies come only from:
  - git clone https://github.com/Asiri1108/ni-al-mlip
  - git clone https://github.com/Asiri1108/NiAl_MACE
  - huggingface_hub, repo asiri1/al3ni-mace
  - the MACE foundation release on github.com/ACEsuit/mace-foundations (base model)

The local archive is READ ONLY here and is not modified or deleted; it is the
left-hand side of the comparison.

Nothing is recomputed. This script only hashes and compares.
"""
import os
import sys
import json
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

PUB = os.path.join(C.ROOT, "work", "public")
GH1 = os.path.join(PUB, "ni-al-mlip")
GH2 = os.path.join(PUB, "NiAl_MACE")
LOCAL = C.ARCH

IDENTICAL, DIFFERENT, MISSING = "IDENTICAL", "DIFFERENT", "MISSING FROM PUBLIC RELEASE"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def find_public(relpath):
    """Look for the same relative path in either public repo."""
    for root, label in ((GH1, "ni-al-mlip"), (GH2, "NiAl_MACE")):
        p = os.path.join(root, relpath)
        if os.path.exists(p):
            return p, label
    # also try by basename anywhere in the repos
    base = os.path.basename(relpath)
    for root, label in ((GH1, "ni-al-mlip"), (GH2, "NiAl_MACE")):
        for dirpath, _, files in os.walk(root):
            if ".git" in dirpath:
                continue
            if base in files:
                return os.path.join(dirpath, base), label
    return None, None


rows = []


def compare(category, relpath, local_abs, phases, note=""):
    if not os.path.exists(local_abs):
        rows.append({"category": category, "artifact": relpath, "public_source": "-",
                     "status": "LOCAL COPY ABSENT", "local_sha": "-", "public_sha": "-",
                     "phases": phases, "note": note})
        return
    lsha = sha(local_abs)
    pub, label = find_public(relpath)
    if pub is None:
        rows.append({"category": category, "artifact": relpath, "public_source": "-",
                     "status": MISSING, "local_sha": lsha, "public_sha": "-",
                     "phases": phases, "note": note})
        return
    psha = sha(pub)
    rows.append({"category": category, "artifact": relpath, "public_source": label,
                 "status": IDENTICAL if psha == lsha else DIFFERENT,
                 "local_sha": lsha, "public_sha": psha,
                 "phases": phases, "note": note})


# ---------------------------------------------------------------- models
MODELS = [
    ("al3ni_combined227_lora_v1", "3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16"),
    ("al3ni_combined227_seed20260812_lora_v1", "3 (multi-seed)"),
    ("al3ni_combined227_seed20260813_lora_v1", "3 (multi-seed)"),
    ("pilot25_matpes_pbe_lora_v1", "3 (three-way comparison), 16"),
    ("dataset100_matpes_pbe_lora_v1", "16"),
    ("al3ni_combined113_lora_v1", "16"),
    ("al3ni_combined127_lora_v1", "16"),
    ("al3ni_combined129_lora_v1", "16"),
    ("al3ni_combined211_lora_v1", "16"),
    ("al3ni_combined218_lora_v1", "16"),
    ("al3ni_combined220_lora_v1", "16"),
]
for name, phases in MODELS:
    compare("model", "models/%s/%s.model" % (name, name), C.model_path(name), phases)

# ---------------------------------------------------------------- datasets
DATASETS = [
    ("ni_al_combined227_dft.extxyz", "1, 3, 4, 5, 6, 7, 9, 10, 13, 14, 15, 16"),
    ("ni_al_combined227_train_189.extxyz", "1, 3 (split derivation)"),
    ("ni_al_combined227_validation_18.extxyz", "1, 3, 16"),
    ("ni_al_combined220_train_182.extxyz", "16"),
    ("ni_al_combined220_validation_18.extxyz", "16"),
    ("ni_al_combined218_train_180.extxyz", "16"),
    ("ni_al_combined218_validation_18.extxyz", "16"),
    ("ni_al_combined211_train_173.extxyz", "16"),
    ("ni_al_combined211_validation_18.extxyz", "16"),
    ("ni_al_combined129_train_91.extxyz", "16"),
    ("ni_al_combined129_validation_18.extxyz", "16"),
    ("ni_al_combined127_train_89.extxyz", "16"),
    ("ni_al_combined127_validation_18.extxyz", "16"),
    ("ni_al_combined113_train_75.extxyz", "16"),
    ("ni_al_combined113_validation_18.extxyz", "16"),
    ("ni_al_dataset100_train_65.extxyz", "16, val18 contamination check"),
    ("ni_al_dataset100_validation_15.extxyz", "16, val18 contamination check"),
    ("ni_al_pilot_train_15.extxyz", "16, val18 contamination check"),
    ("ni_al_pilot_val_5.extxyz", "16, val18 contamination check"),
    ("ni_al_pilot_test_5.extxyz", "3 (zero-shot regime check)"),
]
for f, phases in DATASETS:
    compare("dataset", "data/datasets/" + f, os.path.join(C.DATA, f), phases)

# ---------------------------------------------------------------- configs
CONFIGS = [
    ("STEPB_ELEMENTAL_REFERENCES_STATUS.txt", "7, 10, 13, 14",
     "SOLE SOURCE of mu_Al and mu_Ni"),
    ("AL3NI_ROUND285_FINAL_UNSEALING_RESULT.txt", "1.6, 17",
     "cfg297/cfg299 values; the documented-conflict resolution"),
    ("ROUND285_SEALED_ACCEPTANCE_CRITERION.txt", "3, 17",
     "derivation of the 2.6183 threshold"),
    ("AL3NI_COMBINED227_MERGE_STATUS.txt", "1",
     "recorded dataset SHA256 used for the integrity check"),
    ("LAMMPS_STAGE_A_SINGLE_POINT_STATUS.txt", "12",
     "SOLE EVIDENCE for the Phase 12 verdict"),
    ("LAMMPS_STAGE_B_AL3NI5_ALPHA_DIAGNOSTIC.txt", "4",
     "independent alpha-angle corroboration"),
    ("LAMMPS_STAGE_C_ELASTIC_STATUS.txt", "8",
     "elastic cross-check corroboration"),
    ("pilot25_matpes_pbe_lora_v1_PROVENANCE.txt", "1",
     "base-model SHA256 pin"),
    ("al3ni_combined227_lora_v1.yaml", "1", "training hyperparameters"),
    ("ROUND285_SUCCESS_CRITERIA.txt", "17", "round-285 design record"),
    ("AL3NI_REMEDIATION_ACCEPTANCE_CRITERION.txt", "17", "cfg109/cfg110 threshold"),
    ("AL3NI_FINAL_UNSEALING_RESULT.txt", "17", "cfg109/cfg110 result"),
]
for f, phases, note in CONFIGS:
    compare("config", "configs/" + f, os.path.join(LOCAL, "configs", f), phases, note)

# ---------------------------------------------------------------- HuggingFace
hf = {"status": "NOT CHECKED"}
try:
    from huggingface_hub import hf_hub_download, list_repo_files
    files = list(list_repo_files("asiri1/al3ni-mace"))
    hf["repo_files"] = files
    mp = hf_hub_download("asiri1/al3ni-mace", "al3ni_combined227_lora_v1.model")
    hsha = sha(mp)
    lsha = sha(C.model_path("al3ni_combined227_lora_v1"))
    hf["model_sha256_huggingface"] = hsha
    hf["model_sha256_local"] = lsha
    hf["status"] = IDENTICAL if hsha == lsha else DIFFERENT
    # patch the model row for combined227
    for r in rows:
        if r["artifact"].endswith("al3ni_combined227_lora_v1.model"):
            r["public_source"] = "huggingface asiri1/al3ni-mace"
            r["status"] = hf["status"]
            r["public_sha"] = hsha
except Exception as e:
    hf["status"] = "HF ACCESS FAILED: %s: %s" % (type(e).__name__, e)

# ---------------------------------------------------------------- base model
base_note = {}
try:
    lsha = sha(C.BASE_MODEL)
    base_note = {"artifact": "MACE-matpes-pbe-omat-ft.model",
                 "public_source": "github.com/ACEsuit/mace-foundations release mace_matpes_0",
                 "local_sha": lsha,
                 "status": IDENTICAL if lsha ==
                 "e618ad582b84239905b9c3b77ce6e9ce111b0ecd1533223a1a6aac7a696b8aa0"
                 else DIFFERENT,
                 "note": "downloaded from the public upstream release during Phase 1; "
                         "not hosted in either project repo"}
except Exception as e:
    base_note = {"status": "ERROR: %s" % e}

json.dump({"rows": rows, "huggingface": hf, "base_model": base_note},
          open(os.path.join(C.RESULTS, "provenance_diff.json"), "w"), indent=2)

import collections
counts = collections.Counter(r["status"] for r in rows)
print("PROVENANCE DIFF SUMMARY")
for k, v in counts.items():
    print("  %-32s %d" % (k, v))
print("\nHuggingFace:", hf["status"])
print("Base model :", base_note.get("status"))
print("\nBy category:")
for cat in ["model", "dataset", "config"]:
    c = collections.Counter(r["status"] for r in rows if r["category"] == cat)
    print("  %-9s %s" % (cat, dict(c)))
print("\nNon-identical artifacts:")
for r in rows:
    if r["status"] != IDENTICAL:
        print("  [%s] %-58s phases: %s" % (r["status"][:9], r["artifact"], r["phases"]))
