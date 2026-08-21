#!/usr/bin/env python3
"""Evidence-gathering evaluation of the FROZEN combined-220 checkpoint --
NOT the acceptance test itself, NOT an unsealing event. Purpose: derive
the acceptance threshold from real held-out error, pre-registered before
cfg109/cfg110 are ever opened.

Two independent pieces, same relative-energy formula throughout
(matches evaluate_al3ni_interim_gate_218.py / evaluate_combined211_reserved_set.py):

1. cfg043 / cfg115 -- the known continuity probes. Context only, NOT the
   threshold basis (both were seen during design/validation history in a
   way the reserved-20 never were).

2. The full Dataset-100 TEST (5) + BLIND_HOLDOUT (15) = 20 structures --
   confirmed by explicit leakage check to be absent from combined-220
   TRAIN (182) and VALIDATION (18). This is the real generalization
   evidence. Reused once before at combined-211
   (results/combined211_reserved_evaluation_v1/); this is the second time
   ever, and the first time against combined-220.

cfg109/cfg110 are not part of TEST/BLIND_HOLDOUT and are NOT read, NOT
evaluated, NOT unsealed anywhere in this script.
"""

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from ase.io import read
from mace.calculators import MACECalculator

R = Path("/workspace/ni_al")
OUT = R / "results/combined220_reserved_evaluation_v1"
DATA = R / "data/datasets/ni_al_combined220_dft.extxyz"
TRAIN_FILE = R / "data/datasets/ni_al_combined220_train_182.extxyz"
VALID_FILE = R / "data/datasets/ni_al_combined220_validation_18.extxyz"
TEST = R / "data/datasets/ni_al_dataset100_test_manifest.csv"
BLIND = R / "data/datasets/ni_al_dataset100_blind_holdout_manifest.csv"
MODEL = R / "models/al3ni_combined220_lora_v1/al3ni_combined220_lora_v1.model"
STATUS = R / "configs/COMBINED220_RESERVED_EVALUATION_STATUS.txt"
PROBE_IDS = ["cfg043_Al3Ni_volume_rattle_expansion", "cfg115_Al3Ni_iso_expansion"]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def predict(path, structures):
    calc = MACECalculator(model_paths=str(path), device="cuda", default_dtype="float64")
    out = {}
    for key, a in structures.items():
        w = a.copy()
        w.calc = calc
        out[key] = float(w.get_potential_energy())
    del calc
    torch.cuda.empty_cache()
    return out


def pct(vals, q):
    return float(np.percentile(np.asarray(vals, float), q))


def dist_stats(vals):
    v = np.asarray(vals, float)
    return {"n": len(v), "min": float(v.min()), "median": float(np.median(v)),
            "p75": pct(v, 75), "p90": pct(v, 90), "max": float(v.max())}


