#!/usr/bin/env python3
"""Update the full coverage / extrapolation-ceiling audit for combined-220.

Same reconstruction as prior updates, extended with round220's 2 TRAIN
additions (cfg283, cfg284) closing the last 2 EXTRAPOLATION flags (cfg041,
cfg107). Compared against the combined-218 audit (immediately-prior
checkpoint). cfg109/cfg110 (sealed) excluded entirely -- not read anywhere
in this script.
"""

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path("/workspace/ni_al")
OUT_CSV = ROOT / "results/full_coverage_audit_v1/coverage_ceiling_report_combined220.csv"
OUT_MD = ROOT / "results/full_coverage_audit_v1/priority_ranking_combined220.md"
PREV_CSV = ROOT / "results/full_coverage_audit_v1/coverage_ceiling_report_combined218.csv"
SEALED_IDS = {"cfg109_Al3Ni_iso_expansion", "cfg110_Al3Ni_volume_rattle_expansion"}

ROLE_MAP = {
    "HISTORICAL_TRAIN": "TRAIN", "TRAIN_CANDIDATE": "TRAIN", "TRAIN": "TRAIN",
    "HISTORICAL_VALIDATION": "VALIDATION", "VALIDATION": "VALIDATION",
    "HISTORICAL_TEST": "TEST", "BLIND_HOLDOUT": "BLIND_HOLDOUT",
}


def base_family(config_family, config_type):
    cf = (config_family or "").strip()
    if config_type == "relaxed" or cf == "relaxed":
        return "relaxed"
    if config_type == "iso_m02" or config_type == "iso_p02":
        return "isotropic"
    if config_type == "rattle_003":
        return "rattle"
    if config_type == "shear015_rattle002":
        return "shear_rattle"
    if cf.startswith("iso_"):
        return "isotropic"
    if cf.startswith("shear_rattle"):
        return "shear_rattle"
    if cf.startswith("volume_rattle"):
        return "volume_rattle"
    if cf.startswith("biaxial"):
        return "biaxial"
    if cf.startswith("uniaxial"):
        return "uniaxial"
    if cf.startswith("orthorhombic"):
        return "orthorhombic"
    if cf.startswith("rattle"):
        return "rattle"
    if cf.startswith("shear"):
        return "shear"
    return f"OTHER:{cf}"


AXIS_BY_FAMILY = {
    "isotropic": "strain_value", "biaxial": "strain_value", "uniaxial": "strain_value",
    "orthorhombic": "strain_value", "volume_rattle": "strain_value",
    "shear": "shear_value", "shear_rattle": "shear_value", "rattle": "rattle_sigma_A",
}


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load_dataset100():
    rows = []
    for name in ("train", "validation", "test", "blind_holdout"):
        path = ROOT / f"data/datasets/ni_al_dataset100_{name}_manifest.csv"
        for r in csv.DictReader(path.open(newline="")):
            role = ROLE_MAP.get(r["target_role"], r["target_role"])
            config_type = r["config_type"]
            metadata_gap = config_type in ("rattle_003", "shear015_rattle002")
            strain = -0.02 if config_type == "iso_m02" else (0.02 if config_type == "iso_p02" else fnum(r["strain_value"]))
            rows.append({"config_id": r["config_id"], "phase": r["phase"], "role": role,
                         "family": base_family(r["config_family"], config_type),
                         "strain_value": strain, "rattle_sigma_A": fnum(r["rattle_sigma_A"]),
                         "shear_value": fnum(r["shear_value"]), "metadata_gap": metadata_gap})
    return rows


def load_remediation_v1():
    rows = []
    path = ROOT / "data/al3ni_remediation_v1/remediation_manifest.csv"
    for r in csv.DictReader(path.open(newline="")):
        if r["config_id"] in SEALED_IDS:
            continue
        rows.append({"config_id": r["config_id"], "phase": r["phase"], "role": r["split"],
                     "family": base_family(r["config_family"], r["config_type"]),
                     "strain_value": fnum(r["requested_strain"]) if r["strain_type"] != "none" else None,
                     "rattle_sigma_A": fnum(r["requested_rattle_sigma_A"]),
                     "shear_value": 0.0, "metadata_gap": False})
    return rows


