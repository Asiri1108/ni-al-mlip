#!/usr/bin/env python3
"""Outlier review for Round-300 DFT labels (82 configs).

Two screens: self-population (Pilot-25 method, now meaningful at n=82,
run per-phase since phases aren't comparable on raw force/stress
magnitude) and phase-context percentile vs combined-129.
"""

from pathlib import Path
from collections import defaultdict

import numpy as np
from ase.io import read

ROOT = Path("/workspace/ni_al")
ROUND300 = ROOT / "data/al3ni_remediation_v1/round300_dft.extxyz"
CONTEXT_TRAIN = ROOT / "data/datasets/ni_al_combined129_train_91.extxyz"
CONTEXT_VALID = ROOT / "data/datasets/ni_al_combined129_validation_18.extxyz"
REPORT = ROOT / "data/al3ni_remediation_v1/round300_dft_outlier_review.txt"


def metrics_row(atoms):
    forces = np.asarray(atoms.get_forces(), dtype=float)
    stress = np.asarray(atoms.get_stress(voigt=True), dtype=float)
    return {
        "fmax": float(np.linalg.norm(forces, axis=1).max()),
        "frms": float(np.sqrt(np.mean(forces**2))),
        "stress_mag": float(np.linalg.norm(stress)),
    }


def robust_high_outliers(values):
    array = np.asarray(list(values.values()), dtype=float)
    median = float(np.median(array))
    mad = float(np.median(np.abs(array - median)))
    if mad == 0.0:
        return []
    threshold = median + 8.0 * 1.4826 * mad
    return sorted(key for key, value in values.items() if value > threshold)


def percentile_rank(value, population):
    population = np.asarray(population, dtype=float)
    return float((population < value).sum()) / len(population) * 100.0


def main():
    frames = read(ROUND300, index=":")
    context = read(CONTEXT_TRAIN, index=":") + read(CONTEXT_VALID, index=":")

    context_by_phase = defaultdict(list)
    for a in context:
        context_by_phase[a.info["phase"]].append(metrics_row(a))

    by_phase = defaultdict(list)
    for a in frames:
        m = metrics_row(a)
        m["config_id"] = a.info["config_id"]
        by_phase[a.info["phase"]].append(m)

    lines = ["ROUND-300 DFT OUTLIER REVIEW (forces/stresses)", "=" * 46,
             f"Dataset: {ROUND300}", f"Frames screened: {len(frames)}", ""]

    lines += ["SCREEN 1: SELF-POPULATION PER PHASE (median + 8*1.4826*MAD, Pilot-25 method)", "-" * 78]
    self_flags_all = []
    for phase in sorted(by_phase):
        rows = by_phase[phase]
        fmax_values = {r["config_id"]: r["fmax"] for r in rows}
        frms_values = {r["config_id"]: r["frms"] for r in rows}
        stress_values = {r["config_id"]: r["stress_mag"] for r in rows}
        flags = {
            "maximum force": robust_high_outliers(fmax_values),
            "RMS force": robust_high_outliers(frms_values),
            "stress magnitude": robust_high_outliers(stress_values),
        }
        lines.append(f"{phase} (n={len(rows)}):")
        for metric, fl in flags.items():
            if fl:
                lines.append(f"  {metric}: {', '.join(fl)}")
                self_flags_all.extend(fl)
        if not any(flags.values()):
            lines.append("  none")
    lines.append("")
    lines.append("Rule: median + 8 * 1.4826 * MAD, per-phase population. Advisory only.")

    lines += ["", "SCREEN 2: PHASE-CONTEXT PERCENTILE (vs combined-129 TRAIN+VALIDATION)", "-" * 78]
    lines.append(f"{'config_id':<42s} {'phase':<8s} {'ctx_n':>5s} {'Fmax_pct':>9s} {'Frms_pct':>9s} {'stress_pct':>10s}")
    context_flags = []
    for phase in sorted(by_phase):
        for r in by_phase[phase]:
            pop = context_by_phase.get(phase, [])
            fmax_pct = percentile_rank(r["fmax"], [p["fmax"] for p in pop])
            frms_pct = percentile_rank(r["frms"], [p["frms"] for p in pop])
            stress_pct = percentile_rank(r["stress_mag"], [p["stress_mag"] for p in pop])
            lines.append(f"{r['config_id']:<42s} {phase:<8s} {len(pop):>5d} {fmax_pct:>8.1f}% {frms_pct:>8.1f}% {stress_pct:>9.1f}%")
            if fmax_pct >= 95.0 or frms_pct >= 95.0 or stress_pct >= 95.0:
                context_flags.append(r["config_id"])

    lines.append("")
    lines.append("Context flags (>=95th percentile of phase's combined-129 TRAIN+VALIDATION population): "
                 + (", ".join(sorted(set(context_flags))) if context_flags else "none"))
    lines.append("")
    lines.append("This batch fills previously-EMPTY combo slots (new directions/signs, not ceiling")
    lines.append("extensions like round3), so high percentile rank is NOT automatically expected here")
    lines.append("the way it was for round3's outer candidates -- flagged configs deserve a real look,")
    lines.append("not an automatic 'by design' dismissal.")
    lines.append("")
    lines.append("Advisory only; no configuration removed or altered.")

    REPORT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
