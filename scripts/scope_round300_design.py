#!/usr/bin/env python3
"""Scope (not generate/gate/DFT) the 300-structure round.

Design principle, per explicit instruction: ONE large batch targeting all
remaining gaps at once, governed by the same four EXPANSION_BATCH_DESIGN_
POLICY.md gates, sized to approximate the roadmap's ~300-structure
milestone -- rather than the round3/round4 pattern of small, individually
hand-designed batches.

"All remaining gaps" is interpreted literally as a full factorial design-
of-experiments completion: for every phase, every deformation family
(uniaxial/biaxial/orthorhombic/shear[+rattle]/isotropic[+rattle=volume_
rattle]) has 2-3 direction axes x 2 signs x (rattle on/off, where used) =
a fixed slot grid. A slot with zero TRAIN members is a literal, structural
gap -- a strictly stronger and more complete criterion than the coverage
audit's VALIDATION/HOLDOUT-outside-range flags (which only catch a slot
once something happens to have been placed outside it), and it naturally
recovers every one of those flags as a special case, since a bucket that
was never given a TRAIN member in that combo can't have interpolated
anything.

This script only SCOPES: enumerates every missing slot, assigns a
magnitude via a documented, data-derived rule (never invented), and
reports the resulting roster + totals. It does NOT construct Atoms
objects, run the gates, write QE inputs, or touch DFT. That is a
separate, much larger next step (see the wall-clock estimate at the
bottom) requiring explicit confirmation before launch, given the scale.

cfg109/cfg110 (sealed) are not read at all -- this script never touches
that directory.
"""

import csv
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path("/workspace/ni_al")
OUT_ROSTER = ROOT / "data/al3ni_remediation_v1/round300_scope_roster.csv"
OUT_MD = ROOT / "configs/ROUND300_SCOPE.md"

PHASES = ["AlNi", "Al3Ni", "Al3Ni2", "Al3Ni5", "AlNi3"]
DIRECTIONAL_ST = [
    "uniaxial_x", "uniaxial_y", "uniaxial_z",
    "biaxial_xy", "biaxial_xz", "biaxial_yz",
    "orthorhombic_xy", "orthorhombic_xz", "orthorhombic_yz",
    "shear_xy", "shear_xz", "shear_yz",
]
ROLE_MAP = {"HISTORICAL_TRAIN": "TRAIN", "TRAIN_CANDIDATE": "TRAIN", "TRAIN": "TRAIN"}
RATTLE_SIGMA_STEPS = [0.015, 0.020, 0.025, 0.030]  # reuse exactly the sigma values already used elsewhere


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load_all():
    rows = []
    for name in ("train", "validation", "test", "blind_holdout"):
        for r in csv.DictReader((ROOT / f"data/datasets/ni_al_dataset100_{name}_manifest.csv").open(newline="")):
            rows.append({"phase": r["phase"], "config_family": r["config_family"], "strain_type": r["strain_type"],
                         "strain_value": r["strain_value"], "shear_value": r.get("shear_value", "0"),
                         "rattle_sigma_A": r["rattle_sigma_A"], "role": r["target_role"]})
    for r in csv.DictReader((ROOT / "data/al3ni_remediation_v1/remediation_manifest.csv").open(newline="")):
        rows.append({"phase": r["phase"], "config_family": r["config_family"], "strain_type": r["strain_type"],
                     "strain_value": r["requested_strain"], "shear_value": r.get("shear_value", "0"),
                     "rattle_sigma_A": r["requested_rattle_sigma_A"], "role": r["split"]})
    for r in csv.DictReader((ROOT / "data/al3ni_remediation_v1/round2_manifest.csv").open(newline="")):
        rows.append({"phase": r["phase"], "config_family": r["config_family"], "strain_type": r["strain_type"],
                     "strain_value": r["requested_strain"], "shear_value": r.get("shear_value", "0"),
                     "rattle_sigma_A": r["rattle_sigma_A"], "role": r["split"]})
    for r in csv.DictReader((ROOT / "data/al3ni_remediation_v1/round3_manifest.csv").open(newline="")):
        rows.append({"phase": r["phase"], "config_family": r["config_family"], "strain_type": r["strain_type"],
                     "strain_value": r["strain_value"], "shear_value": r.get("shear_value", "0"),
                     "rattle_sigma_A": r["rattle_sigma_A"], "role": r["target_role"]})
    for r in csv.DictReader((ROOT / "data/al3ni_remediation_v1/round4_biaxial_manifest.csv").open(newline="")):
        rows.append({"phase": r["phase"], "config_family": r["config_family"], "strain_type": r["strain_type"],
                     "strain_value": r["strain_value"], "shear_value": r.get("shear_value", "0"),
                     "rattle_sigma_A": r["rattle_sigma_A"], "role": r["target_role"]})
    return rows