def load_round2():
    rows = []
    path = ROOT / "data/al3ni_remediation_v1/round2_manifest.csv"
    for r in csv.DictReader(path.open(newline="")):
        rows.append({"config_id": r["config_id"], "phase": r["phase"], "role": r["split"],
                     "family": base_family(r["config_family"], r["config_type"]),
                     "strain_value": fnum(r["requested_strain"]), "rattle_sigma_A": fnum(r["rattle_sigma_A"]),
                     "shear_value": 0.0, "metadata_gap": False})
    return rows


def load_round3():
    rows = []
    path = ROOT / "data/al3ni_remediation_v1/round3_manifest.csv"
    for r in csv.DictReader(path.open(newline="")):
        rows.append({"config_id": r["config_id"], "phase": r["phase"], "role": r["target_role"],
                     "family": base_family(r["config_family"], r["config_family"]),
                     "strain_value": fnum(r["strain_value"]), "rattle_sigma_A": fnum(r["rattle_sigma_A"]),
                     "shear_value": fnum(r["shear_value"]), "metadata_gap": False})
    return rows


def load_round4():
    rows = []
    path = ROOT / "data/al3ni_remediation_v1/round4_biaxial_manifest.csv"
    for r in csv.DictReader(path.open(newline="")):
        rows.append({"config_id": r["config_id"], "phase": r["phase"], "role": r["target_role"],
                     "family": base_family(r["config_family"], r["config_family"]),
                     "strain_value": fnum(r["strain_value"]), "rattle_sigma_A": fnum(r["rattle_sigma_A"]),
                     "shear_value": fnum(r["shear_value"]), "metadata_gap": False})
    return rows


def load_round300():
    rows = []
    path = ROOT / "data/al3ni_remediation_v1/round300_manifest.csv"
    for r in csv.DictReader(path.open(newline="")):
        family = base_family(r["config_family"], r["config_family"])
        val = fnum(r["strain_or_shear_value"])
        is_shear = family in ("shear", "shear_rattle")
        rows.append({"config_id": r["config_id"], "phase": r["phase"], "role": r["target_role"],
                     "family": family, "strain_value": None if is_shear else val,
                     "shear_value": val if is_shear else 0.0,
                     "rattle_sigma_A": fnum(r["rattle_sigma_A"]), "metadata_gap": False})
    return rows


def load_round212_213():
    rows = []
    for name in ("round212_manifest.csv", "round213_manifest.csv"):
        path = ROOT / f"data/al3ni_remediation_v1/{name}"
        if not path.exists():
            continue
        for r in csv.DictReader(path.open(newline="")):
            family = base_family(r["config_family"], r["config_family"])
            val = fnum(r["strain_or_shear_value"])
            is_shear = family in ("shear", "shear_rattle")
            rows.append({"config_id": r["config_id"], "phase": r["phase"], "role": r["target_role"],
                         "family": family, "strain_value": None if is_shear else val,
                         "shear_value": val if is_shear else 0.0,
                         "rattle_sigma_A": fnum(r["rattle_sigma_A"]), "metadata_gap": False})
    return rows


def load_round220():
    rows = []
    path = ROOT / "data/al3ni_remediation_v1/round220_manifest.csv"
    for r in csv.DictReader(path.open(newline="")):
        family = base_family(r["config_family"], r["config_family"])
        val = fnum(r["strain_or_shear_value"])
        is_shear = family in ("shear", "shear_rattle")
        rows.append({"config_id": r["config_id"], "phase": r["phase"], "role": r["target_role"],
                     "family": family, "strain_value": None if is_shear else val,
                     "shear_value": val if is_shear else 0.0,
                     "rattle_sigma_A": fnum(r["rattle_sigma_A"]), "metadata_gap": False})
    return rows