def main():
    for p in (DATA, TRAIN_FILE, VALID_FILE, TEST, BLIND, MODEL):
        if not p.exists():
            raise RuntimeError(f"missing required file: {p}")

    frames = read(DATA, index=":")
    by = {a.info["config_id"]: a for a in frames}

    memberships = {s: list(csv.DictReader(p.open())) for s, p in [("TEST", TEST), ("BLIND_HOLDOUT", BLIND)]}
    if len(memberships["TEST"]) != 5 or len(memberships["BLIND_HOLDOUT"]) != 15:
        raise RuntimeError("evaluation membership count wrong (expected 5 TEST, 15 BLIND_HOLDOUT)")
    eval_ids = {r["config_id"] for rows in memberships.values() for r in rows}
    if len(eval_ids) != 20:
        raise RuntimeError("expected 20 unique reserved eval ids")

    train_ids = {a.info["config_id"] for a in read(TRAIN_FILE, index=":")}
    valid_ids = {a.info["config_id"] for a in read(VALID_FILE, index=":")}
    leak_train = eval_ids & train_ids
    leak_valid = eval_ids & valid_ids
    if leak_train or leak_valid:
        raise RuntimeError(f"LEAKAGE: reserved eval ids found in combined-220 TRAIN {leak_train} / VALIDATION {leak_valid}")

    relaxed = {}
    for phase in ("AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3"):
        cid = f"{phase}_relaxed"
        if cid not in by:
            raise RuntimeError(f"missing relaxed reference: {cid}")
        relaxed[phase] = by[cid]

    structures = {f"eval:{cid}": by[cid] for cid in eval_ids}
    structures.update({f"probe:{cid}": by[cid] for cid in PROBE_IDS})
    structures.update({f"relaxed:{p}": a for p, a in relaxed.items()})

    print("Evaluating combined-220 (frozen checkpoint)...", flush=True)
    pred = predict(MODEL, structures)

    def dft_relative(cid):
        a = by[cid]
        phase = a.info["phase"]
        de = float(a.get_potential_energy())
        dre = float(relaxed[phase].get_potential_energy())
        return (de - dre) / len(a) * 1000

    def pred_relative(cid):
        a = by[cid]
        phase = a.info["phase"]
        pe = pred[f"eval:{cid}"] if f"eval:{cid}" in pred else pred[f"probe:{cid}"]
        pre = pred[f"relaxed:{phase}"]
        return (pe - pre) / len(a) * 1000

    # --- probes: context only ---
    probe_rows = []
    for cid in PROBE_IDS:
        dre = dft_relative(cid)
        pre = pred_relative(cid)
        err = pre - dre
        probe_rows.append({"config_id": cid, "phase": by[cid].info["phase"],
                            "dft_relative_mev_atom": dre, "pred_relative_mev_atom": pre,
                            "relative_energy_error_mev_atom": err, "abs_error_mev_atom": abs(err)})

    # --- reserved 20: the real evidence ---
    eval_rows = []
    for split, members in memberships.items():
        for m in members:
            cid = m["config_id"]
            phase = by[cid].info["phase"]
            dre = dft_relative(cid)
            pre = pred_relative(cid)
            err = pre - dre
            eval_rows.append({"split": split, "config_id": cid, "phase": phase,
                               "dft_relative_mev_atom": dre, "pred_relative_mev_atom": pre,
                               "relative_energy_error_mev_atom": err, "abs_error_mev_atom": abs(err)})

    all_22_tagged = ([{**r, "split": "PROBE"} for r in probe_rows] + eval_rows)

    with (OUT / "combined220_reserved_per_config.csv").open("w", newline="") as f:
        fields = ["split", "config_id", "phase", "dft_relative_mev_atom", "pred_relative_mev_atom",
                  "relative_energy_error_mev_atom", "abs_error_mev_atom"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in all_22_tagged:
            w.writerow({k: r[k] for k in fields})

    held20_abs = [r["abs_error_mev_atom"] for r in eval_rows]
    held20_stats = dist_stats(held20_abs)
    all22_abs = [r["abs_error_mev_atom"] for r in all_22_tagged]
    all22_stats = dist_stats(all22_abs)

    by_phase_held20 = {}
    for phase in sorted({r["phase"] for r in eval_rows}):
        vals = [r["abs_error_mev_atom"] for r in eval_rows if r["phase"] == phase]
        by_phase_held20[phase] = dist_stats(vals)

    by_phase_all22 = {}
    for phase in sorted({r["phase"] for r in all_22_tagged}):
        vals = [r["abs_error_mev_atom"] for r in all_22_tagged if r["phase"] == phase]
        by_phase_all22[phase] = dist_stats(vals)

    lines = [
        "COMBINED-220 RESERVED-SET + PROBE EVALUATION (evidence-gathering, NOT the acceptance test)",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        "Purpose: derive the acceptance threshold from real held-out error, PRE-REGISTERED",
        "before cfg109/cfg110 are ever opened. This run does NOT unseal, read, or evaluate",
        "cfg109/cfg110 in any way.",
        "",
        f"DATA: {DATA} sha256={sha(DATA)}",
        f"TRAIN (leakage check source): {TRAIN_FILE} sha256={sha(TRAIN_FILE)}",
        f"VALIDATION (leakage check source): {VALID_FILE} sha256={sha(VALID_FILE)}",
        f"TEST membership: {TEST} (5)  BLIND_HOLDOUT membership: {BLIND} (15)",
        f"MODEL (frozen): {MODEL} sha256={sha(MODEL)}",
        "",
        f"LEAKAGE CHECK: PASS -- 0/20 reserved eval config_ids found in combined-220 TRAIN (182) or VALIDATION (18).",
        "",
        "=== 1. Continuity probes (cfg043, cfg115) -- CONTEXT ONLY, NOT THRESHOLD BASIS ===",
        "",
    ]
    for r in probe_rows:
        lines.append(f"  {r['config_id']} ({r['phase']}): DFT_relative={r['dft_relative_mev_atom']:.4f} meV/atom, "
                      f"pred_relative={r['pred_relative_mev_atom']:.4f} meV/atom, "
                      f"relative_energy_error={r['relative_energy_error_mev_atom']:.4f} meV/atom "
                      f"(|error|={r['abs_error_mev_atom']:.4f})")

    lines += ["", "=== 2. HELD-OUT-20 (Dataset-100 TEST+BLIND_HOLDOUT) -- THE REAL EVIDENCE ===", "",
              "Absolute relative-energy error distribution, n=20, meV/atom:",
              f"  min={held20_stats['min']:.4f}  median={held20_stats['median']:.4f}  "
              f"p75={held20_stats['p75']:.4f}  p90={held20_stats['p90']:.4f}  max={held20_stats['max']:.4f}",
              "", "Per-config detail:"]
    for split in ("TEST", "BLIND_HOLDOUT"):
        for r in sorted([x for x in eval_rows if x["split"] == split], key=lambda x: x["config_id"]):
            lines.append(f"  [{split}] {r['config_id']} ({r['phase']}): DFT_relative={r['dft_relative_mev_atom']:.4f}, "
                          f"pred_relative={r['pred_relative_mev_atom']:.4f}, "
                          f"error={r['relative_energy_error_mev_atom']:.4f}, |error|={r['abs_error_mev_atom']:.4f} meV/atom")

    lines += ["", "Per-phase breakdown (HELD-OUT-20, |relative-energy error|, meV/atom):", ""]
    for phase, s in by_phase_held20.items():
        lines.append(f"  {phase} (n={s['n']}): min={s['min']:.4f} median={s['median']:.4f} "
                      f"p75={s['p75']:.4f} p90={s['p90']:.4f} max={s['max']:.4f}")

    lines += ["", "=== Combined 22-point distribution (probes + held-out-20), for reference only ===", "",
              f"  min={all22_stats['min']:.4f}  median={all22_stats['median']:.4f}  "
              f"p75={all22_stats['p75']:.4f}  p90={all22_stats['p90']:.4f}  max={all22_stats['max']:.4f}", "",
              "Per-phase breakdown (all 22, |relative-energy error|, meV/atom):", ""]
    for phase, s in by_phase_all22.items():
        lines.append(f"  {phase} (n={s['n']}): min={s['min']:.4f} median={s['median']:.4f} "
                      f"p75={s['p75']:.4f} p90={s['p90']:.4f} max={s['max']:.4f}")

    lines += ["", "STATUS", "COMBINED-220 RESERVED-SET + PROBE EVALUATION COMPLETE",
              "This is EVIDENCE-GATHERING, not the acceptance test. No threshold applied here.",
              "cfg109/cfg110 NOT part of TEST/BLIND_HOLDOUT, NOT read, NOT evaluated, NOT unsealed."]
    STATUS.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nPer-config CSV: {OUT / 'combined220_reserved_per_config.csv'}")


if __name__ == "__main__":
    main()