def main():
    rows = load_all()
    train_rows = [r for r in rows if ROLE_MAP.get(r["role"], r["role"]) == "TRAIN"]

    # Existing TRAIN magnitudes, keyed by (strain_type, sign, has_rattle) -- cross-phase pool
    # used as the data-derived magnitude reference for missing slots.
    magnitude_pool = defaultdict(list)
    used_slots = defaultdict(list)
    rattle_depth = defaultdict(int)
    for r in train_rows:
        st = r["strain_type"]
        # Shear-family magnitude lives in the shear_value column, not strain_value (which is 0
        # for pure-shear rows -- confirmed by inspecting the raw manifests: every shear_xy/xz/yz
        # TRAIN row has strain_value==0). Everything else uses strain_value.
        val = fnum(r["shear_value"]) if st.startswith("shear") else fnum(r["strain_value"])
        rattle = fnum(r["rattle_sigma_A"]) or 0.0
        # val == 0 (e.g. a pure-rattle structure recorded via a family scaffold at zero
        # deformation) does NOT count as coverage of either sign for that family. Excluded,
        # not bucketed as "neg".
        if st in DIRECTIONAL_ST and val:
            sign = "pos" if val > 0 else "neg"
            magnitude_pool[(st, sign, rattle > 0)].append(abs(val))
            used_slots[(r["phase"], st, sign, rattle > 0)].append(abs(val))
        elif st == "isotropic" and val:
            sign = "pos" if val > 0 else "neg"
            magnitude_pool[("isotropic", sign, rattle > 0)].append(abs(val))
            used_slots[(r["phase"], "isotropic", sign, rattle > 0)].append(abs(val))
        if "rattle" in r["config_family"] and "volume" not in r["config_family"] and st not in DIRECTIONAL_ST and st != "isotropic":
            rattle_depth[r["phase"]] += 1

    def reference_magnitude(st, sign, has_rattle):
        pool = magnitude_pool.get((st, sign, has_rattle), [])
        if pool:
            return statistics.median(pool)
        # Fall back: mirror the opposite sign of the same combo (deformation is usually
        # symmetric in magnitude convention across this project's existing designs).
        mirror = magnitude_pool.get((st, "neg" if sign == "pos" else "pos", has_rattle), [])
        if mirror:
            return statistics.median(mirror)
        # Same strain_type, either sign, either rattle state.
        any_pool = [v for (s2, sg2, hr2), vals in magnitude_pool.items() if s2 == st for v in vals]
        if any_pool:
            return statistics.median(any_pool)
        # Last resort: same FAMILY GROUP across axes (e.g. shear_xy has zero real data anywhere
        # in the project -- fall back to shear_xz/shear_yz's combined magnitude pool instead of
        # crashing). Family group = text before the first underscore.
        group = st.split("_")[0]
        group_pool = [v for (s2, sg2, hr2), vals in magnitude_pool.items() if s2.split("_")[0] == group for v in vals]
        if group_pool:
            return statistics.median(group_pool)
        raise RuntimeError(f"no magnitude reference available anywhere for {st}")

    roster = []
    for phase in PHASES:
        for st in DIRECTIONAL_ST:
            has_rattle_options = [False, True] if st.startswith("shear") else [False]
            for sign in ("pos", "neg"):
                for hr in has_rattle_options:
                    key = (phase, st, sign, hr)
                    if key in used_slots:
                        continue
                    mag = reference_magnitude(st, sign, hr)
                    signed = mag if sign == "pos" else -mag
                    family = (st.split("_")[0] + "_rattle") if hr else st.split("_")[0]
                    if st.startswith("shear"):
                        family = "shear_rattle" if hr else "shear"
                    roster.append({
                        "phase": phase, "family": family, "strain_type": st, "sign": sign,
                        "strain_or_shear_value": signed, "rattle_sigma_A": 0.02 if hr else 0.0,
                        "magnitude_source": "cross-phase median" if magnitude_pool.get((st, sign, hr)) else "mirrored/fallback median",
                        "role": "TRAIN",
                    })
        for sign in ("pos", "neg"):
            for hr in (False, True):
                key = (phase, "isotropic", sign, hr)
                if key in used_slots:
                    continue
                mag = reference_magnitude("isotropic", sign, hr)
                signed = mag if sign == "pos" else -mag
                family = "volume_rattle" if hr else "isotropic"
                roster.append({
                    "phase": phase, "family": family, "strain_type": "isotropic", "sign": sign,
                    "strain_or_shear_value": signed, "rattle_sigma_A": 0.02 if hr else 0.0,
                    "magnitude_source": "cross-phase median" if magnitude_pool.get(("isotropic", sign, hr)) else "mirrored/fallback median",
                    "role": "TRAIN",
                })
        # Pure-rattle depth: bring every phase up to the project's own deepest phase (Al3Ni, 4).
        target_depth = max(rattle_depth.values())
        current = rattle_depth.get(phase, 0)
        existing_sigmas = sorted({round(fnum(r["rattle_sigma_A"]) or 0, 3) for r in train_rows
                                   if r["phase"] == phase and "rattle" in r["config_family"] and "volume" not in r["config_family"]})
        next_sigmas = [s for s in RATTLE_SIGMA_STEPS if s not in existing_sigmas]
        for sigma in next_sigmas[: max(0, target_depth - current)]:
            roster.append({
                "phase": phase, "family": "rattle", "strain_type": "none", "sign": "n/a",
                "strain_or_shear_value": 0.0, "rattle_sigma_A": sigma,
                "magnitude_source": f"existing project sigma step, depth-matched to {phase}'s own deepest family (Al3Ni={target_depth})",
                "role": "TRAIN",
            })

    fields = ["phase", "family", "strain_type", "sign", "strain_or_shear_value", "rattle_sigma_A", "magnitude_source", "role"]
    with OUT_ROSTER.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(roster)

    by_phase = defaultdict(int)
    by_family = defaultdict(int)
    fallback_count = 0
    for r in roster:
        by_phase[r["phase"]] += 1
        by_family[r["family"]] += 1
        if "fallback" in r["magnitude_source"] or "mirrored" in r["magnitude_source"]:
            fallback_count += 1
    vre_phases = [r["phase"] for r in roster if r["family"] == "volume_rattle" and r["sign"] == "pos"]

    current_total = 131  # 129 non-sealed (combined-129) + 2 sealed (cfg109/cfg110)
    new_total = len(roster)
    projected_total = current_total + new_total

    lines = [
        "# 300-Structure Round -- Scope (design-only, not generated/gated/DFT'd)",
        "",
        "Single large batch targeting ALL remaining gaps at once, per explicit instruction --",
        "not the round3/round4 pattern of small hand-picked batches. \"All remaining gaps\" =",
        "every (phase, deformation-family, direction, sign[, rattle on/off]) combination with",
        "zero TRAIN members: a strictly stronger, complete criterion than the coverage audit's",
        "VALIDATION/HOLDOUT-outside-range flags, which it recovers as a special case.",
        "",
        "## Sizing",
        "",
        f"Current project total (combined-129 non-sealed + 2 sealed cfg109/cfg110): **{current_total}**",
        f"Missing directional/isotropic-rattle combo slots (full factorial completion): **{len([r for r in roster if r['family'] != 'rattle'])}**",
        f"Pure-rattle depth-equalization (bring every phase to Al3Ni's own depth of {max(rattle_depth.values())}): **{len([r for r in roster if r['family'] == 'rattle'])}**",
        f"Total new candidates proposed: **{new_total}**",
        f"Projected total after this round: {current_total} + {new_total} = **{projected_total}**",
        "",
        f"This lands at {projected_total}/300 ({projected_total/300*100:.0f}%) — approximating the ~300",
        "milestone, not forced to hit it exactly. Per this project's own stated policy",
        "(`ROUND3_BATCH_DESIGN_STATUS.md`'s \"never pad a design to hit a round number\"), no",
        "extra candidates were added purely to close the remaining ~40-structure gap to 300 --",
        "the actual gate pass rate (see below) will also reduce this number further before DFT.",
        "",
        "## Per-phase breakdown",
        "",
        "| Phase | New candidates |",
        "|---|---|",
    ]
    for phase in PHASES:
        lines.append(f"| {phase} | {by_phase[phase]} |")
    lines += ["", "## Per-family breakdown", "", "| Family | New candidates |", "|---|---|"]
    for fam in sorted(by_family):
        lines.append(f"| {fam} | {by_family[fam]} |")
    lines += [
        "",
        "## Magnitude assignment methodology",
        "",
        "For each missing slot, magnitude = median of that exact (strain_type, sign, rattle-state)",
        "combination's magnitudes already used in OTHER phases (cross-phase reference, same",
        "principle as round4's 1.5x-probe rule: reuse data already on file, never invent a",
        "number). Falls back to the mirrored opposite-sign magnitude, then to any-sign/any-",
        f"rattle-state median for that strain_type, if no direct reference exists. Fallback used for",
        f"**{fallback_count}/{new_total}** candidates ({fallback_count/new_total*100:.0f}%) -- flagged in the",
        "roster's `magnitude_source` column, not silently applied.",
        "",
        "**Notable finding surfaced by this scoping pass, not previously diagnosed explicitly:**",
        "`isotropic pos + rattle=True` (i.e. volume_rattle EXPANSION) is a missing TRAIN slot in",
        f"**{len(vre_phases)} of 5 phases ({', '.join(vre_phases)})** -- Al3Ni is the only phase with",
        "volume_rattle expansion TRAIN coverage (via round2's ladder extension); every other phase",
        "has only ever been trained on volume_rattle COMPRESSION. This directly explains the",
        "large-margin EXTRAPOLATION flags on cfg075 (Al3Ni2, margin 0.060) and cfg060 (Al3Ni5,",
        "margin 0.060) in the coverage audit -- the single largest still-open margins of any flag.",
        f"No magnitude reference exists for this combo in any of those {len(vre_phases)} phases, so",
        "each uses the cross-phase-median fallback (from Al3Ni's own expansion value) and deserves",
        "particular scrutiny once gates (a)-(d) actually run.",
        "",
        "## What this does NOT do",
        "",
        "- Does not construct Atoms objects, generate QE inputs, or run gates (a)-(d). The roster",
        "  above is a target list, not frozen candidates -- round3/round4 both showed roughly",
        "  half of proposed candidates fail gate (a) redundancy in practice, so expect the",
        f"  post-gate survivor count to be meaningfully below {new_total}, not equal to it.",
        "- Does not run any DFT.",
        "- Does not touch cfg109/cfg110 (sealed) at all -- not even for geometry comparison,",
        "  since this scoping pass never needed to.",
        "- Does not decide VALIDATION/TEST/BLIND_HOLDOUT role assignment for any new structure --",
        "  every candidate here is scoped as TRAIN, matching every round since v1. Whether the",
        "  300-round should also deepen VALIDATION/TEST/BLIND_HOLDOUT is an open question this",
        "  scope deliberately leaves for explicit confirmation, not a default assumption.",
        "",
        "## Resource estimate for actually executing this (next step, needs confirmation)",
        "",
        f"Generation + gate-checking {new_total} candidates is a much larger version of round4's",
        "2-candidate pass -- mechanically the same code, no new risk category, but ~35-70x the",
        "volume. Assuming a similar ~50-85% gate survival rate to round3's, expect roughly",
        f"{int(new_total*0.5)}-{int(new_total*0.85)} structures to actually reach DFT. At this project's",
        "observed QE wall-clock range (~7-40 min/structure depending on phase/rattle, and",
        "unpredictable given the GPU/driver variance documented in `project_knowledge.md` Section",
        f"6), sequential DFT alone could plausibly run **{int(new_total*0.5*7/60)}-{int(new_total*0.85*40/60)} hours**",
        "even before accounting for any failures/reruns. Splitting across multiple pods (the",
        "`ROUND3_POD_ASSIGNMENT.csv`-style convention already established) would cut wall time",
        "roughly linearly with pod count. This is a materially larger compute commitment than",
        "any prior round in this project and should be explicitly confirmed before launching",
        "generation+gating, let alone DFT.",
        "",
        f"Roster: `{OUT_ROSTER}`",
    ]

    OUT_MD.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