def main():
    all_rows = (load_dataset100() + load_remediation_v1() + load_round2() + load_round3()
                + load_round4() + load_round300() + load_round212_213() + load_round220())
    all_rows = [r for r in all_rows if r["family"] != "relaxed" and not r["family"].startswith("OTHER:")]

    by_bucket = defaultdict(list)
    for r in all_rows:
        by_bucket[(r["phase"], r["family"])].append(r)

    out_rows = []
    for (phase, family), members in sorted(by_bucket.items()):
        axis_name = AXIS_BY_FAMILY.get(family)
        if axis_name is None:
            continue
        train_vals = sorted(r[axis_name] for r in members if r["role"] == "TRAIN" and not r["metadata_gap"] and r[axis_name] is not None)
        n_train = len(train_vals)
        train_min = train_vals[0] if train_vals else None
        train_max = train_vals[-1] if train_vals else None

        if n_train in (1, 2):
            out_rows.append({"phase": phase, "family": family, "config_id": "(insufficient TRAIN density)",
                             "role": "TRAIN", "axis_name": axis_name, "axis_value": "", "train_min": train_min,
                             "train_max": train_max, "flag": "INFO_LOW_TRAIN_COUNT",
                             "detail": f"only {n_train} TRAIN member(s) -- gap analysis not meaningful"})
        elif n_train >= 3:
            diffs = [train_vals[i] - train_vals[i - 1] for i in range(1, n_train)]
            median_diff = sorted(diffs)[len(diffs) // 2] if diffs else 0.0
            max_diff = max(diffs) if diffs else 0.0
            if median_diff > 0 and max_diff >= 2.0 * median_diff:
                idx = diffs.index(max_diff)
                out_rows.append({"phase": phase, "family": family, "config_id": "(internal gap)", "role": "TRAIN",
                                 "axis_name": axis_name, "axis_value": "", "train_min": train_min, "train_max": train_max,
                                 "flag": "SPARSE_INTERNAL_GAP",
                                 "detail": f"consecutive TRAIN gap between {train_vals[idx]:.4f} and {train_vals[idx+1]:.4f} (size {max_diff:.4f} vs median {median_diff:.4f}, {max_diff/median_diff:.2f}x)"})

        for r in members:
            if r["role"] not in ("VALIDATION", "TEST", "BLIND_HOLDOUT"):
                continue
            axis_value = r[axis_name]
            if r["metadata_gap"]:
                flag, detail = "METADATA_GAP_NOT_EVALUABLE", "historical_not_recorded (Pilot-25 provenance)"
            elif n_train == 0:
                flag, detail = "EXTRAPOLATION_NO_TRAIN_SUPPORT", "zero TRAIN members in this phase/family bucket"
            elif axis_value is None:
                flag, detail = "SKIPPED_NO_AXIS_VALUE", "axis value unavailable"
            elif axis_value < train_min or axis_value > train_max:
                margin = max(train_min - axis_value, axis_value - train_max)
                flag, detail = "EXTRAPOLATION", f"outside TRAIN [{train_min:.4f}, {train_max:.4f}] by {margin:.4f}"
            else:
                flag, detail = "OK_IN_RANGE", ""
            out_rows.append({"phase": phase, "family": family, "config_id": r["config_id"], "role": r["role"],
                             "axis_name": axis_name, "axis_value": axis_value, "train_min": train_min,
                             "train_max": train_max, "flag": flag, "detail": detail})

    fields = ["phase", "family", "config_id", "role", "axis_name", "axis_value", "train_min", "train_max", "flag", "detail"]
    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    prev_rows = list(csv.DictReader(PREV_CSV.open(newline=""))) if PREV_CSV.exists() else []
    prev_key_flag = {(r["phase"], r["family"], r["config_id"]): r["flag"] for r in prev_rows}
    EXTRAP = ("EXTRAPOLATION_NO_TRAIN_SUPPORT", "EXTRAPOLATION")
    closed, still_open, new_flags = [], [], []
    for r in out_rows:
        key = (r["phase"], r["family"], r["config_id"])
        if r["flag"] in EXTRAP:
            (still_open if (key in prev_key_flag and prev_key_flag[key] in EXTRAP) else new_flags).append(r)
    for key, old_flag in prev_key_flag.items():
        if old_flag not in EXTRAP:
            continue
        match = next((r for r in out_rows if (r["phase"], r["family"], r["config_id"]) == key), None)
        if match is None or match["flag"] not in EXTRAP:
            closed.append({"phase": key[0], "family": key[1], "config_id": key[2], "old_flag": old_flag,
                           "new_flag": match["flag"] if match else "NOT_PRESENT"})

    zero_support = sorted({(r["phase"], r["family"]) for r in out_rows if r["flag"] == "EXTRAPOLATION_NO_TRAIN_SUPPORT"})
    low_count = sorted({(r["phase"], r["family"]) for r in out_rows if r["flag"] == "INFO_LOW_TRAIN_COUNT"})

    phase_counts = defaultdict(lambda: defaultdict(int))
    for r in all_rows:
        phase_counts[r["phase"]]["TOTAL"] += 1
        phase_counts[r["phase"]][r["role"]] += 1

    lines = ["# Full Coverage / Extrapolation-Ceiling Audit -- Updated for Combined-220", "",
             "Reconstruction (same caveats as prior updates). Compared vs combined-218 to isolate",
             "round220's effect. cfg109/cfg110 excluded (sealed, untouched, never loaded).", "",
             "## Per-phase population and TRAIN counts (combined-220)", "",
             "| Phase | TOTAL | TRAIN | VALIDATION | TEST | BLIND_HOLDOUT |", "|---|---|---|---|---|---|"]
    for phase in sorted(phase_counts):
        c = phase_counts[phase]
        lines.append(f"| {phase} | {c['TOTAL']} | {c.get('TRAIN',0)} | {c.get('VALIDATION',0)} | {c.get('TEST',0)} | {c.get('BLIND_HOLDOUT',0)} |")
    total_all = sum(c["TOTAL"] for c in phase_counts.values())
    total_train = sum(c.get("TRAIN", 0) for c in phase_counts.values())
    lines.append(f"| **TOTAL** | **{total_all}** | **{total_train}** | | | |")

    lines += ["", "## Configs that CLOSED an EXTRAPOLATION flag since combined-218", ""]
    if closed:
        lines.append("| Phase | Family | Config | Old flag | New flag |")
        lines.append("|---|---|---|---|---|")
        for c in sorted(closed, key=lambda x: (x["phase"], x["family"], x["config_id"])):
            lines.append(f"| {c['phase']} | {c['family']} | {c['config_id']} | {c['old_flag']} | {c['new_flag']} |")
    else:
        lines.append("(none)")
    lines += ["", "## EXTRAPOLATION flags STILL OPEN after round220", ""]
    if still_open:
        lines.append("| Phase | Family | Config | Role | Flag | Detail |")
        lines.append("|---|---|---|---|---|---|")
        for r in sorted(still_open, key=lambda x: (x["phase"], x["family"], x["config_id"])):
            lines.append(f"| {r['phase']} | {r['family']} | {r['config_id']} | {r['role']} | {r['flag']} | {r['detail']} |")
    else:
        lines.append("(none -- zero EXTRAPOLATION flags project-wide)")
    lines += ["", "## Zero-TRAIN-support buckets remaining", ""]
    lines.append("(none)" if not zero_support else "\n".join(f"- {p}/{f}" for p, f in zero_support))
    lines += ["", "## INFO_LOW_TRAIN_COUNT buckets remaining", ""]
    lines.append("(none)" if not low_count else "\n".join(f"- {p}/{f}" for p, f in low_count))
    lines += ["", "## New flags not present in the combined-218 audit (investigate if non-empty)", ""]
    if new_flags:
        lines.append("| Phase | Family | Config | Role | Flag | Detail |")
        lines.append("|---|---|---|---|---|---|")
        for r in sorted(new_flags, key=lambda x: (x["phase"], x["family"], x["config_id"])):
            lines.append(f"| {r['phase']} | {r['family']} | {r['config_id']} | {r['role']} | {r['flag']} | {r['detail']} |")
    else:
        lines.append("(none)")

    OUT_MD.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nRaw CSV: {OUT_CSV}")


if __name__ == "__main__":
    main()
