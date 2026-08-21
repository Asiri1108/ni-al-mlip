#!/usr/bin/env python3
"""Update the full coverage / extrapolation-ceiling audit for combined-129.

Same reconstruction as update_full_coverage_audit_combined127.py (see that
script's docstring for what is and isn't reproduced from the original),
extended with round4's 2 biaxial TRAIN additions (cfg143 Al3Ni5, cfg145
AlNi3). Compared against the combined-127 audit (the immediately-prior
checkpoint) rather than the original combined-113 one, to show exactly
what round4 changed.

cfg109/cfg110 (sealed) excluded entirely -- never loaded, geometry or
labels.
"""

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path("/workspace/ni_al")
OUT_CSV = ROOT / "results/full_coverage_audit_v1/coverage_ceiling_report_combined129.csv"
OUT_MD = ROOT / "results/full_coverage_audit_v1/priority_ranking_combined129.md"
PREV_CSV = ROOT / "results/full_coverage_audit_v1/coverage_ceiling_report_combined127.csv"
SEALED_IDS = {"cfg109_Al3Ni_iso_expansion", "cfg110_Al3Ni_volume_rattle_expansion"}

ROLE_MAP = {
    "HISTORICAL_TRAIN": "TRAIN", "TRAIN_CANDIDATE": "TRAIN", "TRAIN": "TRAIN",
    "HISTORICAL_VALIDATION": "VALIDATION", "VALIDATION": "VALIDATION",
    "HISTORICAL_TEST": "TEST",
    "BLIND_HOLDOUT": "BLIND_HOLDOUT",
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
    "shear": "shear_value", "shear_rattle": "shear_value",
    "rattle": "rattle_sigma_A",
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
            rows.append({
                "config_id": r["config_id"], "phase": r["phase"], "role": role,
                "family": base_family(r["config_family"], config_type),
                "strain_value": strain, "rattle_sigma_A": fnum(r["rattle_sigma_A"]),
                "shear_value": fnum(r["shear_value"]), "metadata_gap": metadata_gap,
            })
    return rows


def load_remediation_v1():
    rows = []
    path = ROOT / "data/al3ni_remediation_v1/remediation_manifest.csv"
    for r in csv.DictReader(path.open(newline="")):
        if r["config_id"] in SEALED_IDS:
            continue
        rows.append({
            "config_id": r["config_id"], "phase": r["phase"], "role": r["split"],
            "family": base_family(r["config_family"], r["config_type"]),
            "strain_value": fnum(r["requested_strain"]) if r["strain_type"] != "none" else None,
            "rattle_sigma_A": fnum(r["requested_rattle_sigma_A"]),
            "shear_value": 0.0, "metadata_gap": False,
        })
    return rows


def load_round2():
    rows = []
    path = ROOT / "data/al3ni_remediation_v1/round2_manifest.csv"
    for r in csv.DictReader(path.open(newline="")):
        rows.append({
            "config_id": r["config_id"], "phase": r["phase"], "role": r["split"],
            "family": base_family(r["config_family"], r["config_type"]),
            "strain_value": fnum(r["requested_strain"]),
            "rattle_sigma_A": fnum(r["rattle_sigma_A"]),
            "shear_value": 0.0, "metadata_gap": False,
        })
    return rows


def load_round3():
    rows = []
    path = ROOT / "data/al3ni_remediation_v1/round3_manifest.csv"
    for r in csv.DictReader(path.open(newline="")):
        rows.append({
            "config_id": r["config_id"], "phase": r["phase"], "role": r["target_role"],
            "family": base_family(r["config_family"], r["config_family"]),
            "strain_value": fnum(r["strain_value"]), "rattle_sigma_A": fnum(r["rattle_sigma_A"]),
            "shear_value": fnum(r["shear_value"]), "metadata_gap": False,
        })
    return rows


def load_round4():
    rows = []
    path = ROOT / "data/al3ni_remediation_v1/round4_biaxial_manifest.csv"
    for r in csv.DictReader(path.open(newline="")):
        rows.append({
            "config_id": r["config_id"], "phase": r["phase"], "role": r["target_role"],
            "family": base_family(r["config_family"], r["config_family"]),
            "strain_value": fnum(r["strain_value"]), "rattle_sigma_A": fnum(r["rattle_sigma_A"]),
            "shear_value": fnum(r["shear_value"]), "metadata_gap": False,
        })
    return rows


def main():
    raw_rows = load_dataset100() + load_remediation_v1() + load_round2() + load_round3() + load_round4()

    phase_counts = defaultdict(lambda: defaultdict(int))
    for r in raw_rows:
        phase_counts[r["phase"]]["TOTAL"] += 1
        phase_counts[r["phase"]][r["role"]] += 1

    all_rows = [r for r in raw_rows if r["family"] != "relaxed" and not r["family"].startswith("OTHER:")]

    by_bucket = defaultdict(list)
    for r in all_rows:
        by_bucket[(r["phase"], r["family"])].append(r)

    out_rows = []
    for (phase, family), members in sorted(by_bucket.items()):
        axis_name = AXIS_BY_FAMILY.get(family)
        if axis_name is None:
            continue
        train_vals = sorted(
            r[axis_name] for r in members
            if r["role"] == "TRAIN" and not r["metadata_gap"] and r[axis_name] is not None
        )
        n_train = len(train_vals)
        train_min = train_vals[0] if train_vals else None
        train_max = train_vals[-1] if train_vals else None

        if n_train in (1, 2):
            out_rows.append({
                "phase": phase, "family": family, "config_id": "(insufficient TRAIN density)",
                "role": "TRAIN", "axis_name": axis_name, "axis_value": "",
                "train_min": train_min, "train_max": train_max, "flag": "INFO_LOW_TRAIN_COUNT",
                "detail": f"only {n_train} TRAIN member(s) -- gap analysis not meaningful",
            })
        elif n_train >= 3:
            diffs = [train_vals[i] - train_vals[i - 1] for i in range(1, n_train)]
            median_diff = sorted(diffs)[len(diffs) // 2] if diffs else 0.0
            max_diff = max(diffs) if diffs else 0.0
            if median_diff > 0 and max_diff >= 2.0 * median_diff:
                idx = diffs.index(max_diff)
                out_rows.append({
                    "phase": phase, "family": family, "config_id": "(internal gap)",
                    "role": "TRAIN", "axis_name": axis_name, "axis_value": "",
                    "train_min": train_min, "train_max": train_max, "flag": "SPARSE_INTERNAL_GAP",
                    "detail": (f"consecutive TRAIN gap between {train_vals[idx]:.4f} and {train_vals[idx+1]:.4f} "
                               f"(size {max_diff:.4f} vs median consecutive spacing {median_diff:.4f}, "
                               f"{max_diff/median_diff:.2f}x) [reconstructed >=2x heuristic, not verified against original threshold]"),
                })

        for r in members:
            if r["role"] not in ("VALIDATION", "TEST", "BLIND_HOLDOUT"):
                continue
            axis_value = r[axis_name]
            if r["metadata_gap"]:
                flag, detail = "METADATA_GAP_NOT_EVALUABLE", (
                    f"config_family/config_type implies a nonzero historical {axis_name}, but the frozen "
                    "manifest records it as historical_not_recorded (Pilot-25 provenance). NOT a genuine "
                    "extrapolation finding."
                )
            elif n_train == 0:
                flag, detail = "EXTRAPOLATION_NO_TRAIN_SUPPORT", "zero TRAIN members in this phase/family bucket"
            elif axis_value is None:
                flag, detail = "SKIPPED_NO_AXIS_VALUE", "axis value unavailable in source manifest"
            elif axis_value < train_min or axis_value > train_max:
                margin = max(train_min - axis_value, axis_value - train_max)
                flag, detail = "EXTRAPOLATION", f"outside TRAIN [{train_min:.4f}, {train_max:.4f}] by {margin:.4f}"
            else:
                flag, detail = "OK_IN_RANGE", ""
            out_rows.append({
                "phase": phase, "family": family, "config_id": r["config_id"], "role": r["role"],
                "axis_name": axis_name, "axis_value": axis_value, "train_min": train_min,
                "train_max": train_max, "flag": flag, "detail": detail,
            })

    fields = ["phase", "family", "config_id", "role", "axis_name", "axis_value", "train_min", "train_max", "flag", "detail"]
    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    prev_rows = list(csv.DictReader(PREV_CSV.open(newline=""))) if PREV_CSV.exists() else []
    prev_key_flag = {(r["phase"], r["family"], r["config_id"]): r["flag"] for r in prev_rows}

    closed, still_open, new_flags = [], [], []
    EXTRAP = ("EXTRAPOLATION_NO_TRAIN_SUPPORT", "EXTRAPOLATION")
    for r in out_rows:
        key = (r["phase"], r["family"], r["config_id"])
        if r["flag"] in EXTRAP:
            if key in prev_key_flag and prev_key_flag[key] in EXTRAP:
                still_open.append(r)
            else:
                new_flags.append(r)
    for key, old_flag in prev_key_flag.items():
        if old_flag not in EXTRAP:
            continue
        match = next((r for r in out_rows if (r["phase"], r["family"], r["config_id"]) == key), None)
        if match is None or match["flag"] not in EXTRAP:
            closed.append({"phase": key[0], "family": key[1], "config_id": key[2], "old_flag": old_flag,
                            "new_flag": match["flag"] if match else "NOT_PRESENT_IN_RECONSTRUCTION"})

    zero_support_buckets = sorted({(r["phase"], r["family"]) for r in out_rows if r["flag"] == "EXTRAPOLATION_NO_TRAIN_SUPPORT"})

    lines = [
        "# Full Coverage / Extrapolation-Ceiling Audit -- Updated for Combined-129",
        "",
        "**Reconstruction, not a verified rerun** -- same caveats as the combined-127 update "
        "(`scripts/update_full_coverage_audit_combined127.py`): TRAIN-range/zero-support method reproduced "
        "from documented conventions; the geometry-descriptor \"local density\" analysis is NOT reproduced "
        "(original script not found on disk). Compared against the combined-127 audit (immediately-prior "
        "checkpoint), not the original combined-113 one, to isolate what round4 specifically changed.",
        "",
        "cfg109/cfg110 excluded (sealed, untouched, never loaded).",
        "",
        "## Per-phase population and TRAIN counts (combined-129)",
        "",
        "| Phase | TOTAL | TRAIN | VALIDATION | TEST | BLIND_HOLDOUT |",
        "|---|---|---|---|---|---|",
    ]
    for phase in sorted(phase_counts):
        c = phase_counts[phase]
        lines.append(
            f"| {phase} | {c['TOTAL']} | {c.get('TRAIN', 0)} | {c.get('VALIDATION', 0)} | "
            f"{c.get('TEST', 0)} | {c.get('BLIND_HOLDOUT', 0)} |"
        )
    total_all = sum(c["TOTAL"] for c in phase_counts.values())
    total_train = sum(c.get("TRAIN", 0) for c in phase_counts.values())
    total_valid = sum(c.get("VALIDATION", 0) for c in phase_counts.values())
    total_test = sum(c.get("TEST", 0) for c in phase_counts.values())
    total_blind = sum(c.get("BLIND_HOLDOUT", 0) for c in phase_counts.values())
    lines.append(f"| **TOTAL** | **{total_all}** | **{total_train}** | **{total_valid}** | **{total_test}** | **{total_blind}** |")
    lines.append("")
    lines.append(f"(TOTAL should read 129 = 91 TRAIN + 18 VALIDATION + 5 TEST + 15 BLIND_HOLDOUT; "
                  "cfg109/cfg110 sealed, excluded from this count entirely.)")
    lines += [
        "",
        "## Configs that CLOSED an EXTRAPOLATION flag since combined-127",
        "",
    ]
    if closed:
        lines.append("| Phase | Family | Config | Old flag | New flag |")
        lines.append("|---|---|---|---|---|")
        for c in sorted(closed, key=lambda x: (x["phase"], x["family"], x["config_id"])):
            lines.append(f"| {c['phase']} | {c['family']} | {c['config_id']} | {c['old_flag']} | {c['new_flag']} |")
    else:
        lines.append("(none)")
    lines += ["", "## EXTRAPOLATION flags STILL OPEN after round4", ""]
    if still_open:
        lines.append("| Phase | Family | Config | Role | Flag | Detail |")
        lines.append("|---|---|---|---|---|---|")
        for r in sorted(still_open, key=lambda x: (x["phase"], x["family"], x["config_id"])):
            lines.append(f"| {r['phase']} | {r['family']} | {r['config_id']} | {r['role']} | {r['flag']} | {r['detail']} |")
    else:
        lines.append("(none)")
    lines += ["", "## Zero-TRAIN-support buckets remaining (Tier 1 equivalent)", ""]
    if zero_support_buckets:
        for phase, family in zero_support_buckets:
            lines.append(f"- {phase} / {family}")
    else:
        lines.append("(none -- every phase/family bucket now has at least one TRAIN member)")
    lines += ["", "## New flags not present in the combined-127 audit (should not normally happen; investigate if non-empty)", ""]
    if new_flags:
        lines.append("| Phase | Family | Config | Role | Flag | Detail |")
        lines.append("|---|---|---|---|---|---|")
        for r in sorted(new_flags, key=lambda x: (x["phase"], x["family"], x["config_id"])):
            lines.append(f"| {r['phase']} | {r['family']} | {r['config_id']} | {r['role']} | {r['flag']} | {r['detail']} |")
    else:
        lines.append("(none)")
    lines += ["", "## Round4 gap-bucket status (Al3Ni5/biaxial, AlNi3/biaxial)", ""]
    for phase, family in [("Al3Ni5", "biaxial"), ("AlNi3", "biaxial")]:
        bucket_rows = [r for r in out_rows if r["phase"] == phase and r["family"] == family]
        info = next((r for r in bucket_rows if r["flag"] == "INFO_LOW_TRAIN_COUNT"), None)
        lines.append(f"- {phase}/{family}: {info['detail'] if info else 'no INFO_LOW_TRAIN_COUNT row (unexpected)'}")

    OUT_MD.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nRaw CSV: {OUT_CSV}")


if __name__ == "__main__":
    main()
