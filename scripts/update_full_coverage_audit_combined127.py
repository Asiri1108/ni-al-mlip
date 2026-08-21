#!/usr/bin/env python3
"""Update the full coverage / extrapolation-ceiling audit for combined-127.

Reconstruction, not a rerun of the original script: no saved script was
found for `results/full_coverage_audit_v1` (produced inline in a prior
session). This reproduces its documented, mechanical method --
per (phase, deformation-family) TRAIN axis range vs every VALIDATION/
TEST/BLIND_HOLDOUT member's axis value -- from the same manifests and the
same documented conventions (config_type-name-decoded Pilot-25 iso_m02/
iso_p02 strain; rattle_003/shear015_rattle002 marked
METADATA_GAP_NOT_EVALUABLE, unrecoverable from the frozen manifest).

NOT reproduced: the original's "local density" nearest-same-phase-TRAIN-
neighbor descriptor-distance analysis (shape RMSD + Green-Lagrange strain,
z-scored per phase). That method's exact implementation was not found on
disk and is not fully specified in the surviving report text -- guessing
at it risks a confident-looking but unverified number. Flagged, not
silently skipped.

cfg109/cfg110 (sealed) are excluded entirely -- never loaded, geometry or
labels.
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path("/workspace/ni_al")
OUT_CSV = ROOT / "results/full_coverage_audit_v1/coverage_ceiling_report_combined127.csv"
OUT_MD = ROOT / "results/full_coverage_audit_v1/priority_ranking_combined127.md"
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


def load_dataset100(role_col_index_map=None):
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


def main():
    all_rows = load_dataset100() + load_remediation_v1() + load_round2() + load_round3()
    all_rows = [r for r in all_rows if r["family"] != "relaxed" and not r["family"].startswith("OTHER:")]

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

    # Compare vs the original combined-113 audit's flag set to show what round3 changed.
    orig_path = ROOT / "results/full_coverage_audit_v1/coverage_ceiling_report.csv"
    orig_rows = list(csv.DictReader(orig_path.open(newline=""))) if orig_path.exists() else []
    orig_key_flag = {(r["phase"], r["family"], r["config_id"]): r["flag"] for r in orig_rows}

    closed, still_open, new_flags = [], [], []
    for r in out_rows:
        key = (r["phase"], r["family"], r["config_id"])
        if r["flag"] in ("EXTRAPOLATION_NO_TRAIN_SUPPORT", "EXTRAPOLATION"):
            if key in orig_key_flag and orig_key_flag[key] in ("EXTRAPOLATION_NO_TRAIN_SUPPORT", "EXTRAPOLATION"):
                still_open.append(r)
            else:
                new_flags.append(r)
    for key, old_flag in orig_key_flag.items():
        if old_flag not in ("EXTRAPOLATION_NO_TRAIN_SUPPORT", "EXTRAPOLATION"):
            continue
        match = next((r for r in out_rows if (r["phase"], r["family"], r["config_id"]) == key), None)
        if match is None or match["flag"] not in ("EXTRAPOLATION_NO_TRAIN_SUPPORT", "EXTRAPOLATION"):
            closed.append({"phase": key[0], "family": key[1], "config_id": key[2], "old_flag": old_flag,
                            "new_flag": match["flag"] if match else "NOT_PRESENT_IN_RECONSTRUCTION"})

    zero_support_buckets = sorted({(r["phase"], r["family"]) for r in out_rows if r["flag"] == "EXTRAPOLATION_NO_TRAIN_SUPPORT"})

    lines = [
        "# Full Coverage / Extrapolation-Ceiling Audit -- Updated for Combined-127",
        "",
        "**Reconstruction, not a verified rerun** -- see script docstring "
        "(`scripts/update_full_coverage_audit_combined127.py`) for exactly what was and wasn't reproduced "
        "from the original `priority_ranking.md`/`coverage_ceiling_report.csv`. The TRAIN-range/zero-support "
        "mechanical method is reproduced from documented conventions; the geometry-descriptor \"local density\" "
        "analysis is NOT reproduced (original script not found on disk).",
        "",
        "cfg109/cfg110 excluded (sealed, untouched, never loaded).",
        "",
        "## Configs that CLOSED an EXTRAPOLATION flag since the original audit",
        "",
    ]
    if closed:
        lines.append("| Phase | Family | Config | Old flag | New flag |")
        lines.append("|---|---|---|---|---|")
        for c in sorted(closed, key=lambda x: (x["phase"], x["family"], x["config_id"])):
            lines.append(f"| {c['phase']} | {c['family']} | {c['config_id']} | {c['old_flag']} | {c['new_flag']} |")
    else:
        lines.append("(none)")
    lines += ["", "## EXTRAPOLATION flags STILL OPEN after round3", ""]
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
    lines += ["", "## New flags not present in the original audit (should not normally happen; investigate if non-empty)", ""]
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
